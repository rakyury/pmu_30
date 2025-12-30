@echo off
REM PMU-30 Test Suite Launcher
REM Starts Emulator, Configurator and Web UI for testing

echo.
echo ===============================================================
echo            PMU-30 Test Suite Launcher
echo            R2 m-sport (c) 2025
echo ===============================================================
echo.

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0

REM Start the emulator in a new window
echo Starting PMU-30 Emulator...
start "PMU-30 Emulator" "%SCRIPT_DIR%pmu30_emulator.exe"

REM Wait for emulator to initialize
echo Waiting for emulator to initialize...
timeout /t 2 /nobreak > nul

REM Open Web UI in default browser
echo Opening Web UI in browser...
start http://localhost:8080

REM Wait a bit before starting configurator
timeout /t 1 /nobreak > nul

REM Start configurator if it exists
if exist "%SCRIPT_DIR%..\configurator\main.py" (
    echo Starting PMU-30 Configurator...
    start "PMU-30 Configurator" python "%SCRIPT_DIR%..\configurator\main.py"
) else if exist "%SCRIPT_DIR%pmu30_configurator.exe" (
    echo Starting PMU-30 Configurator...
    start "PMU-30 Configurator" "%SCRIPT_DIR%pmu30_configurator.exe"
) else (
    echo.
    echo NOTE: Configurator not found. Run it manually from:
    echo   python configurator\main.py
)

echo.
echo ===============================================================
echo  All components started!
echo.
echo  Emulator:     Running in separate console window
echo  Web UI:       http://localhost:8080 (opened in browser)
echo  Protocol:     localhost:5555 (for Configurator connection)
echo ===============================================================
echo.
echo Press any key to close this launcher (components will keep running)
pause > nul
