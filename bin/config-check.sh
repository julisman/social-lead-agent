#!/bin/sh
# config-check.sh
#
# Validate config.json and report what still needs filling in. Run this after
# editing config, and before the first browser session.
#
# Exit 0 -> usable. Exit 1 -> problems found.

. "$(dirname "$0")/common.sh"

FAIL=0
warn() { echo "  WARN  $*"; }
bad()  { echo "  FAIL  $*"; FAIL=1; }

jq -e . "$CONFIG" >/dev/null 2>&1 || die "config.json is not valid JSON"

echo "config.json"
echo "  timezone: $(cfg '.timezone' '(unset)')"
[ -n "$(cfg '.timezone' '')" ] || bad "timezone is not set"
echo "  today (in that timezone): $(today)"
echo

BRANDS_LIST=$(jq -r '.brands | keys[]' "$CONFIG")
[ -n "$BRANDS_LIST" ] || die "no brands defined in config.json"

for b in $BRANDS_LIST; do
  echo "$b"

  WA=$(jq -r --arg b "$b" '.brands[$b].wa_number // empty' "$CONFIG")
  case "$WA" in
    "")            bad "wa_number missing" ;;
    TODO*)         warn "wa_number is still a placeholder — handoffs will fail" ;;
    628123456789)  warn "wa_number is still the number from config.example.json — replace it with yours" ;;
    *[!0-9]*)      bad "wa_number must be digits only with country code, got '$WA'" ;;
    *)             echo "  wa_number: ok" ;;
  esac

  AREAS=$(jq -r --arg b "$b" '.brands[$b].service_areas | length' "$CONFIG")
  [ "$AREAS" -gt 0 ] 2>/dev/null || warn "no service_areas set — the agent cannot judge whether a lead is in range"

  PROF=$(chrome_profile "$b" threads)
  BRAND_PROF=$(jq -r --arg b "$b" '.brands[$b].chrome_profile // empty' "$CONFIG")
  if [ -n "$PROF" ]; then
    echo "  chrome_profile: $PROF  (not enforced — confirm the logged-in account on screen)"
  else
    warn "no chrome_profile set — nothing tells you which browser profile this brand uses"
  fi

  # A brand-level value that loses to a leftover per-platform one is the kind of
  # thing you set, believe, and never see take effect.
  if [ -n "$BRAND_PROF" ] && [ "$BRAND_PROF" != "$PROF" ]; then
    warn "chrome_profile '$BRAND_PROF' is being SHADOWED by accounts.*.profile ('$PROF')."
    warn "  Remove the per-platform profile fields to make the brand-level value take effect:"
    warn "  jq '(.brands[\"$b\"].accounts[]) |= del(.profile)' config.json > /tmp/c && mv /tmp/c config.json"
  fi

  # Cheap sanity check — a transposed address is easy to type and invisible later.
  case "$PROF" in
    *@*) echo "$PROF" | grep -qE '^[^@[:space:]]+@[A-Za-z][A-Za-z0-9.-]*\.[A-Za-z]{2,}$' \
           || warn "chrome_profile '$PROF' looks like a malformed email address" ;;
  esac

  [ -d "$BRANDS/$b" ] || warn "no brand kit at brands/$b — run: bin/brand-init.sh $b"

  for p in threads tiktok instagram; do
    EN=$(acct "$b" "$p" enabled)
    RAMP=$(acct "$b" "$p" ramp_start)
    HANDLE=$(acct "$b" "$p" handle)
    [ -n "$EN" ] || { warn "$p: not defined"; continue; }
    if [ "$EN" = "true" ]; then
      [ -n "$HANDLE" ] || warn "$p: enabled but handle is null"
      if [ -z "$RAMP" ]; then
        echo "  $p: enabled, READ-ONLY (ramp_start null — 0 public replies)"
      else
        echo "  $p: enabled, replies allowed today: $("$ROOT/bin/budget.sh" "$b" "$p")"
      fi
    else
      echo "  $p: disabled"
    fi
  done
  echo
done

if [ -f "$ROOT/PAUSED" ]; then
  echo "PAUSED file present — all activity is halted: $(cat "$ROOT/PAUSED")"
fi

[ "$FAIL" -eq 0 ] && echo "config is usable." || echo "config has problems (see FAIL above)."
exit "$FAIL"
