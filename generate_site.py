#!/usr/bin/env python3
"""Builds the static website + RSS feed from the news/ folder.

Run this after collect.py (locally or in GitHub Actions). It regenerates:
  site/index.html            - homepage grid
  site/articles/<slug>.html  - one page per article
  site/feed.xml              - RSS feed your readers can subscribe to
  site/sitemap.xml           - for search engines
  site/about.html, privacy.html, contact.html
"""

import html
import json
import os
import re
import sys
from datetime import datetime, timezone

from config import (
    BASE_URL, KO_FI_URL, SITE_DISCLOSURE, SITE_NAME, TAGLINE,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

NEWS_DIR = os.path.join(BASE_DIR, "news")
SITE_DIR = os.path.join(BASE_DIR, "site")
ART_DIR = os.path.join(SITE_DIR, "articles")
INCLUDES_DIR = os.path.join(SITE_DIR, "includes")
ASSETS_DIR = os.path.join(SITE_DIR, "assets")


def esc(text):
    return html.escape(str(text), quote=True)


def eprint(*a):
    print(*a)


# ---------------------------------------------------------------------------
# Markdown article parsing
# ---------------------------------------------------------------------------
def parse_frontmatter(raw):
    """Parse the --- frontmatter block of an article."""
    meta, body = {}, ""
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            front, body = parts[1], parts[2]
            for line in front.strip().splitlines():
                if ":" not in line:
                    continue
                key, _, value = line.partition(":")
                value = value.strip()
                try:
                    value = json.loads(value)
                except Exception:
                    value = value.strip('"').strip("'")
                meta[key.strip()] = value
    return meta, body.strip()


def read_articles():
    articles = []
    if not os.path.isdir(NEWS_DIR):
        return articles
    for fname in sorted(os.listdir(NEWS_DIR)):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(NEWS_DIR, fname)
        with open(path, "r", encoding="utf-8") as fh:
            meta, body = parse_frontmatter(fh.read())
        if not meta.get("title"):
            continue
        slug = fname[:-3]
        articles.append({
            "slug": slug,
            "title": meta.get("title", ""),
            "date": meta.get("date", ""),
            "source": meta.get("source", ""),
            "source_url": meta.get("source_url", ""),
            "category": meta.get("category", "other"),
            "image": meta.get("image", ""),
            "summary": body,
            "url": f"{BASE_URL}articles/{slug}.html",
        })
    articles.sort(key=lambda a: a.get("date", ""), reverse=True)
    return articles
# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
def read_include(name):
    path = os.path.join(INCLUDES_DIR, name)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            content = fh.read().strip()
        if content and not content.startswith("<!--"):
            return content
    return ""


def header_html(active=""):
    ko = f'<a class="btn-donate" href="{esc(KO_FI_URL)}" target="_blank" rel="noopener">&#9749; Support us</a>' if KO_FI_URL else ""
    nav_links = []
    for label, href in (("Home", "index.html"), ("World", "?cat=world"),
                        ("Tech", "?cat=technology"), ("Science", "?cat=science"),
                        ("Business", "?cat=business"), ("About", "about.html")):
        cls = ' class="on"' if label == active else ""
        nav_links.append(f'<a href="{href}"{cls}>{label}</a>')
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(SITE_NAME)}</title>
<meta name="description" content="{esc(TAGLINE)}">
<link rel="stylesheet" href="assets/style.css">
<link rel="alternate" type="application/rss+xml" title="{esc(SITE_NAME)}" href="{esc(BASE_URL)}feed.xml">
{read_include("analytics.html")}
</head>
<body>
<header class="topbar">
  <div class="wrap">
    <a class="brand" href="index.html"><span class="logo">&#128240;</span>
      <span>{esc(SITE_NAME)}<small>{esc(TAGLINE)}</small></span></a>
    <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
      <nav class="main">{''.join(nav_links)}</nav>
      {ko}
    </div>
  </div>
</header>
"""


def footer_html():
    disclosure = f'<p class="disclosure">{esc(SITE_DISCLOSURE)}</p>' if SITE_DISCLOSURE else ""
    return f"""
<footer class="footer">
  <div class="wrap">
    <div class="row">
      <span>Headlines & summaries auto-collected from public RSS feeds & free APIs. Original reporting belongs to the linked sources.</span>
      <span><a href="feed.xml">RSS Feed</a> &middot; <a href="about.html">About</a> &middot; <a href="contact.html">Contact</a> &middot; <a href="privacy.html">Privacy</a></span>
    </div>
    {disclosure}
    <div class="row"><span>&copy; {datetime.now(timezone.utc).year} {esc(SITE_NAME)}</span>
    <span>Built with &#10084; on a 100% free stack</span></div>
  </div>
</footer>
{read_include("ads.html")}
</body>
</html>"""


def html_page(content, title, active=""):
    return header_html(active) + f"""<div class="wrap" style="padding-top:24px;padding-bottom:24px">
{content}
</div>""" + footer_html()
# ---------------------------------------------------------------------------
# Homepage
# ---------------------------------------------------------------------------
CATEGORY_EMOJI = {
    "world": "&#127757;", "technology": "&#128241;", "business": "&#128200;",
    "science": "&#128300;", "sports": "&#9917;", "health": "&#129657;",
    "culture": "&#127917;", "ai": "&#129302;", "politics": "&#127988;",
    "other": "&#128220;",
}


def card_html(a):
    thumb_style = f'background-image:url("{esc(a["image"])}")' if a.get("image") else ""
    thumb = f'<div class="thumb" style="{thumb_style}"></div>' if a.get("image") else ""
    cat = a.get("category", "other")
    emoji = CATEGORY_EMOJI.get(cat, "&#128220;")
    when = a.get("date", "")[:16].replace("T", " ")
    return f"""<article class="card">
  {thumb}
  <div class="body">
    <div class="meta"><span class="pill">{emoji} {esc(cat)}</span>
      <span>{esc(a['source'])}</span><span class="dot">&middot;</span><span>{esc(when)}</span></div>
    <h2 class="title"><a href="articles/{esc(a['slug'])}.html">{esc(a['title'])}</a></h2>
    <p class="snippet">{esc(a['summary'][:200])}{'…' if len(a['summary']) > 200 else ''}</p>
    <a class="more" href="articles/{esc(a['slug'])}.html">Read brief &rarr;</a>
  </div>
</article>"""


def save(fname, content):
    path = os.path.join(SITE_DIR, fname)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def build_index(articles):
    if articles:
        cards = "\n".join(card_html(a) for a in articles[:48])
        hero_updated = (f'<div class="updated">Last updated: '
                        f'{datetime.now(timezone.utc).strftime("%B %d, %Y %H:%M UTC")} '
                        f'&middot; {len(articles)} briefs published</div>')
    else:
        cards = ('<div class="empty"><h2>First articles are being collected&#8230;</h2>'
                 '<p>The hourly automation will publish fresh briefs here shortly.</p></div>')
        hero_updated = ""

    cats = ("All", "world", "technology", "business", "science", "sports", "ai")
    chips = "".join(
        f'<button class="{"on" if c == "All" else ""}" data-cat="{c}">{c.title()}</button>'
        for c in cats
    )
    content = f"""
<div class="hero">
  <h1>{esc(SITE_NAME)}</h1>
  <p>{esc(TAGLINE)} — auto-collected from 20+ free sources, rewritten every hour. Read the full story at the original outlet.</p>
  {hero_updated}
</div>
<div class="wrap">
  <div class="filters" id="filters">{chips}</div>
  <div class="grid" id="grid">{cards}</div>
</div>
{filter_js()}
"""
    save("index.html", html_page(content, SITE_NAME, "Home"))
    eprint("  + index.html")


def filter_js():
    return """<script>
const grid=document.getElementById('grid'),filters=document.getElementById('filters');
if(filters){filters.addEventListener('click',e=>{
  const b=e.target.closest('button'); if(!b) return;
  [...filters.children].forEach(x=>x.classList.toggle('on',x===b));
  const cat=b.dataset.cat;
  [...grid.children].forEach(c=>{
    const pill=c.querySelector('.pill');
    c.style.display=(cat==='All'||(pill&&pill.textContent.toLowerCase().includes(cat)))?'':'none';
  });
});}
</script>"""


def build_articles(articles):
    os.makedirs(ART_DIR, exist_ok=True)
    for a in articles:
        when = a.get("date", "").replace("T", " ")[:16]
        img = (f'<figure><img src="{esc(a["image"])}" alt="{esc(a["title"])}" loading="lazy"></figure>'
               if a.get("image") else "")
        paragraphs = [p for p in re.sub(r"\n{3,}", "\n\n", a["summary"]).strip().split("\n\n") if p]
        body_html = "\n".join(f"<p>{esc(p)}</p>" for p in paragraphs)
        content = f"""
<main class="page article">
  <p><a class="back" href="index.html">&larr; All news</a></p>
  <h1>{esc(a['title'])}</h1>
  <div class="byline"><span class="pill">{esc(a['category'])}</span>
    <span>{esc(a['source'])}</span><span>&middot;</span><span>{esc(when)}</span></div>
  {img}
  <div class="lead">{body_html}</div>
  <p><a class="readmore" href="{esc(a['source_url'])}" target="_blank" rel="noopener">Read the full story on {esc(a['source'])} &rarr;</a></p>
  <p class="note">This brief is an AI-summarized version of reporting by
  <a href="{esc(a['source_url'])}" rel="noopener">{esc(a['source'])}</a>.
  For accuracy, timeliness and the original context, always read the source article. Headline &amp; summary auto-generated.</p>
</main>
"""
        save(f"articles/{a['slug']}.html", html_page(content, a["title"]))
    eprint(f"  + {len(articles)} article page(s)")


def build_feed(articles):
    items = []
    for a in articles[:50]:
        desc = esc(a["summary"]) + f'<p>Source: <a href="{esc(a["source_url"])}">{esc(a["source"])}</a></p>'
        items.append(f"""<item>
<title>{esc(a['title'])}</title>
<link>{esc(a['url'])}</link>
<guid>{esc(a['url'])}</guid>
<pubDate>{esc(a['date'].replace('T', ' ').replace('Z', ' +0000'))}</pubDate>
<description>{desc}</description>
</item>""")
    save("feed.xml", f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>{esc(SITE_NAME)}</title>
<link>{esc(BASE_URL)}</link>
<description>{esc(TAGLINE)}</description>
{''.join(items)}
</channel></rss>
""")
    eprint("  + feed.xml")
def build_sitemap(articles):
    urls = "".join(f"<url><loc>{esc(a['url'])}</loc></url>" for a in articles)
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>{esc(BASE_URL)}</loc></url>
{urls}
</urlset>
"""
    save("sitemap.xml", xml)
    eprint("  + sitemap.xml")


def build_content_pages(articles):
    n = len(articles)
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    about = f"""<main class="page content">
<h1>About {esc(SITE_NAME)}</h1>
<p>{esc(SITE_NAME)} is an experiment in fully-automated news aggregation. Every hour, a free GitHub Actions
worker fetches headlines from public RSS feeds and free news APIs (BBC, The Guardian, Al Jazeera, DW, NPR,
The Verge, TechCrunch, Hacker News, Reddit and more), filters and dedupes them, then asks a free-tier Gemini
model to rewrite each one as a short neutral brief.</p>
<p>We never republish articles. Every brief is a paraphrase that links back to the original reporting —
the same aggregation model used by Google News. Original work belongs to the linked sources.</p>
<h2>The stack (100% free)</h2>
<ul>
<li>Data: public RSS feeds + Guardian Open Platform + Hacker News + Reddit JSON</li>
<li>Writing: Google Gemini free-tier API</li>
<li>Scheduling: GitHub Actions (hourly cron)</li>
<li>Hosting: GitHub Pages</li>
<li>Images: Wikimedia Commons / Pexels free API</li>
</ul>
<p>{n} briefs published so far.</p>
</main>"""

    privacy = f"""<main class="page content">
<h1>Privacy Policy</h1>
<p><strong>Last updated:</strong> {today}</p>
<h2>What we collect</h2>
<p>{esc(SITE_NAME)} is a static site. We do not collect, store or sell personal data. We do not require accounts.
If analytics are enabled later, only aggregate, privacy-respecting metrics may be gathered.</p>
<h2>Article data</h2>
<p>Article briefs in this repository are derived from publicly available RSS feeds. We link to the original
publisher for the full story and respect their copyright &mdash; we do not reproduce full articles.</p>
<h2>Cookies</h2>
<p>None set by this site. Third-party services we link to have their own policies.</p>
</main>"""

    contact = f"""<main class="page content">
<h1>Contact</h1>
<p>Questions, feedback, or a takedown request? Open an issue on the project's GitHub repository.</p>
<p>If you are a rights holder and believe this site links content that should not be aggregated,
please open a GitHub issue with the source URL and it will be removed promptly.</p>
</main>"""

    save("about.html", html_page(about, f"About — {SITE_NAME}", "About"))
    save("privacy.html", html_page(privacy, f"Privacy Policy — {SITE_NAME}"))
    save("contact.html", html_page(contact, f"Contact — {SITE_NAME}"))
    eprint("  + about.html, privacy.html, contact.html")


def main():
    os.makedirs(SITE_DIR, exist_ok=True)
    os.makedirs(ART_DIR, exist_ok=True)
    articles = read_articles()
    eprint(f"Building {SITE_NAME} with {len(articles)} article(s) ...")
    build_index(articles)
    build_articles(articles)
    build_feed(articles)
    build_sitemap(articles)
    build_content_pages(articles)
    eprint("Done. Open site/index.html to preview.")


if __name__ == "__main__":
    main()