from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from .widgets import REGISTRY
from .widgets.base import WidgetResult

@dataclass(frozen=True)
class DashboardData:
    results: list[WidgetResult]

def collect_all(cfg_raw: dict, widget_order: list[str]) -> DashboardData:
    results: list[WidgetResult] = []
    for name in widget_order:
        mod = REGISTRY.get(name)
        if mod is None:
            results.append(WidgetResult(name=name, title=name, data={}, ok=False, error="Unknown widget"))
            continue
        try:
            results.append(mod.collect(cfg_raw))
        except Exception as e:
            results.append(WidgetResult(name=name, title=getattr(mod, "title", name), data={}, ok=False, error=str(e)))
    return DashboardData(results=results)
