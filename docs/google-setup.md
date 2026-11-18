# Connecting the "Poche Family" Google calendar

The app talks to Google with a **service account**: a robot Google identity that you share the
calendar with. No sign-in screen, and no tokens that expire every 7 days. About 10 minutes.

## 1. Create the service account

1. Go to <https://console.cloud.google.com/> and create a project (for example `family-calendar`).
2. **APIs & Services > Library**: search for **Google Calendar API** and click **Enable**.
3. **IAM & Admin > Service Accounts > Create service account**. Name it `family-calendar`. Skip the
   optional role and user steps.
4. Open the new service account, go to **Keys > Add key > Create new key > JSON**. A `.json` file downloads.
5. Copy its email address (looks like `family-calendar@<project>.iam.gserviceaccount.com`).

> Some Google Cloud accounts block key creation by policy (`iam.disableServiceAccountKeyCreation`).
> Personal Gmail accounts normally don't. If you see that error, tell Claude and we'll switch to OAuth.

## 2. Share the calendar with it

1. In Google Calendar on a computer, hover **Poche Family** > **⋮ > Settings and sharing**.
2. **Share with specific people or groups > Add people**: paste the service account email,
   set permission to **Make changes to events**, click **Send**.
3. On the same page, under **Integrate calendar**, copy the **Calendar ID**
   (ends in `@group.calendar.google.com`).

## 3. Give both to the app

On the machine running the backend (the Pi, or the Linux PC):

```bash
cd family-calendar
mkdir -p secrets
cp ~/Downloads/<downloaded-key>.json secrets/google-service-account.json
cp .env.example .env
nano .env        # set GOOGLE_CALENDAR_ID=...@group.calendar.google.com
docker compose up -d --build
curl localhost:8000/api/health   # "mode": "google" and "last_error": null means it's syncing
```

The key file is a password for that calendar: it stays in `secrets/`, which git ignores. Never commit it.

## Who an event belongs to

Everyone shares one calendar, so the owner comes from the title:

| Title | Shows as |
| --- | --- |
| `Mike: Dentist` | Mike's colour |
| `[Ava] Soccer` | Ava's colour |
| `Ava & Mike: Recital` | first name listed (Ava) |
| `Trash day` | grey, everyone |

Picking a person on the wall screen adds the `Name: ` prefix for you, so it also shows up that way
in Google Calendar on your phones.
