#!/bin/sh
# cooldown.sh <brand> <platform> <hours> <reason>
#
# Park an account. Call this the moment a platform pushes back — an action
# block, a "Try again later", a captcha, a login challenge, a reply that
# silently fails to appear.
#
# Never retry through a block. Retrying is how a temporary limit becomes a
# permanent one.
#
#   bin/cooldown.sh motor-sewa-bali threads 24 "action block modal on reply"

. "$(dirname "$0")/common.sh"

BRAND="$1"; PLATFORM="$2"; HOURS="$3"; REASON="$4"
[ -n "$BRAND" ] && [ -n "$PLATFORM" ] && [ -n "$HOURS" ] \
  || die "usage: cooldown.sh <brand> <platform> <hours> [reason]"
[ -n "$REASON" ] || REASON="no reason given"

UNTIL=$(( $(now_epoch) + HOURS * 3600 ))
mkdir -p "$DATA/cooldown"
{ echo "$UNTIL"; echo "$REASON"; } > "$DATA/cooldown/$BRAND-$PLATFORM"

jq -nc --arg b "$BRAND" --arg p "$PLATFORM" --arg r "$REASON" --argjson h "$HOURS" \
  '{brand:$b, platform:$p, kind:"blocked", cooldown_hours:$h, note:$r}' \
  | "$ROOT/bin/log-action.sh"

echo "$BRAND/$PLATFORM parked for ${HOURS}h until $(date -r "$UNTIL" +%Y-%m-%dT%H:%M:%S%z) — $REASON"
