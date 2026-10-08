@echo off
REM ============================================================
REM  Kiro Allow Clicker - start (console version)
REM  Leave this window open while you work. The tool clicks the
REM  Allow button in any Kiro window for you.
REM  Press CTRL+ALT+K to pause/resume. Close the window to stop.
REM ============================================================
cd /d "%~dp0\..\src"
python kiro_allow_clicker.py
pause
