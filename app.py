import cv2
import os
import time
import threading
from flask import Flask, Response, render_template_string, send_from_directory
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
    return '''
    <h1>WALDO Live</h1>
    <img src="/video"><br><br>
    <form action="/capture" method="post">
        <button type="submit" style="width:200px;height:50px;">CAPTURE HIGH-RES PHOTO</button>
    </form>
    <br>
    <a href="/gallery"><button style="width:200px;height:50px;">VIEW GALLERY</button></a>
    '''

@app.route('/video')
def video():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/capture', methods=['POST'])
def capture():
    success, frame = camera.read()
    if success:
        name = f"{SAVE_DIR}/shot_{datetime.now().strftime('%H%M%S')}.jpg"
        cv2.imwrite(name, frame)
    return "Photo Saved to Pi! <a href='/'>Go Back</a> | <a href='/gallery'>View Gallery</a>"

@app.route('/gallery')
def gallery():
    # Get all jpg files from the save directory
    files = [f for f in os.listdir(SAVE_DIR) if f.endswith('.jpg')]
    files.sort(reverse=True)  # Most recent first
    
    html = '<h1>Photo Gallery</h1><a href="/">Back to Live Feed</a><br><br>'
    html += f'<p>Total photos: {len(files)}</p>'
    
    for filename in files:
        html += f'<div style="margin:20px;">'
        html += f'<h3>{filename}</h3>'
        html += f'<img src="/photos/{filename}" style="max-width:800px;"><br>'
        html += f'</div>'
    
    return html

@app.route('/photos/<filename>')
def serve_photo(filename):
    return send_from_directory(SAVE_DIR, filename)

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
