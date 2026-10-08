"""
Kiro Allow Clicker
==================

What it does
------------
This small program runs in the background. It watches every open Kiro IDE
window. When Kiro shows its approval box, this program finds the button whose
text is exactly "Allow" and clicks it -- inside the window, even when Kiro is
behind another app. Your mouse does not move. Your window focus does not change.

What it will NEVER do
---------------------
* It never clicks "Always allow".
* It never clicks "Deny" or "Always deny".
* It never clicks any button that is not exactly "Allow".
* It only looks inside Kiro windows. It ignores every other app.

Safety stop
-----------
Press  CTRL + ALT + K  at any time to turn the clicking ON or OFF.
Close the console window to stop the program fully.

Requirements (installed by setup.bat)
-------------------------------------
* Windows 10 or 11
* Python 3.9+
* pip packages: uiautomation, keyboard

The screen must be ON and UNLOCKED. Windows cannot click a hidden/locked
screen. That is a Windows safety rule, not a limit of this tool.
"""

import sys
import time
import threading

try:
    import uiautomation as auto
except ImportError:
    print("Missing package 'uiautomation'. Run setup.bat first.")
    sys.exit(1)

try:
    import keyboard
except ImportError:
    keyboard = None  # Hotkey is optional. The tool still runs without it.


# ---- Settings you may change -------------------------------------------------

# Only this exact button text is clicked. Keep it as "Allow".
TARGET_BUTTON_TEXT = "Allow"

# Buttons that must NEVER be clicked, as a safety block list.
BLOCKED_BUTTON_TEXT = {"always allow", "deny", "always deny"}

# How often to scan, in seconds. 2.0 is light for all-day running.
# A burst re-look inside each scan still catches fast repeated Allow boxes.
SCAN_INTERVAL_SECONDS = 2.0

# A Kiro window process is named this on Windows. We match the process name,
# so ANY workspace or project window counts, not just one.
KIRO_PROCESS_NAMES = {"kiro.exe"}

# -----------------------------------------------------------------------------


# A simple ON/OFF flag that the hotkey can change from another thread.
class State:
    enabled = True


def is_kiro_window(window):
    """Return True only if this top window belongs to the Kiro app."""
    try:
        proc_name = ""
        # uiautomation exposes the process id; map it to a name.
        pid = window.ProcessId
        proc_name = _process_name_for_pid(pid)
        return proc_name.lower() in KIRO_PROCESS_NAMES
    except Exception:
        return False


_pid_name_cache = {}


def _process_name_for_pid(pid):
    """Look up an .exe name for a process id, with a tiny cache."""
    if pid in _pid_name_cache:
        return _pid_name_cache[pid]
    name = ""
    try:
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION, False, pid
        )
        if handle:
            buf_len = wintypes.DWORD(260)
            buf = ctypes.create_unicode_buffer(buf_len.value)
            if kernel32.QueryFullProcessImageNameW(
                handle, 0, buf, ctypes.byref(buf_len)
            ):
                full = buf.value
                name = full.rsplit("\\", 1)[-1]
            kernel32.CloseHandle(handle)
    except Exception:
        name = ""
    _pid_name_cache[pid] = name
    return name


def _click_all_allow_in_tree(window):
    """
    One pass over a window's control tree. Clicks EVERY button named exactly
    'Allow'. Returns how many it clicked in this pass.
    """
    clicked = 0
    try:
        stack = list(window.GetChildren())
        checked = 0
        while stack and checked < 6000:
            node = stack.pop()
            checked += 1
            try:
                ctrl_type = node.ControlTypeName
                name = (node.Name or "").strip()
            except Exception:
                continue

            lower = name.lower()

            # Safety: never touch a blocked button.
            if lower in BLOCKED_BUTTON_TEXT:
                continue

            # Click EVERY exact 'Allow' button, not just the first.
            if ctrl_type in ("ButtonControl", "HyperlinkControl") and lower == TARGET_BUTTON_TEXT.lower():
                try:
                    pattern = node.GetInvokePattern()
                    if pattern:
                        pattern.Invoke()
                        clicked += 1
                        continue  # do not walk a button we just clicked
                except Exception:
                    pass

            try:
                stack.extend(node.GetChildren())
            except Exception:
                pass
    except Exception:
        pass
    return clicked


def find_and_click_allow(window):
    """
    Clear ALL 'Allow' buttons in one window, even a fast burst.
    It passes over the tree again and again until a pass finds nothing new.
    This way, if clicking one Allow makes a second Allow appear at once,
    the same scan still catches it. Returns True if it clicked at least one.
    """
    total = 0
    # Loop a few times so a burst that appears mid-scan is still caught.
    for _ in range(8):
        n = _click_all_allow_in_tree(window)
        if n == 0:
            break
        total += n
        # Tiny pause lets the next queued Allow box render before the re-pass.
        time.sleep(0.05)
    return total > 0


def scan_once():
    """Scan every top-level window; act only on Kiro ones."""
    clicked_any = False
    try:
        root = auto.GetRootControl()
        for window in root.GetChildren():
            try:
                if not window.ControlTypeName == "WindowControl":
                    continue
                if not is_kiro_window(window):
                    continue
                if find_and_click_allow(window):
                    clicked_any = True
                    print(time.strftime("[%H:%M:%S] Clicked 'Allow' in a Kiro window."))
            except Exception:
                continue
    except Exception:
        pass
    return clicked_any


def hotkey_listener():
    """Toggle ON/OFF with CTRL+ALT+K. Optional."""
    if keyboard is None:
        return

    def toggle():
        State.enabled = not State.enabled
        print(">>> Clicking is now", "ON" if State.enabled else "OFF")

    try:
        keyboard.add_hotkey("ctrl+alt+k", toggle)
    except Exception:
        pass


def main():
    print("=" * 60)
    print(" Kiro Allow Clicker is running.")
    print(" It clicks ONLY the 'Allow' button inside Kiro windows.")
    print(" It never clicks Always allow / Deny / Always deny.")
    print(" Toggle ON/OFF:  CTRL + ALT + K")
    print(" Stop fully:     close this window.")
    print("=" * 60)

    hotkey_listener()

    while True:
        if State.enabled:
            scan_once()
        time.sleep(SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
