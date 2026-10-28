"""Coded status / progress / warning texts for the UIs (the non-error sibling of errors.py).

    coded("radar.saving", "<legacy text>")
    -> {"code": "radar.saving", "params": {}, "text": "<legacy text>"}

`text` is what the legacy dashboard shows as-is; the web app translates `code` from its
message files (`msg_<code with dots as underscores>`, th/en/it) and falls back to `text`.
tests/core/test_error_codes.py checks every coded(...) call against web/messages, so a new
code cannot ship untranslated. Params must be JSON scalars.
"""

from typing import Any


def coded(code: str, text: str, **params: Any) -> dict:
    return {"code": code, "params": params, "text": text}
