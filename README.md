# Wallboard: Wallpaper dashboard generator

Playwright (web renderer) needs a browser installed:

```bash
uv run playwright install --with-deps chromium
```

To run:

```bash
uv run wallboard --config config.yaml
```

Output is written to `~/.cache/wallboard/wallpaper.png` by default.

## Systemd Service

To install as a systemd user service/timer:

```bash
mkdir -p ~/.config/systemd/user

cp systemd/wallboard.* ~/.config/systemd/user/

systemctl --user daemon-reload
systemctl --user enable --now wallboard.timer
systemctl --user list-timers --all | grep wallboard
```

To inspect logs or troubleshoot:

```bash
journalctl --user -u wallboard.service -n 100 --no-pager
systemctl --user status wallboard.service
```
