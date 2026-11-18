# Photo screensaver

After a few minutes without a touch (`SCREENSAVER_MINUTES`, default 5), the wall shows a full-screen
slideshow with a clock. Tap anywhere to get back to the calendar. Photos come from two places:

- **Google Photos**, through Google's Photo Picker: you choose photos on your phone and the app
  keeps copies. Since March 2025, Google no longer lets apps read a whole library or follow an
  album, so photos you add to Google Photos later need to be picked again.
- **Any image copied into `data/photos/`** on the machine running the backend (jpg, png, webp).

## One-time Google setup (about 10 minutes)

Use the same Google Cloud project as the calendar service account.

1. **APIs & Services > Library**: enable **Photos Picker API**.
2. **APIs & Services > OAuth consent screen** (called **Google Auth Platform** in newer consoles):
   - User type **External**, app name `Family Calendar`, your email for support and developer contact.
   - Scopes: add `.../auth/photospicker.mediaitems.readonly`.
   - Audience: add your Google account as a **test user**, then click **Publish app** so it shows
     **In production**. (While it is in "Testing", Google expires the sign-in after 7 days. Since it is
     unverified, the sign-in page shows a "Google hasn't verified this app" warning. Click
     **Advanced > Go to Family Calendar**. That's expected for a personal app.)
3. **Credentials > Create credentials > OAuth client ID**:
   - Application type **Web application**.
   - Authorised redirect URI: `http://localhost:8000/api/photos/auth/callback`
4. Copy the client ID and secret into `.env`:

   ```bash
   GOOGLE_OAUTH_CLIENT_ID=....apps.googleusercontent.com
   GOOGLE_OAUTH_CLIENT_SECRET=...
   PUBLIC_URL=http://localhost:8000
   ```

   then `docker compose up -d`.

> Google only allows plain `http://` redirect addresses for `localhost`. So do the one-time sign-in
> **on the wall screen itself** (when the Pi runs the backend), or in a browser on the Linux PC
> (when the PC runs the backend). After that, picking photos works from any phone.

## Picking photos

1. On the wall: **⚙ Settings > Photos > Connect Google Photos**, then sign in. You only do this once.
2. Tap **Choose photos**. A QR code appears. Scan it with a phone that's signed in to the same
   Google account, pick photos, and tap **Done**. Or tap **Or choose on this screen**.
3. The wall copies them (up to 2048 px) into `data/photos/` and they join the slideshow. Remove any
   photo with its ×, or all of them with **Remove all**. **Preview slideshow** starts it right away.

Videos are skipped for now.
