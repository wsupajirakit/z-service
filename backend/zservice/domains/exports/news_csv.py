"""ztrade_news.csv builder (moved unchanged from main.py)."""

import csv
import io

from zservice.integrations.news import fetch_all_news


def build_news_csv_bytes() -> bytes:
    """Build the news CSV and return it as bytes."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Source", "Published Date", "Title", "Link"])

    all_news = fetch_all_news()

    if len(all_news) == 0:
        writer.writerow(["", "", "ไม่พบข่าวสาร (ยังไม่มีข่าว) หรือไม่สามารถดึงข้อมูลได้ในขณะนี้", ""])
    else:
        for n in all_news:
            writer.writerow([n["source"], n["pubDate"], n["title"], n["link"]])

    return output.getvalue().encode("utf-8-sig")
