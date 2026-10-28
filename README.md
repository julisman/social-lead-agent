# Social Lead-Gen Agent

A [Claude Code](https://claude.com/claude-code) project that finds people publicly
asking for what your business sells, replies to them helpfully, answers your DMs and
comments, and routes everyone into WhatsApp.

It drives a **real, already-logged-in Chrome browser** — no API keys, no OAuth, no
platform app review. It acts as you, in your session, on Threads, TikTok and Instagram.

It is a **top-of-funnel router**. It creates no content and closes no sales.

```
Threads / TikTok / Instagram                     WhatsApp
   │                                                ▲
   ├─ prospect ──→ leads.jsonl                      │
   │                   │                            │
   │                   └─ engage ──→ public reply (no link — bio only)
   │                                                │
   ├─ DM inbox ────────→ triage ──→ wa.me link ─────┤
   │                        │                       │
   └─ comments on our own posts ────────────────────┘
                            │
                            └──→ escalations.md   (complaints, refunds, bookings → human)
```

## Why it's built this way

Most of this repo is guardrails, and that is deliberate. An agent replying to strangers
from a real business account can do lasting damage in three ways: it can get the account
suppressed, it can say something wrong in public, or it can quietly do nothing useful
while appearing to work. The design targets all three.

**The rules are shell scripts, not prompts.** A model can forget an instruction; it
can't forget an exit code. `bin/guard.sh` decides whether the agent may act at all, and
returns a number. Everything else follows from that.

**The agent cannot clear itself to speak.** `ramp_start` in `config.json` gates public
replies, and `.claude/settings.json` denies the agent write access to that file. A new
account starts read-only and stays read-only until a human sets a date.

**Reply templates are prose, not config.** They are shapes with worked examples, not
fields to fill. A reply assembled from JSON reads like a form letter, and a form letter
under someone's post is what gets an account reported by a person rather than flagged by
an algorithm.

## Quick start

Requirements: Claude Code, the Claude in Chrome extension, `jq`, and a Chrome profile
already logged in to the accounts you want to use.

```sh
git clone <your-fork> social-agent && cd social-agent

cp config.example.json config.json
$EDITOR config.json          # phone number, handles, Chrome profile, caps

bin/brand-init.sh my-brand   # scaffolds brands/my-brand/ from the template
$EDITOR brands/my-brand/BRAND.md    # what you sell, and your voice — write this yourself

bin/config-check.sh          # tells you what is still missing
claude                       # then: "prospect my-brand on threads"
```

Grant the Chrome extension site permissions for the platforms you'll use, and **put your
WhatsApp link in each account's bio** — public replies carry no link, so the bio is the
only path from a reply to a conversation.

Leave `ramp_start` as `null` until you have run prospecting read-only for a few days and
actually read the leads. That is the whole point of it.

## The skills

| Skill | Does | Speaks in public? |
|---|---|---|
| `social-prospect` | Finds intent, classifies it, writes `leads.jsonl` | No — read-only |
| `social-engage` | Replies to collected leads | **Yes** — capped and ramped |
| `social-dm` | Answers the inbox, hands off to WhatsApp | No — private |
| `social-comments` | Answers comments on **your own** posts | Yes — uncapped, no links |
| `social-health` | Checks whether the account is being suppressed | No |
| `social-insight` | One-off research: what people are saying about a topic, as a sourced report | No — read-only |
| `social-watch` | Monitors standing watchlists (`watch/*.md`), surfaces only what's new | No — read-only |

The split matters. Prospecting runs freely because it never speaks. Engaging is capped
because it speaks to strangers. DMs and own-post comments are uncapped because answering
someone who came to you is not a spam signal — but comments carry no link and DMs do,
which is why they are separate skills rather than one.

The last two are listeners, not funnel stages. `social-insight` answers a question once
("what are people saying about jual BU?") with verbatim quotes and links.
`social-watch` asks the same question every few hours forever and dedupes against
`data/watch.jsonl`, so it only ever reports a listing once — a watch that repeats
itself trains you to ignore it. Each watch is one file in `watch/` (template:
`watch/_example.md`) holding its queries and, more importantly, its judgement rules —
keyword match alone is never a hit.

## The guardrails

| Script | Enforces |
|---|---|
| `guard.sh` | Kill switch, per-account cooldown, enabled flag, remaining budget |
| `budget.sh` | Warm-up ramp and daily cap — returns **0** until a human sets `ramp_start` |
| `seen.sh` | No post twice, no person twice in 30 days, **across all brands** |
| `pace.sh` | Random gap between public actions (the randomness matters more than the average) |
| `cooldown.sh` | Parks an account after platform pushback |
| `log-action.sh` | Append-only audit log — the thing `budget.sh` counts |
| `config-check.sh` | Validates config and reports what's unfinished |

Stop everything at any time:

```sh
touch PAUSED     # every skill checks this before opening a tab
rm PAUSED
```

## Running it unattended

Add a `schedule` block to `config.json` (see `config.example.json`), then run **one**
loop on your shortest interval:

```
/loop 30m Run bin/due.sh. For each skill it lists, invoke that skill for that brand.
If social-prospect collects any HIGH-intent leads and budget remains, run social-engage
straight after. If bin/due.sh prints nothing, reply "nothing due" and stop — do not
open a browser. Finish with one line from bin/status.sh.
```

**One loop, not one per skill.** Separate loops mean separate sessions driving the same
Chrome tab group, and two skills mid-reply in the same browser is a real corruption
risk. `bin/due.sh` is the dispatcher: it reads the clock and the audit log, and prints
what is actually due.

**It measures elapsed time, not ticks.** Sleep the machine, restart the loop, miss ten
intervals — whatever is overdue fires once on the next tick. A tick-counter would drift
and never recover, and you would have no way to tell.

```sh
bin/due.sh          # what would run right now, and why
bin/status.sh       # budget, today's actions, waiting leads, open escalations
watch -n 30 bin/status.sh
```

### The dashboard

One local page that shows what the agent did and what is waiting on you:

```sh
bin/report-server.sh          # open http://127.0.0.1:8787 — Ctrl+C to stop
bin/report-server.sh 9000     # another port
```

| Page | What's there |
|---|---|
| `/` **Dashboard** | Everything below, on one screen |
| `/reports` | Every file in `reports/` (daily reports, insight reports, watch reports, escalations) as readable HTML |
| `/due` | The output of `bin/due.sh`: what the scheduler would run right now. Nothing is started |

**Reading the dashboard, top to bottom:**

- **Banners:** `PAUSED`, parked accounts with time left, and a warning when nothing has
  been logged for 2+ days. If the loop stopped, this is where you find out.
- **Tiles:**
  - *Open escalations:* conversations waiting on a human.
  - *Leads waiting:* leads `social-engage` would still reply to. This is lower than the
    `status.sh` count because it hides leads whose post or author is already in
    `seen.jsonl`.
  - *High-intent waiting*, *actions today*, and *watch hits this week*.
- **Replies per day:** public, DM, and comment replies stacked per day. Hover a bar for
  the numbers, or open "Show as table".
- **Accounts today:** each brand × platform with its state, replies sent, budget left
  (from `budget.sh`), DMs, comments, escalations, and when it last ran.
- **Open escalations:** newest first. Click one to read the whole entry.
- **Leads waiting for a reply:** filter by brand, platform, or intent, or search the
  text. *Open post* goes straight to what they said.
- **Latest watch hits** and **recent actions:** the newest 20 and 25 entries from
  `data/watch.jsonl` and `data/actions.jsonl`.

**Actions you can take from the page:**

| Button | What it does | Same as |
|---|---|---|
| **Pause everything** / **Resume** | Writes or removes `PAUSED`, with your reason | `echo "reason" > PAUSED` / `rm PAUSED` |
| **Park** (per account) | Parks that account for 6, 24, or 48h | `bin/cooldown.sh <brand> <platform> <h> "<why>"` |
| **Mark resolved** (per escalation) | Changes that entry's `Status: OPEN` to `RESOLVED <time> (dashboard)` and adds your note | editing `reports/escalations.md` by hand |
| **What's due now?** | Shows what the scheduler would run. Read-only | `bin/due.sh` |

Replying to leads and DMs is deliberately not a button. Those go through the skills,
which run the guard, budget, and dedupe checks that a web page can't. The dashboard never
writes to `data/*.jsonl` directly.

**Safety:** the server binds to `127.0.0.1` only, because the data contains customer
names and phone numbers. Actions need a token that changes every time the server starts,
and they reject requests that don't come from `127.0.0.1` or `localhost`. Other websites
open in your browser can't trigger them. If you get "Stale page" after a restart, reload.
Everything is re-read from disk on every page load, so refresh to see a run's progress.

**Pause without touching the loop:**

```sh
touch PAUSED        # due.sh returns nothing; every skill exits at its guard
rm PAUSED
```

That is safer than interrupting a running loop, which can land between "reply sent" and
"reply recorded" — and an unrecorded reply is the one failure that lets the same person
be replied to twice.

### If you add a skill

End every run by logging a marker, **even when the skill did nothing**:

```sh
echo '{"brand":"...","platform":"...","kind":"run","skill":"your-skill","note":"..."}' | bin/log-action.sh
```

`due.sh` reads these to work out when the skill last ran. Miss it and the dispatcher
sees "never run", fires the skill every single tick, and it looks idle the whole time.
An empty inbox is still a run.

`social-engage` deliberately has no schedule — it is triggered by prospecting finding
something. On a clock it would just burn budget checks against an empty lead list.
`social-insight` has none either: it answers a question when you ask one. `social-watch`
is the opposite — monitoring only makes sense on the clock, so give it an
`every_minutes` entry (a few hours is plenty; listings move slowly, and tighter
intervals just spend the account's search activity finding nothing).

## Layout

```
config.json            your settings — GITIGNORED
config.example.json    template, documented
CLAUDE.md              operating rules, always loaded
bin/                   the guardrails + due.sh (dispatcher) and status.sh (monitor)
brands/_example/       brand kit template
brands/<slug>/         your real kits — GITIGNORED
data/                  leads, dedupe keys, audit log — GITIGNORED
reports/               daily reports, escalations — GITIGNORED
watch/                 standing watchlists — GITIGNORED (template: watch/_example.md)
runbook/               SAFETY.md, PLATFORM_NOTES.md
.claude/skills/        the seven skills
```

`config.json`, `brands/`, `data/`, `reports/` and `watch/` are all gitignored. Between
them they hold every phone number, price, customer name, competitor note and thing you
are quietly shopping for. Check `git status` before your first push.

## Honest limitations

**This is browser automation against platforms that don't want it.** Read-only
prospecting is low risk. Public replying is not: a dormant or brand-new account that
suddenly starts replying to strangers is the exact pattern platforms suppress, and a
suppressed account looks completely normal from the inside. `social-health` exists
because of this — run it, and check your replies logged-out.

**Platform UIs change without warning.** `runbook/PLATFORM_NOTES.md` records what
actually worked, with dates. Expect some of it to be wrong by the time you read it, and
update it as you go. Several entries in there are corrections of earlier entries.

**Prospecting yield is lower than you'd hope, and the inbox is richer than you'd think.**
In testing, a full day of prospecting found 7 leads; the same day's inboxes and requests
folders held 35+ real inquiries, most never answered. Clear your inboxes before you go
hunting.

**It is tuned for Indonesian-language Bali service businesses.** The mechanics generalise;
the keyword logic, seeker-vs-seller heuristics and reply voice do not. Rewrite them.

## License

Apache 2.0 — see [LICENSE](LICENSE). No warranty.

You are responsible for what this does from your accounts, including anything it posts
publicly and any action a platform takes in response.
