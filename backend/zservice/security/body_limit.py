"""Request body size cap (OWASP REST: limit request size). Starlette and uvicorn accept a
body of any size, and a JSON body is parsed in memory, so one large POST could exhaust
the container. The cap is checked on Content-Length up front and counted on the stream
(chunked bodies carry no length).

Config: ZS_MAX_BODY_BYTES (config.SecuritySettings).
"""

import json

from zservice.security import config as security_config


class _TooLarge(Exception):
    pass


class BodySizeLimit:
    def __init__(self, app, max_bytes: int | None = None):
        self.app = app
        self.max_bytes = max_bytes or security_config.get_settings().max_body_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = _content_length(scope)
        if declared is not None and declared > self.max_bytes:
            await self._reject(send)
            return

        seen = 0
        started = False

        async def counted_receive():
            nonlocal seen
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > self.max_bytes:
                    raise _TooLarge
            return message

        async def tracked_send(message):
            nonlocal started
            started = started or message["type"] == "http.response.start"
            await send(message)

        try:
            await self.app(scope, counted_receive, tracked_send)
        except _TooLarge:
            if not started:
                await self._reject(send)

    async def _reject(self, send) -> None:
        answer = {
            "detail": f"request body over {self.max_bytes} bytes",
            "code": "http.too_large",
            "params": {"max": self.max_bytes},
        }
        body = json.dumps(answer).encode()
        headers = [(b"content-type", b"application/json"), (b"content-length", b"%d" % len(body))]
        await send({"type": "http.response.start", "status": 413, "headers": headers})
        await send({"type": "http.response.body", "body": body})


def _content_length(scope) -> int | None:
    for name, value in scope.get("headers") or ():
        if name == b"content-length":
            try:
                return int(value)
            except ValueError:
                return None
    return None
