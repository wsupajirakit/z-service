#!/usr/bin/env python3
"""Issue / rotate z-service machine keys (`zsk_<id>_<secret>`) without the secret ever
touching the screen, shell history, argv or the server.

    python3 tools/manage_keys.py new --id home --name "home mac" \
        --scopes read,jobs,watchlist:write --days 180

* the full key goes straight into the macOS Keychain (service `z-service`, account = id)
  through `security -i` on stdin — not argv, so it never shows in `ps`;
* stdout gets only the public entry (id, scopes, sha256 of the secret, expiry) to add to the
  Coolify env `ZS_API_KEYS` JSON list. Keep the old entry next to it until every caller
  moved, then remove it and redeploy (zero-downtime rotation).

    python3 tools/manage_keys.py show-entry --id home    # recompute the entry from the Keychain
    python3 tools/manage_keys.py check                   # parse a ZS_API_KEYS value from stdin
    python3 tools/manage_keys.py env-value               # the same value as base64: (panels)

Server secrets (e.g. AUTH_SECRET) use the same Keychain, account `env:<NAME>`:

    python3 tools/manage_keys.py secret --name AUTH_SECRET   # generate + store, never printed
    python3 tools/manage_keys.py copy --account env:AUTH_SECRET   # to the clipboard for Coolify

Scopes: see backend/zservice/security/machine/scopes.py (`admin` is refused here on purpose).
"""

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
from datetime import date, timedelta

KEYCHAIN_SERVICE = os.environ.get("ZS_KEYCHAIN_SERVICE", "z-service")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))


def _keychain_put(account: str, value: str) -> None:
    # `security -i` reads commands from stdin; the value is quoted for its parser.
    cmd = f'add-generic-password -U -s "{KEYCHAIN_SERVICE}" -a "{account}" -w "{value}"\n'
    r = subprocess.run(["security", "-i"], input=cmd, text=True, capture_output=True)
    if r.returncode != 0 or "error" in (r.stderr or "").lower():
        sys.exit(f"keychain write failed: {r.stderr.strip()}")


def _keychain_get(account: str) -> str:
    r = subprocess.run(
        ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", account, "-w"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        sys.exit(f"no Keychain item service={KEYCHAIN_SERVICE} account={account}")
    return r.stdout.strip()


def _entry(kid: str, name: str, scopes: list[str], secret: str, expires: str | None) -> dict:
    return {
        "id": kid,
        "name": name,
        "scopes": scopes,
        "sha256": hashlib.sha256(secret.encode()).hexdigest(),
        "expires": expires,
    }


def cmd_new(a) -> None:
    from zservice.security import machine as machine_auth

    scopes = sorted({s.strip() for s in a.scopes.split(",") if s.strip()})
    bad = set(scopes) - machine_auth.KNOWN_SCOPES
    if bad:
        sys.exit(f"unknown scopes: {sorted(bad)} (known: {sorted(machine_auth.KNOWN_SCOPES)})")
    if machine_auth.ADMIN_SCOPE in scopes:
        sys.exit("refusing to issue `admin` to a machine — use the web session for admin work")
    secret = secrets.token_urlsafe(32)
    key = f"zsk_{a.id}_{secret}"
    if not machine_auth.KEY_PATTERN.match(key):
        sys.exit("id must be 4-32 letters/digits")
    expires = (date.today() + timedelta(days=a.days)).isoformat() if a.days else None
    _keychain_put(a.id, key)
    entry = _entry(a.id, a.name or a.id, scopes, secret, expires)
    machine_auth.load_keys(json.dumps([entry]))  # same validation the server runs at boot
    print(json.dumps(entry))
    print(f"\nstored in Keychain: service={KEYCHAIN_SERVICE} account={a.id}", file=sys.stderr)
    print("add the JSON above to the Coolify env ZS_API_KEYS list, then redeploy.", file=sys.stderr)


def cmd_show_entry(a) -> None:
    from zservice.security import machine as machine_auth

    key = _keychain_get(a.id)
    m = machine_auth.KEY_PATTERN.match(key)
    if not m:
        sys.exit("Keychain item is not a zsk_ key")
    print(json.dumps({"id": m.group(1), "sha256": hashlib.sha256(m.group(2).encode()).hexdigest()}))


def cmd_secret(a) -> None:
    account = f"env:{a.name}"
    if not a.force and _keychain_has(account):
        sys.exit(f"{account} already exists; pass --force to replace it (rotation)")
    _keychain_put(account, secrets.token_urlsafe(a.bytes))
    print(f"stored {a.bytes}-byte random value in Keychain account {account} (not shown)")
    print(f"next: python3 tools/manage_keys.py copy --account {account}")


def cmd_copy(a) -> None:
    value = _keychain_get(a.account)
    subprocess.run(["pbcopy"], input=value, text=True, check=True)
    print(f"copied {a.account} to the clipboard; paste it into Coolify, then copy something else")


def _keychain_has(account: str) -> bool:
    r = subprocess.run(
        ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", account],
        capture_output=True,
    )
    return r.returncode == 0


def cmd_check(_a) -> None:
    from zservice.security import machine as machine_auth

    keys = machine_auth.load_keys(sys.stdin.read())
    for k in keys.values():
        print(f"{k.id:<12} scopes={','.join(sorted(k.scopes))} expires={k.expires}")


def cmd_env_value(_a) -> None:
    """The ZS_API_KEYS JSON from stdin, checked, as a `base64:` value (no quotes for a
    panel to strip). Only hashes are inside: safe to print."""
    import base64

    from zservice.security import machine as machine_auth

    raw = sys.stdin.read().strip()
    machine_auth.load_keys(raw)
    compact = json.dumps(json.loads(raw), separators=(",", ":"))
    print(machine_auth.BASE64_PREFIX + base64.b64encode(compact.encode()).decode())


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("--id", required=True)
    n.add_argument("--name", default="")
    n.add_argument("--scopes", required=True)
    n.add_argument("--days", type=int, default=180)
    s = sub.add_parser("show-entry")
    s.add_argument("--id", required=True)
    sub.add_parser("check")
    sub.add_parser("env-value")
    sec = sub.add_parser("secret")
    sec.add_argument("--name", required=True)
    sec.add_argument("--bytes", type=int, default=48)
    sec.add_argument("--force", action="store_true")
    cp = sub.add_parser("copy")
    cp.add_argument("--account", required=True)
    a = p.parse_args()
    commands = {
        "new": cmd_new,
        "show-entry": cmd_show_entry,
        "check": cmd_check,
        "env-value": cmd_env_value,
        "secret": cmd_secret,
        "copy": cmd_copy,
    }
    commands[a.cmd](a)


if __name__ == "__main__":
    main()
