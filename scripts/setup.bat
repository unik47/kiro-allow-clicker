@echo off
REM ============================================================
REM  Kiro Allow Clicker - one-time setup
REM  This installs the Python packages the tool needs.
REM ============================================================
echo Installing required packages...
python -m pip install --upgrade pip
python -m pip install uiautomation keyboard pystray pillow
echo.
echo Setup done.
echo   - Tray version:    double-click "Start Kiro Allow Clicker.vbs"
echo   - Console version: double-click START.bat
pause
