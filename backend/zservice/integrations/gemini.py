"""Google Gemini generateContent client (GEMINI_API_KEY, Coolify env)."""

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Annotated

from pydantic import Field, SecretStr

from zservice.core.config import ZsSettings, env_field, settings_getter
from zservice.core.errors import ApiError


class GeminiSettings(ZsSettings):
    api_key: SecretStr = env_field(
        "GEMINI_API_KEY", SecretStr(""), doc="Gemini key (gold analysis, AI scans)."
    )


get_settings = settings_getter(GeminiSettings)


def configured() -> bool:
    return bool(get_settings().api_key.get_secret_value())


GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-2.5-flash"  # shown first in model lists; default for AI scans
# A model id is one URL path segment (e.g. gemini-2.5-flash). Anything else — "/", "..",
# "?" — could steer the request, which carries the server's key, to another API path.
MODEL_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$"
ModelName = Annotated[str, Field(pattern=MODEL_PATTERN)]
_MODEL_RE = re.compile(MODEL_PATTERN)


def auth_headers(extra: dict | None = None) -> dict:
    """Request headers carrying the API key (x-goog-api-key)."""
    return {**(extra or {}), "x-goog-api-key": get_settings().api_key.get_secret_value()}


def call_gemini(model: str, prompt: str) -> str:
    """Call Gemini generateContent and return the text response.
    Retries transient 429/5xx (Gemini overloads intermittently), and surfaces a
    clean error instead of a bare 500 on failure."""
    # Key in the x-goog-api-key header (Gemini API docs), never in the URL: a URL ends up
    # in proxy and error logs (plan B14).
    if not _MODEL_RE.fullmatch(model or "") or ".." in model:
        raise ApiError(400, "ai.invalid_model", "invalid Gemini model name")
    url = f"{GEMINI_BASE}/models/{urllib.parse.quote(model, safe='')}:generateContent"
    body = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4},
        }
    ).encode()

    last_err = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(  # noqa: S310 — fixed https Gemini endpoint
                url,
                data=body,
                headers=auth_headers({"Content-Type": "application/json"}),
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=90) as resp:  # noqa: S310
                data = json.loads(resp.read())
            try:
                parts = data["candidates"][0]["content"]["parts"]
                return "".join(p.get("text", "") for p in parts).strip()
            except (KeyError, IndexError):
                detail = f"Unexpected Gemini response: {json.dumps(data)[:500]}"
                raise ApiError(502, "ai.bad_response", detail) from None
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            # 429 (rate limit) / 5xx (overload) are transient — back off and retry.
            if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                last_err = f"HTTP {e.code}"
                time.sleep(2 * (attempt + 1))
                continue
            # 4xx (bad model, bad key) won't get better by retrying.
            raise ApiError(
                502,
                "ai.http_error",
                f"Gemini error (HTTP {e.code}): {detail}",
                params={"status": e.code, "reason": detail},
            ) from None
        except urllib.error.URLError as e:
            last_err = str(e.reason)
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue

    raise ApiError(
        503,
        "ai.unavailable",
        f"Gemini ไม่ตอบสนอง (ลองใหม่อีกครั้ง): {last_err}",
        params={"reason": str(last_err)},
    )
