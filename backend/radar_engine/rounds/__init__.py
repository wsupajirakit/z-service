"""Radar rounds: glue between z-service (Mongo + CSV builders) and the radar formulas.

Everything z-service-specific lives in this package so `radar_engine/lib.py` stays a
byte-identical copy of the stock-radar library. Public API:

  tf_status()        what is stored per timeframe right now (symbols + when written)
  run_round()        build the CSV set from Mongo -> run the screen -> freeze a round
  start_round()      the same in the background; round_status() reports progress
  ensure_packs_current() / repair_round_meta() / backfill_packs()   self-healing reads
"""

from .compute import run_round
from .config import TIMEFRAMES
from .csv_set import normalize_timeframes, tf_status
from .errors import RadarError
from .job import round_status, start_round
from .packs import PACKS_VERSION, build_packs
from .repair import backfill_packs, ensure_packs_current, repair_round_meta
from .serialize import jsonable

__all__ = [
    "PACKS_VERSION", "TIMEFRAMES", "RadarError", "backfill_packs", "build_packs",
    "ensure_packs_current", "jsonable", "normalize_timeframes", "repair_round_meta",
    "round_status", "run_round", "start_round", "tf_status",
]  # fmt: skip
