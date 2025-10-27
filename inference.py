import tkinter as tk
import requests
import time
import threading
from PIL import Image, ImageTk
import io
import queue
import sounddevice as sd
import speech_recognition as sr
import pyttsx3
import random

# ======================
# CONFIG
# ======================
SERVER_URL = "http://localhost:5000"
WAKEWORD = "mèo ơi"
WAKE_TIMEOUT = 10  # giây cho phép nhận lệnh sau khi kích hoạt

# ======================
# VOICE + SPEECH ENGINE
# ======================
r = sr.Recognizer()
audio_q = queue.Queue()
last_wake_ts = 0

engine = pyttsx3.init()
engine.setProperty('rate', 170)
engine.setProperty('volume', 1.0)

def speak(text):
    """Phát giọng nói"""
    print("🔊 Nói:", text)
    engine.say(text)
    engine.runAndWait()

# ======================
# WEATHER HELPER
# ======================
def get_fake_weather():
    conditions = ["nắng đẹp", "mưa nhẹ", "nhiều mây", "mưa to", "trời âm u", "nắng nóng"]
    temp = random.randint(25, 35)
    cond = random.choice(conditions)
    return temp, cond

def evaluate_weather(temp, cond):
    if "mưa" in cond or "âm u" in cond:
        return f"Hôm nay trời {cond}, không lý tưởng để ra ngoài. Nhớ mang ô nhé ☂️"
    elif temp > 33:
        return f"Trời {cond}, khá nóng. Nên ra ngoài buổi sáng sớm hoặc chiều mát 🌤️"
    else:
        return f"Thời tiết {cond}, rất thích hợp để ra ngoài dạo chơi ☀️"

# ======================
# NETWORK HELPERS
# ======================
def post_cmd(cmd, extra=None):
    payload = {"cmd": cmd}
    if extra:
        payload.update(extra)
    try:
        res = requests.post(SERVER_URL + "/api/command", json=payload, timeout=5)
        print("[VOICE] POST:", cmd, "→", res.json())
        return res.json()
    except Exception as e:
        print("[VOICE] POST error:", e)
        return {}

# ======================
# VOICE THREAD
# ======================
def callback(indata, frames, time_info, status):
    audio_q.put(bytes(indata))

def handle_weather_local(app):
    """Tạo dữ liệu thời tiết giả lập và đọc ra loa"""
    temp, cond = get_fake_weather()
    msg = f"Nhiệt độ hôm nay khoảng {temp}°C, trời {cond}."
    advice = evaluate_weather(temp, cond)
    full_msg = msg + " " + advice
    speak(full_msg)
    app.set_response(full_msg)

def handle_generate_image(app):
    """Gọi API tạo ảnh và hiển thị + phát giọng"""
    data = post_cmd("generate_image")
    url = data.get("url")
    if url:
        app.update_image(url)
        msg = "Đã tạo tranh mới rồi nè 🎨"
        app.set_response(msg)
        speak(msg)
    else:
        msg = "Không tạo được ảnh rồi 😿"
        app.set_response(msg)
        speak(msg)

def voice_loop(app):
    global last_wake_ts
    print("🎧 Voice thread started...")
    buffer_duration = 3  # thu mỗi 3 giây
    sample_rate = 16000
    chunk_size = int(sample_rate * buffer_duration)
    audio_buffer = b""

    with sd.RawInputStream(samplerate=sample_rate, blocksize=1024, dtype='int16',
                           channels=1, callback=callback):
        while True:
            try:
                # Gom dữ liệu vào buffer
                while len(audio_buffer) < chunk_size * 2:
                    audio_buffer += audio_q.get()

                audio_data = sr.AudioData(audio_buffer, sample_rate, 2)
                audio_buffer = b""  # reset sau khi nhận diện

                try:
                    text = r.recognize_google(audio_data, language="vi-VN")
                    lower = text.lower().strip()
                    if not lower:
                        continue
                    print("🗣️", lower)

                    # WAKEWORD
                    if WAKEWORD in lower:
                        print("[VOICE] Wakeword detected")
                        last_wake_ts = time.time()
                        post_cmd("activate_voice")
                        app.voice_label.config(text="🎙️ Voice: ON", fg="lime")

                    # HANDLE COMMANDS
                    elif time.time() - last_wake_ts <= WAKE_TIMEOUT:
                        if any(x in lower for x in ["tạo tranh", "tạo ảnh", "tao tranh"]):
                            handle_generate_image(app)
                            post_cmd("deactivate_voice")
                            last_wake_ts = 0
                            app.voice_label.config(text="🎙️ Voice: OFF", fg="gray")

                        elif any(x in lower for x in ["thời tiết", "thoi tiet"]):
                            handle_weather_local(app)
                            post_cmd("weather")
                            post_cmd("deactivate_voice")
                            last_wake_ts = 0
                            app.voice_label.config(text="🎙️ Voice: OFF", fg="gray")

                        else:
                            print("[VOICE] Heard (no matched command):", lower)

                except sr.UnknownValueError:
                    pass
                except Exception as e:
                    print("[VOICE ERROR]", e)

            except Exception as e:
                print("[STREAM ERROR]", e)
                time.sleep(0.5)

# ======================
# GUI DISPLAY
# ======================
class SmartMirrorApp:
    def __init__(self, root):
        self.root = root
        root.title("Smart Mirror")
        root.configure(bg="black")
        root.attributes("-fullscreen", False)

        self.font_big = ("Arial", 40, "bold")
        self.font_small = ("Arial", 20)
        self.fg = "white"

        # Widgets
        self.time_label = tk.Label(root, text="", font=self.font_big, fg=self.fg, bg="black")
        self.time_label.pack(pady=10)

        self.temp_label = tk.Label(root, text="🌡️ Temp: -- °C", font=self.font_big, fg=self.fg, bg="black")
        self.temp_label.pack()
        self.humi_label = tk.Label(root, text="💧 Humidity: -- %", font=self.font_big, fg=self.fg, bg="black")
        self.humi_label.pack()
        self.light_label = tk.Label(root, text="💡 Light: --", font=self.font_big, fg=self.fg, bg="black")
        self.light_label.pack()
        self.pm_label = tk.Label(root, text="🌫️ PM2.5: -- | PM10: --", font=self.font_small, fg=self.fg, bg="black")
        self.pm_label.pack()

        self.voice_label = tk.Label(root, text="🎙️ Voice: OFF", font=self.font_small, fg="gray", bg="black")
        self.voice_label.pack(pady=10)
        self.response_label = tk.Label(root, text="", font=self.font_small, fg="cyan", bg="black", wraplength=800)
        self.response_label.pack(pady=10)

        self.img_label = tk.Label(root, bg="black")
        self.img_label.pack(pady=10)

        self.exit_btn = tk.Button(root, text="Thoát", command=root.destroy, bg="red", fg="white", font=self.font_small)
        self.exit_btn.pack(side="bottom", pady=20)

        # Threads
        threading.Thread(target=self.update_loop, daemon=True).start()
        threading.Thread(target=self.clock_loop, daemon=True).start()

    def update_loop(self):
        last_img_url = None
        while True:
            try:
                res = requests.get(f"{SERVER_URL}/api/state", timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    self.temp_label.config(text=f"🌡️ Temp: {data.get('temperature', '--')} °C")
                    self.humi_label.config(text=f"💧 Humidity: {data.get('humidity', '--')} %")
                    self.light_label.config(text=f"💡 Light: {data.get('light', '--')}")
                    self.pm_label.config(text=f"🌫️ PM2.5: {data.get('pm25', '--')} | PM10: {data.get('pm10', '--')}")
                    self.voice_label.config(
                        text=f"🎙️ Voice: {'ON' if data.get('voice_mode') else 'OFF'}",
                        fg="lime" if data.get("voice_mode") else "gray"
                    )
            except Exception as e:
                print("[DISPLAY] update error:", e)
            time.sleep(2)

    def clock_loop(self):
        while True:
            now = time.strftime("%H:%M:%S")
            self.time_label.config(text=now)
            time.sleep(1)

    def set_response(self, text):
        self.response_label.config(text=text)

    def update_image(self, url):
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                image = Image.open(io.BytesIO(res.content))
                image = image.resize((400, 400))
                tk_img = ImageTk.PhotoImage(image)
                self.img_label.config(image=tk_img)
                self.img_label.image = tk_img
        except Exception as e:
            print("[DISPLAY] image error:", e)

# ======================
# MAIN
# ======================
if __name__ == "__main__":
    root = tk.Tk()
    app = SmartMirrorApp(root)

    voice_thread = threading.Thread(target=voice_loop, args=(app,), daemon=True)
    voice_thread.start()

    root.mainloop()
