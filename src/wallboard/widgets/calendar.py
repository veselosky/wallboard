from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import os

from dateutil import parser as dtparser
from icalendar import Calendar
import caldav

from .base import WidgetResult

name = "calendar"
title = "Today"

def _expand(path: str) -> str:
    return os.path.expanduser(os.path.expandvars(path))

def _parse_ics_events(ics_text: str) -> list[dict]:
    cal = Calendar.from_ical(ics_text)
    events = []
    for component in cal.walk():
        if component.name != "VEVENT":
            continue
        dtstart = component.get("dtstart")
        dtend = component.get("dtend")
        summary = component.get("summary")
        if not dtstart or not summary:
            continue

        start = dtstart.dt
        end = dtend.dt if dtend else None

        # Normalize to datetime
        if isinstance(start, datetime):
            start_dt = start
        else:
            start_dt = datetime.combine(start, datetime.min.time())

        if end is None:
            end_dt = None
        elif isinstance(end, datetime):
            end_dt = end
        else:
            end_dt = datetime.combine(end, datetime.min.time())

        events.append({
            "summary": str(summary),
            "start": start_dt,
            "end": end_dt,
        })
    return events

def _load_from_ics(path: str) -> list[dict]:
    p = Path(_expand(path))
    if not p.exists():
        return []
    return _parse_ics_events(p.read_text(encoding="utf-8"))

def _load_from_caldav(url: str, username: str, password: str) -> list[dict]:
    client = caldav.DAVClient(url=url, username=username, password=password)
    principal = client.principal()
    calendars = principal.calendars()
    if not calendars:
        return []
    cal = calendars[0]
    results = cal.date_search(
        start=datetime.now(timezone.utc) - timedelta(days=1),
        end=datetime.now(timezone.utc) + timedelta(days=1),
    )
    events = []
    for r in results:
        ics = r.data
        events.extend(_parse_ics_events(ics))
    return events

def collect(cfg: dict) -> WidgetResult:
    try:
        ccfg = cfg.get("calendar", {})
        source = str(ccfg.get("source", "ics")).lower()
        horizon_hours = int(ccfg.get("horizon_hours", 12))
        max_events = int(ccfg.get("max_events", 5))

        now = datetime.now().astimezone()
        horizon = now + timedelta(hours=horizon_hours)

        if source == "ics":
            events = _load_from_ics(str(ccfg.get("ics_path", "")))
        elif source == "caldav":
            url = str(ccfg.get("caldav_url", "")).strip()
            user = str(ccfg.get("caldav_username", "")).strip()
            pw = str(ccfg.get("caldav_password", "")).strip()
            if not (url and user and pw):
                return WidgetResult(name=name, title=title, data={}, ok=False, error="CalDAV configured but missing url/username/password")
            events = _load_from_caldav(url, user, pw)
        else:
            return WidgetResult(name=name, title=title, data={}, ok=False, error=f"Unknown calendar.source: {source}")

        # Filter to “upcoming today-ish”
        upcoming = []
        for e in events:
            start = e["start"]
            if start.tzinfo is None:
                start = start.replace(tzinfo=now.tzinfo)
            if now <= start <= horizon:
                upcoming.append({
                    "summary": e["summary"],
                    "start": start,
                })

        upcoming.sort(key=lambda x: x["start"])
        upcoming = upcoming[:max_events]

        return WidgetResult(
            name=name,
            title=title,
            data={
                "events": [
                    {"time": ev["start"].strftime("%H:%M"), "summary": ev["summary"]}
                    for ev in upcoming
                ]
            },
        )
    except Exception as e:
        return WidgetResult(name=name, title=title, data={}, ok=False, error=str(e))
