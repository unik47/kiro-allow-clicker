@echo off
REM ============================================================
REM  Kiro Allow Clicker - one-time setup
REM  This installs the two Python packages the tool needs.
REM ============================================================
echo Installing required packages (uiautomation, keyboard)...
python -m pip install --upgrade pip
python -m pip install uiautomation keyboard
echo.
echo Setup done. You can now double-click START.bat to run the tool.
pause
