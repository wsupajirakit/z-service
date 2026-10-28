#!/usr/bin/env python3
"""Find the correct exchange of symbols that are not confirmed yet. Run it on a machine
with tvDatafeed (the server image): the dev machine cannot resolve exchanges.

Why: a wrong exchange fails silently (no bars, no error), as INDA and CSWI did.

Usage: python3 resolve_new_symbols.py
then paste the printed lines into SYMBOLS in dash/src/symbols.ts.
"""
from tvDatafeed import TvDatafeed

# Symbols whose exchange is not confirmed: never guess, let the resolver answer.
PENDING = {
    "SKHY": "SK Hynix ADR - listed on Nasdaq Jul 2026 (10 ADS = 1 Korean share); HBM theme",
    "USAR": "USA Rare Earth - critical materials theme",
    "NB":   "NioCorp Developments - critical materials theme",
    "CRML": "Critical Metals Corp - critical materials theme",
    "BULL": "Webull Corp - finance/broker theme",
    "BESI": "BE Semiconductor (Europe) - advanced packaging; may not trade in the US",
    "EROC": "ERock, Inc. - utility-scale on-site power; listed 2026; exchange not confirmed"
            " by search (4 Sep 2026)",
    # Added 9 Sep 2026: already in App.tsx but silently returned no bars for 6 rounds,
    # the same symptom as a wrong exchange. Let the resolver answer; do not guess again.
    "INDA": "iShares MSCI India ETF - in App.tsx, no data for 6 rounds",
    "CSWI": "CSW Industrials - in App.tsx, no data for 6 rounds",
    "ROLL": "RBC Bearings - in App.tsx, no data for 6 rounds",
    # New names from AIDC-LOUD-0909 whose exchange may differ from the first guess.
    "GLXY": "Galaxy Digital - moved its listing from Canada to the US in 2025; NASDAQ assumed",
    "CORZ": "Core Scientific - relisted after Chapter 11; NASDAQ assumed",
    "HUT":  "Hut 8 Corp - formerly dual-listed Toronto/US; NASDAQ assumed",
    "POET": "POET Technologies - dual-listed TSXV/NASDAQ; NASDAQ assumed",
}

tv = TvDatafeed()
ok, bad = [], []
for sym, why in PENDING.items():
    try:
        res = tv.search_symbol(sym) or []
    except Exception as e:
        bad.append((sym, f"search failed: {e}", why)); continue
    hit = next((it for it in res
                if it.get("symbol") == sym and it.get("exchange") in ("NASDAQ", "NYSE", "AMEX")), None)
    if hit:
        name = (hit.get("description") or sym).replace("'", "\\'")
        ok.append(f"{{ symbol: '{sym}', name: '{name}', exchange: '{hit['exchange']}' }},")
    else:
        found = sorted({it.get("exchange") for it in res if it.get("symbol") == sym})
        bad.append((sym, f"not on NASDAQ/NYSE/AMEX; found on: {found or 'nothing'}", why))

print("=== ready to paste into SYMBOLS ===")
for line in ok:
    print(line)
print("\n=== not usable yet: do not add until fixed ===")
for sym, reason, why in bad:
    print(f"{sym:6} {reason}\n       ({why})")
