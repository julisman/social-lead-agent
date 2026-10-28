#!/bin/sh
# log-action.sh   (JSON object on stdin)
#
# Append-only audit log. Every action that touches another human goes here —
# this file is what budget.sh counts, what the daily report reads, and what you
# read when you want to know what the agent actually did.
#
# Required fields: brand, platform, kind
#   kind: public_reply | dm_reply | dm_escalate | prospect_run | health_check | blocked
# Everything else is free-form (post_url, author, template, text, note, ...).
#
# Example:
#   echo '{"brand":"motor-sewa-bali","platform":"threads","kind":"public_reply",
#          "author":"@x","post_url":"https://...","template":"rec-casual-2",
#          "text":"..."}' | bin/log-action.sh

. "$(dirname "$0")/common.sh"

IN=$(cat)
[ -n "$IN" ] || die "log-action.sh: nothing on stdin"

echo "$IN" | jq -e '.brand and .platform and .kind' >/dev/null \
  || die "log-action.sh: brand, platform and kind are all required"

echo "$IN" | jq -c --arg t "$(now_iso)" --argjson e "$(now_epoch)" \
  '. + {ts:$t, epoch:$e}' >> "$DATA/actions.jsonl"
