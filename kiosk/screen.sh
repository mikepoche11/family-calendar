#!/usr/bin/env bash
# Usage: screen.sh on|off — turns the HDMI output on or off (used by cron for night mode).
set -eu
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
OUTPUT=$(wlr-randr | awk '/^[A-Z]/{print $1; exit}')
case "${1:-}" in
  on)  wlr-randr --output "$OUTPUT" --on ;;
  off) wlr-randr --output "$OUTPUT" --off ;;
  *)   echo "usage: $0 on|off" >&2; exit 1 ;;
esac
