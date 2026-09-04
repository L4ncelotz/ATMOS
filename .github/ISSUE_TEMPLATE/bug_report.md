---
name: Bug report
about: Something is broken or behaving wrong
title: ""
labels: bug
assignees: ""
---

## Describe the bug

A clear and concise description of what the bug is.

## To reproduce

```bash
atmos Bangkok --fps 30
```

What you typed, what you expected, what happened instead.

## Environment

- ATMOS version: `atmos --version`
- OS: (e.g. Windows Terminal on Windows 11, iTerm2 on macOS 14)
- Python version (only if `pip install`): (e.g. 3.12.4)
- Terminal: (e.g. Windows Terminal 1.21, iTerm2 3.5, Alacritty 0.13)
- Terminal size: (e.g. 120 × 30)

## Logs

If relevant, attach `atmos.log` from your platform log dir:

- Windows: `%LOCALAPPDATA%\atmos\Logs\atmos.log`
- Linux: `~/.local/state/atmos/atmos.log`
- macOS: `~/Library/Logs/atmos/atmos.log`

To get a verbose log on stderr, run with `ATMOS_DEBUG=1`.

## Screenshots / terminal capture

If applicable, attach a screen recording or screenshot.
