"""Decide whether a request carrying a machine credential may proceed.

`MachineAuth.authorize()` is pure — (method, path, headers, query) -> Decision | None — so
it is testable without a server. None means "no machine credential here"; the caller then
falls through to the browser-session check.
"""

import hmac
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from zservice.security.rate_limit import SlidingWindow

from . import config as machine_config
from .audit import Audit
from .keys import KEY_PATTERN, MachineKey, hash_secret, load_keys
from .scopes import scope_allows

LEGACY_PRINCIPAL = "legacy-pull-key"
# The leaked legacy PULL_KEY (plan B0) reaches only what the home scripts actually call
# (security pass 25 Oct: export/status/symbols/history reads, job start/stop, gold jobs,
# watchlist edits) — not history deletion, settings, Drive, admin or paid AI scans — until
# it is removed after the migration. A denied call is audited like any other.
LEGACY_SCOPES = frozenset({"read", "jobs", "gold:jobs", "watchlist:write"})
# A client presenting this many wrong keys within the window gets 429 until it passes.
WRONG_KEY_LIMIT, WRONG_KEY_WINDOW_S = 10, 300
_NO_MATCH = "0" * 64  # compared when the id is unknown, so timing does not reveal ids


@dataclass(frozen=True)
class Decision:
    allowed: bool
    status: int  # HTTP status to send when not allowed
    reason: str  # short and safe to show the client (never the key)
    principal: str  # key id, or LEGACY_PRINCIPAL
    via: str = "header"  # "header" | "query"
    deprecated: bool = False
    retry_after: int | None = None


class MachineAuth:
    def __init__(
        self,
        keys: dict[str, MachineKey],
        legacy_pull_key: str,
        limiter: SlidingWindow,
        audit: Audit,
    ):
        self.keys = keys
        self.legacy = legacy_pull_key
        self.limiter = limiter
        # Wrong keys per client address: guessing the legacy key or a zsk_ secret gets slow.
        self.guesses = SlidingWindow(WRONG_KEY_LIMIT, WRONG_KEY_WINDOW_S)
        self.audit = audit

    def authorize(
        self,
        method: str,
        path: str,
        headers: Mapping[str, str],
        query: Mapping[str, str],
        today: date | None = None,
    ) -> Decision | None:
        auth = headers.get("authorization", "")
        token = auth[7:].strip() if auth[:7].lower() == "bearer " else ""
        if token.startswith("zsk_"):
            return self._scoped(token, method, path, today or date.today())
        if self.legacy:
            return self._legacy(method, path, headers, query)
        return None

    def _legacy(
        self, method: str, path: str, headers: Mapping[str, str], query: Mapping[str, str]
    ) -> Decision | None:
        candidates = (
            (headers.get("x-pull-key", "").strip(), "header"),
            ((query.get("pull_key") or "").strip(), "query"),
        )
        for supplied, via in candidates:
            if supplied and hmac.compare_digest(supplied, self.legacy):
                if not scope_allows(LEGACY_SCOPES, method, path):
                    reason = "legacy key scope does not allow this request"
                    return Decision(False, 403, reason, LEGACY_PRINCIPAL, via, deprecated=True)
                return Decision(True, 200, "ok", LEGACY_PRINCIPAL, via=via, deprecated=True)
        return None  # wrong or missing legacy key: behave exactly as before (session check)

    def _scoped(self, token: str, method: str, path: str, today: date) -> Decision:
        match = KEY_PATTERN.match(token)
        kid = match.group(1) if match else "?"
        key = self.keys.get(kid)
        presented = hash_secret(match.group(2)) if match else ""
        expected = key.sha256 if key else _NO_MATCH
        if not (hmac.compare_digest(presented, expected) and key):
            return Decision(False, 401, "invalid key", kid)
        if key.expires and today > key.expires:
            return Decision(False, 401, "key expired", key.id)
        if not scope_allows(key.scopes, method, path):
            return Decision(False, 403, "key scope does not allow this request", key.id)
        wait = self.limiter.hit(key.id)
        if wait is not None:
            return Decision(False, 429, "rate limit", key.id, retry_after=wait)
        return Decision(True, 200, "ok", key.id)


def from_env() -> MachineAuth:
    """Build from config.MachineSettings (ZS_API_KEYS, legacy PULL_KEY, rate limit, audit)."""
    cfg = machine_config.get_settings()
    return MachineAuth(
        keys=load_keys(cfg.api_keys.get_secret_value()),
        legacy_pull_key=cfg.pull_key.get_secret_value(),
        limiter=SlidingWindow(cfg.rate_limit, cfg.rate_window_s),
        audit=Audit(cfg.audit_ring_size),
    )
