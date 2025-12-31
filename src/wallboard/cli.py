from __future__ import annotations

import argparse
from .config import load_config
from .dashboard import collect_all
from .wallpaper import set_gnome_wallpaper
from .renderers import render_with

def main() -> None:
    ap = argparse.ArgumentParser(prog="wallboard")
    ap.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    ap.add_argument("--renderer", choices=["pillow", "web"], help="Override renderer.kind from config")
    ap.add_argument("--no-set", action="store_true", help="Do not set GNOME wallpaper")
    args = ap.parse_args()

    cfg = load_config(args.config)
    raw = cfg.raw

    renderer = args.renderer or cfg.renderer_kind
    order = cfg.widget_order

    dash = collect_all(raw, order)
    out_path = cfg.output_path

    theme = raw.get("theme", {})
    web_cfg = raw.get("web_renderer", {})

    rendered = render_with(renderer, out_path, dash, cfg.resolution, cfg.columns, theme, web_cfg)

    if cfg.set_gnome_wallpaper and not args.no_set:
        set_gnome_wallpaper(rendered)
