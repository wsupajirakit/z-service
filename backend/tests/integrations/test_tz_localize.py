"""tvDatafeed builds bar times with datetime.fromtimestamp(): naive wall time in the SERVER's
system zone (UTC in the Coolify container, UTC+7 on the dev Mac). The fetch step localizes
with the real system zone (dateutil tzlocal), never the display setting — the old code used
the display zone and shifted every bar by 7 h on the server. Checked under three system
zones, including a winter (EST) bar."""

import time
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from zservice.domains.market_data.fetch import _to_eastern

ET = ZoneInfo("America/New_York")
TRUTH = [
    datetime(2026, 7, 6, 9, 30, tzinfo=ET),  # RTH open
    datetime(2026, 7, 6, 15, 0, tzinfo=ET),
    datetime(2026, 1, 5, 9, 30, tzinfo=ET),  # winter, EST (UTC-5)
]


@pytest.fixture
def system_zone(monkeypatch):
    def use(zone: str) -> None:
        monkeypatch.setenv("TZ", zone)
        time.tzset()

    yield use
    monkeypatch.undo()
    time.tzset()


@pytest.mark.parametrize("zone", ["UTC", "Asia/Bangkok", "America/New_York"])
def test_bars_land_on_the_right_et_time_in_any_server_zone(system_zone, zone):
    system_zone(zone)
    naive = [datetime.fromtimestamp(t.timestamp()) for t in TRUTH]  # what tvDatafeed does
    frame = pd.DataFrame({"close": [1.0, 2.0, 3.0]}, index=pd.DatetimeIndex(naive))
    assert list(_to_eastern(frame).index) == TRUTH
