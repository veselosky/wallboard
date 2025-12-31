from __future__ import annotations

from pathlib import Path
from ..dashboard import DashboardData

from . import render_pillow, render_web

def render_with(
    kind: str,
    out_path: Path,
    dash: DashboardData,
    resolution: tuple[int, int],
    columns: int,
    theme: dict,
    web_cfg: dict,
) -> Path:
    kind = kind.lower().strip()
    if kind == "pillow":
        return render_pillow.render(out_path, dash, resolution, columns, theme)
    if kind == "web":
        return render_web.render(out_path, dash, resolution, columns, theme, web_cfg)
    raise ValueError(f"Unknown renderer: {kind}")
