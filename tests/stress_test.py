"""
Stress test for the Allow-clicker logic.

It does NOT touch Kiro. It builds a FAKE target: a list of 'Allow' buttons
that appear fast, one after another, sometimes two at once. It runs the SAME
click logic the real tool uses, and measures:

  * How many Allow buttons appeared.
  * How many got clicked.
  * Any that were missed.
  * The worst delay between appear and click.
  * Whether the loop ever crashed.

This tells us if a fast burst breaks the tool.
"""
import time
import random
import threading


# ---- A fake Allow button ----------------------------------------------------
class FakeButton:
    def __init__(self, name):
        self.Name = name
        self.ControlTypeName = "ButtonControl"
        self.clicked = False
        self.appeared_at = time.time()
        self.clicked_at = None

    def GetInvokePattern(self):
        return self

    def Invoke(self):
        # Mimic a real click: the button goes away after it is pressed.
        if not self.clicked:
            self.clicked = True
            self.clicked_at = time.time()


# ---- A fake window that holds live (unclicked) buttons ----------------------
class FakeWindow:
    def __init__(self):
        self.ControlTypeName = "WindowControl"
        self._buttons = []
        self.lock = threading.Lock()

    def add_allow(self):
        with self.lock:
            self._buttons.append(FakeButton("Allow"))

    def GetChildren(self):
        # Only return buttons that are still live (not yet clicked),
        # just like a real UI tree where a clicked dialog disappears.
        with self.lock:
            return [b for b in self._buttons if not b.clicked]

    def all_buttons(self):
        with self.lock:
            return list(self._buttons)


# ---- The SAME click logic as the real tool (one click per scan) -------------
TARGET = "allow"
BLOCKED = {"always allow", "deny", "always deny"}

def find_and_click_allow(window):
    """New logic: click ALL Allow per pass, loop until none, catch bursts."""
    total = 0
    for _ in range(8):
        n = 0
        stack = list(window.GetChildren())
        while stack:
            node = stack.pop()
            name = (node.Name or "").strip().lower()
            if name in BLOCKED:
                continue
            if node.ControlTypeName == "ButtonControl" and name == TARGET:
                p = node.GetInvokePattern()
                if p:
                    p.Invoke()
                    n += 1
        if n == 0:
            break
        total += n
        time.sleep(0.05)
    return total > 0


# ---- The burst generator: fire Allow buttons fast ---------------------------
def burst(win, total, gap_seconds):
    for _ in range(total):
        win.add_allow()
        # Sometimes two appear in the same instant.
        if random.random() < 0.4:
            win.add_allow()
        time.sleep(gap_seconds)


def run_test(scan_interval, burst_gap, total_bursts, label):
    print(f"\n--- {label} ---")
    win = FakeWindow()
    stop = threading.Event()

    # Start firing Allow buttons in the background.
    t = threading.Thread(target=burst, args=(win, total_bursts, burst_gap))
    t.start()

    clicks = 0
    crashed = False
    # Run the scan loop until the burst is done AND the queue is empty.
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            if find_and_click_allow(win):
                clicks += 1
        except Exception as e:
            crashed = True
            print("  CRASH:", e)
            break
        if not t.is_alive() and not win.GetChildren():
            break
        time.sleep(scan_interval)
    t.join(timeout=1)

    all_btns = win.all_buttons()
    appeared = len(all_btns)
    done = [b for b in all_btns if b.clicked]
    missed = [b for b in all_btns if not b.clicked]
    latencies = [(b.clicked_at - b.appeared_at) for b in done if b.clicked_at]
    worst = max(latencies) if latencies else 0

    print(f"  Allow buttons appeared: {appeared}")
    print(f"  Allow buttons clicked:  {len(done)}")
    print(f"  Allow buttons MISSED:   {len(missed)}")
    print(f"  Worst click delay:      {worst:.2f} s")
    print(f"  Loop crashed:           {'YES' if crashed else 'no'}")
    return len(missed), crashed


print("STRESS TEST: fast, repeated Allow buttons")
print("=" * 50)

# Test 1: current 1-second scan, buttons every 1 second.
run_test(scan_interval=1.0, burst_gap=1.0, total_bursts=10, label="1s scan vs 1s bursts")

# Test 2: the WORST case you asked about -- many Allow in a near-instant.
run_test(scan_interval=1.0, burst_gap=0.05, total_bursts=15, label="1s scan vs near-instant flood (15 in <1s)")

# Test 3: 2-second scan (the lighter setting) vs 1s bursts.
run_test(scan_interval=2.0, burst_gap=1.0, total_bursts=10, label="2s scan vs 1s bursts")
