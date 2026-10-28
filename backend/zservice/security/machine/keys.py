"""Machine key format and the server-side key registry parsed from env `ZS_API_KEYS`.

`ZS_API_KEYS` is a JSON list of {"id", "name", "scopes", "sha256", "expires"}; `sha256` is
the hex digest of the secret part. The server never sees or stores a full key. The list may
also be given base64-encoded with a `base64:` prefix: hosting panels that strip double
quotes from env values cannot mangle it (tools/manage_keys.py env-value prints it).
"""

import base64
import binascii
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date

from .scopes import KNOWN_SCOPES

KEY_PATTERN = re.compile(r"^zsk_([A-Za-z0-9]{4,32})_([A-Za-z0-9_-]{32,128})$")
_ID_PATTERN = re.compile(r"[A-Za-z0-9]{4,32}")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
BASE64_PREFIX = "base64:"


@dataclass(frozen=True)
class MachineKey:
    id: str
    name: str
    scopes: frozenset[str]
    sha256: str
    expires: date | None


def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def load_keys(raw: str | None) -> dict[str, MachineKey]:
    """Parse ZS_API_KEYS. Bad config raises, so the app fails closed at boot."""
    if not raw or not raw.strip():
        return {}
    data = _decode(raw.strip())
    if not isinstance(data, list):
        raise ValueError("ZS_API_KEYS must be a JSON list")
    keys: dict[str, MachineKey] = {}
    for item in data:
        key = _parse_entry(item)
        if key.id in keys:
            raise ValueError(f"ZS_API_KEYS: duplicate id {key.id!r}")
        keys[key.id] = key
    return keys


def _decode(raw: str) -> object:
    text = raw
    if raw.startswith(BASE64_PREFIX):
        try:
            text = base64.b64decode(raw[len(BASE64_PREFIX) :], validate=True).decode()
        except (binascii.Error, UnicodeDecodeError) as exc:
            raise ValueError("ZS_API_KEYS: the base64: value does not decode") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        hint = " (were its double quotes stripped? use the base64: form)" if '"' not in text else ""
        raise ValueError(f"ZS_API_KEYS is not valid JSON{hint}: {exc.msg}") from exc


def _parse_entry(item: dict) -> MachineKey:
    kid = str(item["id"])
    if not _ID_PATTERN.fullmatch(kid):
        raise ValueError(f"ZS_API_KEYS: bad id {kid!r}")
    scopes = frozenset(item["scopes"])
    unknown = scopes - KNOWN_SCOPES
    if unknown or not scopes:
        raise ValueError(f"ZS_API_KEYS[{kid}]: unknown or empty scopes {sorted(unknown)}")
    digest = str(item["sha256"]).lower()
    if not _SHA256_PATTERN.fullmatch(digest):
        raise ValueError(f"ZS_API_KEYS[{kid}]: sha256 must be 64 hex chars")
    expires = item.get("expires")
    return MachineKey(
        id=kid,
        name=str(item.get("name") or kid),
        scopes=scopes,
        sha256=digest,
        expires=date.fromisoformat(expires) if expires else None,
    )
