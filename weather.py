"""
weather.py — Fetch current weather from OpenWeatherMap and cache it.

The result is cached to /tmp for one hour so that the Pi does not make a
network request on every display update.

Requires WEATHER_API_KEY and WEATHER_LOCATION to be set in config.py.
Returns None silently when the feature is disabled or unavailable.
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path
from typing import Optional

import config

_CACHE_FILE = Path("/tmp/photoframe_weather.json")
_CACHE_TTL  = 3600  # seconds

# Map the first two characters of an OWM icon code to a short description
_ICON_MAP = {
    "01": "Sunny",
    "02": "Mostly Sunny",
    "03": "Cloudy",
    "04": "Overcast",
    "09": "Showers",
    "10": "Rain",
    "11": "Thunderstorm",
    "13": "Snow",
    "50": "Foggy",
}


def _load_cache() -> Optional[str]:
    try:
        if _CACHE_FILE.exists():
            data = json.loads(_CACHE_FILE.read_text())
            if time.time() - data.get("_ts", 0) < _CACHE_TTL:
                return data.get("summary")
    except Exception:
        pass
    return None


def _save_cache(summary: str) -> None:
    try:
        _CACHE_FILE.write_text(json.dumps({"summary": summary, "_ts": time.time()}))
    except Exception:
        pass


def get_weather() -> Optional[str]:
    """
    Return a short weather string such as ``"Rain  14°C"``, or ``None``.

    Returns None when SHOW_WEATHER is False, when the API key / location are
    not configured, or when the network request fails.
    """
    if not config.SHOW_WEATHER:
        return None
    if not config.WEATHER_API_KEY or not config.WEATHER_LOCATION:
        return None

    cached = _load_cache()
    if cached:
        return cached

    try:
        url = (
            "https://api.openweathermap.org/data/2.5/weather"
            f"?q={config.WEATHER_LOCATION}"
            f"&appid={config.WEATHER_API_KEY}"
            f"&units={config.WEATHER_UNITS}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "photoframe/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())

        temp        = round(data["main"]["temp"])
        icon_code   = data["weather"][0]["icon"][:2]
        description = _ICON_MAP.get(icon_code, data["weather"][0]["main"])
        unit_symbol = "°C" if config.WEATHER_UNITS == "metric" else "°F"
        summary     = f"{description}  {temp}{unit_symbol}"

        _save_cache(summary)
        return summary

    except Exception:
        return None
