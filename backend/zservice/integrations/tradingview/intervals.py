"""API interval names -> tvDatafeed Interval values. The keys are also the set of
intervals the API accepts (moved unchanged from main.py)."""

from tvDatafeed import Interval

INTERVAL_MAP = {
    "15m": Interval.in_15_minute,
    "30m": Interval.in_30_minute,
    "1h": Interval.in_1_hour,
    "4h": Interval.in_4_hour,
    "1d": Interval.in_daily,
    "1w": Interval.in_weekly,
}
