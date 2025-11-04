from flask import Flask, render_template, jsonify
from flask import Response
import cv2
import threading
import RUN_BOTH as rc

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/status")
def get_status():
    return jsonify(rc.status)

@app.route("/command/<cmd>", methods=["POST"])
def command(cmd):
    if cmd == "enable": rc.enable_controls()
    elif cmd == "disable": rc.disable_controls()
    elif cmd == "brush1": rc.set_brush_level(1)
    elif cmd == "brush2": rc.set_brush_level(2)
    elif cmd == "brush3": rc.set_brush_level(3)
    elif cmd == "wheel1": rc.set_wheel_speed(1)
    elif cmd == "wheel2": rc.set_wheel_speed(2)
    elif cmd == "wheel3": rc.set_wheel_speed(3)
    else: return jsonify({"status": "Unknown"})
    return jsonify(rc.status)


# Camera setup (0 = default USB camera, or Pi camera if supported)
camera = cv2.VideoCapture(0)

def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            continue
        else:
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')



if __name__ == "__main__":
    t = threading.Thread(target=rc.joystick_loop, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=5000, debug=True)
