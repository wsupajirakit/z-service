"""Inbound events: Standard Webhooks signatures (v1 HMAC, v1a Ed25519), freshness,
CloudEvents shape, one stored copy per webhook id; the receiving path needs no session
while the list does."""

import base64
import hashlib
import hmac
import json
import os
import time

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from tests.fakes import swap_repos

from zservice.core import config as zs_config
from zservice.core.errors import ApiError
from zservice.domains.inbound_events import service

SECRET = "whsec_" + base64.b64encode(os.urandom(32)).decode()
PRIVATE = Ed25519PrivateKey.generate()
PUBLIC = (
    "whpk_"
    + base64.b64encode(
        PRIVATE.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
    ).decode()
)
EVENT = {
    "specversion": "1.0",
    "id": "e1",
    "source": "https://engine.test/v1/projects/p",
    "type": "run.completed",
    "subject": "runs/r1",
    "time": "2026-10-25T00:00:00+00:00",
    "data": {"run_id": "r1", "links": {"ui": "https://engine.test/projects/p?tab=runs&run=r1"}},
}


class FakeRepo:
    def __init__(self):
        self.rows: dict[tuple[str, str], dict] = {}

    def inbound_insert(self, doc):
        key = (doc["sender"], doc["webhook_id"])
        if key in self.rows:
            return False
        self.rows[key] = doc
        return True

    def inbound_list(self, limit, sender=None, event_type=None):
        rows = [
            r
            for r in self.rows.values()
            if (not sender or r["sender"] == sender) and (not event_type or r["type"] == event_type)
        ]
        return [dict(r) for r in rows][:limit]


@pytest.fixture
def repo(monkeypatch):
    fake = FakeRepo()
    swap_repos(monkeypatch, service, fake)
    senders = [{"name": "engine", "secret": SECRET}, {"name": "keyed", "public_key": PUBLIC}]
    monkeypatch.setenv("ZS_EVENT_SENDERS", json.dumps(senders))
    zs_config.reset()
    yield fake
    zs_config.reset()


def _signed(body: bytes, msg_id: str = "msg_1", stamp: int | None = None, v1a: bool = False):
    stamp = int(time.time()) if stamp is None else stamp
    content = f"{msg_id}.{stamp}.".encode() + body
    if v1a:
        sig = "v1a," + base64.b64encode(PRIVATE.sign(content)).decode()
    else:
        key = base64.b64decode(SECRET.removeprefix("whsec_"))
        sig = "v1," + base64.b64encode(hmac.new(key, content, hashlib.sha256).digest()).decode()
    return {"webhook-id": msg_id, "webhook-timestamp": str(stamp), "webhook-signature": sig}


def test_v1_and_v1a_accepted_and_stored_once(repo):
    body = json.dumps(EVENT).encode()
    assert service.receive("engine", _signed(body), body) is True
    assert service.receive("engine", _signed(body), body) is False  # the retry of msg_1
    assert service.receive("keyed", _signed(body, "msg_2", v1a=True), body) is True
    stored = repo.rows[("engine", "msg_1")]
    assert (stored["type"], stored["subject"], stored["link"]) == (
        "run.completed",
        "runs/r1",
        "https://engine.test/projects/p?tab=runs&run=r1",
    )


@pytest.mark.parametrize(
    ("sender", "headers", "code"),
    [
        ("nobody", None, "events.unknown_sender"),
        (
            "engine",
            {"webhook-id": "m", "webhook-timestamp": "1", "webhook-signature": "v1,x"},
            "events.stale",
        ),
        ("keyed", None, "events.bad_signature"),  # a v1 signature for a key-only sender
        ("engine", {"webhook-timestamp": "1"}, "events.bad_headers"),
    ],
)
def test_refusals(repo, sender, headers, code):
    body = json.dumps(EVENT).encode()
    with pytest.raises(ApiError) as err:
        service.receive(sender, headers if headers is not None else _signed(body), body)
    assert err.value.code == code


def test_body_must_be_a_cloudevent(repo):
    body = json.dumps({"hello": "world"}).encode()
    with pytest.raises(ApiError) as err:
        service.receive("engine", _signed(body), body)
    assert err.value.code == "events.not_cloudevent"


def test_public_receiver_and_private_list(repo):
    import main

    client = TestClient(main.app, raise_server_exceptions=False)
    body = json.dumps(EVENT).encode()
    ok = client.post("/api/events/inbound/engine", content=body, headers=_signed(body, "msg_9"))
    assert ok.status_code == 204
    forged = client.post(
        "/api/events/inbound/engine",
        content=body,
        headers={**_signed(body, "msg_10"), "webhook-signature": "v1,AAAA"},
    )
    assert forged.status_code == 401
    assert client.get("/api/inbound-events").status_code == 401  # needs a session
