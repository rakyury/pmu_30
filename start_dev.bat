@echo off
echo Starting PMU-30 Development Environment...

REM Start the emulator in a new window
start "PMU-30 Emulator" c:\Projects\pmu_30\firmware\.pio\build\pmu30_emulator\program.exe

REM Wait 2 seconds for emulator to start
timeout /t 2 /nobreak > nul

REM Start the configurator in a new window
start "PMU-30 Configurator" pythonw c:\Projects\pmu_30\configurator\src\main.py --connect

echo Both applications started.
