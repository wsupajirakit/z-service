"""JSON exactly as stock-radar writes full.json, with NaN/Infinity removed."""

import json
import math


def _strip_nan(o):
    """NaN/Infinity -> None, recursively."""
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
        return None
    if isinstance(o, dict):
        return {k: _strip_nan(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_strip_nan(v) for v in o]
    return o


def jsonable(obj):
    """Plain JSON types only (numpy/pandas scalars -> str via default), matching
    exactly what stock-radar writes into full.json.

    allow_nan=False on purpose: Python happily writes a bare `NaN` token and
    reads it back, but Starlette's JSONResponse refuses it — a round containing
    one would save fine and then 500 forever on GET. Strip them instead."""
    try:
        return json.dumps(obj, ensure_ascii=False, default=str, allow_nan=False)
    except ValueError:
        loose = json.loads(json.dumps(obj, ensure_ascii=False, default=str))
        return json.dumps(_strip_nan(loose), ensure_ascii=False, allow_nan=False)
