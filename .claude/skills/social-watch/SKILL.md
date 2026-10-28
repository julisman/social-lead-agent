---
name: social-watch
description: Monitor standing watchlists (watch/*.md) for new matching posts — urgent-sale (BU) property, vehicles, or any topic the user wants tracked — dedupe against everything already seen, and surface only what's new. Read-only, never replies. Runs on the scheduler. Use when asked to monitor a topic, watch for listings, check the watchlist, or add something to the watchlist.
---

# Watch

A standing monitor. `social-insight` answers a question once; this checks the same
queries every few hours forever and tells the user **only what's new**. The value is
entirely in the dedupe — a watch that re-reports the same listing every run trains
the user to ignore it.

**Read-only, absolutely.** No replies, no likes, no DMs. Contacting a seller is the
owner's decision, made from the report.

## The watchlist

Each watch is one file: `watch/<slug>.md`. It holds, in plain prose + lists:

- **What we're looking for** — one sentence.
- **Account** — which brand/platform's logged-in session to browse from.
- **Queries** — search phrases and any tag-feed URLs.
- **Counts as a hit** — the judgement rules: location filter, seller-not-hunter,
  category. Keyword match alone is never a hit.
- **Capture** — extra fields worth extracting (asking price, land size, area).

To add a watch, write a new file in that shape and (if it should run unattended)
add nothing else — the scheduler fires the skill, and the skill reads every file
in `watch/`. To retire one, move it to `watch/retired/`.

## Preflight

1. `PAUSED` in project root → stop.
2. For each watch file's account: `bin/guard.sh <brand> <platform>` — exit 1 means
   skip every watch using that account this run.

## Per watch, per run

1. Read the watch file. Read `runbook/PLATFORM_NOTES.md` if you haven't this session.
2. Run each query — Threads: Recent tab first (`&filter=recent`), then any tag
   feeds. Extract with `get_page_text` **plus** permalinks (`find` /
   `read_page filter:"interactive"`; pin stragglers with an author-scoped search
   `?q=<term>&from_author=<handle>`).
3. Judge each candidate against the watch file's hit rules. Ambiguous → not a hit,
   but if it's borderline-interesting, mention it in the report's footnote rather
   than silently dropping it.
4. **Dedupe before recording:** skip if the post_id is already in `data/watch.jsonl`:

```sh
grep -q '"post_id":"<POST_ID>"' data/watch.jsonl 2>/dev/null && skip
```

   Re-posts of the same listing under a new post_id happen (sellers bump); if the
   author+item obviously matches an earlier hit, record it but mark `"bump":true`
   so the report can say "seen before, still unsold" instead of "new".

5. Append each new hit (append-only, like every data file):

```sh
echo '{"watch":"<slug>","platform":"threads","author":"@handle",
       "author_url":"https://...","post_url":"https://...","post_id":"abc123",
       "text":"<their exact words>","price":"26jt nego","location":"Nusa Dua",
       "posted_at":"2026-08-17T...","found_at":"<now>"}' >> data/watch.jsonl
```

## Report

Maintain one rolling file per watch: `reports/watch/<slug>.md`. Newest run at the
top: date, then each new hit as item · price · location · author · link · their
exact words. A run with nothing new gets one line — `2026-08-17 09:00 — no new
listings (checked N queries)` — so silence is visibly "checked, quiet" rather than
"didn't run".

Then the scheduler marker, every run, hits or not:

```sh
echo '{"brand":"<brand>","platform":"<platform>","kind":"run","skill":"social-watch",
       "note":"<slug>: 2 new, 1 bump, 14 dupes"}' | bin/log-action.sh
```

**Tell the user only when there is something to say.** New hits: lead with them —
item, price, link. Nothing new: one line. If a query has produced nothing across
many runs, say so and propose changing it in the watch file — a watch that never
fires is either early or mis-aimed, and only the user knows which.

## Cadence

`config.json → schedule.every_minutes["social-watch"]` — picked up by `bin/due.sh`
like every other skill. Listings-type watches move slowly; every few hours is
plenty, and more frequent runs just spend the account's search activity for zero
new posts.
