"""The gold job's Telegram summary must stay valid Telegram HTML (parse_mode=HTML)."""

import re

from zservice.domains.gold.telegram import TRUNCATED_NOTE, summary_html

ANSWER = "1. **Bias ตอนนี้**: LONG <7/10> & up\n6. **กลยุทธ์ <A&B>**: Entry 2050 | SL 2040\n"


def _tags(text: str) -> list[str]:
    return re.findall(r"</?[a-z]+>", text.replace(TRUNCATED_NOTE, ""))


def test_headings_are_markup_and_model_text_is_escaped():
    out = summary_html(ANSWER)
    assert out == (
        "<b>1. Bias ตอนนี้:</b>\nLONG &lt;7/10&gt; &amp; up\n\n"
        "<b>6. กลยุทธ์ &lt;A&amp;B&gt;:</b>\nEntry 2050 | SL 2040"
    )


def test_plain_answer_is_escaped_whole():
    assert summary_html("a < b & c") == "a &lt; b &amp; c"


def test_cut_never_splits_an_entity_or_leaves_a_tag_open():
    for limit in range(1, len(summary_html(ANSWER)) + 5):
        out = summary_html(ANSWER, limit)
        body = out.replace(TRUNCATED_NOTE, "")
        assert len(body) <= limit
        assert not re.search(r"&[a-z#0-9]*$", body), (limit, body)  # no half entity
        tags = _tags(out)
        assert tags.count("<b>") == tags.count("</b>"), (limit, out)
        assert out.endswith(TRUNCATED_NOTE) == (limit < len(summary_html(ANSWER)))
