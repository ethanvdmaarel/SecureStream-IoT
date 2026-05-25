"""SecureStream device fleet simulator.

Loads the private keys created by register_devices.py, then loops forever:
every few seconds each simulated device takes a temperature reading, signs
it as a JWT, and POSTs it to the ingest service.

Roughly one in twenty readings is deliberately abnormal, so the anomaly
detection step has something to catch later.

Usage:
    python simulator.py https://YOUR-INGEST-URL
"""
import os
import sys
import time
import random
import datetime

import jwt
import requests

# keys/ always sits next to this script, no matter where you run it from.
KEYS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys")

SEND_INTERVAL_SECONDS = 5
NORMAL_RANGE = (18.0, 26.0)
ANOMALY_CHANCE = 0.05


def load_devices():
    """Return a dict of device_id -> private key PEM bytes."""
    if not os.path.isdir(KEYS_DIR):
        sys.exit("keys/ folder not found, run register_devices.py first")

    devices = {}
    for name in sorted(os.listdir(KEYS_DIR)):
        if name.endswith(".pem"):
            device_id = name[:-4]
            with open(os.path.join(KEYS_DIR, name), "rb") as fh:
                devices[device_id] = fh.read()

    if not devices:
        sys.exit("no keys found, run register_devices.py first")
    return devices


def make_reading():
    """Return a temperature value, occasionally an abnormal spike."""
    if random.random() < ANOMALY_CHANCE:
        return round(random.uniform(60.0, 95.0), 2)
    return round(random.uniform(*NORMAL_RANGE), 2)


def signed_token(device_id, private_key, value):
    """Build and sign a JWT carrying one temperature reading."""
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "device_id": device_id,
        "metric": "temperature",
        "value": value,
        "iat": int(now.timestamp()),
        "exp": int((now + datetime.timedelta(minutes=5)).timestamp()),
    }
    return jwt.encode(
        payload, private_key, algorithm="ES256", headers={"kid": device_id}
    )


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python simulator.py https://YOUR-INGEST-URL")
    ingest_url = sys.argv[1].rstrip("/") + "/ingest"

    devices = load_devices()
    print(f"loaded {len(devices)} devices, sending to {ingest_url}")
    print("press Ctrl+C to stop")

    while True:
        for device_id, private_key in devices.items():
            value = make_reading()
            token = signed_token(device_id, private_key, value)
            try:
                resp = requests.post(ingest_url, data=token, timeout=10)
                tag = "ok" if resp.status_code == 202 else f"HTTP {resp.status_code}"
                print(f"{device_id}  temperature={value}  {tag}")
            except requests.RequestException as exc:
                print(f"{device_id}  send failed: {exc}")
        time.sleep(SEND_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
