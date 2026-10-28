"""radar_engine — the stock-radar screen (UIPT/regime/sector/spring) on the server.

lib.py      VERBATIM COPY of the stock-radar formula library
            (stock-radar/.claude/skills/us-stock-fund-manager/scripts/radar_lib.py).
            NEVER edit it here. Re-sync with sync_lib.sh when the formula
            changes upstream; any local edit silently forks the two systems
            and the numbers stop matching.

rounds/     everything z-service-specific: build the CSV set from Mongo with the SAME
            builders /api/export_zip uses, run the screen, and shape the result into
            a "round" document. All behaviour changes belong there.

uipt/       the UIPT-S/M ranking (gates · scores · plans · verdicts · rank).
timing.py   the bar-close / order-day clock (real NYSE calendar) the packs use.
"""
