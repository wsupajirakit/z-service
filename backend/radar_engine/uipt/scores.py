"""UIPT-S / UIPT-M scores (the spec's timeframe weights)."""

from .config import as_float
from .gates import _pullback_ctx


def _norm(x, lo, hi):
    """Clamp to 0..1 for score blending."""
    if x is None:
        return 0.0
    return max(0.0, min(1.0, (x - lo) / (hi - lo) if hi > lo else 0.0))


def score_s(v: dict) -> float:
    """Spec: "score weights: 1H CMF/RVOL/OBV 50%, 4H 30%, 1D 20%".
    Each timeframe contributes its flow quality (CMF + volume + IPI status)."""

    def tf_quality(tf: dict) -> float:
        cmf = _norm(as_float(tf.get("cmf20"), as_float(tf.get("cmf"))), -0.15, 0.25)
        rvol = _norm(as_float(tf.get("rvol")), 0.5, 2.0)
        ipi = 1.0 if tf.get("status") == "Accum" else (0.0 if tf.get("status") == "Dist" else 0.5)
        return 0.5 * cmf + 0.25 * rvol + 0.25 * ipi

    h1, h4, d1 = v.get("1h") or {}, v.get("4h") or {}, v.get("1d") or {}
    base = 0.50 * tf_quality(h1) + 0.30 * tf_quality(h4) + 0.20 * tf_quality(d1)

    # "Rank = coil tightness x flow slope x pivot proximity" — proximity is the
    # part we can measure exactly, so it modulates the flow score.
    coil = v.get("_coil") or {}
    dist = as_float(coil.get("dist_pct"))
    prox = _norm(-abs(dist), -3.0, 0.0) if dist is not None else 0.3
    tight = 1.0 if coil.get("contracting") else 0.7
    ign = 1.0 if coil.get("ignition") else 0.85
    return round(10 * base * (0.6 + 0.4 * prox) * tight * ign, 2)


def score_m(v: dict) -> float:
    """Spec: "1W structure+CMF 40%, 1D 40%, 4H timing 20%"."""

    def struct_flow(tf: dict) -> float:
        gc = 1.0 if tf.get("gc") else 0.0
        cmf = _norm(as_float(tf.get("cmf")), -0.10, 0.20)
        ipi = 1.0 if tf.get("status") == "Accum" else (0.0 if tf.get("status") == "Dist" else 0.5)
        return 0.4 * gc + 0.35 * cmf + 0.25 * ipi

    w1, d1, h4 = v.get("1w") or {}, v.get("1d") or {}, v.get("4h") or {}
    base = 0.40 * struct_flow(w1) + 0.40 * struct_flow(d1) + 0.20 * struct_flow(h4)

    ext = as_float((v.get("_stage") or {}).get("ext200_pct"), 0.0) or 0.0
    stretch = (
        1.0 if ext <= 25 else (0.85 if ext <= 40 else 0.6)
    )  # the more stretched, the bigger the penalty
    if _pullback_ctx(v):
        base *= 1.10  # Phase-3 context bonus
    return round(min(10.0, 10 * base * stretch), 2)
