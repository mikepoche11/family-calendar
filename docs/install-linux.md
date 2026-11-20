# Install the calendar on a Linux PC

Step-by-step for running the whole app (calendar, chores, marbles, grocery, meals, phone view) on
a Linux PC with Docker. Written for **Zorin OS / Ubuntu / Linux Mint / Pop!_OS** (anything that
uses `apt`); Fedora notes are at the end of step 1. Plan on 30 to 45 minutes, most of it waiting
for downloads and the first build.

You'll type commands into a **Terminal** (Zorin: press the Zorin/Windows key, type "Terminal").
Copy each block in one go. Lines starting with `#` are comments and do nothing.

> **Keep it private.** The app has no login: anyone who can reach it can change things. Never
> forward port 8000 on your router and never run `tailscale funnel` for it. Your home Wi-Fi and
> Tailscale (including `tailscale serve`) only let your own devices in.

---

## 0. Check what's already installed

```bash
git --version
docker --version
docker compose version
```

- All three print a version: skip to step 2.
- `docker compose version` says "not a docker command" but `docker-compose --version` works: you
  have the old Compose. Do step 1 anyway; it replaces it.
- Anything says "command not found": do step 1.

---

## 1. Install git and Docker (one time)

### Git

```bash
sudo apt update
sudo apt install -y git curl ca-certificates
```

### Docker Engine + Compose plugin (from Docker's own repository)

Docker's quick `get.docker.com` script refuses Zorin and Mint, so use the repository directly.
These lines work on Ubuntu and on distros built from it, because they ask for the Ubuntu release
your system is based on.

```bash
# Remove any old/unofficial Docker packages (fine if it says none are installed)
sudo apt remove -y docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc

# Add Docker's signing key and repository
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${UBUNTU_CODENAME:-$VERSION_CODENAME} stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start Docker now and on every boot
sudo systemctl enable --now docker

# Let your user run docker without sudo
sudo usermod -aG docker $USER
```

**Log out and back in** (or reboot) so the last line takes effect. Then check:

```bash
docker run --rm hello-world
docker compose version
```

`hello-world` should print "Hello from Docker!". If it says "permission denied ... docker.sock",
you haven't logged out and back in yet (as a stopgap, `newgrp docker` fixes it for that one
terminal window).

**If `apt update` errors about the Docker repository** (usually because `UBUNTU_CODENAME` was
blank), run `cat /etc/os-release`, find the Ubuntu name it's based on (`jammy` for 22.04,
`noble` for 24.04), and redo the `echo` line with that word in place of
`${UBUNTU_CODENAME:-$VERSION_CODENAME}`.

**Fedora instead:** `sudo dnf install -y git dnf-plugins-core`, then
`sudo dnf config-manager addrepo --from-repofile=https://download.docker.com/linux/fedora/docker-ce.repo`
(on older Fedora: `sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo`),
`sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin`,
then the same `systemctl` and `usermod` lines as above.

---

## 2. Download the app (the repository is private)

Because the repo is private, GitHub needs to know it's you. The easiest way is GitHub's own
command-line tool, `gh`, which signs you in through the browser once.

```bash
sudo apt install -y gh
gh auth login
```

Answer the questions:

1. **Where do you use GitHub?** GitHub.com
2. **Preferred protocol?** HTTPS
3. **Authenticate Git with your GitHub credentials?** Yes
4. **How would you like to authenticate?** Login with a web browser

It shows a one-time code like `ABCD-1234`. Press Enter, a browser opens, sign in to GitHub,
paste the code, and approve. Back in the terminal it says "Logged in as mikepoche11".

Now download the app into your home folder:

```bash
cd ~
git clone https://github.com/mikepoche11/family-calendar.git
cd family-calendar
ls
```

You should see `README.md`, `docker-compose.yml`, `backend`, `frontend`, `docs` and so on.
From here on, every command is run **inside this `~/family-calendar` folder**.

<details>
<summary>No <code>gh</code>? Use a personal access token instead</summary>

1. On github.com: your picture > **Settings > Developer settings > Personal access tokens >
   Fine-grained tokens > Generate new token**.
2. Name `family-calendar PC`, expiry 1 year, **Repository access: Only select repositories >
   family-calendar**, **Permissions > Contents: Read-only**. Generate and copy the token.
3. `git clone https://github.com/mikepoche11/family-calendar.git`. When it asks, the username
   is `mikepoche11` and the **password is the token** (pasting shows nothing; that's normal).
4. So it doesn't ask every time you update: `git config --global credential.helper store`
   (it saves the token in `~/.git-credentials` the next time you enter it).

</details>

---

## 3. Put the Google key in place

On 2026-11-18 you finished [google-setup.md](google-setup.md) up to this point: you have a
service-account key (a `.json` file) and the calendar is shared with the service account. Now
the key goes onto this PC.

**Get the key file onto the PC.** If you downloaded it on this PC, it's in `~/Downloads`. If
you downloaded it on another computer, copy it over (USB stick, or email it to yourself and
delete the email afterwards). If you can't find it, make a new one: Google Cloud console >
**IAM & Admin > Service Accounts >** `family-calendar` **> Keys > Add key > Create new key >
JSON**. (You can delete old keys on the same page.)

Find it:

```bash
ls ~/Downloads/*.json
```

It's usually named after your Google Cloud project, like `family-calendar-123456-abcdef123456.json`.
Copy it in under the exact name the app expects (use your file's name):

```bash
mkdir -p secrets
cp ~/Downloads/family-calendar-123456-abcdef123456.json secrets/google-service-account.json
chmod 600 secrets/google-service-account.json
ls -l secrets/
```

You should see `google-service-account.json`. Check it's the right kind of file:

```bash
grep -o '"type": *"service_account"' secrets/google-service-account.json
grep -o '"client_email": *"[^"]*"' secrets/google-service-account.json
```

The first prints `"type": "service_account"`. The second prints the robot's email: it must be
the same address you shared **Poche Family** with in Google Calendar.

The key is a password for the calendar. The `secrets/` folder is ignored by git so it can't be
pushed by accident; don't email it around or put it anywhere else.

---

## 4. Fill in the settings (`.env`)

```bash
cp .env.example .env
nano .env
```

Find the line `GOOGLE_CALENDAR_ID=` and paste the Calendar ID after the `=`. You get it from
Google Calendar on a computer: hover **Poche Family > ⋮ > Settings and sharing > Integrate
calendar > Calendar ID**. It ends in `@group.calendar.google.com`. No quotes, no spaces:

```
GOOGLE_CALENDAR_ID=abc123def456@group.calendar.google.com
```

Everything else is already set for you, so leave it:

| Setting | Already set to |
| --- | --- |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | `/secrets/google-service-account.json` (the path *inside* the container, don't change it) |
| `TIMEZONE` | `America/Chicago` |
| `LATITUDE` / `LONGITUDE` | `30.2274` / `-90.7882` (ZIP 70774, St. Amant) |
| `TEMPERATURE_UNIT` | `fahrenheit` |
| `PEOPLE` | Mike, Bridget, Eppie Marie, Jordyn, Aaron (only used the very first time it starts; change colours and avatars later in ⚙ Settings) |
| Photo lines | blank for now; photos are optional, see [photos-setup.md](photos-setup.md) |

Save and exit nano: **Ctrl+O**, **Enter**, then **Ctrl+X**.

Double-check:

```bash
grep GOOGLE_CALENDAR_ID .env
```

---

## 5. Build and start it

```bash
docker compose up -d --build
```

The first time takes **5 to 10 minutes** (it downloads Node and Python and builds the screen).
Later starts take seconds. When it finishes you'll see `Container family-calendar  Started`.

Check it's running and connected to Google:

```bash
docker compose ps
curl -s localhost:8000/api/health; echo
```

What you want:

```json
{"mode":"google","last_sync":"2026-11-20T...","last_error":null}
```

- `"mode":"google"` and `"last_error":null`: it's syncing with Poche Family.
- `"mode":"demo"`: it can't see the key or the Calendar ID. See troubleshooting below.
- `last_sync` is `null` for the first few seconds; run the `curl` again.

---

## 6. Open it

On the PC, open a browser and go to **<http://localhost:8000>**.

You should see the week view with your real Poche Family events, the weather for St. Amant,
and the family chips along the top. Things to try:

- Add a test event (pick yourself as the person), then check it appears in Google Calendar on
  your phone within a few seconds. Delete it from either side; changes made in Google show on the
  wall within 5 minutes (or right away with `curl -X POST localhost:8000/api/sync`).
- Tabs for Chores, Marbles, Grocery and Meals.
- Press **F11** for full screen, like the wall will look.

It starts by itself whenever the PC boots (Docker is enabled at boot and the app is set to
`restart: unless-stopped`), so there's nothing to do after a reboot.

---

## 7. Phones (Tailscale is already set up on this PC)

**Quick test at home first:** on the PC, run `hostname -I`, then on a phone on the same Wi-Fi open
`http://<first number>:8000`, for example `http://192.168.1.42:8000`. If it doesn't load and you
use the `ufw` firewall, run `sudo ufw allow 8000/tcp`.

**Tailscale (works anywhere, recommended):**

1. In the Tailscale admin console, <https://login.tailscale.com/admin/dns>, make sure
   **MagicDNS** is on and click **Enable HTTPS** further down that page (one time).
2. On the PC:

   ```bash
   sudo tailscale serve --bg 8000
   ```

   It prints an address like `https://zorin-intel.tail1234.ts.net`. It keeps running after
   reboots. `tailscale serve status` shows it again later.
3. On each phone: install the **Tailscale** app, sign in, switch it on, and open that `https://`
   address. Then **Add to Home Screen** (iPhone: Share button; Android: ⋮ > Install app).

Full phone details are in [phone-setup.md](phone-setup.md).

> Again: `tailscale serve` is private to your Tailscale devices. **Never** `tailscale funnel`,
> and never a router port forward, because the app has no login.

---

## If something goes wrong

**See what the app is saying** (the most useful command):

```bash
docker compose logs --tail 100
# or follow it live, Ctrl+C to stop watching (the app keeps running):
docker compose logs -f
```

| What you see | What to do |
| --- | --- |
| `"mode":"demo"` | The key isn't at `secrets/google-service-account.json` or `GOOGLE_CALENDAR_ID` is blank. Check with `ls -l secrets/` and `grep GOOGLE_CALENDAR_ID .env`, fix, then `docker compose up -d`. |
| `last_error` mentions `404` or `Not Found` | The Calendar ID is wrong (copy it again, no spaces), or the calendar isn't shared with the service-account email from step 3. |
| `last_error` mentions `403` or `forbidden` / `accessNotConfigured` | The **Google Calendar API** isn't enabled in the Cloud project, or the share was "See all event details" instead of **Make changes to events**. |
| `last_error` mentions `invalid_grant` / `Invalid JWT` | The key was deleted in Google Cloud, or the PC clock is wrong. Make a new key (step 3) or run `timedatectl` to check the time. |
| `env file .env not found` | You're not in `~/family-calendar`, or skipped `cp .env.example .env`. |
| `permission denied ... docker.sock` | Log out and back in after the `usermod` line (step 1). |
| `port is already allocated` / `address already in use` on 8000 | Something else uses port 8000. `sudo ss -ltnp \| grep 8000` shows what. Or change the first number in `docker-compose.yml` (`"8080:8000"`) and use `localhost:8080`. |
| Build stops with a network or `npm ci` error | Usually a hiccup; run `docker compose up -d --build` again. |
| Page won't load at all | `docker compose ps` should show `family-calendar` as `Up`. If it keeps restarting, the logs say why. |

After changing `.env` or the key, restart with `docker compose up -d` (it picks up the change).
`docker compose restart` does **not** re-read `.env`.

---

## Everyday commands

Run these inside `~/family-calendar`:

| To | Run |
| --- | --- |
| Get new features after a PR is merged | `git pull && docker compose up -d --build` |
| Stop it | `docker compose down` |
| Start it again | `docker compose up -d` |
| Check health | `curl -s localhost:8000/api/health; echo` |
| Watch the logs | `docker compose logs -f` |

**Back up the `data/` folder.** It holds the database (chores, marble jars, grocery list,
meals, settings) and any slideshow photos. Calendar events live in Google, so they're safe
anyway. A simple copy works: `cp -r data ~/family-calendar-backup-$(date +%F)`.

---

## Next

- **Photos (optional):** [photos-setup.md](photos-setup.md). Do the one-time Google sign-in in
  a browser on this PC, since Google only allows `http://localhost` for that step.
- **Wall screen:** once you're happy with it on the PC, the Raspberry Pi can either run
  everything or just show this PC's app full-screen. See [pi-setup.md](pi-setup.md).
