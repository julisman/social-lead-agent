#!/bin/sh
# guard.sh <brand> <platform>
#
# Run this FIRST, every session, before opening a browser tab. It answers one
# question: may I act as this account right now, and how many times?
#
# Exit 0 -> OK to act. Prints JSON with the remaining budget.
# Exit 1 -> Do not act. Prints the reason. Stop the run for this account.
# Exit 2 -> Bad usage or bad config.

. "$(dirname "$0")/common.sh"

BRAND="$1"
PLATFORM="$2"
[ -n "$BRAND" ] && [ -n "$PLATFORM" ] || die "usage: guard.sh <brand> <platform>"

brand_exists "$BRAND" || die "brand '$BRAND' is not defined in config.json"

# 1. Global kill switch. Beats everything.
if [ -f "$ROOT/PAUSED" ]; then
  echo "BLOCKED: global PAUSED file present — $(cat "$ROOT/PAUSED" 2>/dev/null)"
  exit 1
fi

# 2. Per-account cooldown (set after a platform block).
COOLDOWN="$DATA/cooldown/$BRAND-$PLATFORM"
if [ -f "$COOLDOWN" ]; then
  UNTIL=$(head -1 "$COOLDOWN")
  NOW=$(now_epoch)
  if [ "$NOW" -lt "$UNTIL" ]; then
    MINS=$(( (UNTIL - NOW) / 60 ))
    echo "BLOCKED: $BRAND/$PLATFORM in cooldown for ${MINS} more minutes — $(sed -n 2p "$COOLDOWN")"
    exit 1
  fi
  rm -f "$COOLDOWN"
fi

# 3. Account must exist and be enabled.
ENABLED=$(acct "$BRAND" "$PLATFORM" enabled)
if [ "$ENABLED" != "true" ]; then
  echo "BLOCKED: $BRAND/$PLATFORM is not enabled in config.json"
  exit 1
fi

# 4. Budget. A null ramp_start means this account has never been cleared for
#    public replies — read-only prospecting is still fine, engaging is not.
REMAINING=$("$ROOT/bin/budget.sh" "$BRAND" "$PLATFORM") || exit 2

jq -n --arg brand "$BRAND" --arg platform "$PLATFORM" \
      --arg handle "$(acct "$BRAND" "$PLATFORM" handle)" \
      --argjson remaining "$REMAINING" --arg now "$(now_iso)" \
  '{status:"ok", brand:$brand, platform:$platform, handle:$handle,
    replies_remaining_today:$remaining, now:$now}'
exit 0
