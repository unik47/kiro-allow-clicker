"""
Kiro Allow Clicker - Tray App
=============================

This is the quiet background version. It shows a small icon near your clock
(the system tray). No black window. It uses the SAME tested click logic:
it clicks only 'Allow' in any Kiro window, catches fast bursts, and never
clicks Always allow / Deny / Always deny.

Tray menu:
  * Status line  : shows ON (green) or PAUSED.
  * Pause / Resume : stop or start the clicking.
  * Quit         : close the tool fully.

RAM stays small (~40-60 MB). The screen must be ON and UNLOCKED.
"""

import threading
import time

import pystray
from PIL import Image, ImageDraw

import kiro_allow_clicker as core  # reuse the tested engine


class App:
    def __init__(self):
        self.enabled = True
        self.clicks_total = 0
        self.icon = None
        self._stop = threading.Event()

    # ---- draw a simple round icon, green when ON, grey when paused ----------
    def _make_icon(self):
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        color = (46, 160, 67) if self.enabled else (120, 120, 120)
        d.ellipse([6, 6, size - 6, size - 6], fill=color)
        # A small check mark to mean 'allow'.
        d.line([(20, 34), (29, 44), (46, 22)], fill=(255, 255, 255), width=6)
        return img

    def _refresh_icon(self):
        if self.icon:
            self.icon.icon = self._make_icon()
            state = "ON" if self.enabled else "PAUSED"
            self.icon.title = f"Kiro Allow Clicker: {state} (clicks: {self.clicks_total})"

    # ---- the background worker that does the scanning -----------------------
    def _worker(self):
        # UI Automation uses COM. COM must be started in EVERY thread that uses
        # it. Without this, each scan fails with "CoInitialize has not been
        # called" and nothing is ever clicked. If the COM link breaks, the outer
        # loop starts it again, so the worker recovers by itself.
        while not self._stop.is_set():
            try:
                # The cached search rule belongs to one COM session. Build it
                # again after every (re)start.
                core._allow_condition = None
                with core.auto.UIAutomationInitializerInThread():
                    self._scan_loop()
            except Exception:
                self._stop.wait(2.0)

    def _scan_loop(self):
        while not self._stop.is_set():
            if self.enabled:
                try:
                    # Use the HWND-based discovery so minimized or covered Kiro
                    # windows (and Kiro's approval popup) are included.
                    for window in core.iter_kiro_windows():
                        try:
                            if core.find_and_click_allow(window):
                                self.clicks_total += 1
                                self._refresh_icon()
                        except Exception:
                            continue
                except Exception:
                    pass
            self._stop.wait(core.SCAN_INTERVAL_SECONDS)

    # ---- tray menu actions --------------------------------------------------
    def toggle(self, icon, item):
        self.enabled = not self.enabled
        self._refresh_icon()

    def quit(self, icon, item):
        self._stop.set()
        icon.stop()

    def _menu(self):
        return pystray.Menu(
            pystray.MenuItem(
                lambda item: "Pause clicking" if self.enabled else "Resume clicking",
                self.toggle,
            ),
            pystray.MenuItem("Quit", self.quit),
        )

    def run(self):
        # uiautomation must run in its own thread; start the worker first.
        t = threading.Thread(target=self._worker, daemon=True)
        t.start()
        self.icon = pystray.Icon(
            "kiro_allow_clicker",
            self._make_icon(),
            "Kiro Allow Clicker: ON",
            self._menu(),
        )
        self.icon.run()


if __name__ == "__main__":
    App().run()
