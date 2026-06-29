"""
gui.py

Tkinter GUI for sending SBUS channel values to the transmitter ESP32 over USB
serial. The transmitter relays them over ESP-NOW to the receiver ESP32, which
drives the robot's SBUS input. Each slider maps to one SBUS channel; moving any
slider immediately transmits a packet to the transmitter firmware.

Serial packet format:  <CH1,CH2,CH3,CH5,CH6>\n
All values in range [1000, 2000].

Usage:
    python gui.py
    The script auto-detects the transmitter's serial port.  If multiple
    candidates are found, a small picker dialog appears first.
"""

import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports
import time

BAUD_RATE = 115200

# USB-serial chip substrings found in ESP32/Arduino port descriptions
_KNOWN_CHIPS = ('cp210', 'ch340', 'ch341', 'ftdi', 'uart', 'arduino', 'esp')


def select_port():
    """Return a serial port device string, auto-detecting or prompting the user.

    Filters available ports by known USB-serial chip names.  If exactly one
    candidate is found it is returned immediately.  If multiple are found a
    small picker dialog is shown.  Returns None if no ports are available.
    """
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        return None

    matches = [p for p in ports
               if any(kw in (p.description or '').lower() for kw in _KNOWN_CHIPS)]
    candidates = matches or ports   # fall back to all ports if no keyword hit

    if len(candidates) == 1:
        return candidates[0].device

    # Multiple candidates — show a blocking picker before the main window
    picker = tk.Tk()
    picker.title("Select Serial Port")
    picker.geometry("440x110")
    picker.resizable(False, False)

    tk.Label(picker, text="Multiple ports found. Select the ESP32 port:").pack(pady=8)

    labels  = [f"{p.device}  —  {p.description}" for p in candidates]
    devices = [p.device for p in candidates]
    var = tk.StringVar(value=labels[0])
    ttk.Combobox(picker, textvariable=var, values=labels,
                 state='readonly', width=55).pack(padx=20)

    chosen = [devices[0]]

    def confirm():
        chosen[0] = devices[labels.index(var.get())]
        picker.destroy()

    tk.Button(picker, text="Connect", command=confirm).pack(pady=8)
    picker.mainloop()
    return chosen[0]


SERIAL_PORT = select_port()

try:
    if SERIAL_PORT is None:
        raise OSError("No serial ports found")
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print(f"Connected to {SERIAL_PORT}")
    time.sleep(2)   # ESP32 resets on USB connect; wait for it to finish booting
except Exception as e:
    print(f"Could not open serial port: {e}")
    ser = None


def send_channels(*_):
    """Read all five sliders and send one packet to the ESP32."""
    if not (ser and ser.is_open):
        return

    try:
        ch1 = int(slider_ch1.get())
        ch2 = int(slider_ch2.get())
        ch3 = int(slider_ch3.get())
        ch5 = int(slider_ch5.get())
        ch6 = int(slider_ch6.get())
    except NameError:
        # Called before all sliders exist (tkinter fires command during widget creation)
        return

    cmd = f"<{ch1},{ch2},{ch3},{ch5},{ch6}>\n"
    try:
        ser.write(cmd.encode('utf-8'))
        label_status.config(text=f"Sent: {cmd.strip()}", fg="green")
    except Exception:
        label_status.config(text="Send failed", fg="red")


def create_slider(label_text, default_val, min_val=1000, max_val=2000):
    """Add a labeled horizontal slider row to root and return the Scale widget."""
    frame = tk.Frame(root)
    frame.pack(fill='x', padx=20, pady=5)

    tk.Label(frame, text=label_text, width=16, anchor='w').pack(side='left')

    val_lbl = tk.Label(frame, text=str(default_val), width=5)
    val_lbl.pack(side='right')

    slider = ttk.Scale(frame, from_=min_val, to=max_val, orient='horizontal')
    slider.set(default_val)
    slider.pack(side='left', fill='x', expand=True, padx=5)

    # Default-argument capture prevents the late-binding closure pitfall
    slider.config(
        command=lambda v, vl=val_lbl: [vl.config(text=str(int(float(v)))), send_channels()]
    )
    return slider


root = tk.Tk()
root.title("Flapping-Wing SBUS Controller")
root.geometry("480x380")

tk.Label(root, text="ESP32 Flapping-Wing Controller", font=("Arial", 14, "bold")).pack(pady=10)

slider_ch1 = create_slider("Yaw      (CH1):", 1500)
slider_ch2 = create_slider("Pitch    (CH2):", 1500)
slider_ch3 = create_slider("Throttle (CH3):", 1000)   # start at minimum; do not arm at neutral
slider_ch5 = create_slider("Trim 1   (CH5):", 1500)
slider_ch6 = create_slider("Trim 2   (CH6):", 1500)

port_text = SERIAL_PORT if SERIAL_PORT else "No port"
label_status = tk.Label(root, text=f"Connected: {port_text}", bd=1, relief='sunken', anchor='w')
label_status.pack(side='bottom', fill='x', padx=10, pady=10)

root.mainloop()

# Release the port after the window closes
if ser and ser.is_open:
    ser.close()
    print("Serial port closed")
