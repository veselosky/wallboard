from __future__ import annotations

import shutil
import psutil
from .base import WidgetResult

name = "system"
title = "System"

def collect(cfg: dict) -> WidgetResult:
    # Disk usage for / and /home if they exist
    mounts = ["/", "/home"]
    disks = []
    for m in mounts:
        try:
            du = shutil.disk_usage(m)
            disks.append({
                "mount": m,
                "used_gb": round(du.used / (1024**3), 1),
                "free_gb": round(du.free / (1024**3), 1),
                "pct": round((du.used / du.total) * 100, 1) if du.total else 0.0,
            })
        except Exception:
            continue

    vm = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.2)

    return WidgetResult(
        name=name,
        title=title,
        data={
            "cpu_pct": cpu,
            "mem_pct": vm.percent,
            "mem_used_gb": round(vm.used / (1024**3), 1),
            "mem_total_gb": round(vm.total / (1024**3), 1),
            "disks": disks,
        },
    )
