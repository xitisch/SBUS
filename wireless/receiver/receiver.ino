/*
 * receiver.ino
 *
 * ESP32 firmware for the SBUS *receiver* node (mounted on the robot).
 * Receives channel values from the transmitter over ESP-NOW and forwards
 * them to the robot as an SBUS signal on Serial2 (GPIO17, inverted, 100k 8E2).
 *
 * Failsafe: if no packet arrives within LINK_TIMEOUT_MS the output drops to a
 * safe state (throttle minimum, SBUS failsafe flag set) until the link recovers.
 */

#include <esp_now.h>
#include <WiFi.h>
#include <esp_mac.h>
#include "sbus.h"
#include "esp_now_link.h"

// SBUS TX on Serial2, GPIO17, inverted signal (SBUS uses active-low logic)
bfs::SbusTx sbus(&Serial2, 16, 17, true);

uint16_t userChannels[16];

// Link-state, updated from the ESP-NOW receive callback
volatile uint32_t lastPacketMs = 0;
volatile bool linkActive = false;
volatile bool packetReceived = false;

// Safe channel values: used at startup and when the link is lost.
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
  packetReceived = true;
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

  // Read MAC from efuse (WiFi.macAddress() returns zeros on core v3.x here)
  uint8_t mac[6];
  esp_read_mac(mac, ESP_MAC_WIFI_STA);
  Serial.printf("Receiver MAC: %02X:%02X:%02X:%02X:%02X:%02X\n",
                mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

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

  // Debug: print channels when a new packet arrives and a value changed
  if (packetReceived) {
    packetReceived = false;

    static uint16_t lastPrinted[16] = {0};
    int dbg[] = {0, 1, 2, 4, 5, 7};  // CH1,CH2,CH3,CH5,CH6,CH8
    bool changed = false;
    for (int k = 0; k < 6; k++)
      if (userChannels[dbg[k]] != lastPrinted[dbg[k]]) changed = true;

    if (changed) {
      Serial.print("RX  yaw(CH1):");    Serial.print(userChannels[0]);
      Serial.print("  pitch(CH2):");    Serial.print(userChannels[1]);
      Serial.print("  thr(CH3):");      Serial.print(userChannels[2]);
      Serial.print("  trim1(CH5):");    Serial.print(userChannels[4]);
      Serial.print("  trim2(CH6):");    Serial.print(userChannels[5]);
      Serial.print("  thr_lock(CH8):"); Serial.println(userChannels[7]);
      for (int k = 0; k < 6; k++) lastPrinted[dbg[k]] = userChannels[dbg[k]];
    }
  }

  // Build and send the SBUS frame
  bfs::SbusData sbusData;
  for (int i = 0; i < 16; i++) {
    // Map RC microseconds [1000, 2000] to SBUS counts [172, 1811], matching a
    // standard SBUS receiver. CH8 throttle lock: 2000 -> 1811 (unlocked),
    // 1000 -> 172 (locked). This mapping is the tested-correct configuration.
    sbusData.ch[i] = map(userChannels[i], 1000, 2000, 172, 1811);
  }
  sbusData.lost_frame = false;
  sbusData.failsafe   = !linkActive;
  sbusData.ch17       = false;
  sbusData.ch18       = false;

  sbus.data(sbusData);
  sbus.Write();

  delay(14);  // ~14ms matches the standard SBUS frame interval
}