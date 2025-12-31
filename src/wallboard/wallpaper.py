from __future__ import annotations

from pathlib import Path
import subprocess

def set_gnome_wallpaper(image_path: Path) -> None:
    uri = image_path.resolve().as_uri()
    subprocess.run(
        ["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri],
        check=True
    )
    # Many GNOME versions also use picture-uri-dark
    subprocess.run(
        ["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", uri],
        check=False
    )
