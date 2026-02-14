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
    <!DOCTYPE html>
    <html>
    <head>
        <title>WALDO Live</title>
        <style>
            body {
                margin: 0;
                font-family: Arial, sans-serif;
                background-color: #0f172a;
                color: white;
                display: flex;
                height: 100vh;
            }

            /* Sidebar */
            .sidebar {
                width: 250px;
                background-color: #1e293b;
                padding: 20px;
                display: flex;
                flex-direction: column;
                box-shadow: 2px 0 10px rgba(0,0,0,0.5);
            }

            .sidebar h2 {
                text-align: center;
                margin-bottom: 40px;
            }

            .nav-button {
                padding: 15px;
                margin-bottom: 15px;
                border: none;
                border-radius: 8px;
                background-color: #334155;
                color: white;
                cursor: pointer;
                font-size: 16px;
                transition: 0.3s;
                text-align: left;
            }

            .nav-button:hover {
                background-color: #475569;
            }

            /* Main content */
            .main {
                flex-grow: 1;
                padding: 40px;
                display: flex;
                flex-direction: column;
                align-items: center;
            }

            .content-box {
                background-color: #1e293b;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 0 15px rgba(0,0,0,0.4);
                width: 80%;
                max-width: 900px;
                text-align: center;
            }

            img {
                width: 100%;
                border-radius: 10px;
                margin-bottom: 20px;
            }

            .logo {
                width: 100%;
                max-width: 140px;
                height: auto;
                border-radius: 50%;
                object-fit: contain;
                display: block;
                margin: 0 auto;
            }

            .capture-panel {
                position: relative;
                width: 100%;
                display: flex;
                justify-content: center;
                margin-bottom: 8px;
            }

            .capture-button {
                padding: 15px 30px;
                font-size: 16px;
                border-radius: 8px;
                border: none;
                cursor: pointer;
                background-color: #e63946;
                color: white;
                transition: 0.3s;
            }

            .capture-button:hover {
                background-color: #ff4d6d;
            }

            .capture-feedback {
                position: absolute;
                left: 50%;
                bottom: -36px;
                transform: translateX(-50%);
                padding: 6px 14px;
                border-radius: 999px;
                background-color: rgba(14, 165, 233, 0.95);
                color: white;
                font-size: 0.9rem;
                display: inline-flex;
                gap: 6px;
                align-items: center;
                opacity: 0;
                pointer-events: none;
            }

            .capture-feedback.visible {
                animation: fadePop 1.2s ease forwards;
            }

            @keyframes fadePop {
                0% {
                    opacity: 0;
                    transform: translate(-50%, -5px) scale(0.9);
                }
                20% {
                    opacity: 1;
                    transform: translate(-50%, 0) scale(1);
                }
                70% {
                    opacity: 1;
                    transform: translate(-50%, 0) scale(1);
                }
                100% {
                    opacity: 0;
                    transform: translate(-50%, -10px) scale(0.95);
                }
            }

            .hidden {
                display: none;
            }

            a {
                text-decoration: none;
            }

            @media (max-width: 768px) {
                body {
                    flex-direction: column;
                }

                .sidebar {
                    width: 100%;
                    flex-direction: row;
                    flex-wrap: wrap;
                    justify-content: space-between;
                    align-items: center;
                }

                .logo-container {
                    margin: 0 auto 8px;
                }

                .nav-button {
                    width: calc(50% - 12px);
                    margin-bottom: 10px;
                }

                .main {
                    width: 100%;
                    padding: 20px;
                }

                .content-box {
                    width: 90%;
                }
            }
        </style>

        <script>
            function showFeed() {
                document.getElementById("feed").classList.remove("hidden");
                document.getElementById("gallery").classList.add("hidden");
            }

            function showGallery() {
                document.getElementById("gallery").classList.remove("hidden");
                document.getElementById("feed").classList.add("hidden");
            }

            document.addEventListener('DOMContentLoaded', () => {
                const form = document.getElementById('capture-form');
                const feedback = document.querySelector('.capture-feedback');

                const triggerFeedback = () => {
                    if (!feedback) return;
                    feedback.classList.remove('visible');
                    void feedback.offsetWidth;
                    feedback.classList.add('visible');
                };

                form?.addEventListener('submit', (event) => {
                    event.preventDefault();
                    fetch('/capture', { method: 'POST' })
                        .finally(() => triggerFeedback());
                });
            });
        </script>
    </head>

    <body>

        <div class="sidebar">
            <div class="logo-container">
              <img src="/static/POLARIS_LOGO.png" class="logo" alt="WALDO Live logo">
              <h2>WALDO Live</h2>
            </div>

            <button class="nav-button" onclick="showFeed()">📹 Live Feed</button>
            <button class="nav-button" onclick="showGallery()">🖼 Gallery</button>

            <div class="capture-panel">
                <form id="capture-form" action="/capture" method="post">
                    <button class="nav-button capture-button" type="submit">📸 Capture Photo</button>
                </form>
                <span class="capture-feedback" role="status" aria-live="polite">📸 Captured!</span>
            </div>
        </div>

        <div class="main">

            <!-- FEED VIEW -->
            <div id="feed" class="content-box">
                <h1>Live Camera Feed</h1>
                <img src="/video">
            </div>

            <!-- GALLERY VIEW -->
            <div id="gallery" class="content-box hidden">
                <h1>Gallery</h1>
                <p>Your captured images will appear here.</p>
                <a href="/gallery">
                    <button class="capture-button">Open Full Gallery</button>
                </a>
            </div>

        </div>

    </body>
    </html>
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
