"""Current conditions + 5-day forecast from Open-Meteo (free, no API key)."""

from __future__ import annotations

import time

import httpx

URL = "https://api.open-meteo.com/v1/forecast"
CACHE_SECONDS = 30 * 60

# WMO weather codes -> short label + icon name used by the UI
CODES = {
    0: ("Clear", "sun"), 1: ("Mostly clear", "sun"), 2: ("Partly cloudy", "cloud-sun"), 3: ("Cloudy", "cloud"),
    45: ("Fog", "fog"), 48: ("Fog", "fog"),
    51: ("Drizzle", "drizzle"), 53: ("Drizzle", "drizzle"), 55: ("Drizzle", "drizzle"),
    61: ("Rain", "rain"), 63: ("Rain", "rain"), 65: ("Heavy rain", "rain"),
    66: ("Freezing rain", "rain"), 67: ("Freezing rain", "rain"),
    71: ("Snow", "snow"), 73: ("Snow", "snow"), 75: ("Heavy snow", "snow"), 77: ("Snow", "snow"),
    80: ("Showers", "rain"), 81: ("Showers", "rain"), 82: ("Heavy showers", "rain"),
    85: ("Snow showers", "snow"), 86: ("Snow showers", "snow"),
    95: ("Thunderstorm", "storm"), 96: ("Thunderstorm", "storm"), 99: ("Thunderstorm", "storm"),
}


def describe(code: int) -> tuple[str, str]:
    return CODES.get(code, ("", "cloud"))


class Weather:
    def __init__(self, latitude: str, longitude: str, timezone: str, unit: str):
        self.params = {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "temperature_unit": unit,
            "current": "temperature_2m,weather_code",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "forecast_days": 5,
        }
        self.enabled = bool(latitude and longitude)
        self._cache: tuple[float, dict] | None = None

    async def get(self) -> dict | None:
        if not self.enabled:
            return None
        if self._cache and time.monotonic() - self._cache[0] < CACHE_SECONDS:
            return self._cache[1]
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(URL, params=self.params)
                resp.raise_for_status()
                raw = resp.json()
        except httpx.HTTPError:
            return self._cache[1] if self._cache else None
        data = self.shape(raw)
        self._cache = (time.monotonic(), data)
        return data

    @staticmethod
    def shape(raw: dict) -> dict:
        cur = raw["current"]
        label, icon = describe(cur["weather_code"])
        d = raw["daily"]
        days = []
        for i, date in enumerate(d["time"]):
            dl, di = describe(d["weather_code"][i])
            days.append({
                "date": date,
                "high": round(d["temperature_2m_max"][i]),
                "low": round(d["temperature_2m_min"][i]),
                "precip": d["precipitation_probability_max"][i],
                "label": dl,
                "icon": di,
            })
        return {"temperature": round(cur["temperature_2m"]), "label": label, "icon": icon, "days": days}
