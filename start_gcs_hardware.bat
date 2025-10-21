@echo off
REM SKEYE GCS - Hardware Mode Launcher (Windows)
REM
REM Launcher for real Pixhawk hardware connection
REM Supports auto-detection or manual port specification
REM
REM Usage:
REM   start_gcs_hardware.bat           - Auto-detect Pixhawk
REM   start_gcs_hardware.bat COM4      - Use specific COM port
REM

echo ============================================================
echo   SKEYE GCS - Hardware Mode (Real Pixhawk)
echo ============================================================
echo.

REM Get serial port from argument (if provided)
set SERIAL_PORT=%1

if "%SERIAL_PORT%"=="" (
    echo Mode: Auto-detect Pixhawk serial port
    echo.
    echo Scanning for Pixhawk 6X and SiK Radio...
) else (
    echo Mode: Manual serial port
    echo Port: %SERIAL_PORT%
    set GCS_SERIAL=%SERIAL_PORT%
)

REM Set baud rate (57600 for TELEM1/SiK Radio, NOT 115200 which is camera)
set GCS_BAUD=57600

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please install Python 3.9 or later
    pause
    exit /b 1
)

echo.
echo Starting SKEYE GCS Backend...
echo Baud rate: %GCS_BAUD%
echo WebSocket: ws://localhost:8765
echo.
echo Press Ctrl+C to stop
echo ------------------------------------------------------------
echo.

REM Run the GCS server
python src\flight-system\v2\run_gcs.py

echo.
echo SKEYE GCS stopped
pause
