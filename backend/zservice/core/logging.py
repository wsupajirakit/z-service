"""Logger setup.

`logger` is the legacy "automate" logger: INFO to the console and to automate.log, same
format as before. New code logs under the "zs" namespace (zs.machine, zs.watchlist, ...),
which gets a console handler here.

* automate.log lives in ZS_STATE_DIR (the image's app-owned directory; the working
  directory when unset) and rotates (5 MB x 3), so it can neither stop a non-root boot
  nor fill the disk. A log file that cannot be opened only costs the file copy.
* `install_access_log_redaction()` masks secret query values (the legacy `pull_key`,
  tokens) in uvicorn's access log, which prints every request's full path + query.
"""

import logging
import logging.handlers
import os
import re

from zservice.core import runtime

AUTOMATE_LOG_FILE = os.path.join(runtime.get_settings().state_dir or ".", "automate.log")
_LOG_MAX_BYTES = 5 * 1024 * 1024
_LOG_BACKUPS = 3
_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# Query parameters whose values must never reach a log line.
_SECRET_PARAM = re.compile(
    r"(?i)([?&](?:pull_key|token|access_token|api_?key|key|secret|password)=)[^&\s\"]*"
)


def _attach(target: logging.Logger, handler: logging.Handler) -> None:
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(_FORMAT))
    target.addHandler(handler)


def _file_handler() -> logging.Handler | None:
    try:
        return logging.handlers.RotatingFileHandler(
            AUTOMATE_LOG_FILE, maxBytes=_LOG_MAX_BYTES, backupCount=_LOG_BACKUPS
        )
    except OSError as e:
        logging.getLogger("zs").warning("automate.log not writable (%s): console only", e)
        return None


def _setup() -> logging.Logger:
    zs = logging.getLogger("zs")
    zs.setLevel(logging.INFO)
    if not zs.handlers:
        _attach(zs, logging.StreamHandler())
    automate = logging.getLogger("automate")
    automate.setLevel(logging.INFO)
    if not automate.handlers:  # importing twice must not double every line
        handler = _file_handler()
        if handler is not None:
            _attach(automate, handler)
        _attach(automate, logging.StreamHandler())
    return automate


def redact(text: str) -> str:
    return _SECRET_PARAM.sub(r"\1***", text)


class _RedactQuerySecrets(logging.Filter):
    """uvicorn.access records carry (client, method, path_with_query, version, status)."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple):
            record.args = tuple(redact(a) if isinstance(a, str) else a for a in record.args)
        elif isinstance(record.msg, str):
            record.msg = redact(record.msg)
        return True


def install_access_log_redaction() -> None:
    access = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, _RedactQuerySecrets) for f in access.filters):
        access.addFilter(_RedactQuerySecrets())


logger = _setup()
