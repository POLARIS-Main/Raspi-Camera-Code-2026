# WALDO: Bluetooth Camera & Local Storage

This guide sets up a Raspberry Pi Zero 2 W to stream live video over a Bluetooth network and save high-res photos to an internal folder (for when it wanders out of range).

## Prerequisites

* Raspberry Pi Zero 2 W with Raspberry Pi OS installed
* Pi Camera Module connected and enabled
* A phone or laptop for viewing the feed

## 1. Setup the "Moon" Network (Bluetooth PAN)

Since there's no Wi-Fi on the moon, we'll use the Pi as a Bluetooth Access Point.

### Install dependencies

```bash
sudo apt update
sudo apt install bluez python3-pip python3-opencv flask
```

### Make the Pi discoverable

```bash
sudo bluetoothctl
```

Inside the Bluetooth prompt, type:

```
power on
discoverable on
pairable on
exit
```

### Connect your device

Go to your phone/laptop Bluetooth settings, pair with the Pi, and select "Join Personal Area Network" (or "Bluetooth Tethering").

## 2. The Main Code

Create a folder for your project and a file named `app.py`. This script handles the live stream and the "Save Photo" logic.

```python
import cv2
import os
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

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
```

## 3. How to Run & View

### Start the script

```bash
python3 app.py
```

### Find the IP

Type `hostname -I` in your terminal. It usually starts with `192.168...` (look for the Bluetooth interface IP).

### Open the Site

On your paired phone, open the browser and go to:

```
http://[YOUR_PI_IP]:5000
```

## 4. Troubleshooting the "Moon" Environment

* **Video is laggy**: Bluetooth is slow. If it freezes, lower the numbers in the `cv2.resize` line (e.g., `160, 120`).

* **Connection lost**: If the robot goes out of range, the site will stop loading. It will automatically work again once you get back within ~20 feet.

* **Auto-Start**: To make this run as soon as the Pi gets power, add `python3 /path/to/app.py &` to your `/etc/rc.local` file.

## Project Structure

```
moonbot/
├── app.py              # Main application
└── moon_shots/         # Captured photos (auto-created)
    ├── shot_143022.jpg
    ├── shot_143045.jpg
    └── ...
```

## Features

- **Live streaming** over Bluetooth PAN
- **High-resolution capture** stored locally
- **Web interface** accessible from any paired device
- **Offline operation** - photos saved even when out of range

---
