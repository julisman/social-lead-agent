#!/bin/sh
# budget.sh <brand> <platform>
#
# Prints how many public replies this account may still send today (integer).
# Prints 0 when the account has not been cleared for public replies at all.
#
# The warm-up ramp comes from config.json, so a read-only trial is enforced by
# data rather than by remembering: ramp_start = null -> 0 replies allowed,
# forever, until a human sets a date.
#
# Ramp stages are configurable under defaults.ramp; the default is
#   days 1-7   ->  5/day
#   days 8-14  -> 10/day
#   day 15+    -> daily_cap
#
# Only kind=="public_reply" counts. DM replies and comment replies are answers
# to people who came to us, so they are uncapped by design.

. "$(dirname "$0")/common.sh"

BRAND="$1"
PLATFORM="$2"
[ -n "$BRAND" ] && [ -n "$PLATFORM" ] || die "usage: budget.sh <brand> <platform>"

RAMP=$(acct "$BRAND" "$PLATFORM" ramp_start)
CAP=$(acct "$BRAND" "$PLATFORM" daily_cap)
[ -n "$CAP" ] || CAP=$(cfg '.defaults.daily_cap' 20)

if [ -z "$RAMP" ]; then
  echo 0
  exit 0
fi

RAMP_EPOCH=$(date -j -f "%Y-%m-%d" "$RAMP" +%s 2>/dev/null) \
  || RAMP_EPOCH=$(date -d "$RAMP" +%s 2>/dev/null) \
  || die "bad ramp_start '$RAMP' for $BRAND/$PLATFORM (expected YYYY-MM-DD)"

DAYS=$(( ( $(now_epoch) - RAMP_EPOCH ) / 86400 ))

if [ "$DAYS" -lt 0 ]; then
  ALLOWED=0                      # ramp_start is in the future
else
  # Walk the configured ramp stages; fall through to the cap.
  ALLOWED="$CAP"
  STAGES=$(jq -r '.defaults.ramp[]? | "\(.through_day) \(.replies_per_day)"' "$CONFIG")
  OLDIFS=$IFS; IFS='
'
  for stage in $STAGES; do
    THROUGH=${stage%% *}
    PERDAY=${stage##* }
    if [ "$DAYS" -lt "$THROUGH" ]; then ALLOWED="$PERDAY"; break; fi
  done
  IFS=$OLDIFS
fi

# Count public replies already logged today for this account.
USED=$(jq -s --arg b "$BRAND" --arg p "$PLATFORM" --arg d "$(today)" \
  '[ .[] | select(.brand==$b and .platform==$p and .kind=="public_reply" and (.ts|startswith($d))) ] | length' \
  "$DATA/actions.jsonl" 2>/dev/null)
[ -n "$USED" ] || USED=0

REMAINING=$(( ALLOWED - USED ))
[ "$REMAINING" -lt 0 ] && REMAINING=0
echo "$REMAINING"
