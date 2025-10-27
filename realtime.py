import sounddevice as sd
import numpy as np
import speech_recognition as sr
import queue
import requests
import time

r = sr.Recognizer()
q = queue.Queue()

SERVER_URL = "http://localhost:5000"  # change if api.py is on other host
WAKEWORD = "mèo ơi"
last_wake_ts = 0
WAKE_TIMEOUT = 10  # seconds during which commands are accepted after wakeword

def callback(indata, frames, time_info, status):
    q.put(bytes(indata))

def post_cmd(cmd, extra=None):
    payload = {"cmd": cmd}
    if extra:
        payload.update(extra)
    try:
        res = requests.post(SERVER_URL + "/api/command", json=payload, timeout=5)
        print("[CLIENT] server response:", res.json())
    except Exception as e:
        print("[CLIENT] POST error:", e)

with sd.RawInputStream(samplerate=16000, blocksize=16000, dtype='int16',
                       channels=1, callback=callback):
    print("Đang nghe realtime (Ctrl+C để dừng)...")
    audio_buffer = b""
    try:
        while True:
            audio_buffer += q.get()
            # process every ~2 seconds of audio
            if len(audio_buffer) >= 16000 * 2 * 2:
                audio_data = sr.AudioData(audio_buffer, 16000, 2)
                try:
                    text = r.recognize_google(audio_data, language="vi-VN")
                    print("🗣️", text)
                    lower = text.lower()

                    # wakeword detection
                    if WAKEWORD in lower:
                        print("[CLIENT] Wakeword detected")
                        last_wake_ts = time.time()
                        post_cmd("activate_voice")
                    # only accept commands shortly after wakeword
                    elif time.time() - last_wake_ts <= WAKE_TIMEOUT:
                        # generate image
                        if "tạo tranh" in lower or "tạo ảnh" in lower or "tao tranh" in lower:
                            print("[CLIENT] Command: generate image")
                            post_cmd("generate_image")
                            # optionally deactivate after command
                            post_cmd("deactivate_voice")
                            last_wake_ts = 0
                        # weather query
                        elif "thời tiết" in lower or "thoi tiet" in lower:
                            print("[CLIENT] Command: weather")
                            post_cmd("weather")
                            post_cmd("deactivate_voice")
                            last_wake_ts = 0
                        else:
                            print("[CLIENT] Heard (but no matched command in voice-mode):", lower)
                    else:
                        print("[CLIENT] (no wakeword active)")

                except sr.UnknownValueError:
                    pass
                except Exception as e:
                    print("Recognition error:", e)
                audio_buffer = b""
    except KeyboardInterrupt:
        print("\nDừng lại.")