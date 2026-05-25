"""Register simulated devices in the Firestore key registry.

For each device this generates an ES256 (ECDSA P-256) key pair, stores the
public key in Firestore under the 'devices' collection, and saves the private
key locally in keys/<device_id>.pem so the simulator can sign with it.

Only the public key ever leaves this machine. Run this script once before
running simulator.py.
"""
import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from google.cloud import firestore

# How many simulated devices to create.
DEVICE_COUNT = 12

# keys/ always sits next to this script, no matter where you run it from.
KEYS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys")

db = firestore.Client()


def device_ids():
    return [f"sim-{i:02d}" for i in range(1, DEVICE_COUNT + 1)]


def register(device_id):
    # Generate a fresh ECDSA P-256 key pair for this device.
    private_key = ec.generate_private_key(ec.SECP256R1())

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # Save the private key locally. This file is secret, keys/ is gitignored.
    os.makedirs(KEYS_DIR, exist_ok=True)
    with open(os.path.join(KEYS_DIR, f"{device_id}.pem"), "wb") as fh:
        fh.write(private_pem)

    # Store only the public key in the registry.
    db.collection("devices").document(device_id).set({
        "algorithm": "ES256",
        "public_key": public_pem.decode("utf-8"),
        "status": "active",
        "created_at": firestore.SERVER_TIMESTAMP,
    })
    print(f"registered {device_id}")


if __name__ == "__main__":
    for device_id in device_ids():
        register(device_id)
    print(f"done, {DEVICE_COUNT} devices registered in Firestore")
