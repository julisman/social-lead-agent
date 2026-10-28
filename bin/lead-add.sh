#!/bin/sh
# lead-add.sh   (JSON object on stdin)
#
# Append one lead to data/leads.jsonl. This is the deliverable of prospecting —
# a person with intent, plus the link back to what they said.
#
# Required: platform, brand, author, post_url, text, intent
#   intent: high | medium        (reject-tier posts are never written here)
#
# Recommended: post_id, author_url, posted_at, query, language, product, status
#   status: collected            (set by prospecting — engage will reply to these)
#         | replied              (set by engage, via lead-update)
#         | skipped              (dedupe or budget)
#         | research             (market sizing only — engage must never touch these)
#
# `research` is how a product gets prospected before it can be answered. engage
# filters on status=="collected", so a research lead is invisible to it by the
# shape of the data rather than by an instruction someone has to remember. Use it
# whenever BRAND.md cannot yet answer the question the lead is asking — replying
# with "DM us" to a product you can't describe burns the author for 30 days under
# the dedupe rule and teaches the account nothing.
#
# `product` (motor | driver | jastip) says which line of business the lead wants.
# One account can carry several, and they convert nothing like each other.

. "$(dirname "$0")/common.sh"

IN=$(cat)
[ -n "$IN" ] || die "lead-add.sh: nothing on stdin"

echo "$IN" | jq -e '.platform and .brand and .author and .post_url and .text and .intent' >/dev/null \
  || die "lead-add.sh: platform, brand, author, post_url, text, intent are all required"

echo "$IN" | jq -e '.intent == "high" or .intent == "medium"' >/dev/null \
  || die "lead-add.sh: intent must be high or medium — reject-tier posts are not leads"

# Normalise the handle on the way in. engage reads .author straight out of this
# file and hands it to seen.sh, so a lead stored as "@handle" would be checked
# against a key that does not exist and the dedupe gate would wave it through.
AUTHOR="$(norm_handle "$(echo "$IN" | jq -r '.author')")"

echo "$IN" | jq -c --arg t "$(now_iso)" --argjson e "$(now_epoch)" --arg a "$AUTHOR" \
  '{status:"collected"} + . + {author:$a, collected_at:$t, epoch:$e}' >> "$DATA/leads.jsonl"
