"""Pico 2 W main loop — read temperature, sign as JWT, POST to ingest.

Runs forever after boot.py finishes. Every SEND_INTERVAL seconds it:
1. Reads the on-chip temperature sensor (ADC channel 4 on the RP2350).
2. Builds a JWT carrying that reading, signed with HMAC-SHA256.
3. POSTs the raw JWT to the SecureStream ingest service.

Roughly 1 in 20 readings is replaced with a deliberate spike so the
anomaly detection query has live Pico data to flag during the demo.

Everything is hand-rolled because MicroPython does not ship the PyJWT
library. The format on the wire is exactly the same as what the simulator
produces, just with alg=HS256 instead of ES256.
"""
import time
import json
import hashlib
import binascii
import machine
import urequests
import urandom

import config

# RP2350 internal temperature sensor lives on ADC channel 4.
TEMP_SENSOR = machine.ADC(4)
ADC_CONVERSION = 3.3 / 65535

# Same anomaly ratio and ranges as the simulator, so dashboards match.
NORMAL_RANGE = (18.0, 26.0)
ANOMALY_RANGE = (60.0, 95.0)
ANOMALY_CHANCE = 0.05

SECRET_BYTES = config.SHARED_SECRET.encode("utf-8")


def read_temperature_c():
    """Read the on-chip temperature sensor and convert to Celsius.

    Formula from the RP2350 datasheet: T = 27 - (V - 0.706) / 0.001721,
    where V is the ADC voltage in volts.
    """
    raw = TEMP_SENSOR.read_u16()
    voltage = raw * ADC_CONVERSION
    return 27 - (voltage - 0.706) / 0.001721


def make_reading():
    """Return the value to send. Mostly real, sometimes a spike."""
    if urandom.random() < ANOMALY_CHANCE:
        spike = ANOMALY_RANGE[0] + urandom.random() * (ANOMALY_RANGE[1] - ANOMALY_RANGE[0])
        return round(spike, 2), True
    real = read_temperature_c()
    # Clamp to the normal range so a cold lab does not flood flagged_events.
    real = max(NORMAL_RANGE[0], min(NORMAL_RANGE[1], real))
    return round(real, 2), False


def b64url(data):
    """Base64url-encode bytes, no padding, no newlines."""
    encoded = binascii.b2a_base64(data).rstrip(b"\n").rstrip(b"=")
    return encoded.replace(b"+", b"-").replace(b"/", b"_")


def hmac_sha256(key, msg):
    """HMAC-SHA256, implemented by hand because MicroPython lacks hmac."""
    block_size = 64
    if len(key) > block_size:
        key = hashlib.sha256(key).digest()
    if len(key) < block_size:
        key = key + b"\x00" * (block_size - len(key))

    ipad = bytes(b ^ 0x36 for b in key)
    opad = bytes(b ^ 0x5c for b in key)

    inner = hashlib.sha256(ipad + msg).digest()
    return hashlib.sha256(opad + inner).digest()


def build_jwt(value):
    """Build a signed JWT carrying one temperature reading."""
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT", "kid": config.DEVICE_ID}
    payload = {
        "device_id": config.DEVICE_ID,
        "metric": "temperature",
        "value": value,
        "iat": now,
        "exp": now + 300,  # 5 minute window, same as the simulator
    }

    header_b64 = b64url(json.dumps(header).encode("utf-8"))
    payload_b64 = b64url(json.dumps(payload).encode("utf-8"))
    signing_input = header_b64 + b"." + payload_b64

    signature = b64url(hmac_sha256(SECRET_BYTES, signing_input))
    return signing_input + b"." + signature


def send_reading():
    value, is_anomaly = make_reading()
    token = build_jwt(value)
    try:
        resp = urequests.post(config.INGEST_URL, data=token)
        status = resp.status_code
        resp.close()
        tag = "ok" if status == 202 else f"HTTP {status}"
        flag = " ⚠ANOMALY" if is_anomaly else ""
        print(f"{config.DEVICE_ID}  temperature={value}  {tag}{flag}")
    except Exception as exc:
        print(f"{config.DEVICE_ID}  send failed: {exc}")


print(f"pico ready, sending to {config.INGEST_URL} every {config.SEND_INTERVAL}s")
while True:
    send_reading()
    time.sleep(config.SEND_INTERVAL)
