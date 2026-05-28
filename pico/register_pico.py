"""Register a Raspberry Pi Pico 2 W in the Firestore key registry.

The Pico is a microcontroller, so signing each message with an ECDSA P-256
private key (what the simulator does) is too slow and needs a library that
does not ship with MicroPython. The Pico therefore uses HS256 instead: one
shared secret lives both on the device and in Firestore, and the ingest
service compares HMAC signatures.

Trade-off worth noting in the report: with HS256 a compromised device key
also lets the attacker forge messages for that device, while ES256 keeps
the private key on the device only. In production you would use a secure
element such as the ATECC608A to do ES256 signing on-board.

Run this once from Cloud Shell, then copy the printed secret into
pico/config.py before flashing the Pico.

Usage:
    python register_pico.py            # uses default device id "pico-01"
    python register_pico.py pico-02    # any device id you like
"""
import os
import secrets
import sys

from google.cloud import firestore

DEFAULT_DEVICE_ID = "pico-01"
SECRET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pico_secret.txt")


def main():
    device_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DEVICE_ID

    # 32 random bytes, hex-encoded, gives a 256-bit HMAC key.
    shared_secret = secrets.token_hex(32)

    db = firestore.Client()
    db.collection("devices").document(device_id).set({
        "algorithm": "HS256",
        "secret": shared_secret,
        "status": "active",
        "kind": "pico-2w",
        "created_at": firestore.SERVER_TIMESTAMP,
    })

    # Save the secret locally too, so you do not have to scroll back later.
    with open(SECRET_FILE, "w") as fh:
        fh.write(shared_secret + "\n")

    print(f"registered {device_id} with HS256")
    print()
    print("shared secret (paste this into pico/config.py):")
    print(shared_secret)
    print()
    print(f"also saved to {SECRET_FILE}")


if __name__ == "__main__":
    main()
