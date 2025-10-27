# ...existing code...
from flask import Flask, request, render_template, jsonify, Response, stream_with_context
from flask_cors import CORS
import time, json, threading, queue, requests

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# Shared state
state = {
    "device": "unknown",
    "wifi": "disconnected",
    "ip": "",
    "last_event": "",
    "last_update": "",
    "voice_mode": False,
    "last_voice_response": "",
    "generated_image": None
}

# Simple pubsub queue for SSE
events_q = queue.Queue()

def push_event(data):
    events_q.put(data)

@app.route("/")
def index():
    return render_template("index.html", state=state)

@app.route("/events")
def sse_events():
    def gen():
        # send current state once
        yield f"data: {json.dumps(state)}\n\n"
        while True:
            data = events_q.get()
            yield f"data: {json.dumps(data)}\n\n"
    return Response(stream_with_context(gen()), content_type="text/event-stream")

@app.route("/update", methods=["POST"])
def update():
    try:
        d = request.get_json(force=True)
    except:
        return jsonify({"ok": False, "error": "invalid json"}), 400

    # Cập nhật dữ liệu cảm biến
    state["temperature"] = d.get("temperature")
    state["humidity"] = d.get("humidity")
    state["light"] = d.get("light")
    state["pm25"] = d.get("pm25")
    state["pm10"] = d.get("pm10")

    state["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")
    push_event(state.copy())
    return jsonify({"ok": True})

# existing /api/generate kept as helper
@app.route("/api/generate", methods=["POST"])
def generate_image():
    url = "https://picsum.photos/512?random=" + str(int(time.time()))
    state["generated_image"] = url
    state["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")
    push_event({**state, "generated_image": url, "last_update": state["last_update"]})
    return jsonify({"url": url})

# New endpoint to accept voice commands from local realtime client
@app.route("/api/command", methods=["POST"])
def api_command():
    d = request.get_json(force=True)
    cmd = d.get("cmd", "")
    resp = {"ok": True}

    if cmd == "activate_voice":
        state["voice_mode"] = True
        state["last_voice_response"] = "Voice mode activated"
        push_event(state.copy())
        resp["msg"] = "voice activated"
    elif cmd == "deactivate_voice":
        state["voice_mode"] = False
        state["last_voice_response"] = "Voice mode deactivated"
        push_event(state.copy())
        resp["msg"] = "voice deactivated"
    elif cmd == "generate_image":
        # reuse generator
        g = generate_image()
        data = json.loads(g.get_data())
        resp["url"] = data.get("url")
        state["last_voice_response"] = "Đã tạo tranh."
        push_event(state.copy())
    elif cmd == "weather":
        # simple weather via open-meteo (no API key). Edit coords as needed.
        LAT = d.get("lat", 10.8231)   # Ho Chi Minh default
        LON = d.get("lon", 106.6297)
        url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current_weather=true"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            j = r.json()
            cw = j.get("current_weather", {})
            temp = cw.get("temperature")
            wind = cw.get("windspeed")
            wcode = cw.get("weathercode")
            # Basic suitability logic: weathercode 0..3 = good; else caution
            suitable = (wcode is not None and int(wcode) <= 3)
            msg = f"Nhiệt: {temp}°C, gió: {wind} m/s. "
            msg += "Thời tiết thích hợp để ra ngoài." if suitable else "Thời tiết có thể không thích hợp (mưa/bão)."
            state["last_voice_response"] = msg
            push_event(state.copy())
            resp["weather"] = {"temp": temp, "windspeed": wind, "weathercode": wcode, "suitable": suitable}
            resp["msg"] = msg
        else:
            resp = {"ok": False, "error": "weather api failed", "status": r.status_code}
    else:
        resp = {"ok": False, "error": "unknown command", "cmd": cmd}

    return jsonify(resp)

@app.route("/api/state", methods=["GET"])
def api_state():
    return jsonify(state)

if __name__ == "__main__":
    # chạy dev server
    app.run(host="0.0.0.0", port=5000, debug=True)
# ...existing code...