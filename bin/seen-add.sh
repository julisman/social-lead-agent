#!/bin/sh
# seen-add.sh <platform> <post_id> <author_handle> <brand>
#
# Record that we have engaged this post and this author. Call it IMMEDIATELY
# after a reply lands — never batch these at the end of a run, because a crash
# mid-run would leave people eligible to be replied to a second time.

. "$(dirname "$0")/common.sh"

PLATFORM="$1"; POST_ID="$2"; AUTHOR="$3"; BRAND="$4"
[ -n "$PLATFORM" ] && [ -n "$POST_ID" ] && [ -n "$AUTHOR" ] && [ -n "$BRAND" ] \
  || die "usage: seen-add.sh <platform> <post_id> <author_handle> <brand>"

# Must match seen.sh exactly, or we write a key the gate will never read.
AUTHOR="$(norm_handle "$AUTHOR")"

TS=$(now_iso)
EPOCH=$(now_epoch)

{
  jq -nc --arg k "$PLATFORM:$POST_ID" --arg b "$BRAND" --arg t "$TS" --argjson e "$EPOCH" \
    '{kind:"post", key:$k, brand:$b, ts:$t, epoch:$e}'
  jq -nc --arg k "$PLATFORM:$AUTHOR" --arg b "$BRAND" --arg t "$TS" --argjson e "$EPOCH" \
    '{kind:"author", key:$k, brand:$b, ts:$t, epoch:$e}'
} >> "$DATA/seen.jsonl"

echo "recorded $PLATFORM:$POST_ID and $PLATFORM:$AUTHOR"
