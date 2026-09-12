# 📰 Auto News Daily — a 100% free, auto-publishing news website

A news site that **fetches headlines → rewrites them with AI → publishes automatically — every hour, forever, for $0.**

| Ingredient | Free option used | Free-tier limit |
|---|---|---|
| News data | 21 public RSS feeds + Guardian API + Hacker News + Reddit | RSS: unlimited |
| AI writing | Google Gemini API (free tier) | ~400M tokens/day |
| Scheduling | GitHub Actions cron | 500 min/month |
| Hosting | GitHub Pages | unlimited traffic |
| Images | Pexels / Wikimedia (optional) | 200 req/hour |
| Domain | optional (≈$10/yr) | — |

> ⚠️ **Legal note:** free tiers are non-commercial. Switching to monetization later = add paid Gemini key + drop Guardian API (RSS stays free) — see **Monetization**.

---

## 🚀 Deploy (2 minutes, requires GitHub account)

```bash
# 1) From this folder — create the repo & push
gh repo create auto-news --public --source . --remote origin --push

# 2) Add your free Gemini key as a GitHub Secret
gh secret set GEMINI_API_KEY
# (paste the key when prompted — never share it in chat/chats)

# 3) Optional extras (both free)
gh secret set GUARDIAN_API_KEY      # 500 free calls/day
gh secret set PEXELS_API_KEY        # free image search

# 4) In the repo on github.com:
#    Settings → Pages → Source: "GitHub Actions"
#    (then a green Pages URL appears after the first run)
```

**Trigger the first run:** Actions tab → *Auto News* → **Run workflow**.

Your site is live at: `https://<your-username>.github.io/auto-news/`

---

## 🧪 Test locally first

```bat
pip install -r requirements.txt
python collect.py --limit 5            REM no key needed (excerpt fallback)
python generate_site.py
REM open site\index.html in your browser
```

To test the real AI writing locally, set your key first:

```bat
set GEMINI_API_KEY=your-key
python collect.py --limit 5
```

---

## 🧠 How it works

```
GitHub Actions (every hour)
  ├─ collect.py
  │    ├─ fetch RSS (21 sources) + Guardian + HN + Reddit
  │    ├─ dedupe (data/seen.json persists across runs)
  │    ├─ Gemini (free) rewrites each story → news/YYYY-MM-DD-slug.md
  │    └─ optional Pexels image lookup
  ├─ generate_site.py
  │    ├─ site/index.html (homepage grid + category filters)
  │    ├─ site/articles/*.html (one page per brief)
  │    ├─ site/feed.xml (your own RSS — readers subscribe)
  │    └─ about / privacy / contact pages
  └─ commits & deploys to GitHub Pages
```

Every story is an **AI paraphrase + link back to the original outlet** (Google-News style,
never a copy-paste of full articles).

---

## 💰 Monetization switch (when traffic arrives)

1. **Add a domain** (~$10/yr) → AdSense requirement.
2. Kill AdSense's #1 ban risk: **switch Gemini to a paid usage key** (`aistudio.google.com` →
   billing; a few $/month) — the code already reads `GEMINI_API_KEY`, no changes needed.
3. **Remove `GUARDIAN_API_KEY`** from secrets (dev key is non-commercial only; RSS remains).
4. Add your AdSense code → `site/includes/ads.html` (auto-injected on every page).
5. Add analytics → `site/includes/analytics.html`.
6. Add donation button: set repo variable `KO_FI_URL=https://ko-fi.com/yourname`.
7. Add affiliate disclosure: set repo variable `SITE_DISCLOSURE` (text shown in the footer).

Everything is config-driven — no code changes required.

---

## 🔧 Customization

| What | How |
|---|---|
| Site name / tagline | Variables `SITE_NAME`, `SITE_TAGLINE` in repo **Settings → Variables** |
| Articles per run | Variable `MAX_STORIES` (default 12) |
| Add/remove news sources | Edit `RSS_SOURCES` in `config.py` |
| Publish cadence | Edit the `cron: '17 * * * *'` line in `.github/workflows/auto-news.yml` |
| Styling | `site/assets/style.css` |

---

## 🛟 Troubleshooting

| Problem | Fix |
|---|---|
| No articles published | Check Actions log → the run probably failed to reach a feed; RSS needs an internet connection |
| `401 / API key not valid` | Re-set the secret: `gh secret set GEMINI_API_KEY` |
| Site shows "First articles…" | The first Actions run hasn't finished, or Pages source isn't set to "GitHub Actions" |
| Want articles with zero Gemini use | Runs without the key automatically fall back to source excerpts |