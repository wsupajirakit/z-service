"""ztrade_formula.csv builder: the analysis rules and framework text, plus live headlines.

The static rows are data, not code: formula_rules.json holds them in file order. Only the
LATEST_FINANCIAL_NEWS block is built at request time. stock-radar reads this file and
tests/characterization pins its bytes, so edit the JSON, not this module, to change text.
"""

import csv
import io
import json
from pathlib import Path

from zservice.integrations.news import fetch_all_news

_RULES = json.loads(Path(__file__).with_name("formula_rules.json").read_text(encoding="utf-8"))
_NEWS_PER_FEED = 5
_NEWS_SECTION = "LATEST_FINANCIAL_NEWS"


def build_formula_csv_bytes() -> bytes:
    """Build the formula/documentation CSV (incl. live news) and return it as bytes."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(_RULES["before_news"])
    writer.writerow(_RULES["news_header"])
    news = fetch_all_news(per_feed_limit=_NEWS_PER_FEED)
    if not news:
        writer.writerow(_RULES["news_empty_row"])
    for n in news:
        value = f"{n['pubDate']}, {n['title']}, {n['link']}"
        writer.writerow([_NEWS_SECTION, "", n["source"], value])
    writer.writerows(_RULES["after_news"])
    return output.getvalue().encode("utf-8-sig")
