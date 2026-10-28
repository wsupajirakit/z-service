"""Receive one event: known sender, authentic and fresh, a CloudEvents 1.0 structured
body; stored once per webhook id (a retry of the same message is acknowledged again)."""

import json
from datetime import UTC, datetime, timedelta

from zservice.core.errors import ApiError
from zservice.db.repos import inbound_events as inbound_repo

from .config import get_settings
from .verify import check

REQUIRED = ("specversion", "id", "source", "type")


def _sender(name: str):
    for sender in get_settings().senders:
        if sender.name == name:
            return sender
    raise ApiError(404, "events.unknown_sender", "no such sender")


def _event(body: bytes) -> dict:
    try:
        event = json.loads(body)
    except ValueError:
        raise ApiError(400, "events.bad_body", "the body is not JSON") from None
    if not isinstance(event, dict) or any(not isinstance(event.get(k), str) for k in REQUIRED):
        raise ApiError(400, "events.not_cloudevent", "a CloudEvents 1.0 structured body is needed")
    if event["specversion"] != "1.0":
        raise ApiError(400, "events.not_cloudevent", "only CloudEvents 1.0 is accepted")
    return event


def receive(sender_name: str, headers: dict[str, str], body: bytes) -> bool:
    """True when stored, False when this message was already stored (a retry)."""
    cfg = get_settings()
    if len(body) > cfg.max_bytes:
        raise ApiError(413, "events.too_large", "event body too large")
    sender = _sender(sender_name)
    msg_id = check(sender, headers, body, cfg.tolerance_seconds)
    event = _event(body)
    now = datetime.now(UTC)
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    links = data.get("links") if isinstance(data.get("links"), dict) else {}
    return inbound_repo.inbound_insert(
        {
            "sender": sender.name,
            "webhook_id": msg_id,
            "event_id": event["id"],
            "type": event["type"],
            "source": event["source"],
            "subject": event.get("subject"),
            "time": event.get("time"),
            "data": data,
            "link": links.get("ui"),
            "received_at": now,
            "expires_at": now + timedelta(days=cfg.keep_days),
        }
    )


def recent(limit: int, sender: str | None, event_type: str | None) -> list[dict]:
    rows = inbound_repo.inbound_list(limit, sender, event_type)
    for row in rows:
        row.pop("expires_at", None)
        if isinstance(row.get("received_at"), datetime):
            row["received_at"] = row["received_at"].isoformat()
    return rows
