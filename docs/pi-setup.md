# Raspberry Pi kiosk setup

Hardware: Raspberry Pi 5 (8 GB) with active cooler and 27 W power supply, ideally booting from an
NVMe SSD; a touchscreen monitor connected by HDMI (video) and USB (touch).

## 1. Flash the OS

Use Raspberry Pi Imager: **Raspberry Pi OS (64-bit)** with desktop. In the Imager's settings, set the
hostname (`familycal`), your user, Wi-Fi, and enable SSH. Boot the Pi; the desktop should log in
automatically (the default for the desktop image).

Check that touch works on the desktop before going further. Most USB touch monitors need no drivers.

## 2. Get the code and run setup

```bash
sudo apt-get install -y git
git clone https://github.com/mikepoche11/family-calendar.git
cd family-calendar
./kiosk/setup-pi.sh
```

This installs Chromium, emoji fonts and Docker, sets the time zone to Central, starts the kiosk on
login, turns the screen off at 22:00 and on at 06:00, and restarts Chromium nightly at 03:30.
Change the times with `--screen-off 21:30 --screen-on 06:30`.

## 3. Start the backend

Reboot (or log out and in) so your user can run Docker, then follow
[google-setup.md](google-setup.md) step 3. Reboot again and the calendar comes up full screen.

## Fallback: backend on the Linux PC

If the Pi struggles, run the backend on the PC instead (same `docker compose up -d --build` there)
and make the Pi a thin client:

```bash
./kiosk/setup-pi.sh --url http://<pc-ip-address>:8000
```

The PC then has to stay on; give it a fixed IP address in your router.

## Useful commands

| What | Command |
| --- | --- |
| Backend logs | `docker compose logs -f` |
| Force a sync now | `curl -X POST localhost:8000/api/sync` |
| Update to the latest code | `git pull && docker compose up -d --build` |
| Screen off / on now | `./kiosk/screen.sh off` / `./kiosk/screen.sh on` |
| Back up the database | copy `data/calendar.db` somewhere safe |
| Exit the kiosk | plug in a keyboard and press `Alt+F4`, or SSH in and `pkill chromium` |

## Rotating to portrait

```bash
wlr-randr                                   # find the output name, e.g. HDMI-A-1
wlr-randr --output HDMI-A-1 --transform 90
```

To keep it, use **Screen Configuration** in the Pi desktop menu. If touches land in the wrong place
afterwards, the touch input needs the same rotation; tell Claude the monitor model and we'll add it.

## On-screen keyboard

Typing an event on the wall needs an on-screen keyboard. Raspberry Pi OS ships `squeekboard`
(Preferences > Raspberry Pi Configuration > Display > On-screen keyboard). Until we add voice entry,
adding events from a phone at `http://familycal.local:8000` is often quicker.
