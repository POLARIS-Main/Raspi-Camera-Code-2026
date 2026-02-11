# WALDO Setup Guide

This repository already contains the camera server (`app.py`) that streams video over Bluetooth and saves photos locally. Follow these steps to prepare a Raspberry Pi Zero 2 W and start the application.

## Prerequisites

* Raspberry Pi Zero 2 W running Raspberry Pi OS (Lite or Desktop)
* Pi Camera Module connected and enabled via `raspi-config`
* Bluetooth adapter (built-in on the Pi Zero 2 W)
* A client device (phone/laptop) that can pair over Bluetooth

## Install the required packages

```bash
sudo apt update
sudo apt install bluez python3-pip python3-opencv python3-flask
python3 -m pip install --upgrade pip
```

## Configure Bluetooth Personal Area Network (PAN)

1. Start the Bluetooth control utility:
   ```bash
   sudo bluetoothctl
   ```
2. Inside the interactive prompt, enable power, discoverability, and pairability:
   ```
   power on
   discoverable on
   pairable on
   exit
   ```
3. On your phone or laptop, pair with the Pi and join the Personal Area Network (Bluetooth tethering).

## Run the existing server

1. Navigate to this project directory:
   ```bash
   cd /path/to/Raspi-Camera-Code-2026
   ```
2. Start the Flask server:
   ```bash
   python3 app.py
   ```

## Access the live feed

1. Find the Pi IP address assigned to the Bluetooth interface with:
   ```bash
   hostname -I
   ```
2. Open a browser on the paired device and visit `http://[PI_BLUETOOTH_IP]:5000` to view the stream and capture button.

## Notes

* The script creates `moon_shots/` automatically and keeps saving captures even when the viewer disconnects.
* You can adjust Bluetooth or Flask runtime settings by editing `app.py`, but the code itself already exists in this repo.