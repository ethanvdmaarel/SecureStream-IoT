"""Pico 2 W boot script — runs once at power-on.

Two jobs:
1. Join the WiFi network so HTTPS requests work later.
2. Sync the on-board clock to NTP. The ingest service verifies JWT 'exp'
   and 'iat' timestamps, and without NTP the Pico's clock starts at the
   year 2000 and every token gets rejected as expired.

The main loop in main.py only runs after this script completes.
"""
import time
import network
import ntptime

import config


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        print("wifi: already connected", wlan.ifconfig())
        return

    print(f"wifi: connecting to {config.WIFI_SSID}")
    wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)

    # Wait up to 20 seconds for a DHCP lease.
    for _ in range(40):
        if wlan.isconnected():
            print("wifi: connected", wlan.ifconfig())
            return
        time.sleep(0.5)

    raise RuntimeError("wifi: failed to connect within 20s")


def sync_clock():
    # ntptime.settime() blocks until it gets a response. Retry a few times
    # because pool.ntp.org sometimes drops the first packet.
    for attempt in range(5):
        try:
            ntptime.settime()
            print("ntp: clock synced", time.gmtime())
            return
        except Exception as exc:
            print(f"ntp: attempt {attempt + 1} failed: {exc}")
            time.sleep(2)
    raise RuntimeError("ntp: could not sync clock after 5 attempts")


connect_wifi()
sync_clock()
print("boot: ready, handing over to main.py")
