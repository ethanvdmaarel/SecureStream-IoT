# SecureStream — Raspberry Pi Pico 2 W device

This folder contains everything the Pico 2 W needs to join the SecureStream
pipeline: a registration script that runs once in Cloud Shell, and the
device-side MicroPython code that runs on the Pico itself.

## What the Pico does

- Joins the configured WiFi network on boot
- Syncs its clock to NTP so JWT timestamps validate at the ingest service
- Reads the on-chip temperature sensor inside the RP2350 every 5 seconds
- Builds a JWT carrying that reading, signs it with HMAC-SHA256
- POSTs the raw JWT to the SecureStream Cloud Run ingest service
- Occasionally injects a spike so the anomaly query has something to flag

## Why HS256 and not ES256

The 12 simulated devices use ES256, where each device has its own ECDSA
P-256 private key. That is the stronger scheme. On a microcontroller it
needs an extra library that does not ship with MicroPython, and each
signing takes 1 to 2 seconds.

The Pico uses HS256 instead. One shared HMAC secret lives on the device
and in Firestore, and the ingest service verifies signatures with the
same key. Signing is one HMAC and finishes instantly. The ingest service
already supports both schemes per device, see `ingest/main.py`.

This is a real-world trade-off, not a corner cut. The report should call
it out: a production design would use a secure element such as the
ATECC608A to do on-board ES256 signing without the speed problem.

## Step 1 — Flash MicroPython on the Pico

1. Download the latest Pico 2 W MicroPython UF2 from
   https://micropython.org/download/RPI_PICO2_W/
2. Hold the BOOTSEL button on the Pico while plugging the USB cable into
   your laptop. The Pico mounts as a USB drive called `RPI-RP2`.
3. Drag the UF2 file onto that drive. The Pico reboots, the drive
   disappears, and MicroPython is now installed.

## Step 2 — Install Thonny

Thonny is the easiest editor for Pico work. Download from
https://thonny.org/. After installing, open Thonny, go to Tools then
Options then Interpreter, pick "MicroPython (Raspberry Pi Pico)" and the
USB port your Pico is on. The bottom panel should show a `>>>` prompt.

`mpremote` from the command line works too if you prefer it.

## Step 3 — Register the Pico in Firestore

This step lives in Cloud Shell, not on your laptop. Push this whole
`pico/` folder to the SecureStream GitHub repo, then in Cloud Shell:

```
cd ~/SecureStream-IoT/securestream
pip install --user -r pico/requirements.txt
python pico/register_pico.py
```

The script generates a random 256-bit HMAC secret, writes it to
Firestore under `devices/pico-01` with `algorithm: HS256`, and prints it
to the terminal. It also saves it to `pico/pico_secret.txt`. Copy the
secret somewhere safe, you need it in the next step. Both files are
gitignored so the secret never reaches GitHub.

To register more than one Pico, pass a different device id:

```
python pico/register_pico.py pico-02
```

## Step 4 — Make your config.py

On your laptop, copy `config.example.py` to `config.py` in the same
folder and fill in:

- `WIFI_SSID` and `WIFI_PASSWORD` — the network the Pico will join
- `DEVICE_ID` — must match what you used in step 3, default `pico-01`
- `SHARED_SECRET` — the hex string from step 3
- `INGEST_URL` — already set to the deployed Cloud Run URL, leave it

`config.py` is gitignored. The secret lives only on your laptop and on
the Pico, never in the repo.

## Step 5 — Copy the code to the Pico

In Thonny, with the Pico connected:

1. Open `boot.py`, save it to the Pico as `boot.py`
2. Open `main.py`, save it to the Pico as `main.py`
3. Open your `config.py`, save it to the Pico as `config.py`

The Pico now has three files in its root: `boot.py`, `main.py`, `config.py`.

## Step 6 — Reboot and watch

In the Thonny REPL panel press Ctrl+D, or unplug and replug the Pico.
You should see something like:

```
wifi: connecting to your-wifi
wifi: connected ('192.168.1.42', ...)
ntp: clock synced (2026, 5, 28, 9, 12, 4, ...)
boot: ready, handing over to main.py
pico ready, sending to https://securestream-ingest-... every 5s
pico-01  temperature=24.31  ok
pico-01  temperature=24.18  ok
pico-01  temperature=78.4   ok ⚠ANOMALY
```

`ok` means the ingest service returned HTTP 202, the JWT verified and the
reading was published to Pub/Sub.

## Step 7 — Verify in BigQuery

In Cloud Shell:

```
bq query --use_legacy_sql=false \
  'SELECT publish_time, data FROM securestream.raw_telemetry
   WHERE JSON_VALUE(data, "$.device_id") = "pico-01"
   ORDER BY publish_time DESC LIMIT 10'
```

You should see Pico readings landing alongside the simulator readings.
To see the flagged anomalies:

```
bq query --use_legacy_sql=false \
  'SELECT device_id, value, reason, event_time FROM securestream.flagged_events
   WHERE device_id = "pico-01"
   ORDER BY event_time DESC LIMIT 10'
```

## Troubleshooting

- **`wifi: failed to connect`** — wrong SSID or password in `config.py`.
  Also make sure the network is 2.4 GHz, the Pico 2 W does both bands
  but campus 5 GHz networks sometimes use authentication the chip
  cannot handle.
- **`ntp: could not sync clock`** — the network is blocking outbound
  UDP port 123. Try a hotspot from your phone, or hard-code a different
  NTP server with `ntptime.host = "time.google.com"` before calling
  `settime()`.
- **`HTTP 401 signature verification failed`** — the secret in `config.py`
  does not match what is in Firestore. Re-run `register_pico.py` and
  paste the new secret.
- **`HTTP 401 token expired`** — clock not synced. The boot script
  raised an exception, scroll up in the REPL to see why.
- **`HTTP 401 unknown device`** — the `DEVICE_ID` in `config.py` does
  not exist in Firestore. Check the spelling.
- **Tokens validate but readings never reach BigQuery** — the Pub/Sub
  to BigQuery subscription can lag. Wait 1 to 2 minutes and try again.

## Files

- `register_pico.py` — runs once in Cloud Shell, registers the Pico
- `requirements.txt` — Python deps for the registration step
- `config.example.py` — template you copy to `config.py`
- `boot.py` — runs on the Pico at power-on, WiFi plus NTP
- `main.py` — runs on the Pico after boot, the read-sign-send loop
