---
name: social-dm
description: Read unread DMs on Instagram/Threads/TikTok, answer them in brand voice, and hand the person off to WhatsApp with a prefilled context link. Escalates complaints and existing-booking issues to a human. Use when asked to check DMs, answer the inbox, or triage messages.
---

# DM triage

Answer the inbox and move people to WhatsApp.

**Check in this order: Threads → TikTok → Instagram.** Measured 2026-08-09: Threads held
four live inquiries and 20+ threads, TikTok two live inquiries behind a misleading unread
badge, Instagram six threads with zero live inquiries. Instagram is worth a look only for
its **Requests** folder, where cold inbound sits unseen for weeks.

**Do not triage by unread.** Every stalled inquiry found so far was marked *read* —
someone opened it, replied once, and abandoned it. Sort by recency and read the actual
last message. On TikTok the unread badge is mostly `Membagikan video` share-noise.

Answering inbound messages is **not** a spam signal — a person who messaged you expects
a reply. So DMs are not capped by the daily reply budget and don't need `pace.sh`.
`guard.sh` still applies, because a paused or blocked account must stay quiet.

## Preflight

```sh
bin/guard.sh <brand> <platform>     # exit 1 -> stop this account
```

Read `brands/<brand>/BRAND.md`. Open the inbox for that account and work through the
unread threads, oldest first. On Instagram, check **Requests** as well as Primary —
cold inbound from non-followers lands there and is routinely missed.

## Classify each thread

**Service inquiry** — they want to book, rent, price, or ask about availability.
This is the main path. Answer, then hand off.

**Spam, bots, or irrelevant** — promo blasts, crypto, "collab?" from drop-shippers.
Leave it. Don't reply, don't engage. Mark read if the platform makes that easy without
opening a dialog.

**Sensitive — do not auto-reply.** Escalate and move on:
- A complaint, or anything angry
- Anything about an **existing** booking — a change, a delay, a no-show, a damaged item
- Refunds, money disputes, chargebacks
- Accidents, injuries, police, insurance, anything legal
- Press or partnership approaches
- Anything you are not confident you understand

For these, append to `reports/escalations.md` with the platform, handle, timestamp, a
one-line summary, and a link to the thread. Then log it:

```sh
echo '{"brand":"...","platform":"...","kind":"dm_escalate","author":"@...","note":"complaint about yesterday delivery"}' | bin/log-action.sh
```

An angry customer answered by a bot becomes a public post about being answered by a
bot. Escalating is always the cheaper mistake.

## Answering a service inquiry

Reply in brand voice, in their language (Bahasa or English — match what they wrote).
Answer whatever you can from `BRAND.md`. Never invent a price, a vehicle, a date, or a
policy that isn't written there.

Then hand off — links are fine in DMs, unlike public replies.

**Send the readable form, not the prefilled one:**

```
0812-3456-7890 (wa.me/628123456789)
```

Take the real number from `brands.<brand>.wa_number` in `config.json` — never from
memory, and never hardcoded into a skill or a brand file.

`bin/wa-link.sh` produces a percent-encoded link carrying source and topic. That is
right for a bio or a public profile, but in a DM it wraps to four lines of `%20` noise
and reads like a bot. Tested 2026-08-09: the short form renders as one clean clickable
link, the encoded one does not. The customer will restate what they want in WhatsApp
anyway, so the attribution isn't worth looking like spam. Give the number in readable
digits too — people save it.

**Always pair the link with a qualifying question**, never send it alone:

> buat tanggal berapa kak, sama daerah mana? nanti dicek unit yang ready. enak lewat wa
> aja biar cepet — 0812-3456-7890 (wa.me/628123456789)

The question is what keeps the conversation alive if they don't click. A bare "WA ya ka"
with no number and no question is how threads die — it happened five times on this
account before the agent ever ran.

Don't try to close in the DM. The WhatsApp agent has the real availability and pricing.
Your job is answered-and-moved, not booked.

## Record every thread

```sh
echo '{"brand":"...","platform":"...","kind":"dm_reply","author":"@...",
       "topic":"sewa motor 3 hari Canggu","handoff":true,"text":"<what you sent>"}' | bin/log-action.sh
```

## Finish

Record the run, **even if the inbox was empty** — `bin/due.sh` reads this to know when
the skill last ran, and a run that found nothing still counts:

```sh
echo '{"brand":"...","platform":"...","kind":"run","skill":"social-dm","note":"threads handled"}' | bin/log-action.sh
```

Report: threads handled, how many handed off to WhatsApp, how many escalated (and what
they were), and anything that came up repeatedly — a question asked five times in a
week belongs in `BRAND.md` so it can be answered instantly next time.
