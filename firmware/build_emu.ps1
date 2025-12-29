$env:PATH = "C:\msys64\ucrt64\bin;" + $env:PATH
Set-Location -Path "c:\Projects\pmu_30\firmware"
python -m platformio run -e pmu30_emulator
