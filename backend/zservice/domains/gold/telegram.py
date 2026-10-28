"""Telegram text of a finished gold job: header, Drive link and the short analysis."""

import html
import re
from datetime import datetime

from zservice.core.clock import current_tz, current_tz_label
from zservice.core.clock import fmt_wall as _fmt
from zservice.integrations import drive

# Headers like "1. **Current bias**:", "### 1. **Current bias**:" or "1. **Current bias**".
# Sections are matched by number, so a heading in any language parses.
SECTION_HEADER = re.compile(r"(?m)^\s*(?:#+\s*)?(\d+)\.\s+\*\*(.+?)\*\*[:\s]*")
# The sections worth a phone notification: 1 = bias & score, 6 = setup (entry/SL/TP).
SUMMARY_SECTIONS = ((1, "Current bias"), (6, "Strategy"))
SUMMARY_LIMIT = 3500  # Telegram caps a message at 4096 chars; leave room for the header
TRUNCATED_NOTE = "\n\n<i>[ข้อความถูกตัดเนื่องจากยาวเกินไป]</i>"


def gold_job_message(result: dict, info: dict | None, drive_on: bool) -> str:
    lines = [
        "🥇 <b>Gold (XAUUSD) วิเคราะห์เสร็จแล้ว</b>",
        f"🏁 เสร็จ: {_fmt(datetime.now(current_tz()))} ({_esc(current_tz_label())})",
        f"📊 Source: {_esc(result.get('source_label'))} | Model: {_esc(result.get('model'))}",
        f"💰 ราคาโดยประมาณ: {_esc(result.get('latest_price'))}",
    ]
    if info:
        lines.append(f'\n📁 Drive: <a href="{info["link"]}">{info["name"]}</a>')
    elif drive_on and drive.root_folder_id():
        lines.append("\n📁 Drive: อัปโหลดไม่สำเร็จ")
    summary = summary_html(result.get("analysis", ""))
    return "\n".join(lines) + f"\n\n📝 <b>ผลวิเคราะห์ตลาดทองคำ (ย่อ):</b>\n{summary}"


def _esc(value) -> str:
    return html.escape(str(value))


def summary_html(analysis: str, limit: int = SUMMARY_LIMIT) -> str:
    """Telegram-HTML summary: our <b> headings stay markup, the model's text is escaped,
    and a cut at `limit` never splits an entity or leaves a tag open (Telegram rejects
    the whole message for either)."""
    out, used = [], 0
    for heading, body in summary_parts(analysis):
        head = f"<b>{html.escape(heading)}:</b>\n" if heading else ""
        text = html.escape(body)
        room = limit - used - (2 if out else 0) - len(head)
        if len(text) > room:
            if room > 0:
                out.append(head + _cut_escaped(text, room))
            return "\n\n".join(out) + TRUNCATED_NOTE
        out.append(head + text)
        used += (2 if len(out) > 1 else 0) + len(head) + len(text)
    return "\n\n".join(out)


def summary_parts(analysis: str) -> list[tuple[str | None, str]]:
    """(heading, raw text) of the summary sections; the whole answer when it has none."""
    matches = list(SECTION_HEADER.finditer(analysis))
    sections, titles = {}, {}
    for idx, match in enumerate(matches):
        num = int(match.group(1))
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(analysis)
        sections[num] = analysis[match.end() : end].strip()
        titles[num] = match.group(2).strip()
    parts = [
        (f"{num}. {titles.get(num, default)}", sections[num])
        for num, default in SUMMARY_SECTIONS
        if num in sections
    ]
    return parts or [(None, analysis)]


def _cut_escaped(text: str, n: int) -> str:
    """First n chars of escaped text, minus a trailing half entity ("&am")."""
    cut = text[:n]
    amp = cut.rfind("&")
    return cut[:amp] if amp != -1 and ";" not in cut[amp:] else cut
