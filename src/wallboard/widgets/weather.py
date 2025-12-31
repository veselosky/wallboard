from __future__ import annotations

import requests
from .base import WidgetResult

name = "weather"
title = "Weather"

def _zip_to_latlon(zip_code: str) -> tuple[float, float, str]:
    # US-only, no key. If you want international later, swap this out.
    r = requests.get(f"https://api.zippopotam.us/us/{zip_code}", timeout=8)
    r.raise_for_status()
    js = r.json()
    place = js["places"][0]
    lat = float(place["latitude"])
    lon = float(place["longitude"])
    label = f'{place["place name"]}, {place["state abbreviation"]}'
    return lat, lon, label

def collect(cfg: dict) -> WidgetResult:
    try:
        wcfg = cfg.get("weather", {})
        zip_code = str(wcfg.get("zip_code", "")).strip()
        if not zip_code:
            return WidgetResult(name=name, title=title, data={}, ok=False, error="weather.zip_code not set")

        units = str(wcfg.get("units", "imperial")).lower()
        lat, lon, label = _zip_to_latlon(zip_code)

        # Open-Meteo: current + hourly
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
            "hourly": "temperature_2m,precipitation_probability,precipitation",
            "forecast_days": 1,
            "timezone": "auto",
        }
        if units == "imperial":
            params.update({"temperature_unit": "fahrenheit", "wind_speed_unit": "mph", "precipitation_unit": "inch"})

        r = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=10)
        r.raise_for_status()
        js = r.json()

        current = js.get("current", {})
        hourly = js.get("hourly", {})

        # keep it simple for baseline
        return WidgetResult(
            name=name,
            title=title,
            data={
                "location": label,
                "temp": current.get("temperature_2m"),
                "feels_like": current.get("apparent_temperature"),
                "wind": current.get("wind_speed_10m"),
                "precip": current.get("precipitation"),
                "hourly_time": (hourly.get("time") or [])[:6],
                "hourly_temp": (hourly.get("temperature_2m") or [])[:6],
                "hourly_pop": (hourly.get("precipitation_probability") or [])[:6],
            },
        )
    except Exception as e:
        return WidgetResult(name=name, title=title, data={}, ok=False, error=str(e))
