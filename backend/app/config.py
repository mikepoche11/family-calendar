"""Settings, read from environment variables (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(_env("DATA_DIR", "./data")))
    timezone: str = field(default_factory=lambda: _env("TIMEZONE", "America/Chicago"))

    # Google Calendar (service account shared on the family calendar)
    google_calendar_id: str = field(default_factory=lambda: _env("GOOGLE_CALENDAR_ID"))
    google_service_account_file: str = field(
        default_factory=lambda: _env("GOOGLE_SERVICE_ACCOUNT_FILE", "/secrets/google-service-account.json")
    )
    sync_interval_seconds: int = field(default_factory=lambda: int(_env("SYNC_INTERVAL_SECONDS", "300")))
    sync_days_back: int = field(default_factory=lambda: int(_env("SYNC_DAYS_BACK", "35")))
    sync_days_ahead: int = field(default_factory=lambda: int(_env("SYNC_DAYS_AHEAD", "180")))

    # Weather (Open-Meteo, no key needed)
    latitude: str = field(default_factory=lambda: _env("LATITUDE"))
    longitude: str = field(default_factory=lambda: _env("LONGITUDE"))
    temperature_unit: str = field(default_factory=lambda: _env("TEMPERATURE_UNIT", "fahrenheit"))

    # "Name:#hexcolor,Name2:#hexcolor" — seeds the people table on first start only
    people_seed: str = field(default_factory=lambda: _env("PEOPLE", "Family:#64748b"))

    # Serve the built wall UI from here when it exists
    static_dir: Path = field(default_factory=lambda: Path(_env("STATIC_DIR", "./static")))

    @property
    def db_path(self) -> Path:
        return self.data_dir / "calendar.db"

    @property
    def google_enabled(self) -> bool:
        return bool(self.google_calendar_id) and Path(self.google_service_account_file).is_file()

    @property
    def demo_mode(self) -> bool:
        """No Google credentials: run with local sample events so the UI can be developed."""
        return not self.google_enabled


def get_settings() -> Settings:
    return Settings()
