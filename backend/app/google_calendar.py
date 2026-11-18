"""Google Calendar access through a service account.

The service account's email is shared on the family calendar with
"Make changes to events", so no OAuth consent screen or refresh tokens are involved.
See docs/google-setup.md.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


class GoogleCalendar:
    def __init__(self, service_account_file: str, calendar_id: str):
        creds = service_account.Credentials.from_service_account_file(service_account_file, scopes=SCOPES)
        self._service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        self.calendar_id = calendar_id

    def list_window(self, days_back: int, days_ahead: int) -> tuple[str, str, list[dict]]:
        """All event instances (recurring ones expanded) in [now - days_back, now + days_ahead]."""
        now = datetime.now(timezone.utc)
        t_min = (now - timedelta(days=days_back)).replace(hour=0, minute=0, second=0, microsecond=0)
        t_max = (now + timedelta(days=days_ahead)).replace(hour=0, minute=0, second=0, microsecond=0)
        items: list[dict] = []
        page_token = None
        while True:
            resp = (
                self._service.events()
                .list(
                    calendarId=self.calendar_id,
                    timeMin=t_min.isoformat(),
                    timeMax=t_max.isoformat(),
                    singleEvents=True,
                    showDeleted=False,
                    maxResults=2500,
                    pageToken=page_token,
                )
                .execute()
            )
            items.extend(resp.get("items", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        fmt = "%Y-%m-%dT%H:%M:%SZ"
        return t_min.strftime(fmt), t_max.strftime(fmt), items

    def insert(self, body: dict) -> dict:
        return self._service.events().insert(calendarId=self.calendar_id, body=body).execute()

    def patch(self, event_id: str, body: dict) -> dict:
        return self._service.events().patch(calendarId=self.calendar_id, eventId=event_id, body=body).execute()

    def delete(self, event_id: str) -> None:
        self._service.events().delete(calendarId=self.calendar_id, eventId=event_id).execute()
