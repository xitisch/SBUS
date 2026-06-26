import tkinter as tk
from tkinter import ttk
import serial
import time

# ==================== 🛠️ Serial Configuration ====================
# Change this to the COM port your computer actually detects (e.g. COM5)
SERIAL_PORT = 'COM10'
BAUD_RATE = 115200

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print(f"Successfully connected to serial port: {SERIAL_PORT}")
    time.sleep(2)  # Wait for the serial connection to stabilize
except Exception as e:
    print(f"Could not open serial port {SERIAL_PORT}. Check the port number or whether Arduino is using it!")
    print(e)
    ser = None

# ==================== Data Send Function ====================
def send_channels(*args):
    if not (ser and ser.is_open):
        return

    # Read the current value of all 5 sliders
    try:
        ch1 = int(slider_ch1.get())
        ch2 = int(slider_ch2.get())
        ch3 = int(slider_ch3.get())
        ch5 = int(slider_ch5.get())
        ch6 = int(slider_ch6.get())
    except NameError:
        return  # Sliders not all created yet (during startup)

    # Assemble into the format the ESP32 code expects: <CH1,CH2,CH3,CH5,CH6>
    cmd = f"<{ch1},{ch2},{ch3},{ch5},{ch6}>\n"

    try:
        ser.write(cmd.encode('utf-8'))
        label_status.config(text=f"Sent: {cmd.strip()}", fg="green")
    except Exception as err:
        label_status.config(text="Send failed", fg="red")

# ==================== GUI Layout ====================
root = tk.Tk()
root.title("Flapping-Wing SBUS Serial Controller")
root.geometry("450x400")

# Title
label_title = tk.Label(root, text="ESP32 Flapping-Wing Multi-Channel Controller", font=("Arial", 14, "bold"))
label_title.pack(pady=10)

# Helper function to create a slider
def create_slider(label_text, default_val, min_val=1000, max_val=2000):
    frame = tk.Frame(root)
    frame.pack(fill='x', padx=20, pady=5)

    lbl = tk.Label(frame, text=label_text, width=12, anchor='w')
    lbl.pack(side='left')

    slider = ttk.Scale(frame, from_=min_val, to=max_val, orient='horizontal', command=send_channels)
    slider.set(default_val)
    slider.pack(side='left', fill='x', expand=True, padx=5)

    val_lbl = tk.Label(frame, text=str(default_val), width=5)
    val_lbl.pack(side='right')

    # Update the number display in real time as the slider moves
    slider.config(command=lambda v, sl=slider, vl=val_lbl: [vl.config(text=str(int(float(v)))), send_channels()])
    return slider

# Create the 5 channel sliders
slider_ch1 = create_slider("Yaw (CH1):", 1500)
slider_ch2 = create_slider("Pitch (CH2):", 1500)
slider_ch3 = create_slider("Throttle (CH3):", 1000)  # Throttle defaults to minimum (1000)
slider_ch5 = create_slider("Trim 1 (CH5):", 1500)
slider_ch6 = create_slider("Trim 2 (CH6):", 1500)

# Status bar
label_status = tk.Label(root, text="Waiting for input...", bd=1, relief='sunken', anchor='w')
label_status.pack(side='bottom', fill='x', padx=10, pady=10)

# Start the GUI main loop
root.mainloop()

# Release the serial port when the window closes
if ser and ser.is_open:
    ser.close()
    print("Serial port closed")