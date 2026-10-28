"""Gold-mode export: validate the request, build the per-mode zip (formula file + one CSV
per symbol/timeframe set) and keep it in a short TTL cache (each mode's `ttl`)."""

import io
import threading
import time
import zipfile

from zservice.core.errors import ApiError

from .client import _fetch_df
from .config import _COMP_EXCH, _XAU_EXCHANGES, GOLD_MODES
from .export import _formula_csv, _symbol_csv

XAU = "XAUUSD"


class ZipCache:
    """(mode, exchange) -> zip bytes until its expiry; one lock for all threads."""

    def __init__(self) -> None:
        self._items: dict[tuple[str, str], tuple[float, bytes]] = {}
        self._lock = threading.Lock()

    def get(self, key: tuple[str, str], now: float) -> bytes | None:
        with self._lock:
            hit = self._items.get(key)
        return hit[1] if hit and hit[0] > now else None

    def put(self, key: tuple[str, str], data: bytes, expires_at: float) -> None:
        with self._lock:
            self._items[key] = (expires_at, data)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


CACHE = ZipCache()


def validate(mode: str, exchange: str) -> tuple[str, str]:
    mode, exchange = mode.strip().lower(), exchange.strip().upper()
    if mode not in GOLD_MODES:
        raise ApiError(
            400,
            "gold_mode.invalid_mode",
            f"mode ต้องเป็นหนึ่งใน {list(GOLD_MODES)}",
            params={"allowed": ", ".join(GOLD_MODES)},
        )
    if exchange not in _XAU_EXCHANGES:
        raise ApiError(
            400,
            "gold_mode.invalid_exchange",
            f"exchange ต้องเป็นหนึ่งใน {_XAU_EXCHANGES}",
            params={"allowed": ", ".join(_XAU_EXCHANGES)},
        )
    return mode, exchange


def export_zip(mode: str, exchange: str) -> tuple[bytes, bool]:
    """(zip bytes, served from cache)."""
    key, now = (mode, exchange), time.time()
    cached = CACHE.get(key, now)
    if cached is not None:
        return cached, True
    data = _build_zip(mode, exchange)
    CACHE.put(key, data, now + GOLD_MODES[mode]["ttl"])
    return data, False


def _build_zip(mode: str, exchange: str) -> bytes:
    """Every set the mode lists; a failing set is reported in _errors.txt, but at least one
    XAUUSD file must succeed or the export is refused."""
    errors, xau_ok = [], 0
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("gold_formula.csv", _formula_csv(mode, exchange))
        for symbol, tf, n_bars in GOLD_MODES[mode]["sets"]:
            exch = exchange if symbol == XAU else _COMP_EXCH[symbol]
            try:
                df = _fetch_df(symbol, exch, tf, n_bars)
                csv_bytes = _symbol_csv(mode, exchange, symbol, tf, df)
                zf.writestr(f"{symbol.lower()}_{tf}.csv", csv_bytes)
                xau_ok += symbol == XAU
            except Exception as e:
                errors.append(f"{exch}:{symbol} {tf} -> {e}")
        if errors:
            zf.writestr("_errors.txt", "\n".join(errors))
    if xau_ok == 0:
        raise ApiError(
            502,
            "gold_mode.no_xau",
            f"ดึง XAUUSD จาก {exchange} ไม่ได้เลย: {errors}",
            params={"exchange": exchange, "reason": "; ".join(errors)},
        )
    return buf.getvalue()


def modes_listing() -> dict:
    """Lets the UIs render mode buttons without hardcoding."""
    return {
        "exchanges": _XAU_EXCHANGES,
        "modes": [
            {
                "mode": m,
                "horizon": s["horizon"],
                "tf_roles": s["tf_roles"],
                "ttl": s["ttl"],
                "rr_min": s["rr_min"],
                "files": [f"{sym.lower()}_{tf}.csv" for sym, tf, _ in s["sets"]],
            }
            for m, s in GOLD_MODES.items()
        ],
    }
