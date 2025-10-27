# Smart Mirror — mirror_2

This repository contains a small smart mirror demo using an ESP32 firmware (PlatformIO) together with a Flask-based web dashboard and a local realtime voice client that listens on the microphone and posts voice commands to the server.

Summary
-------
- Firmware: `src/main.cpp` — reads sensors, shows data on an OLED, sends sensor state to the Flask server, and can play a raw audio file from SPIFFS for a wake-word demo.
- Server: `api.py` — Flask app that serves a dashboard, receives updates from the ESP, and accepts voice commands (via `/api/command`). It pushes realtime updates to the browser via Server-Sent Events (`/events`).
- Realtime voice client: `realtime.py` — captures mic audio, runs speech recognition (SpeechRecognition + Google by default), detects a wakeword, and posts commands to the Flask server.
- Web UI template: `templates/index.html` — dashboard that receives SSE updates and shows sensor data, voice status and generated images.

Prerequisites
-------------
- Python 3.8+ (recommended). Install project Python deps in your chosen environment. Example packages used in the code:
  - Flask
  - requests
  - flask-cors
  - SpeechRecognition
  - sounddevice (or PyAudio as alternative)
- PlatformIO (for building firmware): https://platformio.org
- An ESP32 development board if you plan to run on hardware. The project also supports Wokwi simulation.

Quick setup
-----------
1. Install Python deps (example):

```powershell
python -m pip install -U flask requests flask-cors SpeechRecognition sounddevice
```

2. Build firmware (creates `.pio/build/esp32dev/firmware.bin`):

```powershell
# using workspace virtualenv python if configured
D:/taileu/IOT/mirror_2/.venv/Scripts/python.exe -m platformio run -e esp32dev
```

3. If you want to simulate a microphone input using an audio file, create `data/` at repo root and convert your MP3/WAV to 16-bit PCM LE raw mono (example using ffmpeg):

```powershell
ffmpeg -i hiesp.mp3 -f s16le -ar 16000 -ac 1 hiesp.raw
# put hiesp.raw into the project's data/ folder
D:/taileu/IOT/mirror_2/.venv/Scripts/python.exe -m platformio run -e esp32dev -t uploadfs
```

4. Start the Flask server (dashboard + API):

```powershell
python api.py
# server listens on http://0.0.0.0:5000 by default
```

5. Start the realtime voice client (on the same machine as your microphone):

```powershell
python realtime.py
# It will listen and POST detected commands to the Flask server
```

How it works
------------
- ESP32 firmware periodically POSTs sensor data to `http://<server>:5000/update`. The Flask server stores this state and pushes it to connected browsers via Server-Sent Events.
- `realtime.py` listens to the mic, sends partial/periodic audio to Google (through SpeechRecognition) and looks for the wakeword `"mèo ơi"`. When the wakeword is recognized the client sends `activate_voice` to the server.
- While voice mode is active (for a short window), speaking commands like `tạo tranh` or `thời tiết hôm nay thế nào` triggers the server endpoints to generate an image (a placeholder image service is used) or fetch the current weather (Open-Meteo) and evaluate if it's suitable to go outside.

Voice commands (default behavior)
-------------------------------
- Wakeword: "mèo ơi" — activates voice mode.
- After wakeword, example recognized commands:
  - "tạo tranh" → server generates an image and sends it to the dashboard.
  - "thời tiết" or "thời tiết hôm nay thế nào" → server calls Open-Meteo to get current weather and returns a short answer (and a simple suitability evaluation for going outside).

Troubleshooting microphone / recognition
---------------------------------------
- If the realtime client doesn't hear microphone input:
  - Make sure your OS microphone permissions are enabled for Python.
  - Check which audio devices are available. Using `sounddevice` you can list devices inside the same Python environment:

```python
import sounddevice as sd
print(sd.query_devices())
```

  - If multiple devices are present, modify `realtime.py` to select the right device index when opening the input stream (the code can be adapted to accept a `--device` argument).

To test recording locally and run recognition on a short file, record a small WAV and test with SpeechRecognition's `recognize_google`.

Notes & next steps
------------------
- The current demo uses client-side speech recognition (Google via SpeechRecognition). If you prefer offline recognition, integrate a local ASR engine.
- The server's image generation is currently a placeholder (random image service). You can replace `generate_image()` with a call to an image generation model or service.
- The weather API uses Open-Meteo (no key). Change latitude/longitude inside `api.py` if you want a different default location.

Files of interest
-----------------
- `src/main.cpp` — ESP32 firmware (sensor reading, SPIFFS playback demo)
- `api.py` — Flask dashboard, SSE, and voice command endpoints
- `realtime.py` — local mic client and speech recognition
- `templates/index.html` — dashboard UI

