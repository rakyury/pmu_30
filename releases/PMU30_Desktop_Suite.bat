@echo off
title PMU-30 Desktop Suite
echo ============================================================
echo        PMU-30 Desktop Suite v0.2.1
echo        R2 m-sport (c) 2025
echo ============================================================
echo.

REM Get script directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Find emulator
if exist "%SCRIPT_DIR%pmu30_emulator.exe" (
    set "EMU_PATH=%SCRIPT_DIR%pmu30_emulator.exe"
) else if exist "%SCRIPT_DIR%..\firmware\.pio\build\pmu30_emulator\program.exe" (
    set "EMU_PATH=%SCRIPT_DIR%..\firmware\.pio\build\pmu30_emulator\program.exe"
) else (
    echo ERROR: Emulator not found!
    pause
    exit /b 1
)

REM Find configurator
if exist "%SCRIPT_DIR%..\configurator\src\main.py" (
    set "CFG_PATH=%SCRIPT_DIR%..\configurator\src\main.py"
) else (
    echo ERROR: Configurator not found!
    pause
    exit /b 1
)

echo [Launcher] Starting emulator...
start "" "%EMU_PATH%"

echo [Launcher] Waiting for emulator to initialize...
timeout /t 2 /nobreak >nul

echo [Launcher] Starting configurator (auto-connecting)...
cd /d "%SCRIPT_DIR%..\configurator\src"
start "" pythonw main.py --connect

echo.
echo [Launcher] Both applications started!
echo.
echo   Emulator WebUI: http://localhost:8080
echo   Protocol Port:  localhost:9876
echo.
echo Close this window when done.
echo.
pause
