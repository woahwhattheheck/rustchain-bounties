import hashlib
import json
import os
import sqlite3
import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from flask import Flask

from node import beacon_api as beacon_module


def _client(tmp_path, monkeypatch):
    db_path = tmp_path / "beacon-agent-messages.db"
    monkeypatch.setattr(beacon_module, "DB_PATH", str(db_path))
    beacon_module.init_beacon_tables(str(db_path))
    app = Flask(__name__)
    app.register_blueprint(beacon_module.beacon_api, url_prefix="/beacon")
    app.config.update(TESTING=True)
    return app.test_client(), db_path


def _identity(db_path, name):
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    agent_id = f"bcn_{hashlib.sha256(public_key).hexdigest()[:12]}"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO relay_agents
               (agent_id, pubkey_hex, name, status, created_at)
               VALUES (?, ?, ?, 'active', ?)""",
            (agent_id, public_key.hex(), name, int(time.time())),
        )
        conn.commit()
    return agent_id, private_key


def _signed_post(client, path, payload, identity, nonce=None):
    agent_id, private_key = identity
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    timestamp = int(time.time())
    nonce = nonce or os.urandom(8).hex()
    canonical = "\n".join(
        [
            "POST",
            path,
            hashlib.sha256(body).hexdigest(),
            str(timestamp),
            nonce,
            agent_id,
        ]
    ).encode("utf-8")
    return client.post(
        path,
        data=body,
        content_type="application/json",
        headers={
            "X-Agent-Id": agent_id,
            "X-Agent-Timestamp": str(timestamp),
            "X-Agent-Nonce": nonce,
            "X-Agent-Signature": private_key.sign(canonical).hex(),
        },
    )


def test_signed_sender_delivers_and_recipient_reads(tmp_path, monkeypatch):
    client, db_path = _client(tmp_path, monkeypatch)
    sender = _identity(db_path, "sender")
    recipient = _identity(db_path, "recipient")

    sent = _signed_post(
        client,
        "/beacon/api/agent-messages",
        {
            "from_agent": sender[0],
            "to_agent": recipient[0],
            "message": "Atlas rendezvous at compiler_heights",
        },
        sender,
    )
    assert sent.status_code == 201
    assert sent.get_json()["message"]["from_agent"] == sender[0]

    inbox = _signed_post(
        client,
        "/beacon/api/agent-messages/query",
        {"agent_id": recipient[0], "peer": sender[0], "limit": 10},
        recipient,
    )
    assert inbox.status_code == 200
    messages = inbox.get_json()["messages"]
    assert len(messages) == 1
    assert messages[0]["content"] == "Atlas rendezvous at compiler_heights"


def test_sender_cannot_impersonate_recipient_mailbox(tmp_path, monkeypatch):
    client, db_path = _client(tmp_path, monkeypatch)
    sender = _identity(db_path, "sender")
    recipient = _identity(db_path, "recipient")
    response = _signed_post(
        client,
        "/beacon/api/agent-messages/query",
        {"agent_id": recipient[0], "limit": 10},
        sender,
    )
    assert response.status_code == 403


def test_missing_signature_is_rejected(tmp_path, monkeypatch):
    client, db_path = _client(tmp_path, monkeypatch)
    sender = _identity(db_path, "sender")
    recipient = _identity(db_path, "recipient")
    response = client.post(
        "/beacon/api/agent-messages",
        json={
            "from_agent": sender[0],
            "to_agent": recipient[0],
            "message": "unsigned",
        },
    )
    assert response.status_code == 401


def test_nonce_replay_is_rejected(tmp_path, monkeypatch):
    client, db_path = _client(tmp_path, monkeypatch)
    sender = _identity(db_path, "sender")
    recipient = _identity(db_path, "recipient")
    payload = {
        "from_agent": sender[0],
        "to_agent": recipient[0],
        "message": "once only",
    }
    nonce = "fixed-replay-nonce"
    first = _signed_post(
        client, "/beacon/api/agent-messages", payload, sender, nonce=nonce
    )
    second = _signed_post(
        client, "/beacon/api/agent-messages", payload, sender, nonce=nonce
    )
    assert first.status_code == 201
    assert second.status_code == 401
