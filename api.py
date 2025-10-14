from flask import Flask, request, render_template, jsonify, Response, stream_with_context
from flask_cors import CORS
import time, json, threading, queue
import requests

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# Shared state
state = {
    "device": "unknown",
    "wifi": "disconnected",
    "ip": "",
    "last_event": "",
    "last_update": ""
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
    """
    ESP32 gửi JSON:
    {
      "temperature": 28.3,
      "humidity": 72.5,
      "light": 40.0,
      "pm25": 35.2,
      "pm10": 70.5
    }
    """
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

    # Ghi nhận thời gian cập nhật
    state["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")

    # Gửi cập nhật qua SSE (realtime cho web)
    push_event(state.copy())

    return jsonify({"ok": True})


@app.route("/api/generate", methods=["POST"])
def generate_image():
    """
    Demo: tạo URL ảnh bằng picsum (hoặc gọi API AI ở đây)
    Body: { "prompt": "..." } optional
    """
    # In demo chúng ta trả url random
    url = "https://picsum.photos/512?random=" + str(int(time.time()))
    resp = {"url": url}
    push_event({**state, "generated_image": url, "last_update": time.strftime("%Y-%m-%d %H:%M:%S")})
    return jsonify(resp)

if __name__ == "__main__":
    # chạy dev server
    app.run(host="0.0.0.0", port=5000, debug=True)
