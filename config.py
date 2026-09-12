"""Central configuration for the Auto-News site.

Every value here can also be set with an environment variable, which lets the
GitHub Actions workflow inject free-tier keys as Secrets at build time
without you ever editing this file in public.
"""

import os

# ---- Site identity -------------------------------------------------------
SITE_NAME = os.environ.get("SITE_NAME", "Auto News Daily")
TAGLINE = os.environ.get("SITE_TAGLINE", "Fresh headlines, summarized by AI")
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME", "YOUR_GITHUB_USERNAME")
REPO_NAME = os.environ.get("REPO_NAME", "auto-news")
BASE_URL = os.environ.get(
    "SITE_URL",
    f"https://{GITHUB_USERNAME}.github.io/{REPO_NAME}/",
).rstrip("/") + "/"

# ---- Monetization-ready hooks (optional) ---------------------------------
KO_FI_URL = os.environ.get("KO_FI_URL", "")           # donation button (free)
SITE_DISCLOSURE = os.environ.get("SITE_DISCLOSURE", "")  # affiliate disclosure

# ---- Collection ------------------------------------------------------------
MAX_STORIES = int(os.environ.get("MAX_STORIES") or "12")   # fresh articles per run
EXCERPT_LIMIT = int(os.environ.get("EXCERPT_LIMIT") or "300")  # chars sent to AI
SUMMARY_WORDS = int(os.environ.get("SUMMARY_WORDS") or "80")   # target summary length
MAX_PER_SOURCE = 3                                        # max picks per source

# ---- Writing brain (free Gemini API tier) ---------------------------------
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "")
GEMINI_MODEL_CANDIDATES = [
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-2.0-flash",
]

# ---- Free news sources ------------------------------------------------------
# name                 feed URL                                                        category      weight
RSS_SOURCES = (
    ("BBC World",          "https://feeds.bbci.co.uk/news/world/rss.xml",                   "world",      3),
    ("BBC Technology",     "https://feeds.bbci.co.uk/news/technology/rss.xml",              "technology", 2),
    ("BBC Business",       "https://feeds.bbci.co.uk/news/business/rss.xml",                "business",   2),
    ("BBC Science",        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "science",    2),
    ("BBC Sport",          "https://feeds.bbci.co.uk/sport/rss.xml",                        "sports",     2),
    ("Al Jazeera",         "https://www.aljazeera.com/xml/rss/all.xml",                     "world",      3),
    ("The Guardian (World)",  "https://www.theguardian.com/world/rss",                      "world",      3),
    ("The Guardian (Tech)",   "https://www.theguardian.com/technology/rss",                 "technology", 2),
    ("The Guardian (Science)","https://www.theguardian.com/science/rss",                    "science",    2),
    ("DW",                 "https://rss.dw.com/rdf/rss-en-all",                             "world",      2),
    ("NPR",                "https://feeds.npr.org/1001/rss.xml",                            "world",      2),
    ("NPR Technology",     "https://feeds.npr.org/1019/rss.xml",                            "technology", 1),
    ("The Verge",          "https://www.theverge.com/rss/index.xml",                        "technology", 2),
    ("TechCrunch",         "https://techcrunch.com/feed/",                                  "technology", 2),
    ("Ars Technica",       "https://feeds.arstechnica.com/arstechnica/index",               "technology", 2),
    ("MIT Tech Review",    "https://www.technologyreview.com/feed/",                        "technology", 1),
    ("ScienceDaily",       "https://www.sciencedaily.com/rss/all.xml",                      "science",    1),
    ("Space.com",          "https://www.space.com/feeds/all",                               "science",    1),
    ("Yahoo Finance",      "https://finance.yahoo.com/news/rssindex",                       "business",   1),
    ("CNN",                "http://rss.cnn.com/rss/edition.rss",                            "world",      2),
    ("ABC News",           "https://abcnews.go.com/abcnews/topstories",                     "world",      2),
)

# Hacker News (free Firebase API, no key)
HN_TOP_ENDPOINT = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_ENDPOINT = "https://hacker-news.firebaseio.com/v0/item/{}.json"
HN_COUNT = 20

# Reddit public JSON (no key, but needs a User-Agent header)
REDDIT_SUBS = ("news", "worldnews", "technology")
REDDIT_COUNT = 15

# ---- Optional image provider (Pexels free: 200 req/hour) --------------------
PEXELS_ENDPOINT = "https://api.pexels.com/v1/search"

# ---- Behaviour ----------------------------------------------------------------
USER_AGENT = "AutoNewsBot/1.0 (educational/news-aggregation project)"

CATEGORIES = (
    "world", "technology", "business", "science", "sports",
    "health", "culture", "ai", "politics", "other",
)