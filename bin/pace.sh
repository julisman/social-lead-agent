#!/bin/sh
# pace.sh <brand> <platform>
#
# Enforce human rhythm between public actions on one account. Picks a fresh
# random gap of 40-120s each time and waits out whatever remains of it since
# the last logged action.
#
# The randomness matters more than the average. A perfectly regular 60s cadence
# is a stronger bot signal than acting quickly — humans are erratic.
#
# Prints the seconds it waited. Call it BEFORE each reply, not after.
#
# If the harness blocks a foreground sleep, run this with run_in_background, or
# call `bin/pace.sh --check <brand> <platform>` to just print the seconds still
# owed and wait via Monitor instead.

. "$(dirname "$0")/common.sh"

CHECK_ONLY=0
if [ "$1" = "--check" ]; then CHECK_ONLY=1; shift; fi

BRAND="$1"; PLATFORM="$2"
[ -n "$BRAND" ] && [ -n "$PLATFORM" ] || die "usage: pace.sh [--check] <brand> <platform>"

GAP_MIN=$(cfg '.defaults.pace_seconds_min' 40)
GAP_MAX=$(cfg '.defaults.pace_seconds_max' 120)
GAP_SPAN=$(( GAP_MAX - GAP_MIN + 1 ))

if command -v jot >/dev/null 2>&1; then
  GAP=$(jot -r 1 "$GAP_MIN" "$GAP_MAX")
else
  GAP=$(( GAP_MIN + ${RANDOM:-0} % GAP_SPAN ))
fi

LAST=$(jq -s --arg b "$BRAND" --arg p "$PLATFORM" \
  '[ .[] | select(.brand==$b and .platform==$p and (.kind=="public_reply" or .kind=="dm_reply")) | .epoch ] | max // 0' \
  "$DATA/actions.jsonl" 2>/dev/null)
[ -n "$LAST" ] && [ "$LAST" != "null" ] || LAST=0

ELAPSED=$(( $(now_epoch) - LAST ))
[ "$LAST" -eq 0 ] && ELAPSED="$GAP"

WAIT=$(( GAP - ELAPSED ))
[ "$WAIT" -lt 0 ] && WAIT=0

if [ "$CHECK_ONLY" -eq 1 ]; then
  echo "$WAIT"
  exit 0
fi

[ "$WAIT" -gt 0 ] && sleep "$WAIT"
echo "waited ${WAIT}s (target gap ${GAP}s)"
