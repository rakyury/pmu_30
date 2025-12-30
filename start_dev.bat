@echo off
echo Starting PMU-30 Development Environment...

REM Start the configurator first (needs to run from configurator dir for imports)
cd /d c:\Projects\pmu_30\configurator
start "PMU-30 Configurator" python src/main.py

REM Wait 3 seconds for configurator to initialize
timeout /t 3 /nobreak > nul

REM Start the emulator
start "PMU-30 Emulator" c:\Projects\pmu_30\firmware\.pio\build\pmu30_emulator\program.exe

echo Both applications started.
