"""In-memory audit trail of machine-key decisions (never contains the key itself).

Exposed through GET /api/admin/key_audit so the legacy PULL_KEY can be retired only
after the log shows no caller still sends it.
"""

import collections
import logging
import threading
import time
from datetime import UTC, datetime

log = logging.getLogger("zs.machine")

# Status polling loops call every few seconds; warn about a deprecated caller once an hour.
_DEPRECATION_WARN_EVERY_S = 3600


class Audit:
    def __init__(self, size: int):
        self._ring: collections.deque[dict] = collections.deque(maxlen=size)
        self._lock = threading.Lock()
        self._warned_at: dict[tuple[str, str, str], float] = {}

    def record(self, decision, method: str, path: str, ip: str, status: int) -> None:
        entry = {
            "ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "principal": decision.principal,
            "via": decision.via,
            "method": method,
            "path": path,
            "ip": ip,
            "status": status,
            "deprecated": decision.deprecated,
        }
        with self._lock:
            self._ring.append(entry)
            should_warn = decision.deprecated and self._due_warning(decision.via, method, path)
        if should_warn:
            log.warning(
                "deprecated PULL_KEY via %s: %s %s from %s; move it to a zsk_ key",
                decision.via,
                method,
                path,
                ip,
            )
        elif not decision.deprecated:
            log.info("machine %s %s %s -> %s (%s)", decision.principal, method, path, status, ip)

    def _due_warning(self, via: str, method: str, path: str) -> bool:
        key, now = (via, method, path), time.monotonic()
        if now - self._warned_at.get(key, float("-inf")) < _DEPRECATION_WARN_EVERY_S:
            return False
        self._warned_at[key] = now
        return True

    def recent(self, limit: int = 200) -> list[dict]:
        with self._lock:
            return list(self._ring)[-limit:][::-1]

    def summary(self) -> dict:
        with self._lock:
            rows = list(self._ring)
        counts = collections.Counter(
            (r["principal"], r["via"], r["method"], r["path"]) for r in rows
        )
        callers = [
            {"principal": p, "via": v, "method": m, "path": path, "count": n}
            for (p, v, m, path), n in counts.most_common()
        ]
        return {"entries": len(rows), "callers": callers}
