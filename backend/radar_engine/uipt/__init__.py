"""UIPT-S / UIPT-M — the two horizon rankings from the formula file's UIPT_HORIZON block.

WHY THIS FILE EXISTS
--------------------
`lib.py` (the stock-radar copy, never edited here) stops at `uipt_stage()` — one
stage per symbol — plus two coarse helpers, `rank_short()` (names sitting near a
pivot) and `conviction()` (a blended score). None of those is the UIPT-S/UIPT-M
ranking that `csv/ztrade_formula.csv` specifies under `UIPT_HORIZON`; that spec
was always assembled by hand when writing a report. This module implements it so
the page can show it.

    UIPT = Ultra Institutional Pivot Trigger
    -S   = SHORT horizon, 1–5 trading days   (default 3D)
    -M   = MEDIUM horizon, 1–8 weeks / 1–2 months (default 4W)

The suffix is the HOLDING HORIZON. It is unrelated to lib.py's `-S` stage names
(TRIGGER-S/SETUP-S/…), which mean something else entirely: a fallback staging
used when the CSV set has no 1D/1W bars at all. Two different "S". Do not merge.

Every rule below is transcribed from the formula file, quoted in the docstring of
the function that implements it, so a reader can diff spec against code.

SPEC LIMITS WE CANNOT MEET FROM CSV ALONE (reported, never faked):
  * "median dollar-volume > $30M/day" — the export carries the LAST bar's
    dollar volume, not a median. We gate on that and label it as such.
  * "1D CMF rising 3 bars", "3+ narrow/inside bars", "volume dry-up on down
    bars", "ignition bar in last 15 bars" — need per-bar history; the round only
    keeps the last bar per timeframe. The coil detector therefore runs on the
    flags lib.py already computed (`contracting`, `ignition`) and says so.
  * TIME-STOP as a calendar date, earnings/CPI/FOMC inside the window, and
    sector-flow IN/OUT — need a calendar and the sector map; the first two are
    emitted as trading-day counts and left to the report, the third is filled
    from the round's own sector table where the symbol maps to a known ETF.
"""

from .config import DVOL_MIN_M, M_WEEKS_DEFAULT, S_DAYS_DEFAULT  # noqa: F401
from .rank import packs, rank  # noqa: F401
from .state import phase4_live, state_tag  # noqa: F401
from .verdicts import entry_verdict  # noqa: F401
