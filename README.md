# POLARIS Pi Zero 2 W Setup Guide

This guide walks through setting up your POLARIS camera + Flask app on a Raspberry Pi Zero 2 W, including all dependencies and workarounds needed to get it running.

## 1️⃣ Flash Raspberry Pi OS (Headless)

1. Download **Raspberry Pi OS Lite (64-bit)** from the [Raspberry Pi website](https://www.raspberrypi.com/software/).
2. Flash it using **Raspberry Pi Imager**:
   - Enable SSH
   - Configure Wi-Fi (or plan to use Ethernet)
   - Set your username/password
3. Insert SD card and boot Pi. This can take upwards of 10 minutes; be patient.

## 2️⃣ SSH Into the Pi

```bash
ssh pi@<PI_HOSTNAME>
```

Replace `<PI_HOSTNAME>` with your Pi's IP. For Ethernet, you can find the Pi's IP in your router's connected devices.

If that doesn't work... ping each ip in a range with this command:

```bash
for /L %i in (0,1,255) do @ping -n 1 -w 100 192.168.0.%i | find "TTL="
```

## 3️⃣ Update System Packages

```bash
sudo apt update && sudo apt upgrade -y
```

## 4️⃣ Install Dependencies

### Recommended: System OpenCV + Flask (lightweight)

```bash
sudo apt install python3-opencv python3-flask git -y
```

✅ Test OpenCV:

```bash
python3 -c "import cv2; print(cv2.__version__)"
```

### Alternative: Pip / Virtual Environment (if newer OpenCV needed)

```bash
sudo apt install python3-pip python3-venv -y
python3 -m venv waldo_env
source waldo_env/bin/activate
pip install --upgrade pip
pip install opencv-python-headless flask
```

- Use `opencv-python-headless` to save memory (no GUI needed).

## 5️⃣ Clone Your POLARIS Repo

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/POLARIS.git
cd POLARIS
```

- Make sure the main script is called `app.py`.
- If the repo is private, use a personal access token:

```bash
git clone https://USERNAME:TOKEN@github.com/USERNAME/POLARIS.git
```

## 6️⃣ Create Save Directory

```bash
mkdir -p moon_shots
chmod 755 moon_shots
```

- This folder stores captured photos.

## 7️⃣ Running the App

- If using system packages:

```bash
python3 app.py
```

- If using virtual environment:

```bash
source waldo_env/bin/activate
python3 app.py
```

Access from browser:

```
http://<PI_IP_ADDRESS>:5000
```

## 8️⃣ Auto-Start on Boot (Optional)

Create a service file:

```bash
sudo nano /etc/systemd/system/waldo.service
```

Paste:

```ini
[Unit]
Description=POLARIS Camera Server
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/POLARIS
ExecStart=/usr/bin/python3 /home/pi/POLARIS/app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable waldo.service
sudo systemctl start waldo.service
sudo systemctl status waldo.service
```

## 9️⃣ Updating the Repo Over SSH

```bash
cd ~/POLARIS
git fetch
git pull origin main
```

Optional forced update (overwrites local changes):

```bash
git fetch --all
git reset --hard origin/main
```

## 🔹 Notes / Troubleshooting

| Problem | Fix |
|---------|-----|
| `python-opencv` not found | Use `python3-opencv` or `opencv-python-headless` |
| `app.py` not found | Navigate to the correct repo folder (`cd ~/POLARIS`) |
| Weird LED blink / no boot | Reflash SD card, use good quality 16GB+ card, check power supply ≥2.5A |
| Network scanning | Use ping sweep: `for i in {1..254}; do ping -c1 -W1 192.168.0.$i >/dev/null 2>&1 && echo 192.168.0.$i is up & done; wait` |
| Ethernet setup | Use USB-to-Ethernet adapter and check `ip a` for `eth0` IP |

## 🔟 Quick One-Line Update + Run (Optional)

```bash
cd ~/POLARIS && git fetch && git pull && python3 app.py
```

- Updates your repo and starts the app in one command.
