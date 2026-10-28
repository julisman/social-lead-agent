#!/bin/sh
# status.sh [brand]
#
# What the agent has done today, and what it may still do. Written for watching
# an unattended or looped run — `watch -n 30 bin/status.sh` gives a live view
# without touching a browser.
#
# Read-only. Safe to run at any time, including mid-run.

. "$(dirname "$0")/common.sh"

ONLY="$1"
ACTIONS="$DATA/actions.jsonl"
TODAY=$(today)

echo "$(now_iso)   [$TZ]"
echo

if [ -f "$ROOT/PAUSED" ]; then
  echo "*** PAUSED — all activity halted ***"
  echo "    $(cat "$ROOT/PAUSED" 2>/dev/null)"
  echo "    resume:  rm PAUSED"
  echo
fi

# Any parked accounts?
if [ -d "$DATA/cooldown" ] && [ -n "$(ls -A "$DATA/cooldown" 2>/dev/null)" ]; then
  echo "COOLDOWNS"
  for f in "$DATA/cooldown"/*; do
    [ -f "$f" ] || continue
    UNTIL=$(head -1 "$f"); MINS=$(( (UNTIL - $(now_epoch)) / 60 ))
    [ "$MINS" -gt 0 ] && echo "  $(basename "$f") — ${MINS}m left — $(sed -n 2p "$f")"
  done
  echo
fi

for b in $(jq -r '.brands | keys[]' "$CONFIG"); do
  [ -n "$ONLY" ] && [ "$ONLY" != "$b" ] && continue

  ENABLED_ANY=$(jq -r --arg b "$b" '[.brands[$b].accounts[] | select(.enabled == true)] | length' "$CONFIG")
  [ "$ENABLED_ANY" = "0" ] && continue

  echo "$b"
  for p in threads tiktok instagram; do
    [ "$(acct "$b" "$p" enabled)" = "true" ] || continue
    LEFT=$("$ROOT/bin/budget.sh" "$b" "$p")
    COUNTS=$(jq -rs --arg b "$b" --arg p "$p" --arg d "$TODAY" '
      [ .[] | select(.brand==$b and .platform==$p and (.ts|startswith($d))) ] as $t
      | { pub: ([$t[]|select(.kind=="public_reply")]|length),
          dm:  ([$t[]|select(.kind=="dm_reply")]|length),
          com: ([$t[]|select(.kind=="comment_reply")]|length),
          esc: ([$t[]|select(.kind|endswith("_escalate"))]|length) }
      | "\(.pub) \(.dm) \(.com) \(.esc)"' "$ACTIONS" 2>/dev/null)
    [ -n "$COUNTS" ] || COUNTS="0 0 0 0"
    set -- $COUNTS
    printf '  %-10s replies %s (%s left today)   dm %s   comments %s   escalated %s\n' \
      "$p" "$1" "$LEFT" "$2" "$3" "$4"
  done

  # Leads waiting on a reply
  if [ -f "$DATA/leads.jsonl" ]; then
    OPEN=$(jq -s --arg b "$b" '[ .[] | select(.brand==$b and .status=="collected") ] | length' "$DATA/leads.jsonl" 2>/dev/null)
    [ "$OPEN" != "0" ] && [ -n "$OPEN" ] && echo "  leads collected and not yet replied to: $OPEN"

    # Products being sized before they can be answered. These are deliberately
    # invisible to engage, which also makes them invisible here unless we ask —
    # and a market you cannot see is a market you will forget you are measuring.
    jq -rs --arg b "$b" '
      [ .[] | select(.brand==$b and .status=="research") ]
      | group_by(.product // "unspecified")[]
      | "  research (\(.[0].product // "unspecified")): \(length) collected, \([.[]|select(.intent=="high")]|length) high"
    ' "$DATA/leads.jsonl" 2>/dev/null
  fi
  echo
done

# The last few things it touched — the fastest way to see if a loop is doing
# something sensible or spinning.
if [ -s "$ACTIONS" ]; then
  echo "LAST 5 ACTIONS"
  tail -5 "$ACTIONS" | jq -r '"  \(.ts[11:16])  \(.platform[0:2]|ascii_upcase)  \(.kind)  \(.author // "-")"'
else
  echo "no actions logged yet"
fi

# Escalations are the one thing that needs a human, so surface the count loudly.
if [ -f "$ROOT/reports/escalations.md" ]; then
  OPENN=$(grep -c '^Status: \*\*OPEN\*\*' "$ROOT/reports/escalations.md" 2>/dev/null || echo 0)
  [ "$OPENN" -gt 0 ] && { echo; echo "*** $OPENN OPEN escalation(s) waiting on you — reports/escalations.md ***"; }
fi
