"""What each machine-key scope may call. Anything not matched is denied for machine keys,
so a new route is never reachable by a key by accident. Browser sessions are not
governed by this table."""

import re

Rule = tuple[frozenset[str], re.Pattern[str]]

# `admin` matches everything and is never issued to a machine (OWASP REST: do not rely
# on API keys alone for high-value resources); tools/manage_keys.py refuses to mint it.
ADMIN_SCOPE = "admin"

SCOPE_RULES: dict[str, list[Rule]] = {
    "read": [
        # Data reads. Google Drive listings and admin views stay out of reach.
        (frozenset({"GET", "HEAD"}), re.compile(r"^/api/(?!drive/|admin/).+")),
    ],
    "jobs": [
        (
            frozenset({"POST"}),
            # stock_radar/scan calls a paid AI model: kept reachable by the scripts' keys.
            re.compile(
                r"^/api/(automate|data|auto/(start|stop|start_all)|radar_round/run"
                r"|stock_radar/scan)$"
            ),
        ),
    ],
    "gold:jobs": [
        (frozenset({"POST"}), re.compile(r"^/api/gold/automate(/stop)?$")),
    ],
    "watchlist:write": [
        (frozenset({"POST"}), re.compile(r"^/api/watchlist$")),
        (frozenset({"PUT"}), re.compile(r"^/api/watchlist/[^/]+$")),
        (frozenset({"DELETE"}), re.compile(r"^/api/watchlist/[^/]+/[^/]+$")),
    ],
}

KNOWN_SCOPES = frozenset(SCOPE_RULES) | {ADMIN_SCOPE}


def scope_allows(scopes: frozenset[str], method: str, path: str) -> bool:
    if ADMIN_SCOPE in scopes:
        return True
    for scope in scopes:
        for methods, pattern in SCOPE_RULES.get(scope, ()):
            if method in methods and pattern.match(path):
                return True
    return False
