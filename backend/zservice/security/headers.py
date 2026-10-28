"""Security response headers on every response (plan item B8; OWASP REST / HTML5 sheets).

* all responses: nosniff, no framing, no referrer, locked-down browser features, HSTS
  (browsers ignore HSTS on plain http, so local dev is unaffected)
* /api/*: Cache-Control no-store unless the route set its own
* the new web UI (APP_BASE, default /app/): the full Content-Security-Policy, enforced
* everything else (legacy dashboard, login page): an enforced script policy — scripts only
  from this origin plus the login page's own inline <script>, allowed by its sha256 hash
  computed from the served file at start-up — and the full policy as Report-Only. The
  legacy UI keeps its token in localStorage, so stopping injected scripts is what counts;
  its styles are left alone (not verified against the full style-src).
"""

import base64
import functools
import hashlib
import os
import re

from zservice.web import config as web_config
from zservice.web.paths import APP_BASE

CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "connect-src 'self'",
        "font-src 'self'",
        "object-src 'none'",
        "base-uri 'none'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)
_INLINE_SCRIPT = re.compile(r"<script>(.*?)</script>", re.S)

BASE_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Strict-Transport-Security": "max-age=31536000",
}


def inline_script_hashes(html: str) -> list[str]:
    """CSP source expressions for every inline <script> (no src). The HTML parser turns
    CRLF into LF before the browser hashes the text, so the hash is taken the same way."""
    out = []
    for body in _INLINE_SCRIPT.findall(html.replace("\r\n", "\n")):
        digest = base64.b64encode(hashlib.sha256(body.encode()).digest()).decode()
        out.append(f"'sha256-{digest}'")
    return out


@functools.cache
def legacy_csp() -> str:
    login = os.path.join(web_config.get_settings().frontend_dir, "login.html")
    try:
        with open(login, encoding="utf-8") as f:
            hashes = inline_script_hashes(f.read())
    except OSError:
        hashes = []  # API-only run: no legacy page to allow
    return "; ".join(
        [
            " ".join(["script-src 'self'", *hashes]),
            "object-src 'none'",
            "base-uri 'none'",
            "form-action 'self'",
            "frame-ancestors 'none'",
        ]
    )


def headers_for(path: str) -> dict[str, str]:
    out = dict(BASE_HEADERS)
    if path.startswith(APP_BASE):
        out["Content-Security-Policy"] = CSP
    else:
        out["Content-Security-Policy"] = legacy_csp()
        out["Content-Security-Policy-Report-Only"] = CSP
    return out


async def security_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path
    for name, value in headers_for(path).items():
        response.headers.setdefault(name, value)
    if path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response
