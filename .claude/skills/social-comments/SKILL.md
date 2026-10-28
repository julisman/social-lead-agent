---
name: social-comments
description: Answer comments left on OUR OWN posts and videos across TikTok, Threads and Instagram — questions from people who came to us. Public, so never links. Use when asked to check comments, answer comments, or clear the comment backlog.
---

# Owned-surface comments

Answer people who commented on **our own content**. They came to us and asked in public.

This is not prospecting. Comments on *other people's* posts are `social-prospect` and
`social-engage`, and they live under a strict daily budget. This skill covers only
surfaces we own, and behaves differently on purpose.

## Why this is its own skill

A comment on our own video is a hybrid — inbound like a DM, public like a reply:

| | |
|---|---|
| **Uncapped** | They messaged us first. Answering inbound is not a spam signal, so no daily budget and no `pace.sh`. |
| **No dedupe** | Do **not** call `seen.sh`. Refusing to answer a customer because another brand replied to them 20 days ago would be absurd. |
| **No freshness rule** | The 7-day rule governs prospecting. A price question under our own video deserves an answer whether it is a week or six months old. |
| **NO LINKS** | This is the one rule inherited from `social-engage`, and it is absolute. The WhatsApp link lives in the bio. |

That last row is why this is separate from `social-dm`. DMs allow the WhatsApp link;
public comments never do. A single skill that sometimes permits links is a skill that
will eventually paste one into a public comment.

Log with `kind: "comment_reply"` — **not** `public_reply`. `budget.sh` counts
`public_reply`, so using the right kind is what keeps comments from eating the
cold-outreach budget.

## Preflight

```sh
bin/guard.sh <brand> <platform>     # exit 1 -> stop this account
```

A paused or blocked account stays quiet everywhere, comments included. Then read
`brands/<brand>/BRAND.md` — answers come from there and nowhere else.

## Where the comments are

**TikTok — verified 2026-08-09.** Business Suite aggregates them, which makes this the
easiest of the three:

```
https://www.tiktok.com/business-suite/comments
```

Lists our videos with a `N komentar baru` count and a red dot on ones needing attention.
Reach it via `Pesan` in the sidebar, then the `Komentar` tab.

**Threads — unverified.** `Aktivitas` in the left sidebar has a replies view; our own
posts also show replies inline. Confirm the layout before trusting it, and update
`runbook/PLATFORM_NOTES.md` with what you find.

**Instagram — unverified.** Comments surface in Activity (heart icon) and inline on each
post and Reel. There is no Business-Suite-style aggregator in the app. Again: verify,
then write it down.

Do not guess a URL on a platform you have not confirmed — on TikTok, direct URL
navigation fails outright and the UI path is the only one that works.

## Classify each comment

**A question** — price, availability, requirements, delivery, models. The main path.
Answer it.

**A compliment or tag** — *"bagus banget"*, someone tagging a friend. A short warm reply
is fine and cheap; it also makes the comment section look alive to future viewers. Never
pitch here.

**Spam, bots, or promo** — other rentals advertising under our video, follow-for-follow.
Leave it. Do not reply, do not argue.

**Sensitive — do not auto-reply.** Complaints, an existing rental gone wrong, damage,
money, accidents, anything legal.

> A public complaint is more urgent than a private one, not less — every future viewer
> of that video sees it and sees whether we answered.

Escalate it: append to `reports/escalations.md` with the platform, handle, the comment
text, a link to the post, and mark it **URGENT — public**. Then:

```sh
echo '{"brand":"...","platform":"...","kind":"comment_escalate","author":"@...","note":"public complaint about delivery on <video>"}' | bin/log-action.sh
```

## Answering

Same voice as everywhere else — casual Bahasa, lowercase-leaning, at most one emoji.
Match their language; English question gets an English answer.

1. **Answer the actual question** from `BRAND.md`. Give the number, the requirement, the
   model. The two most common by far are the pricelist and *"belum punya SIM, bisa?"* —
   both are already written out in `BRAND.md`, so answer them in full rather than
   deflecting.
2. **Then a soft invite** — *"boleh dm ya"* or *"info lengkap di bio"*.
3. **No link, no phone number.** Bio only.

Answering the question properly in public is the point. Every future viewer of that
video reads the answer too, so one good reply serves everyone who had the same question
and never asked.

## Record every reply

```sh
echo '{"brand":"...","platform":"...","kind":"comment_reply","author":"@...",
       "post_url":"https://...","topic":"pricelist","text":"<what you sent>"}' | bin/log-action.sh
```

## Finish

Record the run, **even if the inbox was empty** — `bin/due.sh` reads this to know when
the skill last ran, and a run that found nothing still counts:

```sh
echo '{"brand":"...","platform":"...","kind":"run","skill":"social-comments","note":"comments answered"}' | bin/log-action.sh
```

Report: comments answered per platform, anything escalated, and — most usefully — any
question asked more than once. Repeats belong in `BRAND.md` under common questions, so
the next one is answered instantly instead of researched.
