---
name: social-insight
description: Collect insight from social media on a topic the user gives in their own wording — what people are saying, how they phrase it, what they complain about, what they pay — across Threads, TikTok and Instagram, and write it into a sourced report. Read-only, never replies. Use when asked to collect insights, research a topic, check sentiment, size demand, or find out "what are people saying about X".
---

# Insight

The user gives you wording — a topic, a question, or exact phrases they've heard —
and you find out what real people are publicly saying about it. The output is a
report with verbatim quotes and links, not replies and not leads.

**Read-only, absolutely.** No replies, no likes, no follows, no DMs. You are
borrowing a brand's logged-in browser to *listen*. This skill runs only when the
user asks — it is never scheduled.

This is not prospecting. `social-prospect` collects *who to reply to*;
this collects *what the market sounds like*. That difference relaxes two of
prospecting's rules — see "What's different from prospecting" below.

## Preflight

1. If `PAUSED` exists in the project root, stop.
2. Pick which brand's browser profile to use: the one the user names, otherwise the
   brand closest to the topic (see `bin/config-check.sh`). Then:

```sh
bin/guard.sh <brand> <platform>     # exit 1 -> that account is parked; try another brand's profile
```

Reading is low-risk, but it is still a logged-in session on an account we protect —
a parked account stays parked even for reading.

## Frame the question first

From the user's wording, pin down before opening a tab:

- **The question** — one sentence you could answer yes/no/with-a-number.
  "What do people say about X" is fine; sharpen it if the user gave more.
- **Search phrases** — the user's wording, plus obvious Indonesian *and* English
  variants. Broad beats specific: Threads token-matching widens with every word.
- **Timeframe** — default: last 30 days where the platform lets you tell.
- **What decision this feeds**, if the user said — it decides what's worth quoting.

If the topic is near a brand, read that brand's `KEYWORDS.md` first: the
seeker-vs-seller table and the session log of dead queries save you an hour of
rediscovery.

## Where to look

Read `runbook/PLATFORM_NOTES.md` first — exact search URLs, the two-call extraction
recipe (`get_page_text` for text **plus** `find` for permalinks and timestamps),
and the UI traps.

**Threads — primary.** Both sorted tabs per query:

```
Recent:  https://www.threads.com/search?q=<encoded>&serp_type=default&filter=recent
Top:     https://www.threads.com/search?q=<encoded>&serp_type=default
```

**TikTok — useful here, unlike prospecting.** Prospecting skips TikTok because
comment intent sits on months-old videos and can't be replied to in time. Insight
doesn't need freshness the same way: the comment sections under the top videos for
a topic are dense, candid opinion — complaints, price talk, "is it worth it".
Search the topic, open the top handful of videos, read the comments. Just record
the video's age with every quote, and weight old ones accordingly.

**Instagram — last.** Keyword search barely works; hashtag pages and comments on
recent Reels from relevant accounts only. Don't force it.

## What's different from prospecting

- **Old posts count.** The 7-day rule exists because a late reply reads as a bot.
  You aren't replying, so a 6-month-old thread is evidence, not waste — but always
  note the date, and say in the report how old your evidence skews.
- **Sellers count too.** A competitor's ad is a rejection in prospecting; here it's
  data — pricing, positioning, offer structure, volume of competition. Tag every
  quote **seeker** or **seller** and report the mix; the ratio itself is a finding.

## What to capture

For everything you keep: **verbatim quote, permalink, date, platform, and a
seeker/seller tag.** A quote you can't link back to is an anecdote, not evidence.
Collect into a scratch file as you go, not from memory at the end.

Watch for, and tally where you can:

- **Recurring themes** — the complaint or desire that keeps reappearing.
- **Phrasing** — the actual words people use to ask. This is the highest-value
  byproduct: real phrasings (`info nya dong`, `rekomenin aku`) become prospecting
  queries. Propose additions to `KEYWORDS.md` in the report.
- **Numbers** — prices mentioned, fees quoted, "berapa ya?" questions with answers.
- **Objections and horror stories** — what makes people distrust the category.
- **Seeker-vs-seller mix per query** — which queries reach buyers at all.

**Live leads are a side-effect, not the goal.** If you hit a post that would be a
HIGH under `social-prospect`'s rules (fresh, first-person, real request), don't
waste it: check `bin/seen.sh`, write it via `bin/lead-add.sh` per that skill's
format, and list it in the report. Do **not** reply — that stays `social-engage`'s
job, under its budget.

## Report

Write `reports/insights/YYYY-MM-DD-<topic-slug>.md`:

1. **Question** — as framed above, and the answer in 2-3 sentences up top.
2. **Method** — platforms, queries run, roughly how many posts/comments read,
   date range of the evidence. Say what you *didn't* cover.
3. **Findings by theme** — each with 2-4 verbatim quotes, linked and dated.
   Counts where you have them ("7 of 21 buyer posts mentioned delivery"), and
   plain "I only saw this once" where you don't. Never round a vibe up into a
   statistic.
4. **Phrasing worth adding to `KEYWORDS.md`** — proposed, not auto-edited.
5. **Leads captured**, if any.

Then log the run marker (required even if you found nothing — `bin/due.sh` and the
audit trail read this):

```sh
echo '{"brand":"<brand>","platform":"<platform>","kind":"run","skill":"social-insight",
       "note":"topic: <slug> — 21 buyer posts, 34 seller, 3 themes"}' | bin/log-action.sh
```

Tell the user the answer first, then where the full report is. If the evidence was
thin — few posts, all old, all sellers — say so plainly; "the market isn't talking
about this" is itself a finding, and a truthful thin report beats a padded one.
