"""API errors that carry a stable machine `code` (+ `params`) next to `detail`.

`detail` stays the human text the legacy dashboard prints as-is; the web app translates
`code` from its message files (`err_<code with dots as underscores>` in th/en/it) and
falls back to `detail` for codes it does not know. tests/core/test_error_codes.py keeps
every code used here in sync with web/messages.

Body: {"detail": str, "code": "domain.reason", "params": {...}}  (params only if any).
"""

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse


class ApiError(HTTPException):
    """An HTTPException with a code: existing `except HTTPException` and `e.detail` users
    keep working unchanged."""

    def __init__(
        self,
        status_code: int,
        code: str,
        detail: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.code = code
        self.params = params or {}


async def _api_error_response(_request: Request, exc: ApiError) -> JSONResponse:
    body: dict[str, Any] = {"detail": exc.detail, "code": exc.code}
    if exc.params:
        body["params"] = exc.params
    return JSONResponse(body, status_code=exc.status_code, headers=exc.headers)


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, _api_error_response)  # type: ignore[arg-type]
