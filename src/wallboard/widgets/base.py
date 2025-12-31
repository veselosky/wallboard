from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Any

@dataclass(frozen=True)
class WidgetResult:
    name: str
    title: str
    data: dict[str, Any]
    ok: bool = True
    error: str | None = None
    stale: bool = False

class Widget(Protocol):
    name: str
    title: str

    def collect(self, cfg: dict) -> WidgetResult:
        ...
