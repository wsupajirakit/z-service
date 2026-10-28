"""Machine (non-browser) access — the home machine and scripts calling the API directly.

* Scoped keys: `Authorization: Bearer zsk_<id>_<secret>`. The server stores only the
  SHA-256 of `<secret>` (env `ZS_API_KEYS`), checks scopes against `scopes.SCOPE_RULES`
  (default deny), rate-limits per key and audits every decision. Header only — a key in
  the URL ends up in proxy and access logs (OWASP REST Security Cheat Sheet).
* Legacy `PULL_KEY` (migration only): `X-Pull-Key` header or `pull_key` query with the
  same full access as before, so callers that still use it keep working; every use is
  audited and tagged deprecated. Unset the env var to retire it.
"""

from .auth import Decision, MachineAuth, from_env
from .keys import BASE64_PREFIX, KEY_PATTERN, MachineKey, hash_secret, load_keys
from .scopes import ADMIN_SCOPE, KNOWN_SCOPES, scope_allows

__all__ = [
    "ADMIN_SCOPE",
    "BASE64_PREFIX",
    "KEY_PATTERN",
    "KNOWN_SCOPES",
    "Decision",
    "MachineAuth",
    "MachineKey",
    "from_env",
    "hash_secret",
    "load_keys",
    "scope_allows",
]
