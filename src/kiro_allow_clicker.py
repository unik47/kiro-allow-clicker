"""
Kiro Allow Clicker  (robust engine, v2)
=======================================

What it does
------------
Runs in the background. Watches every open Kiro IDE window. When Kiro shows its
approval box, it finds the button whose text is exactly "Allow" and clicks it,
inside the window, even when Kiro is behind another app. Your mouse does not
move. Your window focus does not change.

The delay problem, and the fix
------------------------------
The old build read Kiro's window node by node from Python. Each node is one
call across the Windows accessibility bridge. Kiro has over 1000 nodes, so
one scan took about 1.4-2.0 seconds (slower when Kiro is in the background),
and the old build then slept another 2 seconds.

This build asks Windows to do the search itself, in ONE call:
"find every Button or Hyperlink named exactly Allow". On a real Kiro window
that takes about 55 ms instead of about 2000 ms. It then scans every 0.5 s.
If the native search ever fails, it falls back to the old Python walk, so a
button is never skipped.

What it will NEVER do
---------------------
* Never clicks "Always allow".
* Never clicks "Deny" or "Always deny".
* Never clicks any button that is not exactly "Allow".
* Only looks inside Kiro windows. Ignores every other app.

Safety stop
-----------
Press  CTRL + ALT + K  to turn clicking ON or OFF. Close the window to stop.

Requirements: Windows 10/11, Python 3.9+, pip: uiautomation, keyboard.
The screen must be ON and UNLOCKED (a Windows rule, not a limit of this tool).
"""

import sys
import time

try:
    import uiautomation as auto
except ImportError:
    print("Missing package 'uiautomation'. Run setup.bat first.")
    sys.exit(1)

try:
    import keyboard
except ImportError:
    keyboard = None


# ---- Settings you may change -------------------------------------------------

TARGET_BUTTON_TEXT = "Allow"
BLOCKED_BUTTON_TEXT = {"always allow", "deny", "always deny"}

# Look this often. The scan exits early when it finds a button, so a short
# interval stays light while making clicks fast.
SCAN_INTERVAL_SECONDS = 0.5

# Pass 1 is a quick shallow look. Pass 2 is the deep safety net.
SHALLOW_DEPTH = 16        # cheap first look
FULL_DEPTH = 34           # deep enough for Kiro chat buttons (seen at depth 32)
MAX_NODES_PER_SCAN = 4000 # hard safety cap so a scan can never hang

KIRO_PROCESS_NAMES = {"kiro.exe"}

# -----------------------------------------------------------------------------


class State:
    enabled = True


_pid_name_cache = {}
_pid_cache_time = [0.0]
PID_CACHE_SECONDS = 30.0


def _process_name_for_pid(pid):
    # Forget old answers every 30 s. When Kiro is closed and opened again it
    # gets new process ids, and Windows can give an old id to another app.
    # Without this, a reused id could be treated as Kiro by mistake.
    now = time.time()
    if now - _pid_cache_time[0] > PID_CACHE_SECONDS:
        _pid_name_cache.clear()
        _pid_cache_time[0] = now
    if pid in _pid_name_cache:
        return _pid_name_cache[pid]
    name = ""
    try:
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            buf_len = wintypes.DWORD(260)
            buf = ctypes.create_unicode_buffer(buf_len.value)
            if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(buf_len)):
                name = buf.value.rsplit("\\", 1)[-1]
            kernel32.CloseHandle(handle)
    except Exception:
        name = ""
    _pid_name_cache[pid] = name
    return name


def is_kiro_window(window):
    try:
        return _process_name_for_pid(window.ProcessId).lower() in KIRO_PROCESS_NAMES
    except Exception:
        return False


def _click_allow_pass(window, max_depth, click_all=True):
    """
    One depth-capped pass. Clicks exact 'Allow' buttons.
    If click_all is True it keeps going and clicks EVERY Allow it meets in this
    pass (good for bursts). It still returns as soon as the node budget ends.
    Returns the number clicked.
    """
    clicked = 0
    nodes = 0
    try:
        stack = [(c, 1) for c in window.GetChildren()]
        while stack and nodes < MAX_NODES_PER_SCAN:
            node, depth = stack.pop()
            nodes += 1
            try:
                ctrl_type = node.ControlTypeName
                name = (node.Name or "").strip()
            except Exception:
                continue

            lower = name.lower()

            if lower in BLOCKED_BUTTON_TEXT:
                continue

            if ctrl_type in ("ButtonControl", "HyperlinkControl") and lower == TARGET_BUTTON_TEXT.lower():
                try:
                    pattern = node.GetInvokePattern()
                    if pattern:
                        pattern.Invoke()
                        clicked += 1
                        if not click_all:
                            return clicked  # early exit: found and clicked one
                        continue
                except Exception:
                    pass

            if depth < max_depth:
                try:
                    stack.extend((c, depth + 1) for c in node.GetChildren())
                except Exception:
                    pass
    except Exception:
        pass
    return clicked


# ---- Native search (fast path) ------------------------------------------------
# Windows walks the tree itself in ONE call. On a real Kiro window this takes
# about 55 ms, where the Python walk above takes about 2000 ms.
_UIA_NAME = 30005
_UIA_CONTROLTYPE = 30003
_UIA_BUTTON = 50000
_UIA_HYPERLINK = 50005
_TREESCOPE_DESCENDANTS = 4
_IGNORE_CASE = 1
_allow_condition = None


def _get_allow_condition():
    """Build (once) the condition: (Button OR Hyperlink) AND Name == 'Allow'."""
    global _allow_condition
    if _allow_condition is None:
        import uiautomation.uiautomation as _m
        uia = _m._AutomationClient.instance().IUIAutomation
        is_button = uia.CreateOrCondition(
            uia.CreatePropertyCondition(_UIA_CONTROLTYPE, _UIA_BUTTON),
            uia.CreatePropertyCondition(_UIA_CONTROLTYPE, _UIA_HYPERLINK),
        )
        is_allow = uia.CreatePropertyConditionEx(_UIA_NAME, TARGET_BUTTON_TEXT, _IGNORE_CASE)
        _allow_condition = uia.CreateAndCondition(is_button, is_allow)
    return _allow_condition


def find_allow_elements(window):
    """Return controls whose name is exactly 'Allow'. Never clicks. None = native search failed."""
    try:
        found = window.Element.FindAll(_TREESCOPE_DESCENDANTS, _get_allow_condition())
    except Exception:
        return None
    controls = []
    if not found:
        return controls
    for i in range(found.Length):
        try:
            ctrl = auto.Control.CreateControlFromElement(found.GetElement(i))
            if ctrl is not None:
                controls.append(ctrl)
        except Exception:
            continue
    return controls


def _click_allow_native(window):
    """One native pass. Clicks every exact 'Allow'. Returns count, or None on failure."""
    controls = find_allow_elements(window)
    if controls is None:
        return None
    clicked = 0
    for ctrl in controls:
        try:
            name = (ctrl.Name or "").strip().lower()
            # Safety re-check right before the click.
            if name != TARGET_BUTTON_TEXT.lower() or name in BLOCKED_BUTTON_TEXT:
                continue
            pattern = ctrl.GetInvokePattern()
            if pattern:
                pattern.Invoke()
                clicked += 1
        except Exception:
            continue
    return clicked


def _click_pass(window):
    """Fast native pass; fall back to the Python walk only if native fails."""
    n = _click_allow_native(window)
    if n is None:
        n = _click_allow_pass(window, FULL_DEPTH, click_all=True)
    return n


def find_and_click_allow(window):
    """
    Clear all 'Allow' buttons in one window with a SINGLE full-depth walk per
    pass (not two). Reading Kiro's tree costs about the same whether the depth
    is shallow or full, so one deep walk is cheaper than a shallow walk plus a
    deep walk. The walk clicks every Allow it meets, then re-loops only if it
    actually clicked something (to catch a burst of new boxes). When nothing is
    there, it is exactly one walk and then it returns.
    """
    total = 0
    for _ in range(6):
        n = _click_pass(window)
        if n == 0:
            break
        total += n
        time.sleep(0.03)
    return total > 0


def scan_once():
    clicked_any = False
    try:
        root = auto.GetRootControl()
        for window in root.GetChildren():
            try:
                if window.ControlTypeName not in ("WindowControl", "PaneControl"):
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
    print(" Kiro Allow Clicker is running (robust engine v2).")
    print(" It clicks ONLY the 'Allow' button inside Kiro windows.")
    print(" It never clicks Always allow / Deny / Always deny.")
    print(f" Scan every {SCAN_INTERVAL_SECONDS}s. Shallow {SHALLOW_DEPTH}, deep {FULL_DEPTH}.")
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
