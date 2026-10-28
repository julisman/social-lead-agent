#!/bin/sh
# brand-init.sh <brand-slug>
#
# Scaffold brands/<slug>/ from the templates in brands/_example/, filling in the
# facts that live in config.json (display name, what it sells, service areas).
#
# What it does NOT do is write your brand voice or your reply templates. Those
# are prose for a reason: a reply assembled from config fields reads like a form
# letter, and sounding like a form letter is the failure this project exists to
# prevent. The scaffold marks those sections and leaves them to you.
#
# Refuses to overwrite an existing kit.

. "$(dirname "$0")/common.sh"

SLUG="$1"
[ -n "$SLUG" ] || die "usage: brand-init.sh <brand-slug>   (slug must exist in config.json)"

brand_exists "$SLUG" || die "brand '$SLUG' is not in config.json — add it there first"

SRC="$BRANDS/_example"
DST="$BRANDS/$SLUG"
[ -d "$SRC" ] || die "template directory missing: $SRC"
[ -d "$DST" ] && die "brands/$SLUG already exists — delete it first if you really mean to regenerate"

DISPLAY=$(jq -r --arg b "$SLUG" '.brands[$b].display_name // $b' "$CONFIG")
SELLS=$(jq -r --arg b "$SLUG" '.brands[$b].sells // "TODO — describe what this brand sells"' "$CONFIG")
AREAS=$(jq -r --arg b "$SLUG" '(.brands[$b].service_areas // []) | if length==0 then "TODO — none set in config.json" else join(", ") end' "$CONFIG")
EXCLUDED=$(jq -r --arg b "$SLUG" '(.brands[$b].excluded_areas // []) | if length==0 then "(none recorded yet)" else join(", ") end' "$CONFIG")

mkdir -p "$DST"
for f in BRAND.md KEYWORDS.md REPLIES.md; do
  [ -f "$SRC/$f" ] || continue
  sed -e "s|{{DISPLAY_NAME}}|$DISPLAY|g" \
      -e "s|{{SLUG}}|$SLUG|g" \
      -e "s|{{SELLS}}|$SELLS|g" \
      -e "s|{{SERVICE_AREAS}}|$AREAS|g" \
      -e "s|{{EXCLUDED_AREAS}}|$EXCLUDED|g" \
      "$SRC/$f" > "$DST/$f"
  echo "  created brands/$SLUG/$f"
done

cat <<EOF

brands/$SLUG scaffolded. Before this brand can do anything useful:

  1. Fill in "What we sell" in brands/$SLUG/BRAND.md — the agent answers from
     that file and nothing else.
  2. Write the "Voice" section yourself, with a sound-like / not-like pair.
  3. Replace the placeholder shapes in brands/$SLUG/REPLIES.md with real examples
     in that voice.
  4. Put your queries in brands/$SLUG/KEYWORDS.md and fill the seeker-vs-seller table.
  5. Set handles, profile and wa_number in config.json, then: bin/config-check.sh

Leave ramp_start as null until you have run prospecting read-only and read the
leads. That is what keeps a new account from replying to strangers on day one.
EOF
