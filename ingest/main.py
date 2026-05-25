"""SecureStream ingest service.

Receives signed device telemetry over HTTPS, verifies the JWT signature
against the device's key in the Firestore registry, and republishes the
validated reading to the Pub/Sub telemetry topic.

A device sends an HTTP POST to /ingest with the raw JWT as the request body.
The JWT header carries the device id in its 'kid' field, and the JWT payload
carries the actual reading.
"""
import os
import json
import datetime

from flask import Flask, request, jsonify
import jwt
from google.cloud import firestore
from google.cloud import pubsub_v1

PROJECT_ID = os.environ["PROJECT_ID"]
TOPIC_ID = os.environ.get("TOPIC_ID", "telemetry")

app = Flask(__name__)
db = firestore.Client(project=PROJECT_ID)
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)


@app.get("/")
def health():
    """Simple health check so you can open the URL in a browser."""
    return "SecureStream ingest is running.", 200


@app.post("/ingest")
def ingest():
    # The device sends the raw JWT as the request body.
    token = request.get_data(as_text=True).strip()
    if not token:
        return jsonify(error="empty body, expected a JWT"), 400

    # Read the device id from the JWT header without verifying yet.
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        return jsonify(error=f"malformed token: {exc}"), 400

    device_id = header.get("kid")
    if not device_id:
        return jsonify(error="token header has no kid (device id)"), 400

    # Look the device up in the Firestore registry.
    snapshot = db.collection("devices").document(device_id).get()
    if not snapshot.exists:
        print(f"REJECT unknown device: {device_id}")
        return jsonify(error="unknown device"), 401

    device = snapshot.to_dict()
    if device.get("status") != "active":
        print(f"REJECT inactive device: {device_id}")
        return jsonify(error="device is not active"), 403

    # The registry records which algorithm the device uses and the matching
    # key material. ES256 stores a public key, HS256 stores a shared secret.
    algorithm = device.get("algorithm", "ES256")
    key = device.get("public_key") if algorithm == "ES256" else device.get("secret")
    if not key:
        print(f"REJECT device {device_id}: no key material registered")
        return jsonify(error="device has no key on file"), 401

    # Verify the signature and the expiry.
    try:
        payload = jwt.decode(token, key, algorithms=[algorithm])
    except jwt.ExpiredSignatureError:
        print(f"REJECT expired token from {device_id}")
        return jsonify(error="token expired"), 401
    except jwt.InvalidTokenError as exc:
        print(f"REJECT bad signature from {device_id}: {exc}")
        return jsonify(error="signature verification failed"), 401

    # Build the clean telemetry record and publish it to Pub/Sub.
    issued = int(payload.get("iat", 0))
    reading = {
        "device_id": device_id,
        "metric": payload.get("metric"),
        "value": payload.get("value"),
        "ts": datetime.datetime.fromtimestamp(
            issued, datetime.timezone.utc
        ).isoformat(),
    }
    publisher.publish(topic_path, json.dumps(reading).encode("utf-8")).result()
    print(f"ACCEPT {device_id}: {reading['metric']}={reading['value']}")
    return jsonify(status="accepted"), 202


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
