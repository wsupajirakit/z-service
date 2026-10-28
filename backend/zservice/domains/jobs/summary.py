"""Telegram summary of a finished job or auto round (HTML parse mode).

Every value that comes from settings or the request (timezone label, timeframes, symbol
names) is HTML-escaped: Telegram rejects the whole message on a stray "<" or "&".
"""

from html import escape

from zservice.core.clock import current_tz_label
from zservice.core.clock import fmt_wall as _fmt

MAX_FAILED_SHOWN = 10


def summary_text(title, started, finished, timeframes, per_tf, n_symbols, rows) -> str:
    """`per_tf` holds (tf, extended, ok_count, failed_symbols) per timeframe that ran."""
    mins, secs = divmod(int((finished - started).total_seconds()), 60)
    lines = [
        title,
        f"🕒 เริ่ม: {_fmt(started)}",
        f"🏁 เสร็จ: {_fmt(finished)} ({escape(current_tz_label())})",
        f"⏱ ใช้เวลา: {mins} นาที {secs} วินาที",
        f"📊 Timeframes: {escape(', '.join(timeframes))}",
        f"🔍 Filter: rows={rows}, symbols/TF={n_symbols}",
        "",
    ]
    for tf, ext, ok, failed in per_tf:
        line = f"• <b>{escape(tf)}</b> (ext={'on' if ext else 'off'}): สำเร็จ {ok}/{n_symbols}"
        if failed:
            more = " …" if len(failed) > MAX_FAILED_SHOWN else ""
            shown = escape(", ".join(failed[:MAX_FAILED_SHOWN]))
            line += f" | ❌ {len(failed)}: {shown}{more}"
        lines.append(line)
    return "\n".join(lines)
