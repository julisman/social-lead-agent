# Safety

The accounts are real, they belong to real businesses, and they are not replaceable.
Everything here exists to keep them alive.

## The kill switch

```sh
touch PAUSED                    # stop everything, immediately
echo "why" > PAUSED             # stop everything, with a note
rm PAUSED                       # resume
```

`bin/guard.sh` checks this first, before cooldowns, before budgets, before anything.
Every skill calls `guard.sh` before opening a browser tab.

## Budgets

| | Cap |
|---|---|
| Public replies | 15-25/day/account (`daily_cap`, default 20) |
| DMs | Uncapped — answering inbound is not a spam signal |
| Prospecting | Uncapped — read-only |

The ramp, from `ramp_start` in `config.json`:

| | Replies/day |
|---|---|
| `ramp_start: null` | **0** — the account has never been cleared. This is how Phase 1 stays read-only. |
| Week 1 | 5 |
| Week 2 | 10 |
| Week 3+ | `daily_cap` |

Only a human edits `ramp_start`. The agent proposes; it does not clear itself to speak.

## Pacing

`bin/pace.sh` waits a fresh random 40-120s between public actions.

The randomness matters more than the average — a metronomic 60s cadence is a stronger
bot signal than acting quickly, because humans are erratic and bots are not. Never
batch replies back to back, even when the budget allows it.

Spread the daily budget across ~3 sessions rather than firing it all at 09:00.

## When a platform pushes back

Any of these means **stop that account for at least 24 hours**:

- An action block, a rate limit notice, or "Try again later"
- A captcha or login challenge appearing where it didn't before
- A reply that submits successfully but never appears
- The reply box refusing to open

```sh
bin/cooldown.sh <brand> <platform> 24 "<exactly what you saw>"
```

**Never retry through a block.** Retrying is how a 24-hour limit becomes a permanent
one. Don't switch to another post and try again, don't "test whether it still works",
don't reduce volume and continue. Stop.

Two blocks on the same account within a week means stop for the week and rethink volume.

## Suppression

Run `social-health` daily. The failure it catches is the one that hides: a shadowbanned
account behaves normally from the inside, so the only reliable test is viewing your own
replies **logged out**.

If replies aren't visible logged-out: park the account 3-7 days, then resume at week-1
volume with a reset `ramp_start` — not at the volume it was running before.

## Things the agent must never do

- Post original content of any kind
- Put a link, phone number, or WhatsApp number in a **public** reply
- Reply to the same post twice, or the same person twice inside 30 days, across any brand
- Click delete, block, report, or any control that opens a native dialog — a modal
  freezes browser automation and the session cannot recover on its own
- Auto-reply to a complaint, a refund request, or anything about an existing booking
- Edit `ramp_start`, `enabled`, or `daily_cap` in `config.json`
- Rewrite or prune `leads.jsonl`, `seen.jsonl`, or `actions.jsonl`
- Follow, like, or mass-view profiles as a growth tactic — not in scope, and it is a
  much stronger spam signal than replying

## Weekly human review

Fifteen minutes, once a week:

1. Read 10 random replies from `actions.jsonl`. Do they sound like a person? Would you
   be happy to have sent them?
2. Check `reports/escalations.md` — anything sitting unanswered?
3. Run the logged-out visibility check on each active account.
4. Confirm no account is running above its intended cap.

If the replies have started sounding samey, that's the signal to rewrite the template
bank — not to reduce volume.
