# Copy this file to config.py on the Pico and fill in your own values.
# config.py is gitignored so the secret never leaves the device.

# WiFi network the Pico joins on boot.
WIFI_SSID = "your-wifi-name"
WIFI_PASSWORD = "your-wifi-password"

# Device identity in the Firestore registry. Must match what you passed
# to register_pico.py (default is "pico-01").
DEVICE_ID = "pico-01"

# Shared HMAC secret printed by register_pico.py. Paste the 64-char hex string.
SHARED_SECRET = "paste-the-hex-string-from-register_pico-here"

# Cloud Run ingest URL from the SecureStream deploy.
INGEST_URL = "https://securestream-ingest-972935473814.asia-east1.run.app/ingest"

# How often to send a reading, in seconds.
SEND_INTERVAL = 5
