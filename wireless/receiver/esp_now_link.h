/*
 * esp_now_link.h
 *
 * Shared definition of the ESP-NOW payload exchanged between the SBUS
 * transmitter and receiver nodes.
 *
 * NOTE: Arduino sketch folders are self-contained, so an identical copy of
 * this file lives in both firmware/transmitter/ and firmware/receiver/.
 * If you change the payload, update BOTH copies so the structs stay binary
 * compatible.
 */

#ifndef ESP_NOW_LINK_H
#define ESP_NOW_LINK_H

#include <stdint.h>

// Channel payload sent over ESP-NOW. Values are in microseconds [1000, 2000].
// 16 channels mirror the SBUS frame; unused channels carry their neutral/safe
// defaults filled in by the transmitter.
typedef struct __attribute__((packed)) {
  uint16_t ch[16];
} SbusPacket;

// If no packet is received within this window the receiver engages failsafe.
static const uint32_t LINK_TIMEOUT_MS = 500;

#endif  // ESP_NOW_LINK_H
