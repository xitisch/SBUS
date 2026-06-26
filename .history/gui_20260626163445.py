import tkinter as tk
from tkinter import ttk
import serial
import time

# ==================== 🛠️ 串口配置 ====================
# 💡 请根据你电脑上实际认出来的 COM 口进行修改（比如 COM5）
SERIAL_PORT = 'COM5' 
BAUD_RATE = 115200

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print(f"✅ 成功连接到串口: {SERIAL_PORT}")
    time.sleep(2) # 等待串口稳定
except Exception as e:
    print(f"❌ 无法打开串口 {SERIAL_PORT}，请检查端口号是否正确或被 Arduino 占用！")
    print(e)
    ser = None

# ==================== 🚀 数据发送函数 ====================
def send_channels(*args):
    if ser and ser.is_open:
        # 读取 5 个滑块的当前数值
        ch1 = int(slider_ch1.get())
        ch2 = int(slider_ch2.get())
        ch3 = int(slider_ch3.get())
        ch5 = int(slider_ch5.get())
        ch6 = int(slider_ch6.get())
        
        # 拼接成 ESP32 代码识别的格式: <CH1,CH2,CH3,CH5,CH6>
        cmd = f"<{ch1},{ch2},{ch3},{ch5},{ch6}>\n"
        
        try:
            ser.write(cmd.encode('utf-8'))
            label_status.config(text=f"已发送: {cmd.strip()}", fg="green")
        except Exception as err:
            label_status.config(text="发送失败", fg="red")

# ==================== 🎨 GUI 界面布局 ====================
root = tk.Tk()
root.title("扑翼机 SBUS 串口控制器")
root.geometry("450 Vintage")
root.geometry("450x400")

# 标题
label_title = tk.Label(root, text="ESP32 扑翼机多通道控制器", font=("Arial", 14, "bold"))
label_title.pack(pady=10)

# 创建滑块的辅助函数
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
    
    # 绑定滑动时实时更新数字显示
    slider.config(command=lambda v, sl=slider, vl=val_lbl: [vl.config(text=str(int(float(v)))), send_channels()])
    return slider

# 创建 5 个通道的滑块
slider_ch1 = create_slider("转向 (CH1):", 1500)
slider_ch2 = create_slider("升降 (CH2):", 1500)
slider_ch3 = create_slider("油门 (CH3):", 1000) # 油门默认最低 1000
slider_ch5 = create_slider("微调1 (CH5):", 1500)
slider_ch6 = create_slider("微调2 (CH6):", 1500)

# 状态栏显示
label_status = tk.Label(root, text="等待操作...", bd=1, relief='sunken', anchor='w')
label_status.pack(side='bottom', fill='x', padx=10, pady=10)

# 启动 GUI 主循环
root.mainloop()

# 关闭窗口时自动释放串口
if ser and ser.is_open:
    ser.close()
    print("🔒 串口已关闭")