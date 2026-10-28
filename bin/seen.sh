#!/bin/sh
# seen.sh <platform> <post_id> <author_handle>
#
# The dedupe gate. Call it before every single public reply.
#
# Exit 0 -> NEW, safe to engage.
# Exit 1 -> SKIP, with the reason on stdout.
#
# Two independent checks:
#   post   — platform:post_id, never expires. Never reply to a post twice.
#   author — platform:handle, 30-day window, checked across ALL brands.
#            Three different businesses replying to one person is the clearest
#            bot signal we can emit, so the author set is deliberately global.
#
# The handle is normalised (norm_handle) before it becomes a key. "@Handle" and
# "handle" are the same person, and a gate that treats them as two is no gate.

. "$(dirname "$0")/common.sh"

PLATFORM="$1"
POST_ID="$2"
AUTHOR="$3"
[ -n "$PLATFORM" ] && [ -n "$POST_ID" ] && [ -n "$AUTHOR" ] \
  || die "usage: seen.sh <platform> <post_id> <author_handle>"

POST_KEY="$PLATFORM:$POST_ID"
AUTHOR_KEY="$PLATFORM:$(norm_handle "$AUTHOR")"
CUTOFF=$(( $(now_epoch) - AUTHOR_TTL_DAYS * 86400 ))

[ -s "$DATA/seen.jsonl" ] || { echo "NEW"; exit 0; }

HIT=$(jq -rs --arg pk "$POST_KEY" --arg ak "$AUTHOR_KEY" --argjson cut "$CUTOFF" '
  ( [ .[] | select(.kind=="post" and .key==$pk) ] | first ) as $post
  | ( [ .[] | select(.kind=="author" and .key==$ak and .epoch >= $cut) ] | first ) as $auth
  | if   $post then "SKIP: already replied to this post on \($post.ts) as \($post.brand)"
    elif $auth then "SKIP: replied to \($auth.key) on \($auth.ts) as \($auth.brand) — inside the 30-day author window"
    else "NEW" end
' "$DATA/seen.jsonl")

echo "$HIT"
[ "$HIT" = "NEW" ] || exit 1
exit 0
