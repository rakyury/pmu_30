# PMU-30 Development Environment Launcher
# Starts both the emulator and configurator in parallel

Write-Host "Starting PMU-30 Development Environment..." -ForegroundColor Cyan

# Start emulator in new window
Write-Host "  - Starting Emulator..." -ForegroundColor Green
Start-Process -FilePath "c:\Projects\pmu_30\firmware\.pio\build\pmu30_emulator\program.exe" -WindowStyle Normal

# Wait for emulator to start
Start-Sleep -Seconds 2

# Start configurator with auto-connect
Write-Host "  - Starting Configurator..." -ForegroundColor Green
Start-Process -FilePath "pythonw" -ArgumentList "c:\Projects\pmu_30\configurator\src\main.py", "--connect" -WindowStyle Normal

Write-Host ""
Write-Host "Both applications started successfully!" -ForegroundColor Cyan
Write-Host "Emulator: localhost:9876" -ForegroundColor Yellow
Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
