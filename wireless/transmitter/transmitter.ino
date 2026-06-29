/*
 * transmitter.ino
 *
 * ESP32 firmware for the SBUS *transmitter* node (tethered to the PC).
 *
 * Receives channel values from the host GUI over USB serial, then forwards
 * them to the receiver node over ESP-NOW. This replaces the host-side leg of
 * the old wired bridge; the SBUS output now lives on the receiver node.
 *
 * Link:   host --(USB serial)--> transmitter --(ESP-NOW)--> receiver
 *
 * Serial packet format (host -> ESP32):
 *   <CH1,CH2,CH3,CH5,CH6>
 *   All values in the range [1000, 2000] microseconds.
 *
 * ESP-NOW payload: SbusPacket (see esp_now_link.h), 16 channel values.
 *
 * By default packets are broadcast (FF:FF:FF:FF:FF:FF) so the link works
 * without knowing the receiver's MAC. To pin the link to one receiver, set
 * RECEIVER_MAC below to the address printed by the receiver on boot.
 *
 * Dependencies: esp_now / WiFi  (bundled with the ESP32 Arduino core)
 */

#include <esp_now.h>
#include <WiFi.h>
#include "esp_now_link.h"

// Destination MAC. Broadcast by default; replace with the receiver's MAC
// (printed over serial when the receiver boots) to pin the link.
uint8_t RECEIVER_MAC[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

// Resend the latest channel values at least this often (ms) so the receiver's
// failsafe stays satisfied even when the host sends no updates.
static const uint32_t HEARTBEAT_MS = 50;

uint16_t userChannels[16];
uint32_t lastSendMs = 0;

void sendChannels() {
  SbusPacket packet;
  for (int i = 0; i < 16; i++) {
    packet.ch[i] = userChannels[i];
  }
  esp_now_send(RECEIVER_MAC, (uint8_t *)&packet, sizeof(packet));
  lastSendMs = millis();
}

void setup() {
  Serial.begin(115200);

  // Default all channels to neutral
  for (int i = 0; i < 16; i++) {
    userChannels[i] = 1500;
  }

  // Override channels that need non-neutral safe defaults
  userChannels[0] = 1500;  // CH1: yaw      (neutral)
  userChannels[1] = 1500;  // CH2: pitch    (neutral)
  userChannels[2] = 1000;  // CH3: throttle (minimum - do not arm at neutral)
  userChannels[4] = 1500;  // CH5: trim 1   (neutral)
  userChannels[5] = 1500;  // CH6: trim 2   (neutral)
  userChannels[7] = 1800;  // CH8: throttle lock (armed position)

  // ESP-NOW runs on Wi-Fi in station mode, disconnected from any AP
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  Serial.print("Transmitter MAC: ");
  Serial.println(WiFi.macAddress());

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed");
    return;
  }

  // Register the receiver (or broadcast address) as a peer
  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, RECEIVER_MAC, 6);
  peer.channel = 0;       // use the current Wi-Fi channel
  peer.encrypt = false;
  if (esp_now_add_peer(&peer) != ESP_OK) {
    Serial.println("Failed to add ESP-NOW peer");
    return;
  }
  Serial.println("ESP-NOW transmitter ready");
}

void loop() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    // Packet format: <v0,v1,v2,v3,v4,v5>
    if (command.startsWith("<") && command.endsWith(">")) {
      String data = command.substring(1, command.length() - 1);

      // Map the 6 incoming values to their respective (non-contiguous) SBUS indices
      int targetChannels[] = {0, 1, 2, 4, 5, 7};
      int commaIndex = 0;
      int startIndex = 0;
      int idx = 0;

      while ((commaIndex = data.indexOf(',', startIndex)) != -1 && idx < 5) {
        int val = data.substring(startIndex, commaIndex).toInt();
        userChannels[targetChannels[idx]] = constrain(val, 1000, 2000);
        startIndex = commaIndex + 1;
        idx++;
      }
      // Parse the final value after the last comma
      if (idx <= 5 && startIndex < data.length()) {
        int val = data.substring(startIndex).toInt();
        userChannels[targetChannels[idx]] = constrain(val, 1000, 2000);
      }

      // Push the updated values out over ESP-NOW immediately
      sendChannels();

      // Echo parsed values for debugging
      Serial.print("yaw(CH1):");      Serial.println(userChannels[0]);
      Serial.print("pitch(CH2):");    Serial.println(userChannels[1]);
      Serial.print("throttle(CH3):"); Serial.println(userChannels[2]);
      Serial.print("trim1(CH5):");    Serial.println(userChannels[4]);
      Serial.print("trim2(CH6):");    Serial.println(userChannels[5]);
      Serial.print("thr_lock(CH8):"); Serial.println(userChannels[7]);
      Serial.println();
    }
  }

  // Heartbeat: resend periodically so the receiver's failsafe stays satisfied
  if (millis() - lastSendMs >= HEARTBEAT_MS) {
    sendChannels();
  }
}
