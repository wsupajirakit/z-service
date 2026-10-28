"""Earnings providers and the fallback chain.

Keys: config.EarningScanSettings (an empty key skips that provider). Where they travel
(plan B14):
* Finnhub: X-Finnhub-Token header (its docs)
* FMP: `apikey` header (FMP docs: "Authorization can be done using either request headers
  or URL query parameters"); not verified against these /api/v3 endpoints with a real key,
  so a 401/403 answer is retried once with the query key, and that fallback is logged
* Alpha Vantage: documents the key as a query parameter only; the access-log filter and
  error texts never echo the URL
"""

import csv
import io
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta

from . import config as earning_config

EARNING_SCAN_QUARTERS_BACK = 4
EARNING_SCAN_PROVIDERS = ["finnhub", "fmp", "alpha_vantage"]


def _finnhub_key() -> str:
    return earning_config.get_settings().finnhub_api_key.get_secret_value()


def _fmp_key() -> str:
    return earning_config.get_settings().fmp_api_key.get_secret_value()


def _alpha_vantage_key() -> str:
    return earning_config.get_settings().alpha_vantage_api_key.get_secret_value()


# Codes this module returns in plain response dicts (for the translation check).
MESSAGE_CODES = {"earning.no_provider": ()}
log = logging.getLogger("zs.earning_scan")


def _http_get_json(url: str, timeout: int = 10, headers: dict | None = None):
    req = urllib.request.Request(  # noqa: S310
        url, headers={"User-Agent": "Mozilla/5.0", **(headers or {})}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — fixed https APIs
        return json.loads(resp.read())


def _finnhub_headers() -> dict:
    return {"X-Finnhub-Token": _finnhub_key()}


def _fmp_get_json(url: str):
    """FMP with the key in the `apikey` header; one retry with the query key when the
    header is refused (401/403)."""
    try:
        return _http_get_json(url, headers={"apikey": _fmp_key()})
    except urllib.error.HTTPError as e:
        if e.code not in (401, 403):
            raise
        log.warning("FMP refused the header key (HTTP %s); retrying with the query key", e.code)
    joiner = "&" if "?" in url else "?"
    return _http_get_json(f"{url}{joiner}apikey={urllib.parse.quote(_fmp_key())}")


def _fetch_earnings_finnhub(symbol: str):
    if not _finnhub_key():
        return None
    quarters = _http_get_json(
        f"https://finnhub.io/api/v1/stock/earnings?symbol={urllib.parse.quote(symbol)}",
        headers=_finnhub_headers(),
    )
    if not quarters:
        return None
    history = [
        {
            "period": q.get("period"),
            "eps_actual": q.get("actual"),
            "eps_estimate": q.get("estimate"),
            "surprise_percent": q.get("surprisePercent"),
            "revenue_actual": None,
            "revenue_estimate": None,
        }
        for q in quarters[:EARNING_SCAN_QUARTERS_BACK]
    ]

    next_date = None
    try:
        today = datetime.now(UTC).date()
        cal = _http_get_json(
            "https://finnhub.io/api/v1/calendar/earnings"
            f"?from={today.isoformat()}&to={(today + timedelta(days=120)).isoformat()}"
            f"&symbol={urllib.parse.quote(symbol)}",
            headers=_finnhub_headers(),
        )
        rows = cal.get("earningsCalendar", []) if cal else []
        if rows:
            next_date = sorted(r.get("date") for r in rows if r.get("date"))[0]
    except Exception:  # noqa: S110 — the next date is optional; history is still returned
        pass

    return {"provider": "finnhub", "history": history, "next_earnings_date": next_date}


def _fetch_earnings_fmp(symbol: str):
    if not _fmp_key():
        return None
    rows = _fmp_get_json(
        f"https://financialmodelingprep.com/api/v3/earnings-surprises/{urllib.parse.quote(symbol)}"
    )
    if not rows:
        return None
    rows = sorted(rows, key=lambda r: r.get("date", ""), reverse=True)
    history = [
        {
            "period": r.get("date"),
            "eps_actual": r.get("actualEarningResult"),
            "eps_estimate": r.get("estimatedEarning"),
            "surprise_percent": None,
            "revenue_actual": None,
            "revenue_estimate": None,
        }
        for r in rows[:EARNING_SCAN_QUARTERS_BACK]
    ]

    next_date = None
    try:
        today = datetime.now(UTC).date()
        cal = _fmp_get_json(
            "https://financialmodelingprep.com/api/v3/earning_calendar"
            f"?from={today.isoformat()}&to={(today + timedelta(days=120)).isoformat()}"
        )
        upcoming = (
            sorted(
                (r.get("date") for r in cal if r.get("symbol") == symbol and r.get("date")),
            )
            if cal
            else []
        )
        if upcoming:
            next_date = upcoming[0]
    except Exception:  # noqa: S110 — the next date is optional; history is still returned
        pass

    return {"provider": "fmp", "history": history, "next_earnings_date": next_date}


def _fetch_earnings_alpha_vantage(symbol: str):
    if not _alpha_vantage_key():
        return None
    data = _http_get_json(
        f"https://www.alphavantage.co/query?function=EARNINGS&symbol={urllib.parse.quote(symbol)}&apikey={urllib.parse.quote(_alpha_vantage_key())}"
    )
    if not data or "Note" in data or "Information" in data:
        # "Note"/"Information" keys mean the free-tier rate limit was hit.
        return None
    quarters = data.get("quarterlyEarnings", [])
    if not quarters:
        return None
    history = [
        {
            "period": q.get("fiscalDateEnding"),
            "eps_actual": q.get("reportedEPS"),
            "eps_estimate": q.get("estimatedEPS"),
            "surprise_percent": q.get("surprisePercentage"),
            "revenue_actual": None,
            "revenue_estimate": None,
        }
        for q in quarters[:EARNING_SCAN_QUARTERS_BACK]
    ]

    next_date = None
    try:
        # EARNINGS_CALENDAR returns CSV, not JSON, so it can't use _http_get_json.
        url = f"https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&symbol={urllib.parse.quote(symbol)}&horizon=3month&apikey={urllib.parse.quote(_alpha_vantage_key())}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 — fixed https API
            text = resp.read().decode()
        reader = csv.DictReader(io.StringIO(text))
        dates = sorted(
            row["reportDate"]
            for row in reader
            if row.get("symbol") == symbol and row.get("reportDate")
        )
        if dates:
            next_date = dates[0]
    except Exception:  # noqa: S110 — the next date is optional; history is still returned
        pass

    return {"provider": "alpha_vantage", "history": history, "next_earnings_date": next_date}


EARNING_SCAN_FETCHERS = {
    "finnhub": _fetch_earnings_finnhub,
    "fmp": _fetch_earnings_fmp,
    "alpha_vantage": _fetch_earnings_alpha_vantage,
}


def _fetch_earnings_for_symbol(symbol: str):
    """Try each provider in EARNING_SCAN_PROVIDERS order; return the first
    usable result. Records which providers were attempted/skipped so the
    caller can report why a symbol has no data."""
    attempted = []
    for provider in EARNING_SCAN_PROVIDERS:
        fetcher = EARNING_SCAN_FETCHERS[provider]
        try:
            result = fetcher(symbol)
        except Exception as e:
            attempted.append({"provider": provider, "status": "error", "detail": str(e)[:200]})
            continue
        if result is None:
            attempted.append({"provider": provider, "status": "skipped_or_empty"})
            continue
        result["attempted"] = [*attempted, {"provider": provider, "status": "ok"}]
        return result

    return {
        "provider": None,
        "history": [],
        "next_earnings_date": None,
        "attempted": attempted,
        "error_code": "earning.no_provider",
        "error": "หมดทุก provider (Finnhub, FMP, Alpha Vantage) แล้ว — ไม่มีข้อมูล earnings สำหรับสัญลักษณ์นี้",
    }
