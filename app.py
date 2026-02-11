import cv2
import os
import time
import threading
from flask import Flask, Response, render_template_string
from datetime import datetime

app = Flask(__name__)
camera = cv2.VideoCapture(0)

# Folder to store photos when out of range
SAVE_DIR = "moon_shots"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

def gen_frames():
    while True:
        success, frame = camera.read()
        if not success: break
        # Resize for Bluetooth speed (low res = smoother)
        small_frame = cv2.resize(frame, (320, 240))
        _, buffer = cv2.imencode('.jpg', small_frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/')
def index():
    return '<h1>MoonBot Live</h1><img src="/video"><br><br><form action="/capture" method="post"><button type="submit" style="width:200px;height:50px;">CAPTURE HIGH-RES PHOTO</button></form>'

@app.route('/video')
def video():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/capture', methods=['POST'])
def capture():
    success, frame = camera.read()
    if success:
        name = f"{SAVE_DIR}/shot_{datetime.now().strftime('%H%M%S')}.jpg"
        cv2.imwrite(name, frame)
    return "Photo Saved to Pi! <a href='/'>Go Back</a>"


def periodic_capture(interval=10):
    while True:
        success, frame = camera.read()
        if success:
            name = f"{SAVE_DIR}/auto_{datetime.now().strftime('%H%M%S')}.jpg"
            cv2.imwrite(name, frame)
        time.sleep(interval)

if __name__ == "__main__":
    capture_thread = threading.Thread(target=periodic_capture, daemon=True)
    capture_thread.start()
    app.run(host='0.0.0.0', port=5000)