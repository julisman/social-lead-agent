---
name: social-prospect
description: Find people publicly asking for what a Bali brand sells, on Threads/TikTok/Instagram, classify their intent, and write them to leads.jsonl with a link back to their post. Read-only — never replies. Use when asked to prospect, find leads, scan keywords, or run a prospecting session.
---

# Prospecting

Find humans with buying intent. Write them down. **Do not reply to anyone** — replying
is `social-engage`'s job, and keeping the two separate is what lets prospecting run
freely while replies stay under a budget.

## Preflight

```sh
bin/guard.sh <brand> <platform>       # exit 1 -> stop this account, no exceptions
```

Then read `brands/<brand>/KEYWORDS.md` and `brands/<brand>/BRAND.md`. You need the
service area and what the business actually offers to judge intent correctly.

## Where to search

Work in this order and stop when you've spent the session's time:

**Read `runbook/PLATFORM_NOTES.md` first.** It has the exact search URLs, the two-call
extraction recipe, and the UI traps. Skipping it means rediscovering all of it.

### Step 1 — read the home feed before touching the search bar

Open **`Untuk Anda`** on Threads and scroll it first, for 5-10 minutes.

The algorithm has been learning what this account cares about, so the feed already
carries motor-rental conversations — and it solves the two problems search cannot:

- **Freshness.** A feed is recent by construction. Search's best buyer posts were 8-23
  days old and died on the 7-day rule.
- **Phrasing.** You cannot guess how people ask. Real posts used `info nya dong untuk`,
  `Help me yg tau`, `Rekomenin aku`, `ada info sewa motor yang bisa`. A feed requires no
  guessing at all.

It also compounds: every buyer post you reply to teaches the feed to show more of them.
That is a reason to start here *every* run, not just once.

**The catch — the feed skews seller.** The same signal that surfaces buyers also
surfaces competitors, and Bali rental accounts post several times a day. Expect a lot of
repeat promotional posts from the same rental accounts. Apply the same seeker-vs-seller test as everywhere else
and do not let volume fool you into thinking the feed is working.

**Time-box it.** The feed is infinite and has no natural end. When it starts repeating
or turns mostly promotional, stop and move to search.

> **Tested 2026-08-09 on a small, low-activity account — yielded 0 leads.** The feed loaded only 5
> posts and refused to paginate no matter how long it was scrolled. Of those 5: one
> competitor rental ad, two adjacent but off-topic (a property-cost
> question, a business-partner post), two unrelated entirely.
>
> **The cause is fixable and worth fixing.** The account's followed topics under `Kabar`
> are **Bali Property**, *Postingan hantu* and *YouTube Creators* — nothing about motor
> rental or Bali travel. That is exactly why a villa-cost post outranked everything.
> Combined with a small following and almost no posting history, the algorithm has
> nothing to work with.
>
> Until the account follows relevant topics and accounts, **do the feed pass quickly
> (2 minutes, not 10) and move to search.** Re-test after the topics change — the
> reasoning behind this step is sound, the account just isn't feeding it yet.

Also check the tags on any lead you find — posts carry topic tags like
`sewa motor bali`, and a tag feed would be both fresh and topical. **Unverified:** work
out how to open one, then write it into `runbook/PLATFORM_NOTES.md`.

### Step 2 — then search

**Threads — primary.** Navigate straight to the sorted URL rather than clicking tabs:

```
Recent:  https://www.threads.com/search?q=<encoded>&serp_type=default&filter=recent
Top:     https://www.threads.com/search?q=<encoded>&serp_type=default
```

Do both tabs. Recent is ~60% competitor ads with a few fresh buyers; Top has better
buyer posts but most are too old to use. Extract with `get_page_text` (text) **plus**
`find` "post permalink timestamp links" (URLs + exact timestamps) — neither alone is
enough.

**Use few broad queries, not many specific ones.** Threads does loose token matching, so
extra words widen the net instead of narrowing it — `sewa motor canggu` returns rentals
in Malang and Bogor. Check the brand's `KEYWORDS.md` session log for which queries are
already known dead.

**TikTok — skip it.** Tested 2026-08-09, yield was zero and the reasons are structural:
caption search returns 100% sellers, and while the comment intent is real it sits on
videos months to a year old. TikTok web search has **no upload-date filter**, so fresh
comment intent is unreachable. Do not spend prospecting time here — see
`runbook/PLATFORM_NOTES.md`. TikTok's value on these accounts is the inbox
(`social-dm`) and comments on our own videos (`social-comments`).

**Instagram — last, and only if time remains.** Keyword search doesn't work. Use
hashtag pages and comments on recent Reels from Bali travel accounts. Expect a poor
yield. Do not spend a whole session here.

## What to capture

For each candidate, extract: author handle, author URL, post URL (the permalink — this
is the "link to the topic"), the full post text, and the posted-at time. The post URL
is mandatory; a lead you can't click back to is worthless.

## Classification

Keyword match is not intent. Judge each post into one of three tiers.

**HIGH** — first person, present tense, an actual request. They want this now.
- *"ada rekomendasi sewa motor di Canggu?"*
- *"cari jastip Bali dong, ada yang open?"*
- *"besok landing di DPS, butuh sewa motor yang bisa anter ke hotel"*

**MEDIUM** — real person, real interest, but planning or vague. Worth collecting;
reply only if the daily budget has room after the HIGHs.
- *"bulan depan ke Bali, enaknya sewa motor atau pakai grab ya?"*
- *"lagi nyusun itinerary Bali 5 hari, ada saran?"*

**REJECT** — do not write these to leads.jsonl at all.

- **Older than 7 days.** The conversation is over. A reply arriving late reads as a bot
  scraping backlog, which is exactly what it is.
- **The poster is selling, not buying.** This is the one that will quietly ruin the
  jastip list if you're careless: *"open jastip Bali"*, *"PO jastip"*, *"slot jastip
  tersisa 3"* are **competitors advertising**. *"cari jastip"*, *"ada yang open jastip?"*
  are **customers**. The word "jastip" appears in both. Read the direction of the
  sentence, not the keyword. The same trap exists more mildly for the other two brands
  ("sewa motor murah, DM!" is a rental company, not a tourist).
- **Business or creator account posting promo.**
- **Saturated** — more than ~20 comments already. Your reply is invisible; the effort
  is wasted and the spam risk is unchanged.
- **Wrong place** — not Bali, or a different island.
- **Not Indonesian or English.**

When a post is genuinely ambiguous, reject it. A smaller, cleaner list is worth much
more than a big one, because every bad lead becomes a reply to someone who didn't ask.

## Writing leads

```sh
echo '{"platform":"threads","brand":"motor-sewa-bali","author":"@handle",
       "author_url":"https://...","post_url":"https://...","post_id":"abc123",
       "text":"<their exact words>","posted_at":"2026-08-09T03:12:00+0800",
       "query":"sewa motor bali","intent":"high","language":"id","product":"motor"}' | bin/lead-add.sh
```

**Always set `product`** — `motor`, `driver`, or `jastip`. One account can sell several
things and they convert nothing like each other; without this the lead list is a single
undifferentiated pile and you cannot tell which market is actually there.

### Products in market-research mode

If `BRAND.md` cannot yet answer what the lead is asking — no fee, no turnaround, no
shipping — the product is not repliable yet. **Collect it with `"status":"research"`.**

```sh
echo '{... ,"product":"jastip","intent":"high","status":"research"}' | bin/lead-add.sh
```

`social-engage` filters on `status=="collected"`, so a research lead cannot be replied to
by accident. That is the point: the data shape enforces it, not your memory.

**Currently in research mode: `jastip`** (owner is sizing the market first, 2026-08-10).
Collect these exactly as carefully as repliable leads — the whole value is knowing
whether the demand is real, so a sloppy jastip list answers the wrong question.

Check `bin/seen.sh <platform> <post_id> <author>` as you go and mark already-seen
candidates `"status":"skipped"` rather than dropping them silently — knowing the list
overlaps the last run is useful signal about whether your keywords are exhausted.

## Finish

Log the run and report:

```sh
echo '{"brand":"...","platform":"...","kind":"run","skill":"social-prospect",
       "note":"12 high, 8 medium, 31 rejected"}' | bin/log-action.sh
```

**Log this even if you found nothing.** `bin/due.sh` uses it to work out when this
skill last ran; without it a scheduled loop re-fires the same skill every tick.

Report to the user: counts by tier, which queries produced the most, which produced
nothing (those should be retired), and anything that looked like a new phrasing worth
adding to `KEYWORDS.md`. The keyword set is supposed to evolve — that's the main
product of early prospecting runs.
