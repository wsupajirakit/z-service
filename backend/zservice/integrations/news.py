"""RSS headlines used by the news CSV and the gold analysis (moved unchanged from main.py).

The formula CSV used to carry its own copy of this list and fetcher; the only difference
was taking the first 5 entries per feed, which is now `per_feed_limit=5`.
"""

import concurrent.futures
import urllib.request

import feedparser

# Some feeds reject requests without a browser User-Agent.
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

NEWS_FEEDS = [
    {
        "name": "CNBC (World)",
        "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362",
    },
    {"name": "Investing.com", "url": "https://www.investing.com/rss/news_14.rss"},
    {
        "name": "MarketWatch Top",
        "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    },
    {
        "name": "NYT Business (US)",
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
    },
    {"name": "SCMP China News (China)", "url": "https://www.scmp.com/rss/4/feed"},
    {"name": "SCMP Business (China)", "url": "https://www.scmp.com/rss/92/feed"},
    {"name": "Japan Times (Japan)", "url": "https://www.japantimes.co.jp/feed/"},
    {
        "name": "ET Economy (India)",
        "url": "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms",
    },
    {
        "name": "The Hindu (India)",
        "url": "https://www.thehindu.com/news/national/feeder/default.rss",
    },
]


def fetch_all_news(per_feed_limit: int | None = None) -> list:
    """Fetch every RSS feed in parallel and return a flat list of news dicts.
    Shared by the news CSV export and the gold analysis endpoint."""

    def fetch_single_feed(feed_info):
        try:
            req = urllib.request.Request(  # noqa: S310 — URLs come from NEWS_FEEDS only
                feed_info["url"],
                headers={"User-Agent": _USER_AGENT},
            )
            with urllib.request.urlopen(req, timeout=3) as response:  # noqa: S310 — fixed https feeds
                content = response.read()
            d = feedparser.parse(content)
            return [
                {
                    "source": feed_info["name"],
                    "title": e.get("title", ""),
                    "link": e.get("link", ""),
                    "pubDate": e.get("published", ""),
                }
                for e in d.entries[:per_feed_limit]
            ]
        except Exception:
            return []

    all_news = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_single_feed, f) for f in NEWS_FEEDS]
        for future in concurrent.futures.as_completed(futures):
            all_news.extend(future.result())
    return all_news
