from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import requests
from platformdirs import user_cache_dir

from .base import WidgetResult

name = "weather"
title = "Weather"


# Cache utilities
def _get_cache_dir() -> Path:
    d = Path(user_cache_dir("wallboard"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_load_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _cache_save_json(path: Path, obj) -> None:
    try:
        with path.open("w", encoding="utf-8") as fh:
            json.dump(obj, fh)
    except Exception:
        return


def _params_hash(url: str, params: dict) -> str:
    # Stable serialization of params
    s = json.dumps({"url": url, "params": params}, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _zip_to_latlon(zip_code: str) -> tuple[float, float, str]:
    # US-only, no key. If you want international later, swap this out.
    cache_dir = _get_cache_dir()
    cache_path = cache_dir / f"zip_{zip_code}.json"
    cached = _cache_load_json(cache_path)
    if cached:
        try:
            return float(cached["lat"]), float(cached["lon"]), str(cached["label"])
        except Exception:
            pass

    r = requests.get(f"https://api.zippopotam.us/us/{zip_code}", timeout=8)
    r.raise_for_status()
    js = r.json()
    place = js["places"][0]
    lat = float(place["latitude"])
    lon = float(place["longitude"])
    label = f'{place["place name"]}, {place["state abbreviation"]}'

    # save cache (no expiration)
    _cache_save_json(cache_path, {"lat": lat, "lon": lon, "label": label})
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

        # caching: compute key from URL+params and honor configurable expiration
        cache_dir = _get_cache_dir()
        expire_seconds = int(wcfg.get("cache_expire_seconds", 3600))
        url = "https://api.open-meteo.com/v1/forecast"
        key = _params_hash(url, params)
        cache_path = cache_dir / f"om_{key}.json"
        cached = _cache_load_json(cache_path)
        if cached and isinstance(cached, dict) and (time.time() - float(cached.get("ts", 0)) < expire_seconds):
            js = cached.get("resp", {})
        else:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            js = r.json()
            try:
                _cache_save_json(cache_path, {"ts": time.time(), "resp": js})
            except Exception:
                pass

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
