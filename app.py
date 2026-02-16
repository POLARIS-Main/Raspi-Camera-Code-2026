import cv2
import os
import time
import threading
import shutil
from flask import Flask, Response, render_template_string, send_from_directory, request, jsonify
from datetime import datetime

app = Flask(__name__)

# SETTINGS - Change these to customize your camera behavior


SAVE_DIR = "moon_shots"              # Where photos get saved
AUTO_CAPTURE_INTERVAL = 10           # Seconds between auto-captures
STREAM_QUALITY = 70                  # JPEG quality (1-100, lower = faster)
STREAM_WIDTH = 320                   # Live stream width
STREAM_HEIGHT = 240                  # Live stream height
PHOTO_WIDTH = 1280                   # Full photo width
PHOTO_HEIGHT = 720                   # Full photo height
MAX_STORAGE_MB = 500                 # Auto-delete old photos if storage exceeds this

# CAMERA SETUP - Thread-safe camera access. (I think)
# This section sets up the camera for use in the application.
# It ensures that only one thread can access the camera at a time,
# preventing crashes and other issues.


camera = None
camera_lock = threading.Lock()       # Prevents crashes from multiple threads

def get_camera():
    """Get the camera, opening it if needed."""
    global camera
    if camera is None or not camera.isOpened():
        camera = cv2.VideoCapture(0)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, PHOTO_WIDTH)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, PHOTO_HEIGHT)
    return camera

def read_frame():
    """Safely read a frame from the camera."""
    with camera_lock:
        cam = get_camera()
        success, frame = cam.read()
        if not success:
            # Try reopening the camera if it failed
            cam.release()
            cam = get_camera()
            success, frame = cam.read()
        return success, frame

# Create the save folder if it doesn't exist
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

def gen_frames():
    """Generate frames for the live video stream."""
    while True:
        success, frame = read_frame()
        if not success:
            time.sleep(0.1)  # Brief pause before retry
            continue
        
        # Resize for smooth streaming over slow connections
        small_frame = cv2.resize(frame, (STREAM_WIDTH, STREAM_HEIGHT))
        
        # Encode as JPEG with adjustable quality
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, STREAM_QUALITY]
        _, buffer = cv2.imencode('.jpg', small_frame, encode_params)
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        
        # Small delay to control frame rate and reduce CPU usage
        time.sleep(0.033)  # ~30 FPS max

# ============================================================
# HTML TEMPLATES - The web pages
# ============================================================

GALLERY_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>WALDO Gallery</title>
    <style>
        body {
            margin: 0;
            padding: 20px;
            font-family: Arial, sans-serif;
            background-color: #0f172a;
            color: white;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 10px;
        }
        .header h1 { margin: 0; }
        .back-btn, .delete-all-btn {
            padding: 10px 20px;
            border-radius: 8px;
            border: none;
            cursor: pointer;
            font-size: 14px;
            text-decoration: none;
        }
        .back-btn {
            background-color: #334155;
            color: white;
        }
        .delete-all-btn {
            background-color: #dc2626;
            color: white;
        }
        .stats {
            background-color: #1e293b;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .gallery-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }
        .photo-card {
            background-color: #1e293b;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .photo-card img {
            width: 100%;
            height: 200px;
            object-fit: cover;
        }
        .photo-info {
            padding: 15px;
        }
        .photo-info h3 {
            margin: 0 0 10px 0;
            font-size: 14px;
            word-break: break-all;
        }
        .photo-actions {
            display: flex;
            gap: 10px;
        }
        .photo-actions a, .photo-actions button {
            flex: 1;
            padding: 8px;
            border-radius: 6px;
            border: none;
            cursor: pointer;
            font-size: 12px;
            text-align: center;
            text-decoration: none;
        }
        .download-btn { background-color: #22c55e; color: white; }
        .delete-btn { background-color: #ef4444; color: white; }
        .empty-state {
            text-align: center;
            padding: 60px;
            color: #94a3b8;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📸 Photo Gallery</h1>
        <div>
            <a href="/" class="back-btn">← Back to Live Feed</a>
            {% if files %}
            <button class="delete-all-btn" onclick="deleteAll()">🗑️ Delete All</button>
            {% endif %}
        </div>
    </div>
    
    <div class="stats">
        <strong>{{ files|length }}</strong> photos | 
        <strong>{{ "%.1f"|format(size_mb) }} MB</strong> used
    </div>
    
    {% if files %}
    <div class="gallery-grid">
        {% for filename in files %}
        <div class="photo-card" id="card-{{ loop.index }}">
            <img src="/photos/{{ filename }}" alt="{{ filename }}" loading="lazy">
            <div class="photo-info">
                <h3>{{ filename }}</h3>
                <div class="photo-actions">
                    <a href="/download/{{ filename }}" class="download-btn">⬇️ Download</a>
                    <button class="delete-btn" onclick="deletePhoto('{{ filename }}', 'card-{{ loop.index }}')">🗑️ Delete</button>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
    {% else %}
    <div class="empty-state">
        <h2>No photos yet!</h2>
        <p>Go back to the live feed and capture some shots.</p>
    </div>
    {% endif %}
    
    <script>
        function deletePhoto(filename, cardId) {
            if (!confirm('Delete ' + filename + '?')) return;
            fetch('/delete/' + filename, { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    if (data.status === 'success') {
                        document.getElementById(cardId).remove();
                    }
                });
        }
        
        function deleteAll() {
            if (!confirm('Delete ALL photos? This cannot be undone!')) return;
            fetch('/delete_all', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    if (data.status === 'success') {
                        location.reload();
                    }
                });
        }
    </script>
</body>
</html>
'''

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
                margin-bottom: 20px;
            }

            .nav-button {
                padding: 15px;
                margin-bottom: 10px;
                border: none;
                border-radius: 8px;
                background-color: #334155;
                color: white;
                cursor: pointer;
                font-size: 14px;
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
                overflow-y: auto;
            }

            .content-box {
                background-color: #1e293b;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 0 15px rgba(0,0,0,0.4);
                width: 80%;
                max-width: 900px;
                text-align: center;
                margin-bottom: 20px;
            }

            .video-feed {
                width: 100%;
                border-radius: 10px;
                margin-bottom: 20px;
            }

            .logo {
                width: 100%;
                max-width: 100px;
                height: auto;
                border-radius: 50%;
                object-fit: contain;
                display: block;
                margin: 0 auto 10px;
            }

            /* Buttons */
            .capture-button {
                padding: 15px 30px;
                font-size: 16px;
                border-radius: 8px;
                border: none;
                cursor: pointer;
                background-color: #e63946;
                color: white;
                transition: 0.3s;
                margin: 5px;
            }

            .capture-button:hover {
                background-color: #ff4d6d;
            }

            .burst-button {
                background-color: #f59e0b;
            }

            .burst-button:hover {
                background-color: #fbbf24;
            }

            /* Feedback message */
            .feedback {
                padding: 10px 20px;
                border-radius: 8px;
                background-color: #22c55e;
                color: white;
                margin-top: 10px;
                display: none;
            }

            .feedback.show {
                display: block;
                animation: fadeOut 2s forwards;
            }

            @keyframes fadeOut {
                0% { opacity: 1; }
                70% { opacity: 1; }
                100% { opacity: 0; display: none; }
            }

            /* System stats panel */
            .stats-panel {
                background-color: #1e293b;
                padding: 15px;
                border-radius: 8px;
                margin-top: 10px;
                text-align: left;
                font-size: 13px;
            }

            .stats-panel h3 {
                margin: 0 0 10px 0;
                font-size: 14px;
            }

            .stat-row {
                display: flex;
                justify-content: space-between;
                padding: 5px 0;
                border-bottom: 1px solid #334155;
            }

            .stat-row:last-child {
                border-bottom: none;
            }

            .hidden {
                display: none;
            }

            a {
                color: #60a5fa;
                text-decoration: none;
            }

            /* Settings */
            .settings-group {
                margin: 15px 0;
                text-align: left;
            }

            .settings-group label {
                display: block;
                margin-bottom: 5px;
                font-size: 13px;
            }

            .settings-group input {
                width: 100%;
                padding: 10px;
                border-radius: 6px;
                border: none;
                background-color: #334155;
                color: white;
                font-size: 14px;
            }

            @media (max-width: 768px) {
                body {
                    flex-direction: column;
                }

                .sidebar {
                    width: 100%;
                    flex-direction: row;
                    flex-wrap: wrap;
                    justify-content: center;
                    padding: 10px;
                }

                .logo-container {
                    width: 100%;
                    text-align: center;
                }

                .logo { max-width: 60px; }
                .sidebar h2 { font-size: 16px; margin-bottom: 10px; }

                .nav-button {
                    width: auto;
                    padding: 10px 15px;
                    margin: 5px;
                    font-size: 12px;
                }

                .main {
                    padding: 15px;
                }

                .content-box {
                    width: 95%;
                }
            }
        </style>
    </head>

    <body>
        <div class="sidebar">
            <div class="logo-container">
                <img src="/static/POLARIS_LOGO.png" class="logo" alt="POLARIS logo">
                <h2>WALDO Live</h2>
            </div>

            <button class="nav-button" onclick="showSection('feed')">📹 Live Feed</button>
            <button class="nav-button" onclick="window.location.href='/gallery'">🖼️ Gallery</button>
            <button class="nav-button" onclick="showSection('system')">📊 System</button>
            <button class="nav-button" onclick="showSection('settings')">⚙️ Settings</button>
            
            <div style="margin-top: auto; padding-top: 20px;">
                <button class="nav-button capture-button" onclick="capturePhoto()">📸 Capture</button>
                <button class="nav-button capture-button burst-button" onclick="burstCapture()">⚡ Burst (5)</button>
            </div>
            
            <div class="feedback" id="feedback">Photo saved!</div>
        </div>

        <div class="main">
            <!-- LIVE FEED -->
            <div id="feed" class="content-box">
                <h1>Live Camera Feed</h1>
                <img src="/video" class="video-feed" alt="Live camera feed">
                <p style="color: #94a3b8; font-size: 12px;">Streaming at low resolution for speed</p>
            </div>

            <!-- SYSTEM INFO -->
            <div id="system" class="content-box hidden">
                <h1>📊 System Status</h1>
                <div class="stats-panel" id="stats-content">
                    <p>Loading...</p>
                </div>
                <button class="nav-button" onclick="loadSystemStats()" style="margin-top: 15px;">🔄 Refresh</button>
            </div>

            <!-- SETTINGS -->
            <div id="settings" class="content-box hidden">
                <h1>⚙️ Settings</h1>
                <div class="settings-group">
                    <label>Auto-capture interval (seconds)</label>
                    <input type="number" id="interval-input" min="5" max="3600" value="10">
                </div>
                <div class="settings-group">
                    <label>Stream quality (1-100)</label>
                    <input type="number" id="quality-input" min="1" max="100" value="70">
                </div>
                <button class="nav-button" onclick="saveSettings()" style="margin-top: 15px;">💾 Save Settings</button>
            </div>
        </div>

        <script>
            // Show/hide sections
            function showSection(section) {
                document.getElementById('feed').classList.add('hidden');
                document.getElementById('system').classList.add('hidden');
                document.getElementById('settings').classList.add('hidden');
                document.getElementById(section).classList.remove('hidden');
                
                if (section === 'system') loadSystemStats();
                if (section === 'settings') loadSettings();
            }

            // Show feedback message
            function showFeedback(message) {
                const fb = document.getElementById('feedback');
                fb.textContent = message;
                fb.classList.remove('show');
                void fb.offsetWidth;  // Force reflow
                fb.classList.add('show');
            }

            // Capture a single photo
            function capturePhoto() {
                fetch('/capture', { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        if (data.status === 'success') {
                            showFeedback('📸 Photo saved!');
                        } else {
                            showFeedback('❌ Capture failed');
                        }
                    })
                    .catch(() => showFeedback('❌ Error'));
            }

            // Burst capture
            function burstCapture() {
                showFeedback('⚡ Capturing burst...');
                fetch('/burst', { 
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ count: 5, delay: 0.2 })
                })
                    .then(r => r.json())
                    .then(data => {
                        showFeedback('⚡ ' + data.count + ' photos captured!');
                    })
                    .catch(() => showFeedback('❌ Burst failed'));
            }

            // Load system stats
            function loadSystemStats() {
                fetch('/system')
                    .then(r => r.json())
                    .then(data => {
                        let html = '';
                        html += '<div class="stat-row"><span>🌡️ CPU Temp</span><span>' + data.cpu_temp + '</span></div>';
                        html += '<div class="stat-row"><span>💾 Disk Used</span><span>' + data.disk_used + ' / ' + data.disk_total + ' (' + data.disk_percent + ')</span></div>';
                        html += '<div class="stat-row"><span>💽 Disk Free</span><span>' + data.disk_free + '</span></div>';
                        html += '<div class="stat-row"><span>📸 Photos</span><span>' + data.photo_count + ' (' + data.photos_size + ')</span></div>';
                        html += '<div class="stat-row"><span>⏱️ Auto-capture</span><span>Every ' + data.auto_capture_interval + '</span></div>';
                        document.getElementById('stats-content').innerHTML = html;
                    })
                    .catch(() => {
                        document.getElementById('stats-content').innerHTML = '<p>Failed to load stats</p>';
                    });
            }

            // Load current settings
            function loadSettings() {
                fetch('/settings')
                    .then(r => r.json())
                    .then(data => {
                        document.getElementById('interval-input').value = data.auto_capture_interval;
                        document.getElementById('quality-input').value = data.stream_quality;
                    });
            }

            // Save settings
            function saveSettings() {
                const interval = document.getElementById('interval-input').value;
                const quality = document.getElementById('quality-input').value;
                
                fetch('/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        auto_capture_interval: parseInt(interval),
                        stream_quality: parseInt(quality)
                    })
                })
                    .then(r => r.json())
                    .then(data => {
                        if (data.status === 'success') {
                            showFeedback('✅ Settings saved!');
                        }
                    })
                    .catch(() => showFeedback('❌ Save failed'));
            }
        </script>
    </body>
    </html>
    '''


@app.route('/video')
def video():
    """Stream live video to the browser."""
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


# ============================================================
# PHOTO CAPTURE - Take and save photos
# ============================================================

@app.route('/capture', methods=['POST'])
def capture():
    """Take a photo and save it."""
    success, frame = read_frame()
    if success:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"shot_{timestamp}.jpg"
        filepath = os.path.join(SAVE_DIR, filename)
        cv2.imwrite(filepath, frame)
        return jsonify({"status": "success", "filename": filename})
    return jsonify({"status": "error", "message": "Camera failed"}), 500


@app.route('/burst', methods=['POST'])
def burst_capture():
    """Take multiple photos in quick succession."""
    count = request.json.get('count', 5) if request.is_json else 5
    delay = request.json.get('delay', 0.2) if request.is_json else 0.2
    
    saved_files = []
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    for i in range(count):
        success, frame = read_frame()
        if success:
            filename = f"burst_{timestamp}_{i+1}.jpg"
            filepath = os.path.join(SAVE_DIR, filename)
            cv2.imwrite(filepath, frame)
            saved_files.append(filename)
        time.sleep(delay)
    
    return jsonify({"status": "success", "files": saved_files, "count": len(saved_files)})


# ============================================================
# GALLERY - View, download, and manage photos
# ============================================================

@app.route('/gallery')
def gallery():
    """Show all captured photos."""
    files = [f for f in os.listdir(SAVE_DIR) if f.endswith('.jpg')]
    files.sort(reverse=True)  # Newest first
    
    # Calculate storage used
    total_size = sum(os.path.getsize(os.path.join(SAVE_DIR, f)) for f in files)
    size_mb = total_size / (1024 * 1024)
    
    return render_template_string(GALLERY_TEMPLATE, files=files, size_mb=size_mb)


@app.route('/photos/<filename>')
def serve_photo(filename):
    """Serve a photo file."""
    return send_from_directory(SAVE_DIR, filename)


@app.route('/download/<filename>')
def download_photo(filename):
    """Download a photo file."""
    return send_from_directory(SAVE_DIR, filename, as_attachment=True)


@app.route('/delete/<filename>', methods=['POST'])
def delete_photo(filename):
    """Delete a single photo."""
    filepath = os.path.join(SAVE_DIR, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "File not found"}), 404


@app.route('/delete_all', methods=['POST'])
def delete_all_photos():
    """Delete all photos (careful!)."""
    files = [f for f in os.listdir(SAVE_DIR) if f.endswith('.jpg')]
    for f in files:
        os.remove(os.path.join(SAVE_DIR, f))
    return jsonify({"status": "success", "deleted": len(files)})


# ============================================================
# SYSTEM INFO - Check Pi status
# ============================================================

@app.route('/system')
def system_info():
    """Get system stats (CPU temp, disk space, etc.)."""
    info = {}
    
    # CPU Temperature
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = int(f.read()) / 1000
            info['cpu_temp'] = f"{temp:.1f}°C"
    except:
        info['cpu_temp'] = "Unknown"
    
    # Disk space
    try:
        total, used, free = shutil.disk_usage('/')
        info['disk_total'] = f"{total // (1024**3)} GB"
        info['disk_used'] = f"{used // (1024**3)} GB"
        info['disk_free'] = f"{free // (1024**3)} GB"
        info['disk_percent'] = f"{(used / total) * 100:.1f}%"
    except:
        info['disk_total'] = "Unknown"
    
    # Photo count and size
    files = [f for f in os.listdir(SAVE_DIR) if f.endswith('.jpg')]
    total_size = sum(os.path.getsize(os.path.join(SAVE_DIR, f)) for f in files)
    info['photo_count'] = len(files)
    info['photos_size'] = f"{total_size / (1024*1024):.1f} MB"
    
    # Auto-capture status
    info['auto_capture_interval'] = f"{AUTO_CAPTURE_INTERVAL} seconds"
    
    return jsonify(info)


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """View or update settings."""
    global AUTO_CAPTURE_INTERVAL, STREAM_QUALITY
    
    if request.method == 'POST':
        data = request.json
        if 'auto_capture_interval' in data:
            AUTO_CAPTURE_INTERVAL = int(data['auto_capture_interval'])
        if 'stream_quality' in data:
            STREAM_QUALITY = int(data['stream_quality'])
        return jsonify({"status": "success"})
    
    return jsonify({
        "auto_capture_interval": AUTO_CAPTURE_INTERVAL,
        "stream_quality": STREAM_QUALITY,
        "stream_width": STREAM_WIDTH,
        "stream_height": STREAM_HEIGHT
    })


# ============================================================
# AUTO CAPTURE - Background photo capture
# ============================================================

def periodic_capture():
    """Automatically capture photos at regular intervals."""
    while True:
        success, frame = read_frame()
        if success:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"auto_{timestamp}.jpg"
            filepath = os.path.join(SAVE_DIR, filename)
            cv2.imwrite(filepath, frame)
            
            # Clean up old photos if we're using too much storage
            cleanup_old_photos()
        
        time.sleep(AUTO_CAPTURE_INTERVAL)


def cleanup_old_photos():
    """Delete oldest photos if storage exceeds limit."""
    files = [f for f in os.listdir(SAVE_DIR) if f.endswith('.jpg')]
    files.sort()  # Oldest first
    
    total_size = sum(os.path.getsize(os.path.join(SAVE_DIR, f)) for f in files)
    max_bytes = MAX_STORAGE_MB * 1024 * 1024
    
    # Delete oldest files until we're under the limit
    while total_size > max_bytes and len(files) > 10:
        oldest = files.pop(0)
        filepath = os.path.join(SAVE_DIR, oldest)
        file_size = os.path.getsize(filepath)
        os.remove(filepath)
        total_size -= file_size


# ============================================================
# STARTUP
# ============================================================

if __name__ == "__main__":
    print("🚀 Starting WALDO Camera System...")
    print(f"📁 Photos will be saved to: {SAVE_DIR}")
    print(f"📸 Auto-capture every {AUTO_CAPTURE_INTERVAL} seconds")
    print(f"🌐 Access at http://<pi-ip>:5000")
    
    # Start the auto-capture background thread
    capture_thread = threading.Thread(target=periodic_capture, daemon=True)
    capture_thread.start()
    
    # Run the web server
    app.run(host='0.0.0.0', port=5000, threaded=True)
