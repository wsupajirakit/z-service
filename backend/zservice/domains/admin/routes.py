"""GET /api/admin/key_audit — who called the API with a machine key, newest first.

Used to confirm no caller still sends the legacy PULL_KEY before retiring it. `read`
keys cannot reach /api/admin/ (see security/machine/scopes.py).
"""

from fastapi import APIRouter

from zservice.core.schemas import clamp
from zservice.security.machine import registry

router = APIRouter()

_MAX_LIMIT = 2000


@router.get("/api/admin/key_audit")
def key_audit(limit: int = 200) -> dict:
    limit = clamp(limit, 1, _MAX_LIMIT)
    auth = registry.current()
    keys = [
        {
            "id": k.id,
            "name": k.name,
            "scopes": sorted(k.scopes),
            "expires": k.expires.isoformat() if k.expires else None,
        }
        for k in auth.keys.values()
    ]
    return {
        "legacy_pull_key_enabled": bool(auth.legacy),
        "keys": keys,
        "summary": auth.audit.summary(),
        "recent": auth.audit.recent(limit),
    }
