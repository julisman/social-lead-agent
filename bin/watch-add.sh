#!/bin/sh
# watch-add.sh   (JSON object on stdin)
#
# Append one hit to data/watch.jsonl. This is the deliverable of social-watch —
# a listing that matched a standing watchlist's hit rules.
#
# Required: watch, platform, author, post_url, post_id, text
#
# Recommended: author_url, price, location, size, seller_type, posted_at, found_at
#
# Read-only by nature: this only ever records what was found. Nothing here
# replies, likes, or DMs — contacting a seller is the owner's decision, made
# from the report.

. "$(dirname "$0")/common.sh"

IN=$(cat)
[ -n "$IN" ] || die "watch-add.sh: nothing on stdin"

echo "$IN" | jq -e '.watch and .platform and .author and .post_url and .post_id and .text' >/dev/null \
  || die "watch-add.sh: watch, platform, author, post_url, post_id, text are all required"

echo "$IN" | jq -c --arg t "$(now_iso)" --argjson e "$(now_epoch)" \
  '. + {recorded_at:$t, epoch:$e}' >> "$DATA/watch.jsonl"
