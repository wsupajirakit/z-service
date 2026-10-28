"""Standard Webhooks verification: the signed content is `<id>.<timestamp>.<body>`; the
header holds space-separated `v1,<hmac>` and/or `v1a,<ed25519>` signatures; one valid
signature from the configured sender is enough."""

import base64
import binascii
import hashlib
import hmac
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from zservice.core.errors import ApiError

from .config import MIN_SECRET_BYTES, Sender, decode_secret


def _hmac_ok(secret: str, content: bytes, signature: str) -> bool:
    key = decode_secret(secret)
    if len(key) < MIN_SECRET_BYTES:
        return False
    want = base64.b64encode(hmac.new(key, content, hashlib.sha256).digest()).decode()
    return hmac.compare_digest(want, signature)


def _ed25519_ok(public_key: str, content: bytes, signature: str) -> bool:
    try:
        raw = base64.b64decode(public_key.removeprefix("whpk_"))
        Ed25519PublicKey.from_public_bytes(raw).verify(base64.b64decode(signature), content)
    except (binascii.Error, ValueError, InvalidSignature):
        return False
    return True


def check(sender: Sender, headers: dict[str, str], body: bytes, tolerance: int) -> str:
    """The webhook id when the message is authentic and fresh; ApiError otherwise."""
    msg_id = headers.get("webhook-id", "")
    stamp = headers.get("webhook-timestamp", "")
    if not msg_id or "." in msg_id or not stamp.isdigit():
        raise ApiError(400, "events.bad_headers", "webhook-id / webhook-timestamp missing")
    if abs(time.time() - int(stamp)) > tolerance:
        raise ApiError(401, "events.stale", "timestamp outside the accepted window")
    content = f"{msg_id}.{stamp}.".encode() + body
    for part in headers.get("webhook-signature", "").split():
        version, _, sig = part.partition(",")
        if (
            version == "v1"
            and sender.secret
            and _hmac_ok(sender.secret.get_secret_value(), content, sig)
        ):
            return msg_id
        if version == "v1a" and sender.public_key and _ed25519_ok(sender.public_key, content, sig):
            return msg_id
    raise ApiError(401, "events.bad_signature", "no valid signature for this sender")
