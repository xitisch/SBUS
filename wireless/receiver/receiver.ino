/*
 * receiver.ino
 *
 * ESP32 firmware for the SBUS *receiver* node (mounted on the robot).
 *
 * Receives channel values from the transmitter node over ESP-NOW and
 * forwards them to the flapping-wing robot as an SBUS signal on Serial2.
 * This is the wireless counterpart of the old wired SBUS bridge: the USB
 * serial parsing now lives on the transmitter, and this node only consumes
 * ESP-NOW packets and drives the SBUS output.
 *
 * Link:   transmitter --(ESP-NOW)--> receiver --(SBUS)--> robot
 *
 * ESP-NOW payload: SbusPacket (see esp_now_link.h), 16 channel values.
 * SBUS hardware:   GPIO17 (TX), inverted logic, 100kbaud, 8E2.
 *
 * Failsafe: if no packet arrives within LINK_TIMEOUT_MS the output drops to
 * a safe state (throttle minimum, SBUS failsafe flag set) until the link
 * recovers.
 *
 * Dependencies: bolderflight/sbus  (provides sbus.h / bfs::SbusTx)
 *               esp_now / WiFi      (bundled with the ESP32 Arduino core)
 */

#include <esp_now.h>
#include <WiFi.h>
#include "sbus.h"
#include "esp_now_link.h"

// SBUS TX on Serial2, GPIO17, inverted signal (SBUS uses active-low logic)
bfs::SbusTx sbus(&Serial2, 16, 17, true);

uint16_t userChannels[16];

// Timestamp of the most recently received ESP-NOW packet, for the failsafe.
volatile uint32_t lastPacketMs = 0;
volatile bool linkActive = false;

// Load the safe channel values used at startup and when the link is lost.
void applyFailsafe() {
  for (int i = 0; i < 16; i++) {
    userChannels[i] = 1500;
  }
  userChannels[2] = 1000;  // CH3: throttle to minimum
  userChannels[7] = 1000;  // CH8: throttle lock disarmed
}

// ESP-NOW receive callback. Signature matches the ESP32 Arduino core (3.x).
void onDataRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  if (len != sizeof(SbusPacket)) {
    return;  // ignore malformed / foreign packets
  }
  SbusPacket packet;
  memcpy(&packet, data, sizeof(packet));

  for (int i = 0; i < 16; i++) {
    userChannels[i] = constrain(packet.ch[i], 1000, 2000);
  }
  lastPacketMs = millis();
  linkActive = true;
}

void setup() {
  Serial.begin(115200);

  // SBUS requires 100kbaud, 8-bit, Even parity, 2 stop bits, inverted
  Serial2.begin(100000, SERIAL_8E2, 16, 17, true);

  // Start in the failsafe state until the first packet arrives
  applyFailsafe();

  // ESP-NOW runs on Wi-Fi in station mode, disconnected from any AP
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  Serial.print("Receiver MAC: ");
  Serial.println(WiFi.macAddress());  // note this address for the transmitter

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed");
    return;
  }
  esp_now_register_recv_cb(onDataRecv);
  Serial.println("ESP-NOW receiver ready");
}

void loop() {
  // Failsafe: if the link goes quiet, force the safe channel values
  if (linkActive && (millis() - lastPacketMs > LINK_TIMEOUT_MS)) {
    linkActive = false;
    applyFailsafe();
    Serial.println("Link lost - failsafe engaged");
  }

  // Build and send the SBUS frame
  bfs::SbusData sbusData;
  for (int i = 0; i < 16; i++) {
    sbusData.ch[i] = userChannels[i];
  }
  sbusData.lost_frame = false;
  sbusData.failsafe   = !linkActive;
  sbusData.ch17       = false;
  sbusData.ch18       = false;

  sbus.data(sbusData);
  sbus.Write();

  delay(14);  // ~14ms matches the standard SBUS frame interval
}
