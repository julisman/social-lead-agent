---
name: social-health
description: Check whether the brand accounts are being suppressed or shadowbanned — verify replies are visible logged-out, watch reply-to-response ratios, and park unhealthy accounts. Use when asked to run a health check, check for shadowban, or investigate why leads dried up.
---

# Health check

The failure mode this exists to catch: **a suppressed account looks exactly like a
working one from the inside.** Your replies post successfully, they appear in your own
feed, the logs look clean — and nobody else can see any of it. Without this check, the
system can spend weeks talking to an empty room.

Run daily, per account.

## 1. Logged-out visibility — the decisive test

Take three replies from `actions.jsonl` posted **24-48 hours ago**. For each, open the
post URL in a **logged-out context** — a fresh tab in a browser profile with no session
for that platform, or an incognito window.

Can you see your reply in the thread?

- **All three visible** → healthy.
- **Some missing** → possible per-reply filtering. Note it, check again tomorrow before
  acting.
- **None visible** → the account is suppressed. Park it:

```sh
bin/cooldown.sh <brand> <platform> 72 "shadowban check: 0/3 replies visible logged-out"
```

Then tell the user plainly. Don't quietly keep going at a lower volume — a suppressed
account needs to go quiet completely and rebuild, and that's a decision for a human.

## 2. Response ratio

From `actions.jsonl`, count public replies over the last 7 days per account, and count
how many produced any response at all — a like, a reply back, a profile visit, a DM.

A healthy conversational account gets *something* back on a meaningful share of replies.
An account that sent 100 replies in a week and received zero interactions of any kind is
almost certainly being filtered, even if test 1 looked fine.

Compare against the previous week. A sharp drop with no change in what you were doing
is the signal — the absolute number matters less than the shape of the trend.

## 3. Friction signals

Scan the last 7 days of `actions.jsonl` for `kind:"blocked"` entries and note anything
observed during runs:

- Action blocks or "Try again later" — even one is worth recording; a second within a
  week means back off hard
- Captchas or login challenges appearing where they didn't before
- Reply boxes that take longer to open, or replies that need resubmitting
- Follower count flat or falling while activity is up

## 4. Report

Write the result into today's `reports/YYYY-MM-DD.md` and log it:

```sh
echo '{"brand":"...","platform":"...","kind":"health_check","note":"3/3 visible logged-out, 12% response rate, no blocks"}' | bin/log-action.sh
echo '{"brand":"...","platform":"...","kind":"run","skill":"social-health","note":"daily check"}' | bin/log-action.sh
```

The second line is the scheduler marker — log it every run, healthy or not.

State a verdict per account in plain words — healthy, watch, or parked — and say what
you're basing it on. If anything is parked, lead the report with that.

## If an account is unhealthy

Recommend, in this order: stop all public replies for that account (DMs can continue —
answering inbound is never the cause), let it sit 3-7 days, then resume at week-1 ramp
volume rather than where it left off. Reset `ramp_start` in `config.json` to the
resume date — but that edit is the user's call, so propose it, don't do it.
