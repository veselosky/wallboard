from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import yaml

SUPPORTED_RESOLUTIONS = {
    "1920x1080": (1920, 1080),
    "3840x2160": (3840, 2160),
    "2560x1600": (2560, 1600),
}

def _expand(path: str) -> str:
    return os.path.expanduser(os.path.expandvars(path))

@dataclass(frozen=True)
class Config:
    raw: dict

    @property
    def resolution(self) -> tuple[int, int]:
        res = self.raw.get("resolution", "1920x1080")
        if res not in SUPPORTED_RESOLUTIONS:
            raise ValueError(f"Unsupported resolution {res!r}. Supported: {list(SUPPORTED_RESOLUTIONS)}")
        return SUPPORTED_RESOLUTIONS[res]

    @property
    def columns(self) -> int:
        return int(self.raw.get("columns", 3))

    @property
    def output_path(self) -> Path:
        out = self.raw.get("output", {}).get("path", "~/.cache/wallboard/wallpaper.png")
        return Path(_expand(out))

    @property
    def set_gnome_wallpaper(self) -> bool:
        return bool(self.raw.get("output", {}).get("set_gnome_wallpaper", False))

    @property
    def renderer_kind(self) -> str:
        return str(self.raw.get("renderer", {}).get("kind", "pillow"))

    @property
    def widget_order(self) -> list[str]:
        return list(self.raw.get("dashboard", {}).get("widgets", ["clock", "weather", "calendar", "system"]))

def load_config(path: str | Path) -> Config:
    p = Path(_expand(str(path)))
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("config.yaml must contain a YAML mapping at top level.")
    return Config(raw=raw)
