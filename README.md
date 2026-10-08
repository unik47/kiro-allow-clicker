# Kiro Allow Clicker

A tiny Windows background tool that automatically clicks the **Allow** button
in the [Kiro IDE](https://kiro.dev) approval prompt — so your AI agent keeps
working while you do something else.

It runs quietly in the system tray, uses about **40 MB of RAM**, and clicks
**only** the `Allow` button. It never clicks `Always allow`, `Deny`, or
`Always deny`.

![tray icon: a green circle with a white check](docs/icon-preview.png)

---

## Why

The Kiro IDE asks you to approve each tool action with an **Allow** prompt.
If you run long agent sessions, you click **Allow** again and again. This tool
does that one click for you, in the background, in any Kiro window.

## What it does

- Finds **every** open Kiro window — not tied to one workspace.
- Reads the window with Windows UI Automation (no screenshots saved).
- Clicks the button named exactly `Allow`.
- Catches **fast bursts** of Allow prompts (stress-tested, zero missed).
- Does **not** move your mouse. Does **not** steal your window focus.

## What it will NEVER do

- It never clicks `Always allow`.
- It never clicks `Deny` or `Always deny`.
- It only looks inside Kiro windows. It ignores every other app.

## Requirements

- Windows 10 or 11
- Python 3.9 or newer
- The screen must be **on and unlocked** (a Windows safety rule — no tool can
  click a locked screen).

## Install

```bat
git clone https://github.com/USERNAME/kiro-allow-clicker.git
cd kiro-allow-clicker
setup.bat
```

`setup.bat` installs the Python packages: `uiautomation`, `keyboard`,
`pystray`, and `pillow`.

## Run

**Background tray version (recommended):**

Double-click `Start Kiro Allow Clicker.vbs`. A small green icon appears near
your clock. Right-click it for **Pause** and **Quit**.

**Simple console version:**

Double-click `START.bat`. A console window stays open and logs each click.

## Start automatically at login

```powershell
powershell -ExecutionPolicy Bypass -File install_autostart.ps1
```

This adds a shortcut to your Windows Startup folder. To stop auto-start,
delete `Kiro Allow Clicker.lnk` from your Startup folder.

## Settings

Open `kiro_allow_clicker.py` and change the values near the top:

- `TARGET_BUTTON_TEXT` — the button text to click (default `"Allow"`).
- `BLOCKED_BUTTON_TEXT` — buttons that are never clicked.
- `SCAN_INTERVAL_SECONDS` — how often to look (default `2.0`).

## How it handles fast bursts

Each scan clicks **every** Allow button it finds, then looks again right away.
So if clicking one Allow makes a second Allow appear at the same moment, the
same scan still catches it. The included `stress_test.py` proves this with a
flood of prompts.

```bat
python stress_test.py
```

## Safety

This tool clicks a button for you. That means it approves actions without you
reading them. Use it only when you trust the agent and the work. It is limited
to the `Allow` button on purpose, so the riskier `Always allow` and the
`Deny` choices always stay a manual decision.

## License

MIT — free for anyone to use, change, and share. See [LICENSE](LICENSE).
