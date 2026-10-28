"""Where the new web UI lives (one source for the auth gate and the security headers).

APP_BASE (env, default /app/) must match the base the web/ build used. Its sign-in page
and its hashed assets are public: the bundle holds no data (everything comes from the API
behind the gate), and the sign-in page cannot render without them.
"""

from . import config as web_config

APP_BASE = web_config.get_settings().app_base
APP_LOGIN = f"{APP_BASE}login/"
APP_PUBLIC_PATHS = frozenset({APP_LOGIN, f"{APP_LOGIN}index.html", f"{APP_BASE}theme-init.js"})
APP_PUBLIC_PREFIXES = (f"{APP_BASE}assets/",)
