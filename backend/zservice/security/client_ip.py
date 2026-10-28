"""The client address used by the login rate limit and the machine-key audit.

With FORWARDED_ALLOW_IPS=* uvicorn takes the leftmost X-Forwarded-For entry, which the
client writes itself when the proxy appends to the header. The rightmost entry is the
address the nearest proxy (Traefik) saw, so it is used instead. With an explicit proxy
list, uvicorn already picks the rightmost untrusted hop and its value is kept.
"""

from zservice.security import config as security_config


def client_ip(request) -> str:
    peer = request.client.host if request.client else "?"
    if security_config.get_settings().forwarded_allow_ips.strip() != "*":
        return peer
    hops = [h.strip() for v in request.headers.getlist("x-forwarded-for") for h in v.split(",")]
    hops = [h for h in hops if h]
    return _host(hops[-1]) if hops else peer


def _host(value: str) -> str:
    if value.startswith("["):
        return value[1:].split("]", 1)[0]
    return value.rsplit(":", 1)[0] if value.count(":") == 1 else value
