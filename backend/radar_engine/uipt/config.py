"""Horizon presets from the formula file ("Horizon Parameters") and a number helper."""

S_DAYS_DEFAULT = 3  # UIPT-S xD, x = 1–5 trading days


M_WEEKS_DEFAULT = 4  # UIPT-M xW, x = 1–8 weeks


# "Risk per trade: UIPT-S = 0.25-0.5% ... UIPT-M = 0.5-1.0%.
#  Max concurrent: 4 S-trades and 5 M-trades."
S_RISK_PCT = (0.25, 0.5)


M_RISK_PCT = (0.5, 1.0)


S_MAX_CONCURRENT = 4


M_MAX_CONCURRENT = 5


DVOL_MIN_M = 30.0  # $30M/day median (approximated by the last bar)


def as_float(x, default=None):
    """Number or default — the export leaves plenty of nulls."""
    try:
        return float(x) if x is not None else default
    except (TypeError, ValueError):
        return default
