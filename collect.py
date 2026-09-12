#!/usr/bin/env python3
"""Auto-News collector.

Fetches headlines from FREE sources (RSS, Guardian Open Platform, Hacker News,
Reddit), dedupes them, summarizes them with the free Gemini API tier, and
writes articles as Markdown into the news/ folder. generate_site.py then
builds the static website.

Free-tier friendly by design:
  - RSS / Hacker News / Reddit : unlimited, no key required
  - Guardian Open Platform     : 500 calls/day (free dev key) - optional
  - Gemini API                 : free tier, generous daily quota - recommended
"""

import argparse
import hashlib
import html as htmlmod
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import feedparser
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from config import (
    BASE_URL, CATEGORIES, EXCERPT_LIMIT, GEMINI_MODEL, GEMINI_MODEL_CANDIDATES,
    HN_COUNT, HN_ITEM_ENDPOINT, HN_TOP_ENDPOINT, MAX_PER_SOURCE, MAX_STORIES,
    PEXELS_ENDPOINT, REDDIT_COUNT, REDDIT_SUBS, RSS_SOURCES, SITE_NAME,
    SUMMARY_WORDS, USER_AGENT,
)

NEWS_DIR = os.path.join(BASE_DIR, "news")
DATA_DIR = os.path.join(BASE_DIR, "data")
SEEN_FILE = os.path.join(DATA_DIR, "seen.json")

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
# ---------------------------------------------------------------------------
# Persistence (dedup survives across runs, even in GitHub Actions)
# ---------------------------------------------------------------------------
def load_seen():
    if not os.path.exists(SEEN_FILE):
        return {"links": [], "titles": []}
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {"links": [], "titles": []}


def save_seen(seen):
    seen["links"] = seen["links"][-2000:]
    seen["titles"] = seen["titles"][-2000:]
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SEEN_FILE, "w", encoding="utf-8") as fh:
        json.dump(seen, fh)


def link_key(url):
    return hashlib.sha256(url.strip().encode("utf-8", "ignore")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------
def clean_excerpt(text, limit):
    text = htmlmod.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def norm_words(s):
    return re.findall(r"[a-z0-9]+", (s or "").lower())


def title_similar(a, b):
    sa, sb = set(norm_words(a)), set(norm_words(b))
    if not sa or not sb:
        return False
    overlap = len(sa & sb) / len(sa | sb)
    return overlap > 0.6 and min(len(sa), len(sb)) >= 3


def is_seen(seen, title, url):
    if link_key(url) in seen["links"]:
        return True
    for t in seen["titles"]:
        if title_similar(title, t):
            return True
    return False


def mark_seen(seen, title, url):
    seen["links"].append(link_key(url))
    seen["titles"].append(title)
GUARDIAN_KEY = os.environ.get("GUARDIAN_API_KEY", "")
PEXELS_KEY = os.environ.get("PEXELS_API_KEY", "")

if GEMINI_MODEL:
    GEMINI_MODEL_CANDIDATES.insert(0, GEMINI_MODEL)

MODELS = GEMINI_MODEL_CANDIDATES
# ---------------------------------------------------------------------------
# Source fetchers
# ---------------------------------------------------------------------------
def fetch_rss():
    items = []
    for name, url, cat, weight in RSS_SOURCES:
        try:
            parsed = feedparser.parse(url)
            for entry in (parsed.entries or [])[:8]:
                title = (getattr(entry, "title", "") or "").strip()
                link = (getattr(entry, "link", "") or "").strip()
                if not title or not link:
                    continue
                excerpt = clean_excerpt(getattr(entry, "summary", ""), EXCERPT_LIMIT)
                published = None
                for key in ("published_parsed", "updated_parsed"):
                    ts = getattr(entry, key, None)
                    if ts:
                        try:
                            published = datetime.fromtimestamp(time.mktime(ts), tz=timezone.utc)
                        except Exception:
                            published = None
                        break
                items.append({
                    "title": title, "link": link, "source": name,
                    "category": cat, "excerpt": excerpt,
                    "weight": weight, "published": published,
                })
        except Exception as err:
            print(f"  ! RSS {name}: {err}")
    return items


def fetch_guardian():
    if not GUARDIAN_KEY:
        return []
    items = []
    try:
        url = "https://content.guardianapis.com/search"
        params = {
            "api-key": GUARDIAN_KEY, "page-size": 20, "order-by": "newest",
            "section": "world|technology|science|business",
            "show-fields": "trailText,thumbnail",
        }
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        results = resp.json().get("response", {}).get("results") or []
        for r in results:
            fields = r.get("fields", {})
            items.append({
                "title": (r.get("webTitle") or "").strip(),
                "link": r.get("webUrl", ""),
                "source": "The Guardian",
                "category": r.get("sectionId", "world"),
                "excerpt": clean_excerpt(fields.get("trailText", ""), EXCERPT_LIMIT),
                "image": fields.get("thumbnail", ""),
                "weight": 3, "published": datetime.now(timezone.utc),
            })
    except Exception as err:
        print(f"  ! Guardian: {err}")
    return items


def fetch_hn():
    items = []
    try:
        ids = requests.get(HN_TOP_ENDPOINT, timeout=20).json()[:HN_COUNT]
        for sid in ids:
            try:
                data = requests.get(HN_ITEM_ENDPOINT.format(sid), timeout=10).json()
                if not data or data.get("type") != "story" or not data.get("title"):
                    continue
                link = data.get("url") or f"https://news.ycombinator.com/item?id={data.get('id')}"
                items.append({
                    "title": data["title"].strip(), "link": link,
                    "source": "Hacker News", "category": "technology",
                    "excerpt": "", "weight": 2,
                    "published": datetime.fromtimestamp(data.get("time", time.time()), tz=timezone.utc),
                })
            except Exception:
                continue
    except Exception as err:
        print(f"  ! Hacker News: {err}")
    return items


def fetch_reddit():
    items = []
    for sub in REDDIT_SUBS:
        try:
            resp = requests.get(
                f"https://www.reddit.com/r/{sub}/top.json",
                params={"t": "day", "limit": REDDIT_COUNT},
                headers={"User-Agent": USER_AGENT}, timeout=20,
            )
            resp.raise_for_status()
            children = resp.json().get("data", {}).get("children", [])
            for c in children:
                d = c.get("data", {})
                if not d.get("title"):
                    continue
                items.append({
                    "title": d["title"].strip(),
                    "link": "https://www.reddit.com" + (d.get("permalink") or ""),
                    "source": f"r/{sub}", "category": sub if sub in CATEGORIES else "other",
                    "excerpt": clean_excerpt(d.get("selftext", ""), 150),
                    "weight": 1, "published": datetime.fromtimestamp(d.get("created_utc", time.time()), tz=timezone.utc),
                })
        except Exception as err:
            print(f"  ! Reddit r/{sub}: {err}")
    return items
# ---------------------------------------------------------------------------
# Selection & ranking
# ---------------------------------------------------------------------------
def pick_top(items, seen, limit, max_per_source=MAX_PER_SOURCE):
    chosen, per_source = [], {}

    def sort_key(item):
        age = 0.0
        if item.get("published"):
            try:
                age = abs((datetime.now(timezone.utc) - item["published"]).total_seconds()) / 3600.0
            except Exception:
                age = 0.0
        freshness = 3.0 if age <= 24 else (2.0 if age <= 48 else (1.0 if age <= 96 else 0.0))
        return (item.get("weight", 1) + freshness, -age)

    for item in sorted(items, key=sort_key, reverse=True):
        if len(chosen) >= limit:
            break
        src = item["source"]
        if per_source.get(src, 0) >= max_per_source:
            continue
        if is_seen(seen, item["title"], item["link"]):
            continue
        if any(title_similar(item["title"], c["title"]) for c in chosen):
            continue
        chosen.append(item)
        per_source[src] = per_source.get(src, 0) + 1
    return chosen


# ---------------------------------------------------------------------------
# Gemini (free tier) — the writing brain
# ---------------------------------------------------------------------------
def gemini_generate(payload):
    """Try each model candidate until one answers. Returns text or ''."""
    for model in MODELS:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            resp = requests.post(url, params={"key": GEMINI_KEY}, json=payload, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
                return (parts[0].get("text", "") if parts else "")
            if resp.status_code in (400, 403, 404):
                print(f"  ! Gemini {model}: HTTP {resp.status_code} (trying next model)")
                continue
            print(f"  ! Gemini {model}: HTTP {resp.status_code}: {resp.text[:200]}")
            break
        except Exception as err:
            print(f"  ! Gemini {model}: {err}")
    return ""


def parse_model_list(text):
    text = (text or "").strip()
    text = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text).strip()
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("no JSON array found in model response")
    return json.loads(text[start:end + 1])


def summarize_chunk(stories):
    """Summarize a batch of stories in one Gemini call. Returns {index: result}."""
    payload_in = [
        {"index": i, "title": s["title"], "source": s["source"],
         "url": s["link"], "excerpt": s["excerpt"][:EXCERPT_LIMIT]}
        for i, s in enumerate(stories)
    ]
    cats = ", ".join(CATEGORIES)
    prompt = (
        "You are a neutral news editor. For each story below, write a short factual news brief.\n"
        "Rules:\n"
        "- Base everything ONLY on the provided excerpt. Never invent facts.\n"
        f"- Each summary must be {SUMMARY_WORDS} words or fewer ({SUMMARY_WORDS * 5} chars max).\n"
        "- Paraphrase. Never copy sentences verbatim. Do not use quotes from the article.\n"
        "- Mention the source inline once, e.g. \"...according to BBC.\"\n"
        f"- Pick ONE category from this exact list: {cats}\n"
        "- image_query: 2-4 generic keywords for a free stock-style image, or \"\" if not needed.\n"
        "- The title may be edited for a headline feel (max 90 chars), keep it truthful.\n"
        "Return ONLY valid JSON: an array of objects with keys "
        "\"index\", \"title\", \"summary\", \"category\", \"image_query\".\n\n"
        f"STORIES:\n{json.dumps(payload_in, ensure_ascii=False)}"
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 4096},
    }
    if not GEMINI_KEY:
        return {}
    text = gemini_generate(body)
    if not text:
        return {}
    try:
        outs = parse_model_list(text)
        result = {}
        for o in outs:
            if isinstance(o, dict) and o.get("index") is not None and o.get("summary"):
                result[int(o["index"])] = o
        if result:
            print(f"  + Gemini: summarized {len(result)}/{len(stories)} stories")
        return result
    except Exception as err:
        print(f"  ! Gemini output parse failed: {err}")
        return {}
# ---------------------------------------------------------------------------
# Fallbacks & images
# ---------------------------------------------------------------------------
def fallback_summary(story):
    """Used when Gemini is unavailable so the site still publishes cleanly."""
    text = clean_excerpt(story.get("excerpt", ""), SUMMARY_WORDS * 6)
    if not text:
        text = story.get("title", "")
    words = text.split()
    if len(words) > SUMMARY_WORDS:
        words = words[:SUMMARY_WORDS]
    return " ".join(words).rstrip(".,;: ") + "."


def fetch_pexels_image(query):
    if not PEXELS_KEY or not query:
        return ""
    try:
        resp = requests.get(
            PEXELS_ENDPOINT,
            params={"query": query, "per_page": 3, "orientation": "landscape"},
            headers={"Authorization": PEXELS_KEY}, timeout=15,
        )
        photos = resp.json().get("photos") or []
        if photos:
            return photos[0]["src"].get("large2x", "")
    except Exception as err:
        print(f"  ! Pexels: {err}")
    return ""


def make_slug(title, pub_date):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60] or "story"
    return f"{pub_date:%Y-%m-%d}-{s}"


def write_article(story, ai):
    pub = story.get("published") or datetime.now(timezone.utc)
    slug = make_slug(ai.get("title") or story["title"], pub)
    unique = slug
    n = 2
    while os.path.exists(os.path.join(NEWS_DIR, f"{unique}.md")):
        unique = f"{slug}-{n}"
        n += 1

    title = (ai.get("title") or story["title"]).strip()
    summary = (ai.get("summary") or fallback_summary(story)).strip()
    category = ai.get("category") or story.get("category", "other")
    if category not in CATEGORIES:
        category = "other"
    image = story.get("image") or ""
    if not image and ai.get("image_query"):
        image = fetch_pexels_image(ai["image_query"])

    front = "\n".join([
        "---",
        f"title: {json.dumps(title, ensure_ascii=False)}",
        f"date: {json.dumps(pub.strftime('%Y-%m-%dT%H:%M:%SZ'), ensure_ascii=False)}",
        f"source: {json.dumps(story['source'], ensure_ascii=False)}",
        f"source_url: {json.dumps(story['link'], ensure_ascii=False)}",
        f"category: {json.dumps(category, ensure_ascii=False)}",
        f"image: {json.dumps(image, ensure_ascii=False)}",
        "---",
    ])
    body = summary.rstrip()
    path = os.path.join(NEWS_DIR, f"{unique}.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(front + "\n\n" + body + "\n")
    print(f"  + Wrote {path}")
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Auto-News collector")
    parser.add_argument("--limit", type=int, default=MAX_STORIES,
                        help="max fresh articles to publish in this run")
    parser.add_argument("--no-ai", action="store_true",
                        help="skip Gemini; use raw source excerpts (offline test)")
    args = parser.parse_args()

    os.makedirs(NEWS_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    if args.no_ai:
        global GEMINI_KEY
        GEMINI_KEY = ""

    print(f"[1/4] Fetching headlines ({SITE_NAME}) ...")
    items = fetch_rss() + fetch_guardian() + fetch_hn() + fetch_reddit()
    print(f"      {len(items)} raw items collected")

    print("[2/4] Filtering & deduping ...")
    seen = load_seen()
    picks = pick_top(items, seen, args.limit)
    print(f"      {len(picks)} new stories selected")

    print("[3/4] Writing articles ...")
    batch_size = 5
    written = 0
    for start in range(0, len(picks), batch_size):
        batch = picks[start:start + batch_size]
        results = summarize_chunk([{"title": s["title"], "source": s["source"],
                                    "link": s["link"], "excerpt": s.get("excerpt", "")}
                                   for s in batch])
        for i, story in enumerate(batch):
            ai = results.get(i, {})
            write_article(story, ai)
            mark_seen(seen, story["title"], story["link"])
            written += 1

    save_seen(seen)
    print(f"[4/4] Done — {written} article(s) published into news/")
    print("Next step: python generate_site.py")


if __name__ == "__main__":
    main()