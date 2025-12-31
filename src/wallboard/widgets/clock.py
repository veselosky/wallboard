from __future__ import annotations

from datetime import datetime
from .base import WidgetResult

name = "clock"
title = "Time"

def collect(cfg: dict) -> WidgetResult:
    now = datetime.now()
    return WidgetResult(
        name=name,
        title=title,
        data={
            "time": now.strftime("%H:%M"),
            "date": now.strftime("%a %b %d, %Y"),
        },
    )
