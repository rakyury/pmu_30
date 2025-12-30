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

REM Find emulator (check multiple locations)
set "EMU_PATH="
if exist "%SCRIPT_DIR%pmu30_emulator.exe" (
    set "EMU_PATH=%SCRIPT_DIR%pmu30_emulator.exe"
) else if exist "%SCRIPT_DIR%..\firmware\.pio\build\pmu30_emulator\program.exe" (
    set "EMU_PATH=%SCRIPT_DIR%..\firmware\.pio\build\pmu30_emulator\program.exe"
)

if "%EMU_PATH%"=="" (
    echo ERROR: Emulator not found!
    echo.
    echo Expected locations:
    echo   - %SCRIPT_DIR%pmu30_emulator.exe
    echo   - %SCRIPT_DIR%..\firmware\.pio\build\pmu30_emulator\program.exe
    echo.
    pause
    exit /b 1
)

REM Find configurator (check multiple locations)
set "CFG_DIR="
if exist "%SCRIPT_DIR%..\configurator\src\main.py" (
    set "CFG_DIR=%SCRIPT_DIR%..\configurator\src"
) else if exist "%SCRIPT_DIR%..\..\configurator\src\main.py" (
    set "CFG_DIR=%SCRIPT_DIR%..\..\configurator\src"
) else if exist "%SCRIPT_DIR%configurator\src\main.py" (
    set "CFG_DIR=%SCRIPT_DIR%configurator\src"
)

if "%CFG_DIR%"=="" (
    echo ERROR: Configurator not found!
    echo.
    echo This launcher must be run from the PMU-30 project structure.
    echo.
    echo Expected structure:
    echo   pmu_30/
    echo     releases/          ^<-- Run from here
    echo       PMU30_Desktop_Suite.bat
    echo       pmu30_emulator.exe
    echo     configurator/
    echo       src/
    echo         main.py
    echo.
    echo Please extract the ZIP to the 'releases' folder of the PMU-30 project.
    echo.
    pause
    exit /b 1
)

echo [Launcher] Starting emulator...
start "" "%EMU_PATH%"

echo [Launcher] Waiting for emulator to initialize...
timeout /t 2 /nobreak >nul

echo [Launcher] Starting configurator (auto-connecting)...
cd /d "%CFG_DIR%"
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
