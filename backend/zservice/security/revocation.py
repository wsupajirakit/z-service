"""Server-side session revocation (OWASP Session Management: logout must end the session
on the server, not only in the browser).

Session JWTs are stateless, so revocation is a small denylist in the settings collection:
* `auth_revoked_before` — unix time; every token issued before it is invalid (password
  change, and logout of tokens minted before tokens carried a `jti`)
* `auth_revoked_jti` — {jti: exp} for single tokens ended by logout; an entry is dropped
  once its token would have expired anyway, so the list stays tiny

Reads are cached for ZS_REVOCATION_CACHE_S seconds (config.SecuritySettings) so the auth
gate does not query Mongo on every request; a second container (rolling update) sees a
revocation within that time.
A failed read keeps the last known state: the app cannot serve data without Mongo anyway,
and failing closed would lock every session out during a database blip.
"""

import logging
import threading
import time

from zservice.db.repos import settings as settings_repo
from zservice.security import config as security_config

log = logging.getLogger("zs.security")

BEFORE_KEY = "auth_revoked_before"
JTI_KEY = "auth_revoked_jti"

_lock = threading.Lock()
_cache: dict = {"before": 0.0, "jti": {}, "loaded_at": float("-inf")}


def is_revoked(payload: dict) -> bool:
    state = _state()
    if float(payload.get("iat", 0)) < state["before"]:
        return True
    jti = payload.get("jti")
    return bool(jti) and jti in state["jti"]


def revoke_token(payload: dict) -> None:
    """End one session. A token without a jti (minted before jti existed) can only be
    ended together with every older token."""
    jti = payload.get("jti")
    if not jti:
        revoke_all()
        return
    now = time.time()
    current = settings_repo.settings_get(JTI_KEY) or {}
    kept = {k: v for k, v in current.items() if float(v) > now}
    kept[jti] = int(payload.get("exp", now))
    settings_repo.settings_set(JTI_KEY, kept)
    _invalidate()


def revoke_all(now: float | None = None) -> int:
    """Invalidate every token issued before `now` (second resolution: a token minted in
    the same second, e.g. right after a password change, stays valid). Returns the cutoff."""
    cutoff = int(now if now is not None else time.time())
    settings_repo.settings_set(BEFORE_KEY, cutoff)
    settings_repo.settings_set(JTI_KEY, {})  # every listed token is older than the cutoff
    _invalidate()
    return cutoff


def _state() -> dict:
    now = time.monotonic()
    with _lock:
        if now - _cache["loaded_at"] < security_config.get_settings().revocation_cache_s:
            return _cache
        try:
            got = settings_repo.settings_get_many([BEFORE_KEY, JTI_KEY])
            _cache["before"] = float(got.get(BEFORE_KEY) or 0)
            _cache["jti"] = dict(got.get(JTI_KEY) or {})
        except Exception as e:
            log.warning("revocation list unreadable, keeping the last known state: %s", e)
        _cache["loaded_at"] = now
        return _cache


def _invalidate() -> None:
    with _lock:
        _cache["loaded_at"] = float("-inf")
