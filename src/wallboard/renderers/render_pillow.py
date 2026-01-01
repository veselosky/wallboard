from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import math

from ..dashboard import DashboardData

def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i:i+2], 16) for i in (0, 2, 4))

def _load_font(theme: dict, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    # Allow explicit font_path, else try family name
    font_path = theme.get("font_path")
    try:
        if font_path:
            fp = os.path.expanduser(font_path)
            return ImageFont.truetype(fp, size=size)
        # This usually works on Ubuntu for DejaVuSansMono
        family = theme.get("font_family", "DejaVuSansMono")
        return ImageFont.truetype(f"{family}.ttf", size=size)
    except Exception:
        return ImageFont.load_default()

@dataclass(frozen=True)
class Layout:
    width: int
    height: int
    columns: int
    gap: int
    margin: int
    cell_w: int
    cell_h: int
    rows: int

def _compute_layout(width: int, height: int, columns: int, n: int) -> Layout:
    margin = max(24, width // 80)
    gap = max(18, width // 120)
    cols = max(1, columns)
    rows = max(1, math.ceil(n / cols))
    cell_w = (width - 2 * margin - (cols - 1) * gap) // cols
    cell_h = (height - 2 * margin - (rows - 1) * gap) // rows
    return Layout(width, height, cols, gap, margin, cell_w, cell_h, rows)

def _scanlines(img: Image.Image, strength: int = 18) -> Image.Image:
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for y in range(0, h, 4):
        d.rectangle([0, y, w, y+1], fill=(0, 0, 0, strength))
    return Image.alpha_composite(img.convert("RGBA"), overlay)

def _draw_glow_text(img: Image.Image, draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font, fill_rgb, glow_rgb, glow_radius: int = 8):
    # Render glow on a temp layer and blur it
    x, y = xy
    # Create small temp image around text
    tw, th = draw.textbbox((0, 0), text, font=font)[2:]
    pad = glow_radius * 2
    tmp = Image.new("RGBA", (tw + pad*2, th + pad*2), (0, 0, 0, 0))
    td = ImageDraw.Draw(tmp)
    td.text((pad, pad), text, font=font, fill=(*glow_rgb, 120))
    tmp = tmp.filter(ImageFilter.GaussianBlur(radius=glow_radius))
    # Paste glow (with alpha) then crisp text on main image
    img.paste(tmp, (x - pad, y - pad), tmp)
    draw.text((x, y), text, font=font, fill=fill_rgb)

def render(
    out_path: Path,
    dash: DashboardData,
    resolution: tuple[int, int],
    columns: int,
    theme: dict,
) -> Path:
    w, h = resolution
    bg = _hex(theme.get("background", "#020402"))
    fg = _hex(theme.get("foreground", "#00ff66"))
    fg_dim = _hex(theme.get("foreground_dim", "#00aa44"))
    border = _hex(theme.get("panel_border", "#00aa44"))
    alert = _hex(theme.get("alert", "#ff3355"))

    img = Image.new("RGBA", (w, h), (*bg, 255))
    draw = ImageDraw.Draw(img)

    n = max(1, len(dash.results))
    layout = _compute_layout(w, h, columns, n)

    font_h = _load_font(theme, size=max(20, w // 90))
    font_b = _load_font(theme, size=max(16, w // 120))
    font_s = _load_font(theme, size=max(14, w // 140))

    for i, res in enumerate(dash.results):
        r = i // layout.columns
        c = i % layout.columns
        x0 = layout.margin + c * (layout.cell_w + layout.gap)
        y0 = layout.margin + r * (layout.cell_h + layout.gap)
        x1 = x0 + layout.cell_w
        y1 = y0 + layout.cell_h

        # Panel
        draw.rounded_rectangle([x0, y0, x1, y1], radius=18, outline=border, width=2)

        # Header
        header = res.title
        header_color = fg if res.ok else alert
        _draw_glow_text(img, draw, (x0 + 16, y0 + 12), header, font_h, header_color, fg, glow_radius=6)

        # Body lines
        lines: list[str] = []
        if not res.ok:
            lines.append("ERROR")
            if res.error:
                lines.append(res.error[:80])
        else:
            # very baseline formatting; refine later per-widget
            if res.name == "clock":
                lines.append(res.data.get("time", ""))
                lines.append(res.data.get("date", ""))
            elif res.name == "weather":
                loc = res.data.get("location", "")
                temp = res.data.get("temp")
                feels = res.data.get("feels_like")
                wind = res.data.get("wind")
                lines.append(loc)
                if temp is not None:
                    lines.append(f"Temp: {temp}  Feels: {feels}")
                if wind is not None:
                    lines.append(f"Wind: {wind}")
                # mini hourly strip
                ht = res.data.get("hourly_time", [])
                htemp = res.data.get("hourly_temp", [])
                hpop = res.data.get("hourly_pop", [])
                if ht and htemp:
                    lines.append("Next hours:")
                    for t, tt, pop in zip(ht, htemp, hpop):
                        # t is ISO string from API, keep just HH:MM
                        hhmm = str(t)[11:16]
                        lines.append(f"{hhmm}  {tt}  POP {pop}%")
            elif res.name == "calendar":
                ev = res.data.get("events", [])
                if not ev:
                    lines.append("No upcoming events")
                else:
                    for e in ev:
                        lines.append(f'{e["time"]}  {e["summary"][:40]}')
            elif res.name == "system":
                lines.append(f'CPU: {res.data.get("cpu_pct")}%')
                lines.append(f'Mem: {res.data.get("mem_pct")}% ({res.data.get("mem_used_gb")} / {res.data.get("mem_total_gb")} GB)')
                for dsk in res.data.get("disks", []):
                    lines.append(f'Disk {dsk["mount"]}: {dsk["pct"]}% (free {dsk["free_gb"]} GB)')
            else:
                lines.append(str(res.data)[:120])

        y = y0 + 58
        for ln in lines[:18]:
            draw.text((x0 + 16, y), ln, font=font_b, fill=fg_dim)
            y += 22

    img = _scanlines(img, strength=18)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out_path, format="PNG")
    return out_path
