#!/usr/bin/env bash
# Full-screen Chromium pointed at the calendar. Started by labwc autostart (see setup-pi.sh).
# Restarts Chromium if it exits, and waits for the backend to answer before opening.
set -u

CONF="$HOME/.config/family-calendar/kiosk.env"
[ -f "$CONF" ] && . "$CONF"
KIOSK_URL="${KIOSK_URL:-http://localhost:8000}"

BROWSER=$(command -v chromium || command -v chromium-browser)

until curl -fsS -o /dev/null "$KIOSK_URL/api/health"; do
  sleep 3
done

while true; do
  # Clear the "Chromium didn't shut down correctly" bubble after power loss
  sed -i 's/"exited_cleanly":false/"exited_cleanly":true/; s/"exit_type":"Crashed"/"exit_type":"Normal"/' \
    "$HOME/.config/chromium/Default/Preferences" 2>/dev/null || true

  "$BROWSER" \
    --kiosk "$KIOSK_URL" \
    --noerrdialogs --disable-infobars --no-first-run \
    --disable-session-crashed-bubble --disable-features=Translate \
    --overscroll-history-navigation=0 --disable-pinch \
    --touch-events=enabled \
    --ozone-platform=wayland --enable-features=OverlayScrollbar
  sleep 2
done
