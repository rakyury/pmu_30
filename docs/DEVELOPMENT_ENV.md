# PMU-30 Development Environment

## Windows (No Bash)

**Important:** Development environment uses Windows without bash. All commands run via **CMD** or **PowerShell**.

## Building Firmware for Nucleo-F446RE

```cmd
:: Build firmware (Windows CMD)
cmd /c "set PATH=C:\msys64\ucrt64\bin;%PATH% && cd c:\Projects\pmu_30\firmware && python -m platformio run -e nucleo_f446re"

:: Upload firmware
cmd /c "set PATH=C:\msys64\ucrt64\bin;%PATH% && cd c:\Projects\pmu_30\firmware && python -m platformio run -e nucleo_f446re -t upload"

:: Clean and rebuild
cmd /c "set PATH=C:\msys64\ucrt64\bin;%PATH% && cd c:\Projects\pmu_30\firmware && python -m platformio run -e nucleo_f446re -t clean && python -m platformio run -e nucleo_f446re"
```

## Requirements

- Python 3.x with PlatformIO (`pip install platformio`)
- MSYS2 UCRT64 toolchain (`C:\msys64\ucrt64\bin`) - ARM GCC compiler
- ST-LINK drivers for USB flashing

## Primary Development Platform

**Nucleo-F446RE** is the main platform for debugging and testing:

- Full binary protocol support
- CAN interface (requires external transceiver)
- 6 PWM outputs with real GPIO
- 8 digital inputs  
- 5 ADC channels
- USB Serial via ST-LINK VCP

**All firmware changes are continuously tested on this board.**

## Common Issues

### Build command not found
Use full cmd wrapper: `cmd /c "set PATH=... && python -m platformio run ..."`

### Python not found
Use Windows Apps Python: `C:\Users\User\AppData\Local\Microsoft\WindowsApps\python.exe`

### Bash commands fail
This environment does not have bash. Use CMD or PowerShell equivalents.
