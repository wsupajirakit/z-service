"""The one way scripts talk to z-service: header-only key, TLS always verified, no key in files.

    sys.path.insert(0, os.path.join(os.environ["ZSERVICE_REPO"], "tools"))  # the checkout
    import zsvc_client as Z
    Z.get("/api/automate/status")
    Z.post("/api/watchlist", {"symbol": "QQQ", "name": "Invesco QQQ Trust",
                              "list_name": "X", "exchange": "NASDAQ"})
    Z.download("/api/export_zip?all=true", "/tmp/x.zip", timeout=1500)

Key lookup order: env ZS_API_KEY -> macOS Keychain (service `z-service`, account env
ZS_KEY_ACCOUNT or `home`). Base URL: env ZS_BASE_URL (default the production domain).
Errors raise ZsvcError with the HTTP status and the server's `detail` — never the key.
"""

from __future__ import annotations

import json
import os
import shutil
import ssl
import subprocess
import time
import urllib.error
import urllib.request

BASE_URL = os.environ.get("ZS_BASE_URL", "https://z-service.duckdns.org").rstrip("/")
KEYCHAIN_SERVICE = os.environ.get("ZS_KEYCHAIN_SERVICE", "z-service")
KEY_ACCOUNT = os.environ.get("ZS_KEY_ACCOUNT", "home")
_TLS = ssl.create_default_context()  # verifies certificate + hostname
_RETRY_STATUS = {502, 503, 504}


class ZsvcError(RuntimeError):
    def __init__(self, status: int, detail: str):
        super().__init__(f"z-service HTTP {status}: {detail}")
        self.status, self.detail = status, detail


_key_cache: str | None = None


def api_key() -> str:
    global _key_cache
    if _key_cache:
        return _key_cache
    key = os.environ.get("ZS_API_KEY", "").strip()
    if not key and shutil.which("security"):
        r = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", KEY_ACCOUNT, "-w"],
            capture_output=True,
            text=True,
        )
        key = r.stdout.strip() if r.returncode == 0 else ""
    if not key.startswith("zsk_"):
        raise ZsvcError(
            0,
            f"no zsk_ key: set ZS_API_KEY or add Keychain item {KEYCHAIN_SERVICE}/{KEY_ACCOUNT} "
            "(tools/manage_keys.py new ...)",
        )
    _key_cache = key
    return key


def _request(method: str, path: str, body=None, timeout: float = 60, retries: int = 2):
    if not path.startswith("/api/"):
        raise ValueError("path must start with /api/")
    data = None if body is None else json.dumps(body).encode()
    headers = {"Authorization": f"Bearer {api_key()}", "User-Agent": "zsvc-client/1"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    for attempt in range(retries + 1):
        req = urllib.request.Request(BASE_URL + path, data=data, method=method, headers=headers)
        try:
            return urllib.request.urlopen(req, timeout=timeout, context=_TLS)
        except urllib.error.HTTPError as e:
            if e.code in _RETRY_STATUS and attempt < retries:
                time.sleep(2**attempt * 3)
                continue
            if e.code == 429 and attempt < retries:
                time.sleep(int(e.headers.get("Retry-After", "5")))
                continue
            try:
                detail = json.loads(e.read() or b"{}").get("detail", "")
            except ValueError:
                detail = ""
            raise ZsvcError(e.code, str(detail)) from None


def get(path: str, timeout: float = 60):
    with _request("GET", path, timeout=timeout) as r:
        return json.loads(r.read() or b"null")


def post(path: str, body=None, timeout: float = 120):
    with _request("POST", path, body if body is not None else {}, timeout=timeout) as r:
        return json.loads(r.read() or b"null")


def put(path: str, body=None, timeout: float = 60):
    with _request("PUT", path, body if body is not None else {}, timeout=timeout) as r:
        return json.loads(r.read() or b"null")


def delete(path: str, timeout: float = 60):
    with _request("DELETE", path, timeout=timeout) as r:
        return json.loads(r.read() or b"null")


def download(path: str, dest: str, timeout: float = 1500) -> int:
    """Stream a file (e.g. export_zip) to `dest`; returns bytes written."""
    with _request("GET", path, timeout=timeout, retries=0) as r, open(dest, "wb") as f:
        n = 0
        while chunk := r.read(1 << 20):
            f.write(chunk)
            n += len(chunk)
    return n
