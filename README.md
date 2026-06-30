# SBUS Controller for a Flapping-Wing Robot

A host GUI sends control-channel values to an ESP32, which drives the robot's
flight controller over a standard **SBUS** signal. The repo contains two
variants of the link:

- **`wired/`** — the original single-board bridge. The PC talks to one ESP32
  over USB serial, and that ESP32 outputs SBUS directly to the robot.
- **`wireless/`** — a two-board ESP-NOW link. The PC talks to a transmitter
  ESP32, which relays the channels wirelessly to a receiver ESP32 on the robot
  that outputs the SBUS signal.

Both variants speak the same host protocol, so `gui.py` is functionally
identical in each: it just sends `<CH1,CH2,CH3,CH5,CH6>` over USB serial.

```
            wired/                                 wireless/

 PC (gui.py)                            PC (gui.py)
    │ USB serial <CH1,..>                  │ USB serial <CH1,..>
    ▼                                      ▼
 ESP32 ──SBUS──▶ robot          ESP32 transmitter ──ESP-NOW──▶ ESP32 receiver
                                                                   │ SBUS
                                                                   ▼
                                                                 robot
```

## Repository layout

```
.
├── wired/
│   ├── SBUS.ino                  # single ESP32: USB serial -> SBUS output
│   └── gui.py                    # Tkinter slider GUI
├── wireless/
│   ├── transmitter/
│   │   ├── transmitter.ino       # USB serial -> ESP-NOW   (PC-tethered node)
│   │   └── esp_now_link.h        # shared ESP-NOW payload definition
│   ├── receiver/
│   │   ├── receiver.ino          # ESP-NOW -> SBUS output  (robot node)
│   │   └── esp_now_link.h        # identical copy of the payload definition
│   └── gui.py                    # Tkinter slider GUI (same as wired/gui.py)
├── README.md
└── .gitignore
```

> The two `wireless/.../esp_now_link.h` files are intentional duplicates:
> Arduino sketch folders are self-contained. Keep them identical so the
> `SbusPacket` struct stays binary compatible across both nodes.

## Channels (both variants)

| Value sent | SBUS index | Channel | Function            | Safe default |
|------------|-----------:|---------|---------------------|-------------:|
| 1          | 0          | CH1     | Yaw                 | 1500         |
| 2          | 1          | CH2     | Pitch               | 1500         |
| 3          | 2          | CH3     | Throttle            | 1000 (min)   |
| 4          | 4          | CH5     | Trim 1              | 1500         |
| 5          | 5          | CH6     | Trim 2              | 1500         |
| —          | 7          | CH8     | Throttle lock / arm | 1800 (armed) |

All values are in microseconds, range `[1000, 2000]`. CH8 is set in firmware and
is not exposed in the GUI.

## Common setup

- Install the **ESP32 Arduino core** (Boards Manager) and the
  **bolderflight/sbus** library (Library Manager). `esp_now` and `WiFi` ship
  with the ESP32 core.
- `pip install pyserial` for the GUI.
- SBUS output is on **GPIO17 (TX)**, inverted, 100kbaud / 8E2 — wire it to the
  flight controller's SBUS input with a common ground.

---

## Wired variant (`wired/`)

The original setup: one ESP32 between the PC and the robot.

1. Flash `wired/SBUS.ino` to the ESP32.
2. Wire the ESP32's GPIO17 to the robot's SBUS input.
3. Run the GUI:
   ```bash
   python wired/gui.py
   ```

The GUI auto-detects the ESP32's USB-serial port and exposes a slider per
channel; moving a slider sends a packet that the ESP32 converts straight to SBUS.

---

## Wireless variant (`wireless/`)

Two ESP32s linked over ESP-NOW. Hardware: 2× ESP32 dev boards, SBUS from the
**receiver** node to the robot, USB from the PC to the **transmitter** node.

### Build & flash (Arduino IDE)

1. Open `wireless/receiver/receiver.ino`, select your ESP32 board, and flash the
   **robot** node. Open the Serial Monitor at 115200 baud and note the
   `Receiver MAC` it prints on boot.
2. (Optional but recommended) In `wireless/transmitter/transmitter.ino`, set
   `RECEIVER_MAC` to that address to pin the link to one receiver. Left at the
   default broadcast address, the link still works without any MAC setup.
3. Open `wireless/transmitter/transmitter.ino`, select the board, and flash the
   **PC-tethered** node. Close the Serial Monitor afterward so the GUI can claim
   the port.

### Run the GUI

```bash
python wireless/gui.py
```

The GUI auto-detects the transmitter's USB-serial port (prompting if several
candidates are found) and exposes a slider per channel. Moving a slider sends a
packet to the transmitter, which forwards it over ESP-NOW.

### Failsafe

The transmitter resends the latest channel values every ~50 ms (heartbeat). If
the receiver hears nothing for `LINK_TIMEOUT_MS` (500 ms, see `esp_now_link.h`)
it engages failsafe: throttle to minimum, throttle lock disarmed, and the SBUS
`failsafe` flag is set until the link recovers.
