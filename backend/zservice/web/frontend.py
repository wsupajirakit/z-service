"""Static frontend serving (moved unchanged from main.py).

The built frontend is mounted LAST so every /api/* route takes precedence. FRONTEND_DIR
is the build folder (the Dockerfile copies it to ./static).
"""

import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config as web_config

NO_CACHE = "no-store, no-cache, must-revalidate"


async def no_cache_html(request, call_next):
    """index.html / login must never be cached by browsers or proxies, so a new deploy
    shows up on a plain reload (hashed asset bundles stay cacheable)."""
    resp = await call_next(request)
    path = request.url.path
    if path in ("/", "/login") or path.endswith(".html"):
        resp.headers["Cache-Control"] = NO_CACHE
    return resp


def mount_frontend(app: FastAPI) -> None:
    frontend_dir = web_config.get_settings().frontend_dir
    if not os.path.isdir(frontend_dir):
        print(f"[frontend] '{frontend_dir}' not found; serving API only")
        return

    @app.get("/login")
    def login_page():
        """Explicit route: StaticFiles(html=True) resolves /login to a *directory* named
        `login`, so without this the login page 404s."""
        path = os.path.join(frontend_dir, "login.html")
        if not os.path.isfile(path):
            raise HTTPException(status_code=404, detail="login.html not built")
        return FileResponse(path)

    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
