#!/bin/sh
# wa-link.sh <brand> <platform> [topic]
#
# Build the WhatsApp handoff link, URL-encoded correctly.
#
# The prefilled message carries source and topic across to the WhatsApp agent,
# so it opens the chat already knowing where the person came from.
#
# NOTE: use the encoded link for a bio or profile. In a DM, send the readable
# form instead — `0812-3456-7890 (wa.me/628123456789)`. The encoded version wraps to
# several lines of %20 noise and reads like a bot. See social-dm.
#
#   bin/wa-link.sh motor-sewa-bali threads "sewa motor di Canggu 3 hari"

. "$(dirname "$0")/common.sh"

BRAND="$1"; PLATFORM="$2"; TOPIC="$3"
[ -n "$BRAND" ] && [ -n "$PLATFORM" ] || die "usage: wa-link.sh <brand> <platform> [topic]"
[ -n "$TOPIC" ] || TOPIC="mau tanya-tanya"

brand_exists "$BRAND" || die "brand '$BRAND' is not defined in config.json"

WA=$(jq -r --arg b "$BRAND" '.brands[$b].wa_number // empty' "$CONFIG" | tr -d ' +-')
[ -n "$WA" ] || die "brands.$BRAND.wa_number is not set in config.json"
case "$WA" in
  TODO*|*[!0-9]*) die "brands.$BRAND.wa_number must be digits only with country code, got '$WA'" ;;
esac

MSG="Halo, saya dari $PLATFORM — $TOPIC"
ENC=$(printf '%s' "$MSG" | jq -sRr @uri)

echo "https://wa.me/$WA?text=$ENC"
