@echo off
REM SKEYE GCS - SITL Mode Launcher (Windows)
REM
REM Quick launcher for SITL testing with Mission Planner simulator
REM
REM Usage:
REM   start_gcs_sitl.bat                    - Use Mission Planner (default)
REM   start_gcs_sitl.bat mavproxy_udp       - Use MAVProxy UDP
REM   start_gcs_sitl.bat mavproxy_tcp       - Use MAVProxy TCP
REM

echo ============================================================
echo   SKEYE GCS - SITL Mode
echo ============================================================
echo.

REM Get preset name from argument (default to mission_planner)
set PRESET=%1
if "%PRESET%"=="" set PRESET=mission_planner

echo Starting SKEYE GCS with SITL preset: %PRESET%
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please install Python 3.9 or later
    pause
    exit /b 1
)

REM Run the SITL launcher script
python src\flight-system\v2\run_gcs_sitl.py %PRESET% %2 %3

echo.
echo SKEYE GCS stopped
pause
