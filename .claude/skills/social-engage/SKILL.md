---
name: social-engage
description: Reply publicly to collected leads on Threads/TikTok/Instagram in brand voice, with no links, under a strict daily budget and human pacing. Use when asked to engage, reply to leads, or run an engagement session.
---

# Engaging

Turn collected leads into conversations. This is the only skill that speaks in public,
so it is the one with real teeth on it.

## Preflight — all three, in order

```sh
bin/guard.sh <brand> <platform>     # exit 1 -> stop. Also prints today's remaining budget.
```

If `replies_remaining_today` is **0**, stop. Zero usually means `ramp_start` is still
`null` in `config.json` — that account has never been cleared for public replies, and
clearing it is the user's decision, not yours. Say so and stop; don't edit the file.

Then read `brands/<brand>/BRAND.md` and `brands/<brand>/REPLIES.md`.

## Pick who to answer

Read `data/leads.jsonl`, filter to this brand and platform with `status:"collected"`.
HIGH intent first, then MEDIUM if budget remains. Prefer the newest — a 6-hour-old post
converts far better than a 6-day-old one.

**`status:"collected"` is the whole filter — do not widen it.** Leads written as
`status:"research"` belong to a product the brand kit cannot answer yet, and replying to
one means pitching something you cannot describe. It also burns that author for 30 days
under the dedupe rule, so the cost lands on the product that *is* ready.

Check `product` before writing the reply. `motor`, `driver` and `jastip` are different
businesses sharing one account, and a reply that answers the wrong one reads worse than
no reply at all.

## The loop, per lead

```sh
bin/seen.sh <platform> <post_id> <author>   # exit 1 -> skip this lead entirely
bin/pace.sh <brand> <platform>              # waits out a random 40-120s gap
```

Then open the post, read it properly, write the reply, screenshot before submitting,
submit, and immediately record it.

**The screenshot before submitting is not a formality — it is the control that stops
this project publishing something it must never publish.** On Threads, clicking the
reply box sometimes opens a **"Utas baru" (new thread)** composer over the reply
composer; submitting blind there posts an original public thread from the brand account.
It has already happened once. Read the screenshot every time: right post, right account,
right text, no link. If a "Utas baru" modal is up, click "Batal" and use the "Balas"
composer underneath. Per-platform recovery steps are in `runbook/PLATFORM_NOTES.md`.

Also: **do not batch click → type → submit** into one `browser_batch`. Step through
writes one call at a time.

After the reply lands, immediately:

```sh
bin/seen-add.sh <platform> <post_id> <author> <brand>
echo '{"brand":"...","platform":"...","kind":"public_reply","author":"@...",
       "post_url":"...","template":"rec-casual-2","text":"<what you actually sent>"}' | bin/log-action.sh
```

Record before moving on, every time. If the run dies between the reply and the record,
that person becomes eligible to be replied to again — which is the worst failure this
system can produce.

## What a reply must be

1. **Specific to their post.** Name the thing they mentioned — Canggu, the dates, the
   budget, the fact that they're landing at DPS at midnight. A reply that could be
   pasted under any post is a reply that reads as a bot, and people say so in public.
2. **Short.** One or two sentences. Look at the length of other replies on the post.
3. **Bahasa, casual, lowercase-ish** — the way a small Bali business actually types.
   Not corporate, no marketing adjectives, no emoji walls.
4. **Genuinely useful on its own.** Answer their question even if they never contact
   you. This is the difference between helpful and spam, and it's also what stops
   people reporting the account.
5. **No link. No phone number. No WhatsApp number.** Close with a soft invite —
   *"boleh DM ya"* or *"info lengkap ada di bio"*. The WA link is in the bio; that is
   the entire reason this account survives.
6. **A different opening from the last reply.** Check the recent `template` values in
   `actions.jsonl`. Never the same template twice in a row, and vary the wording within
   the template — the bank is a starting shape, not a script to paste.

Never claim a price, a vehicle, an availability, or a policy that isn't in `BRAND.md`.
If you don't know, invite them to DM and let the WhatsApp agent answer.

## When the platform pushes back

Any of: an action-block modal, a captcha, a login challenge, a reply that submits but
doesn't appear, or the reply box refusing to open —

```sh
bin/cooldown.sh <brand> <platform> 24 "<exactly what you saw>"
```

Stop that account for the run. Do not retry, do not switch to a different post and try
again, do not "test whether it still works". Report it to the user.

## Finish

Report: replies sent vs budget, which leads you skipped and why, anything that felt
like the tone was off, and any sign of suppression worth a `social-health` check.
