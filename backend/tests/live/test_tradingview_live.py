"""Live TradingView check: fetch SPY and verify sessions line up with volume and daily bars
are stamped at the 09:30 ET open. Calls TradingView for real, so it runs when asked:
ZS_RUN_LIVE=1 venv/bin/python -m pytest -m live
"""

import pandas as pd
import pytest

from zservice.domains.market_data.pipeline import process_symbol

pytestmark = pytest.mark.live
RTH_VOLUME_RATIO = 3  # RTH bars carry several times the extended-hours volume


def test_hourly_sessions_line_up_with_volume():
    recs = process_symbol("SPY", "AMEX", "1h", extended_session=True, rows=40, store=False)
    df = pd.DataFrame(recs)
    df["dt"] = pd.to_datetime(df["datetime"])
    rth = df[df["session"] == "RTH"]
    ext = df[df["session"].isin(["PRE", "POST", "CLOSED"])]
    assert rth["volume"].median() > ext["volume"].median() * RTH_VOLUME_RATIO
    hours = rth["dt"].dt.hour + rth["dt"].dt.minute / 60
    assert hours.between(9.5, 16).all(), "RTH bars must sit inside 09:30-16:00 ET"


def test_daily_bars_are_stamped_at_the_open():
    recs = process_symbol("SPY", "AMEX", "1d", rows=5, store=False)
    assert all(r["datetime"].endswith("09:30:00") for r in recs)
