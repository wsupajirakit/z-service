"""Round settings: the timeframes the screen understands, retention, staleness limits."""

from pydantic import PositiveInt

from zservice.core.config import ZsSettings, env_field, settings_getter

from .. import lib

# The 4 timeframes the radar screen understands, coarse -> fine (lib.TFS order).
TIMEFRAMES = list(lib.TFS)


class RoundsSettings(ZsSettings):
    keep_rounds: PositiveInt = env_field(
        "RADAR_KEEP_ROUNDS", 30, doc="Radar rounds kept; older ones are pruned after a run."
    )


get_settings = settings_getter(RoundsSettings)


# A timeframe written more than this long before the freshest one in the same
# round is flagged: mixing a 2-day-old 1W with a fresh 1H is a real analysis
# hazard, not a detail.
STALE_SPREAD_HOURS = 6


# A round whose data is older than this at compute time is flagged too. A round
# built from last week's stored bars is perfectly valid history, but it is NOT a
# picture of the market now — and it looks identical to a fresh one otherwise.
STALE_DATA_HOURS = 18
