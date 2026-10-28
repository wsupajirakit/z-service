"""Application factory: one place that wires middleware, routers, start-up and the
frontend.

Middleware order matters (the last one added is the outermost): CORS (dev only), the auth
gate, the no-cache header for HTML, then security headers. Routers are included in the
old registration order; the static frontend is mounted last so every /api/* route wins.
Every Settings class is validated once the routers are imported, so a malformed env value
stops the boot. Start-up (lifespan): AUTH_SECRET check, then the auto-job autostart.
ApiError answers carry a translatable `code` next to the legacy `detail` (zservice/core/errors.py).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from zservice import bootstrap
from zservice.core import config, runtime
from zservice.core.errors import install_error_handlers
from zservice.core.logging import install_access_log_redaction
from zservice.security.body_limit import BodySizeLimit
from zservice.security.cors import add_cors
from zservice.security.headers import security_headers
from zservice.security.machine import registry
from zservice.security.middleware import require_auth
from zservice.web.frontend import mount_frontend, no_cache_html


def create_app() -> FastAPI:
    docs_on = runtime.get_settings().docs
    app = FastAPI(
        lifespan=_lifespan,
        docs_url="/docs" if docs_on else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs_on else None,
    )
    install_error_handlers(app)  # {"detail", "code", "params"} for ApiError
    install_access_log_redaction()  # pull_key / token query values never reach the log
    add_cors(app)  # only for origins listed in ZS_CORS_ORIGINS (local dev); none in prod
    app.middleware("http")(require_auth)
    # Built now so a malformed ZS_API_KEYS stops the boot instead of failing open.
    registry.current()

    from zservice.domains.auth import routes as auth_routes

    app.include_router(auth_routes.router)
    bootstrap.connect_store()
    bootstrap.start_tradingview()
    _include_domain_routers(app)
    app.middleware("http")(no_cache_html)
    app.add_middleware(BodySizeLimit)  # ZS_MAX_BODY_BYTES; its 413 still gets the headers
    app.middleware("http")(security_headers)  # outermost: also on 401 / redirects
    mount_frontend(app)
    config.validate_all()  # every domain is imported by now
    return app


@asynccontextmanager
async def _lifespan(app: FastAPI):
    from zservice.domains.jobs import autostart
    from zservice.security import tokens

    # Fail closed: refuse to serve without a real AUTH_SECRET (no fallback in auth.py).
    tokens.assert_configured()
    autostart.start_if_enabled()  # only after the AUTH_SECRET check
    yield


def _include_domain_routers(app: FastAPI) -> None:

    from zservice.domains.admin import routes as admin
    from zservice.domains.drive import routes as drive
    from zservice.domains.earning_scan import routes as earning_scan
    from zservice.domains.exports import routes as exports
    from zservice.domains.gold import routes as gold
    from zservice.domains.gold_mode import routes as gold_mode  # docs/gold-mode-design.md
    from zservice.domains.health import routes as health
    from zservice.domains.history import routes as history
    from zservice.domains.inbound_events import routes as inbound_events
    from zservice.domains.jobs import routes as jobs
    from zservice.domains.market_data import routes as market_data
    from zservice.domains.portfolio import routes as portfolio
    from zservice.domains.radar_rounds import routes as radar_rounds
    from zservice.domains.settings import routes as settings
    from zservice.domains.stock_radar import routes as stock_radar
    from zservice.domains.symbols import routes as symbols
    from zservice.domains.tradingview import routes as tradingview
    from zservice.domains.watchlist import routes as watchlist

    for module in (
        drive,
        gold_mode,
        radar_rounds,
        admin,
        settings,
        watchlist,
        portfolio,
        history,
        inbound_events,
        exports,
        tradingview,
        market_data,
        symbols,
        jobs,
        gold,
        stock_radar,
        earning_scan,
        health,
    ):
        app.include_router(module.router)
