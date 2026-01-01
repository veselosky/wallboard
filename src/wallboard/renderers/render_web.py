from __future__ import annotations

from pathlib import Path
import json
import os
from playwright.sync_api import sync_playwright

from ..dashboard import DashboardData

HTML_TEMPLATE = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Wallboard</title>
  <style>
    :root {{
      --bg: {bg};
      --fg: {fg};
      --fg-dim: {fg_dim};
      --border: {border};
      --alert: {alert};
      --gap: {gap}px;
      --pad: {pad}px;
      --radius: {radius}px;
      --cols: {cols};
      --font: ui-monospace, Menlo, Monaco, "DejaVu Sans Mono", "Liberation Mono", monospace;
    }}
    html, body {{
      margin: 0;
      width: {w}px;
      height: {h}px;
      background: var(--bg);
      color: var(--fg);
      font-family: var(--font);
      overflow: hidden;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(var(--cols), 1fr);
      gap: var(--gap);
      padding: var(--pad);
      box-sizing: border-box;
      width: 100%;
      height: 100%;
    }}
    .card {{
      border: 2px solid var(--border);
      border-radius: var(--radius);
      padding: 16px;
      box-sizing: border-box;
      position: relative;
    }}
    .title {{
      font-size: 22px;
      margin: 0 0 10px 0;
      color: var(--fg);
      text-shadow: 0 0 10px rgba(0, 255, 102, 0.35);
    }}
    .title.bad {{
      color: var(--alert);
      text-shadow: 0 0 10px rgba(255, 51, 85, 0.35);
    }}
    .line {{
      color: var(--fg-dim);
      font-size: 16px;
      line-height: 1.35;
      white-space: pre;
    }}
    .scanlines::before {{
      content: "";
      pointer-events: none;
      position: fixed;
      inset: 0;
      background: repeating-linear-gradient(
        to bottom,
        rgba(0,0,0,0.10),
        rgba(0,0,0,0.10) 1px,
        rgba(0,0,0,0.00) 4px
      );
      mix-blend-mode: multiply;
    }}
  </style>
</head>
<body class="scanlines">
  <div class="grid" id="grid"></div>

  <script>
    const data = {data_json};

    function linesForWidget(w) {{
      if (!w.ok) {{
        const out = ["ERROR"];
        if (w.error) out.push(w.error.slice(0, 120));
        return out;
      }}
      const d = w.data || {{}};
      switch (w.name) {{
        case "clock":
          return [d.time || "", d.date || ""];
        case "weather": {{
          const out = [];
          if (d.location) out.push(d.location);
          if (d.temp != null) out.push(`Temp: ${{d.temp}}  Feels: ${{d.feels_like}}`);
          if (d.wind != null) out.push(`Wind: ${{d.wind}}`);
          const t = d.hourly_time || [];
          const tt = d.hourly_temp || [];
          const pop = d.hourly_pop || [];
          if (t.length && tt.length) {{
            out.push("Next hours:");
            for (let i = 0; i < Math.min(6, t.length, tt.length, pop.length); i++) {{
              const hhmm = String(t[i]).slice(11, 16);
              out.push(`${{hhmm}}  ${{tt[i]}}  POP ${{pop[i]}}%`);
            }}
          }}
          return out;
        }}
        case "calendar": {{
          const ev = d.events || [];
          if (!ev.length) return ["No upcoming events"];
          return ev.map(e => `${{e.time}}  ${{String(e.summary).slice(0, 60)}}`);
        }}
        case "system": {{
          const out = [];
          out.push(`CPU: ${{d.cpu_pct}}%`);
          out.push(`Mem: ${{d.mem_pct}}% (${{d.mem_used_gb}} / ${{d.mem_total_gb}} GB)`);
          for (const dk of (d.disks || [])) {{
            out.push(`Disk ${{dk.mount}}: ${{dk.pct}}% (free ${{dk.free_gb}} GB)`);
          }}
          return out;
        }}
        default:
          return [JSON.stringify(d).slice(0, 120)];
      }}
    }}

    const grid = document.getElementById("grid");
    for (const w of data.results) {{
      const card = document.createElement("div");
      card.className = "card";

      const title = document.createElement("div");
      title.className = "title" + (w.ok ? "" : " bad");
      title.textContent = w.title || w.name;
      card.appendChild(title);

      for (const ln of linesForWidget(w)) {{
        const div = document.createElement("div");
        div.className = "line";
        div.textContent = ln;
        card.appendChild(div);
      }}

      grid.appendChild(card);
    }}
  </script>
</body>
</html>
"""

def render(
    out_path: Path,
    dash: DashboardData,
    resolution: tuple[int, int],
    columns: int,
    theme: dict,
    web_cfg: dict,
) -> Path:
    w, h = resolution
    pad = max(24, w // 80)
    gap = max(18, w // 120)
    radius = 22

    payload = {
        "results": [
            {
                "name": r.name,
                "title": r.title,
                "ok": r.ok,
                "error": r.error,
                "data": r.data,
            }
            for r in dash.results
        ]
    }

    html = HTML_TEMPLATE.format(
        w=w, h=h,
        cols=max(1, columns),
        pad=pad, gap=gap, radius=radius,
        bg=theme.get("background", "#020402"),
        fg=theme.get("foreground", "#00ff66"),
        fg_dim=theme.get("foreground_dim", "#00aa44"),
        border=theme.get("panel_border", "#00aa44"),
        alert=theme.get("alert", "#ff3355"),
        data_json=json.dumps(payload),
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_html = out_path.with_suffix(".html")
    tmp_html.write_text(html, encoding="utf-8")

    scale = float(web_cfg.get("viewport_device_scale_factor", 1))
    headless = bool(web_cfg.get("headless", True))
    browser_name = str(web_cfg.get("browser", "chromium"))

    with sync_playwright() as p:
        browser = getattr(p, browser_name).launch(headless=headless)
        page = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=scale)
        page.goto(tmp_html.as_uri())
        page.wait_for_timeout(250)  # small settle time for JS layout
        page.screenshot(path=str(out_path), full_page=False)
        browser.close()

    return out_path
