#!/usr/bin/env bash
# One-time setup for the Raspberry Pi kiosk (Raspberry Pi OS Bookworm or Trixie, desktop, 64-bit).
#
#   ./kiosk/setup-pi.sh                         # Pi runs everything (recommended)
#   ./kiosk/setup-pi.sh --url http://192.168.1.20:8000   # thin client: backend on the Linux PC
#
# Options: --url URL   --screen-off HH:MM (default 21:00)   --screen-on HH:MM (default 06:00)
set -euo pipefail

URL="http://localhost:8000"
OFF="21:00"
ON="06:00"
while [ $# -gt 0 ]; do
  case "$1" in
    --url) URL="$2"; shift 2 ;;
    --screen-off) OFF="$2"; shift 2 ;;
    --screen-on) ON="$2"; shift 2 ;;
    *) echo "unknown option $1" >&2; exit 1 ;;
  esac
done

REPO="$(cd "$(dirname "$0")/.." && pwd)"
KIOSK_DIR="$REPO/kiosk"

echo "==> Packages"
sudo apt-get update
CHROMIUM=chromium
apt-cache show chromium >/dev/null 2>&1 || CHROMIUM=chromium-browser
sudo apt-get install -y "$CHROMIUM" fonts-noto-color-emoji wlr-randr curl

echo "==> Time zone"
sudo timedatectl set-timezone America/Chicago

if [ "$URL" = "http://localhost:8000" ] && ! command -v docker >/dev/null; then
  echo "==> Docker (backend runs on this Pi)"
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
  echo "    Log out and back in (or reboot) before running 'docker compose up -d'."
fi

echo "==> Kiosk config"
mkdir -p "$HOME/.config/family-calendar" "$HOME/.config/labwc"
echo "KIOSK_URL=$URL" > "$HOME/.config/family-calendar/kiosk.env"
chmod +x "$KIOSK_DIR/kiosk.sh" "$KIOSK_DIR/screen.sh"

AUTOSTART="$HOME/.config/labwc/autostart"
touch "$AUTOSTART"
grep -q "family-calendar" "$AUTOSTART" || echo "$KIOSK_DIR/kiosk.sh &  # family-calendar" >> "$AUTOSTART"

echo "==> Night mode and nightly browser restart (cron)"
off_h=${OFF%:*}; off_m=${OFF#*:}; on_h=${ON%:*}; on_m=${ON#*:}
( crontab -l 2>/dev/null | grep -v "family-calendar" || true
  echo "$off_m $off_h * * * $KIOSK_DIR/screen.sh off  # family-calendar"
  echo "$on_m $on_h * * * $KIOSK_DIR/screen.sh on  # family-calendar"
  echo "30 3 * * * pkill -f 'chromium.*--kiosk'  # family-calendar (kiosk.sh relaunches it)"
) | crontab -

echo
echo "Done. Reboot to start the kiosk: sudo reboot"
