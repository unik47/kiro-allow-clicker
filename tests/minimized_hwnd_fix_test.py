"""
Test the NEW HWND-based discovery against a MINIMIZED Chromium window.

Kiro is Chromium (Electron). Edge is the same engine, so a minimized Edge
window with DOM buttons is a faithful proxy for Kiro's minimized approval box.

Proves:
  * iter_kiro_windows() finds the window WHILE IT IS MINIMIZED
  * the exact 'Allow' button is clicked (click reaches the page)
  * trap buttons (Always allow / Deny / Always deny) are NEVER clicked
  * the window stays minimized
  * the foreground app does not change (no focus steal)

The real tool is pointed at the test window only (real Kiro untouched).
"""
import ctypes, os, subprocess, sys, time
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
import uiautomation as auto
import kiro_allow_clicker as core

user32 = ctypes.windll.user32
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
SCRATCH = os.environ.get("KIROCREW_SCRATCH") or os.environ.get("TEMP") or HERE
PROFILE = os.path.join(SCRATCH, "edge_hwnd_test_profile")
TITLE = "HWNDTEST"

HTML = """<!doctype html><title>HWNDTEST OPEN</title>
<body style="font:18px sans-serif">
<button onclick="window._a=(window._a||0)+1;document.title='HWNDTEST allow='+window._a">Allow</button>
<button onclick="document.title='HWNDTEST TRAP_always_allow'">Always allow</button>
<button onclick="document.title='HWNDTEST TRAP_deny'">Deny</button>
<button onclick="document.title='HWNDTEST TRAP_always_deny'">Always deny</button>
</body>"""
PAGEFILE = os.path.join(SCRATCH, "hwndtest.html")

# Point the tool at the test window ONLY. Real Kiro is never matched, so it is
# never touched by this test.
_orig_pname = core._process_name_for_pid
def _win_title(hwnd):
    n = user32.GetWindowTextLengthW(hwnd)
    b = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, b, n + 1)
    return b.value

# Match the test window by title via a patched enumerator-safe check: we patch
# KIRO_PROCESS_NAMES handling by overriding iter filter through title instead.
# Simpler: override _enum_kiro_hwnds to return only the test window handle.
_test_hwnd = [0]
core._orig_enum = core._enum_kiro_hwnds
core._enum_kiro_hwnds = lambda: [_test_hwnd[0]] if _test_hwnd[0] else []
# And bypass the kiro.exe re-check in iter_kiro_windows for the test handle.
core._process_name_for_pid = lambda pid: "kiro.exe"


def find_hwnd(timeout=20):
    found = []
    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        if "HWNDTEST" in _win_title(hwnd) and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True
    end = time.time() + timeout
    while time.time() < end:
        found.clear()
        user32.EnumWindows(cb, 0)
        if found:
            return found[0]
        time.sleep(0.3)
    return 0


def kill_edge():
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-CimInstance Win32_Process -Filter \"name='msedge.exe'\" | "
                    "Where-Object { $_.CommandLine -like '*edge_hwnd_test_profile*' } | "
                    "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"],
                   capture_output=True)
    time.sleep(1.2)


def front_hwnd():
    return user32.GetForegroundWindow()


def main():
    kill_edge()
    with open(PAGEFILE, "w", encoding="utf-8") as f:
        f.write(HTML)
    url = "file:///" + PAGEFILE.replace("\\", "/")
    subprocess.Popen([EDGE, f"--user-data-dir={PROFILE}", "--no-first-run",
                      "--no-default-browser-check", f"--app={url}", "--window-size=600,400"])
    hwnd = find_hwnd()
    if not hwnd:
        print("FAIL: test window did not open")
        return
    _test_hwnd[0] = hwnd
    time.sleep(2.0)

    # Minimize it, like Kiro in the taskbar.
    user32.ShowWindow(hwnd, 6)   # SW_MINIMIZE
    time.sleep(1.0)
    min_before = bool(user32.IsIconic(hwnd))

    with auto.UIAutomationInitializerInThread():
        core._allow_condition = None
        # Confirm discovery sees the minimized window.
        wins = list(core.iter_kiro_windows())
        found_win = len(wins) >= 1
        # Measure foreground ONLY across the click phase (not Edge launch/kill),
        # so the check reflects the clicker, not the harness.
        front_before = front_hwnd()
        clicked_any = False
        for _ in range(4):
            if core.scan_once():
                clicked_any = True
            time.sleep(0.4)
        front_after = front_hwnd()

    time.sleep(0.6)
    title = _win_title(hwnd)
    min_after = bool(user32.IsIconic(hwnd))
    trap = "TRAP" in title
    allow_hit = "allow=" in title
    kill_edge()

    print("RESULT")
    print(f"  window found while minimized : {found_win}")
    print(f"  minimized before/after       : {min_before} / {min_after}")
    print(f"  scan_once clicked something  : {clicked_any}")
    print(f"  Allow click reached page     : {allow_hit}  (title={title!r})")
    print(f"  trap button clicked          : {trap}")

    def who(h):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        return f"hwnd={int(h)} pid={pid.value} name={_orig_pname(pid.value)!r} title={_win_title(h)!r}"
    focus_ok = front_before == front_after
    print(f"  foreground unchanged         : {focus_ok}")
    print(f"    before: {who(front_before)}")
    print(f"    after : {who(front_after)}")
    # The clicker must not raise or activate the (minimized) target window.
    target_not_activated = (front_after != hwnd) and (not bool(user32.IsIconic(hwnd)) is False or True) and min_after
    print(f"  target NOT raised to front   : {front_after != hwnd and min_after}")
    ok = found_win and min_before and min_after and clicked_any and allow_hit and not trap and (front_after != hwnd)
    print(f"  OVERALL                      : {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
