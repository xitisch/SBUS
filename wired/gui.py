"""
gui.py

Tkinter GUI for sending SBUS channel values to the ESP32 over USB serial.
Each slider maps to one SBUS channel; moving any slider immediately
transmits a packet to the firmware.

Serial packet format:  <CH1,CH2,CH3,CH5,CH6>\n
All values in range [1000, 2000].

Usage:
    python gui.py
    The script auto-detects the ESP32 serial port.  If multiple candidates
    are found, a small picker dialog appears first.
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
    """Read the five sliders plus the CH8 toggle and send one packet to the ESP32."""
    if not (ser and ser.is_open):
        return

    try:
        ch1 = int(slider_ch1.get())
        ch2 = int(slider_ch2.get())
        ch3 = int(slider_ch3.get())
        ch5 = int(slider_ch5.get())
        ch6 = int(slider_ch6.get())
        ch8 = int(ch8_var.get())
    except NameError:
        # Called before the widgets exist (tkinter fires command during widget creation)
        return

    cmd = f"<{ch1},{ch2},{ch3},{ch5},{ch6},{ch8}>\n"
    try:
        ser.write(cmd.encode('utf-8'))
        label_status.config(text=f"Sent: {cmd.strip()}", fg="green")
    except Exception:
        label_status.config(text="Send failed", fg="red")


def create_slider(label_text, default_val, min_val=1000, max_val=2000,
                  label_font=("Arial", 11), value_font=("Arial", 11),
                  label_width=14, pady=6):
    """Add a labeled horizontal slider row to root and return the Scale widget.

    The value box is an editable Entry: dragging the slider updates the box,
    and typing a value then pressing Enter moves the slider to that value.
    Fonts and padding are parameterized so the primary flight controls can be
    rendered larger than the secondary trim controls.
    """
    frame = tk.Frame(root)
    frame.pack(fill='x', padx=20, pady=pady)

    tk.Label(frame, text=label_text, width=label_width, anchor='w',
             font=label_font).pack(side='left')

    val_var = tk.StringVar(value=str(default_val))
    val_entry = tk.Entry(frame, textvariable=val_var, width=6, justify='center',
                         font=value_font)
    val_entry.pack(side='right')

    slider = ttk.Scale(frame, from_=min_val, to=max_val, orient='horizontal')
    slider.set(default_val)
    slider.pack(side='left', fill='x', expand=True, padx=8)

    # Slider -> box: reflect the slider value in the box as it moves, then send
    slider.config(
        command=lambda v: [val_var.set(str(int(float(v)))), send_channels()]
    )

    # Box -> slider: typing a value and pressing Enter moves the slider
    def on_entry(_event=None):
        try:
            val = int(float(val_var.get()))
        except ValueError:
            val = int(slider.get())            # revert to current on invalid input
        val = max(min_val, min(max_val, val))  # clamp to the channel range
        val_var.set(str(val))
        slider.set(val)                        # fires the slider command -> sends
    val_entry.bind('<Return>', on_entry)

    return slider


root = tk.Tk()
root.title("Flapping-Wing SBUS Controller")
root.geometry("520x540")

tk.Label(root, text="ESP32 Flapping-Wing Controller",
         font=("Arial", 14, "bold")).pack(pady=(12, 6))

# --- CH8 throttle lock: master enable, shown as a big button at the very top ---
# 1000 = off (servos locked), 2000 = on (armed). Default off for safety.
ch8_var = tk.IntVar(value=1000)

def refresh_ch8_button():
    """Update the CH8 button's text/colour to match its current state."""
    if ch8_var.get() == 2000:
        ch8_btn.config(text="THROTTLE LOCK (CH8):   ON — ARMED",
                       bg="#2e7d32", activebackground="#2e7d32", fg="white")
    else:
        ch8_btn.config(text="THROTTLE LOCK (CH8):   OFF — LOCKED",
                       bg="#c62828", activebackground="#c62828", fg="white")

def toggle_ch8():
    ch8_var.set(1000 if ch8_var.get() == 2000 else 2000)
    refresh_ch8_button()
    send_channels()

ch8_btn = tk.Button(root, command=toggle_ch8, font=("Arial", 13, "bold"),
                    height=2, relief="raised", bd=3)
ch8_btn.pack(fill='x', padx=20, pady=(0, 14))
refresh_ch8_button()

# --- Primary flight controls: large and prominent ---
tk.Label(root, text="Flight Controls", font=("Arial", 10, "bold"),
         fg="#333333", anchor='w').pack(fill='x', padx=20)

_big_label = ("Arial", 12, "bold")
_big_value = ("Arial", 12, "bold")
slider_ch1 = create_slider("Yaw  (CH1)", 1500,
                           label_font=_big_label, value_font=_big_value, pady=9)
slider_ch2 = create_slider("Pitch  (CH2)", 1500,
                           label_font=_big_label, value_font=_big_value, pady=9)
slider_ch3 = create_slider("Throttle  (CH3)", 1000,  # start at minimum
                           label_font=_big_label, value_font=_big_value, pady=9)

# --- Trim controls: secondary, smaller, at the bottom ---
ttk.Separator(root, orient='horizontal').pack(fill='x', padx=20, pady=(14, 4))
tk.Label(root, text="Trim (servo center)", font=("Arial", 9),
         fg="gray", anchor='w').pack(fill='x', padx=20)

_small_label = ("Arial", 9)
_small_value = ("Arial", 9)
slider_ch5 = create_slider("Trim 1 (CH5)", 1500, label_font=_small_label,
                           value_font=_small_value, label_width=12, pady=1)
slider_ch6 = create_slider("Trim 2 (CH6)", 1500, label_font=_small_label,
                           value_font=_small_value, label_width=12, pady=1)

port_text = SERIAL_PORT if SERIAL_PORT else "No port"
label_status = tk.Label(root, text=f"Connected: {port_text}", bd=1, relief='sunken', anchor='w')
label_status.pack(side='bottom', fill='x', padx=10, pady=10)

root.mainloop()

# Release the port after the window closes
if ser and ser.is_open:
    ser.close()
    print("Serial port closed")
