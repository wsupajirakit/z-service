# 🩺 Symbol health — entries that occupy a slot but never return data

Checked 3 Sep 2026 against the CSV set pulled by `stock-radar/.claude/skills/us-stock-fund-manager/scripts/load_all.sh`.

**Method:** compare the `SYMBOLS` array in `dash/src/symbols.ts` against the symbols that
actually appear in `ztrade_export_1d_part*.csv`. Anything in the array but missing from
the export is being fetched every round and returning nothing.

```
SYMBOLS array (symbols.ts)   397
in the 1d export          394
gap                         3   -> SPCX, INDA, CSWI
```

A wrong `exchange` is the usual cause, and per `ADD_SYMBOLS.md` troubleshooting it costs
roughly **35 s per symbol per round** — so three bad entries burn ~1.5 min of every
automate round for nothing.

## Resolved

| Symbol | Status |
|--|--|
| **SPCX** | **Removed 3 Sep 2026.** The entry read `Space Exploration Technologies Corp (SpaceX)` on NASDAQ — SpaceX has no US-listed common stock, so this could never resolve. Array is now 396. |

## Still open — needs the exchange verified, do NOT guess

| Symbol | Currently in symbols.ts | Suspicion |
|--|--|--|
| **INDA** | `iShares MSCI India ETF`, `NASDAQ` | Most iShares ETFs list on NYSE Arca, which TradingView exposes as `AMEX`. Likely the wrong exchange rather than a bad ticker. |
| **CSWI** | `CSW Industrials, Inc.`, `NASDAQ` | Real, actively traded company. Exchange looks right, so the failure is probably something else — check whether the fetch errors or just returns an empty frame. |

**How to verify** (needs `tvDatafeed`, which is installed in the backend venv, not on the
laptop shell):

```bash
cd backend && source venv/bin/activate
python - <<'PY'
from tvDatafeed import TvDatafeed
tv = TvDatafeed()
for sym in ("INDA", "CSWI"):
    for r in (tv.search_symbol(sym) or []):
        if r.get("symbol") == sym:
            print(sym, r.get("exchange"), "|", r.get("description"), "|", r.get("type"))
PY
```

Then update the `exchange` field in `dash/src/symbols.ts`, push (Coolify redeploys), and on
the dashboard press **หยุด Auto Run → Automate All** so the job picks up the new list —
see `ADD_SYMBOLS.md` step 4.

## Cosmetic — 49 entries have no display name

These carry `name` equal to the ticker, so the dash shows a bare symbol. Harmless for
fetching, annoying to read:

`AAON · AGO · AGX · AROC · ATEX · BG · CECO · CRS · CW · EXEL · EXP · FIX · FLEX · FLS ·
FN · GHM · HNRG · IDCC · IESC · IRM · ITRN · JEF · KGC · KGS · LEU · MLI · MWA · NGS ·
NI · NWPX · NXST · OTTR · PIPR · PLMR · SBAC · SKWD · STE · STRL · T · TOL · UFPT · UMH ·
USFD · USLM · UTI · VICI · WHD · WLDN · WST`

(`HBM` was in this list and was filled in on 3 Sep 2026 as `Hudbay Minerals Inc.`)
`resolve_symbols.py` already does exactly this lookup — it can fill all 49 in one pass.
