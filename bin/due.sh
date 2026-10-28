#!/bin/sh
# due.sh [brand]
#
# Prints which skills are due to run right now, one per line, most important
# first. Prints nothing if nothing is due.
#
# Designed to be the body of a single loop. Rather than counting ticks, it asks
# "when did this last actually run?" — so a missed tick, a crash, a restart or a
# machine that was asleep all self-correct instead of drifting.
#
# Cadence and working hours come from config.json:
#
#   "schedule": {
#     "working_hours": { "start": 8, "end": 21, "days": [1,2,3,4,5,6,7] },
#     "every_minutes": { "social-dm": 30, "social-prospect": 60, "social-comments": 180 }
#   }
#
# Skills record that they ran by logging kind:"run" with a skill field, even
# when they did nothing — a run that found an empty inbox still counts, or the
# dispatcher would fire it again every tick forever.

. "$(dirname "$0")/common.sh"

ONLY="$1"
ACTIONS="$DATA/actions.jsonl"
NOW=$(now_epoch)

# ---- working hours -----------------------------------------------------------
HSTART=$(cfg '.schedule.working_hours.start' 8)
HEND=$(cfg '.schedule.working_hours.end' 21)
HOUR=$(date +%H | sed 's/^0//'); [ -z "$HOUR" ] && HOUR=0
DOW=$(date +%u)   # 1=Mon .. 7=Sun

DAYS=$(jq -r '(.schedule.working_hours.days // [1,2,3,4,5,6,7]) | join(" ")' "$CONFIG" 2>/dev/null)
[ -n "$DAYS" ] || DAYS="1 2 3 4 5 6 7"

day_ok=0
for d in $DAYS; do [ "$d" = "$DOW" ] && day_ok=1; done

if [ "$HOUR" -lt "$HSTART" ] || [ "$HOUR" -ge "$HEND" ] || [ "$day_ok" -eq 0 ]; then
  echo "# outside working hours (${HSTART}:00-${HEND}:00, day $DOW) — nothing due" >&2
  exit 0
fi

if [ -f "$ROOT/PAUSED" ]; then
  echo "# PAUSED — nothing due" >&2
  exit 0
fi

# ---- which skills, in priority order -----------------------------------------
# DM first, deliberately: answering someone who already contacted you beats
# going looking for someone who hasn't.
SKILLS=$(jq -r '(.schedule.every_minutes // {}) | keys_unsorted[]' "$CONFIG" 2>/dev/null)
[ -n "$SKILLS" ] || SKILLS="social-dm social-prospect social-comments"

for b in $(jq -r '.brands | keys[]' "$CONFIG"); do
  [ -n "$ONLY" ] && [ "$ONLY" != "$b" ] && continue
  [ "$(jq -r --arg b "$b" '[.brands[$b].accounts[]|select(.enabled==true)]|length' "$CONFIG")" = "0" ] && continue

  for s in $SKILLS; do
    MINS=$(jq -r --arg s "$s" '.schedule.every_minutes[$s] // empty' "$CONFIG")
    # Fall back to sensible defaults so this works before anyone configures it.
    # Silently doing nothing would look identical to "nothing is due".
    if [ -z "$MINS" ]; then
      case "$s" in
        social-dm)       MINS=30 ;;
        social-prospect) MINS=60 ;;
        social-comments) MINS=180 ;;
        social-health)   MINS=1440 ;;
        *) continue ;;   # social-engage is triggered by prospect, not the clock
      esac
    fi

    LAST=$(jq -rs --arg b "$b" --arg s "$s" \
      '[ .[] | select(.brand==$b and .kind=="run" and .skill==$s) | .epoch ] | max // 0' \
      "$ACTIONS" 2>/dev/null)
    [ -n "$LAST" ] && [ "$LAST" != "null" ] || LAST=0

    AGE_MIN=$(( (NOW - LAST) / 60 ))
    if [ "$LAST" -eq 0 ]; then
      echo "$s $b   # never run"
    elif [ "$AGE_MIN" -ge "$MINS" ]; then
      echo "$s $b   # last run ${AGE_MIN}m ago, due every ${MINS}m"
    fi
  done
done
