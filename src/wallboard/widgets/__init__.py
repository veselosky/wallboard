from __future__ import annotations

from . import clock, system, weather, calendar

REGISTRY = {
    clock.name: clock,
    system.name: system,
    weather.name: weather,
    calendar.name: calendar,
}
