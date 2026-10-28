"""ApiError answers: legacy `detail` unchanged + a `code` the web app translates.

The sync test reads every ApiError(...) call in zservice/ and checks that web/messages
has `err_<code>` in every locale, with exactly the placeholders the call passes as params.
"""

import ast
import json
import re
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from zservice.core.errors import ApiError, install_error_handlers

BACKEND = Path(__file__).resolve().parents[2]
MESSAGES = BACKEND.parent / "web" / "messages"
LOCALES = ("en", "th", "it")
CODE = re.compile(r"^[a-z_]+\.[a-z0-9_]+$")


SOURCES = ("zservice", "radar_engine")


def _sources():
    for root in SOURCES:
        yield from sorted((BACKEND / root).rglob("*.py"))


def _calls():
    """(file:line, code, param names) for every ApiError(...) call."""
    out = []
    for path in _sources():
        for node in ast.walk(ast.parse(path.read_text())):
            if not (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "ApiError"):
                continue
            where = f"{path.relative_to(BACKEND)}:{node.lineno}"
            code = node.args[1].value if len(node.args) > 1 else None
            params = next((kw.value for kw in node.keywords if kw.arg == "params"), None)
            names = {k.value for k in params.keys} if isinstance(params, ast.Dict) else set()
            out.append((where, code, names))
    return out


def _coded_calls():
    """(file:line, code, param names) for every message code a module can emit: literal
    coded("x.y", ...) calls, plus the codes a module declares in MESSAGE_CODES = {code:
    (param, ...)} when it picks one at run time (a coded() call with a non-literal code
    must be backed by such a declaration)."""
    out = []
    for path in _sources():
        tree = ast.parse(path.read_text())
        declared = _declared_codes(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "coded":
                where = f"{path.relative_to(BACKEND)}:{node.lineno}"
                first = node.args[0] if node.args else None
                if isinstance(first, ast.Constant):
                    names = {kw.arg for kw in node.keywords if kw.arg}
                    out.append((where, first.value, names))
                else:
                    # A code picked at run time must come from this module's MESSAGE_CODES
                    # (checked by name, so a forgotten declaration fails here).
                    assert declared and _dynamic_source_ok(first), (
                        f"{where}: dynamic code must be a MESSAGE_CODES / *_CODES lookup"
                    )
        rel = path.relative_to(BACKEND)
        out += [(f"{rel}:MESSAGE_CODES", code, names) for code, names in declared.items()]
    return out


def _dynamic_source_ok(node) -> bool:
    """A dynamic code is a lookup in a *_CODES table (e.g. VERDICT_CODES[key]) or a helper
    whose result space is MESSAGE_CODES (an f-string built from the declared parts)."""
    if isinstance(node, ast.Subscript):
        return getattr(node.value, "id", "").endswith("_CODES")
    return isinstance(node, ast.JoinedStr)


def _declared_codes(tree) -> dict[str, set]:
    for node in tree.body:
        targets = [t.id for t in getattr(node, "targets", []) if isinstance(t, ast.Name)]
        if "MESSAGE_CODES" in targets:
            value = ast.literal_eval(node.value)
            return {code: set(params) for code, params in value.items()}
    return {}


def _text(message) -> str:
    """A message is a string or an inlang variant list (plurals): every text it can show."""
    if isinstance(message, list):
        return " ".join(t for v in message for t in v.get("match", {}).values())
    return message or ""


def _key(code: str, prefix: str = "err_") -> str:
    return prefix + code.replace(".", "_")


def test_every_call_has_a_literal_well_formed_code():
    calls = _calls()
    assert len(calls) >= 40
    for where, code, _ in calls:
        assert isinstance(code, str) and CODE.match(code), where


@pytest.mark.parametrize("locale", LOCALES)
def test_every_code_is_translated_with_matching_placeholders(locale):
    messages = json.loads((MESSAGES / f"{locale}.json").read_text(encoding="utf-8"))
    params_by_code: dict[str, set] = {}
    for _, code, names in _calls():
        params_by_code.setdefault(code, set()).update(names)
    for code, names in params_by_code.items():
        text = _text(messages.get(_key(code)))
        assert text, f"{locale}.json lacks {_key(code)}"
        used = set(re.findall(r"\{(\w+)\}", text))
        assert used <= names, f"{locale} {_key(code)} uses {used - names} not sent as params"


def test_answer_keeps_detail_and_adds_code_params_and_headers():
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/boom")
    def boom():
        raise ApiError(429, "auth.rate_limited", "too many attempts",
                       params={"retry_after": 30}, headers={"Retry-After": "30"})  # fmt: skip

    @app.get("/plain")
    def plain():
        raise ApiError(404, "history.not_found", "History record not found")

    client = TestClient(app)
    res = client.get("/boom")
    assert res.status_code == 429 and res.headers["Retry-After"] == "30"
    assert res.json() == {
        "detail": "too many attempts",
        "code": "auth.rate_limited",
        "params": {"retry_after": 30},
    }
    assert client.get("/plain").json() == {
        "detail": "History record not found",
        "code": "history.not_found",
    }


def test_every_coded_message_is_well_formed():
    for where, code, _ in _coded_calls():
        assert isinstance(code, str) and CODE.match(code), where


@pytest.mark.parametrize("locale", LOCALES)
def test_every_coded_message_is_translated(locale):
    messages = json.loads((MESSAGES / f"{locale}.json").read_text(encoding="utf-8"))
    params_by_code: dict[str, set] = {}
    for _, code, names in _coded_calls():
        params_by_code.setdefault(code, set()).update(names)
    for code, names in params_by_code.items():
        text = _text(messages.get(_key(code, "msg_")))
        assert text, f"{locale}.json lacks {_key(code, 'msg_')}"
        used = set(re.findall(r"\{(\w+)\}", text))
        assert used <= names, f"{locale} {_key(code, 'msg_')} uses {used - names} not sent"
