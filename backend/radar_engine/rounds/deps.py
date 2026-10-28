"""The outside world a round touches, behind one seam: Mongo (the radar_rounds repo) and
the app side (display clock + the export CSV builders). tests/radar/test_rounds_parity.py
swaps both for fakes that serve stock-radar's reference CSVs; nothing else in the package
imports them directly.
The app side is imported lazily so the package imports without the app."""

from types import SimpleNamespace

from zservice.db.repos import radar_rounds as _rounds_repo

_overrides: dict = {}


def _app():
    from zservice.core.clock import current_tz
    from zservice.domains.exports.formula_csv import build_formula_csv_bytes
    from zservice.domains.exports.selection import fetch_export_rows
    from zservice.domains.exports.stock_csv import build_export_csv_bytes

    return SimpleNamespace(
        current_tz=current_tz,
        fetch_export_rows=fetch_export_rows,
        build_export_csv_bytes=build_export_csv_bytes,
        build_formula_csv_bytes=build_formula_csv_bytes,
    )


def store():
    return _overrides.get("store", _rounds_repo)


def app():
    return _overrides["app"] if "app" in _overrides else _app()


def override(*, app=None, store=None) -> None:
    """Tests only: replace the app side and/or the store until reset()."""
    if app is not None:
        _overrides["app"] = app
    if store is not None:
        _overrides["store"] = store


def reset() -> None:
    _overrides.clear()
