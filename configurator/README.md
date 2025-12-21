# PMU-30 Configurator

**Owner:** R2 m-sport
**Platform:** Cross-platform (Windows, Linux, macOS)
**Framework:** Python 3.10+ with PyQt6

---

## Overview

Professional configuration software for the PMU-30 Power Distribution Module. Provides a modern, cross-platform GUI for:

- Device configuration and monitoring
- 30 output channel setup
- 20 universal input configuration
- CAN bus message and signal mapping
- Logic engine programming
- Lua script development
- Real-time data visualization
- Firmware updates

## Features

### Device Communication
- **USB**: Direct serial connection via USB-C
- **WiFi**: Wireless configuration via Access Point mode
- **Bluetooth**: BLE connectivity for mobile access

### Configuration Management
- Load/save configuration files (.yaml format)
- Import/export CAN DBC files
- Backup and restore device settings
- Configuration validation

### Real-Time Monitoring
- Live output channel status
- Input sensor readings
- CAN bus traffic analysis
- System diagnostics

### Advanced Features
- Lua 5.4 script editor with syntax highlighting
- DBC signal browser and mapping
- Logic engine visual programming
- Data logger with CSV export
- Over-the-air (OTA) firmware updates

## Installation

### Prerequisites

- Python 3.10 or newer
- pip package manager

### Setup

1. **Clone or extract the project:**
   ```bash
   cd pmu_30/configurator
   ```

2. **Create virtual environment (recommended):**
   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # Linux/macOS
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Running the Configurator

### Development Mode

```bash
cd src
python main.py
```

### Build Standalone Executable (Optional)

```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller --name="PMU30-Configurator" \
            --windowed \
            --onefile \
            --icon=resources/icon.ico \
            src/main.py
```

The executable will be in the `dist/` directory.

## Project Structure

```
configurator/
├── src/
│   ├── main.py                 # Application entry point
│   ├── ui/
│   │   ├── main_window.py      # Main application window
│   │   ├── tabs/               # Configuration tabs
│   │   │   ├── outputs_tab.py  # 30 output channels
│   │   │   ├── inputs_tab.py   # 20 input channels
│   │   │   ├── can_tab.py      # CAN bus config
│   │   │   ├── logic_tab.py    # Logic engine
│   │   │   ├── hbridge_tab.py  # H-Bridge motors
│   │   │   ├── lua_tab.py      # Lua scripting
│   │   │   ├── monitoring_tab.py # Real-time monitor
│   │   │   └── settings_tab.py # System settings
│   │   ├── widgets/            # Custom widgets
│   │   └── dialogs/            # Dialog windows
│   ├── controllers/
│   │   └── device_controller.py # Device communication
│   ├── models/
│   │   └── configuration.py    # Configuration data models
│   └── utils/
│       ├── logger.py           # Logging setup
│       ├── dbc_parser.py       # DBC file parser
│       └── serial_comm.py      # Serial communication
├── resources/                  # Icons, images, styles
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Usage

### Connecting to Device

1. Launch the configurator
2. Select connection type (USB/WiFi/Bluetooth)
3. Choose device port/address
4. Click "Connect"

### Loading Configuration

**From File:**
- File → Open Configuration
- Select .yaml configuration file

**From Device:**
- Device → Read Configuration
- Configuration will be loaded from connected PMU-30

### Editing Configuration

Navigate through tabs to configure:
- **Outputs**: Set current limits, PWM, soft-start
- **Inputs**: Configure sensor types, scaling, calibration
- **CAN**: Define messages, map signals
- **Logic**: Create virtual switches and functions
- **H-Bridge**: Configure motor control parameters
- **Lua**: Write custom control scripts

### Saving Configuration

**To File:**
- File → Save Configuration
- Choose location for .yaml file

**To Device:**
- Device → Write Configuration
- Configuration will be uploaded to PMU-30

### Updating Firmware

1. Device → Update Firmware
2. Select firmware file (.bin)
3. Wait for upload and verification
4. Device will automatically restart

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New Configuration |
| Ctrl+O | Open Configuration |
| Ctrl+S | Save Configuration |
| Ctrl+Shift+S | Save As |
| Ctrl+Q | Quit |
| F5 | Refresh Device List |
| F9 | Connect/Disconnect |

## Configuration File Format

Configurations are saved in YAML format:

```yaml
device:
  name: "PMU-30"
  serial: "PMU30-12345"
  firmware_version: "1.0.0"

outputs:
  - channel: 1
    name: "Fuel Pump"
    enabled: true
    current_limit_mA: 25000
    pwm_frequency_hz: 1000
    soft_start_ms: 100

inputs:
  - channel: 1
    name: "Oil Pressure"
    type: "linear_analog"
    multiplier: 2.5
    offset: -1.25
    unit: "bar"

can:
  messages:
    - name: "ECU_Data"
      id: 0x600
      bus: "CAN1"
      dlc: 8
      rate_hz: 100
```

## Troubleshooting

### Device Not Detected

- Check USB cable connection
- Install USB-to-Serial drivers if needed
- Try different USB port
- Check Device Manager (Windows) or `lsusb` (Linux)

### Connection Failed

- Ensure device is powered on
- Verify correct COM port selected
- Check firewall settings (WiFi mode)
- Try restarting the application

### Configuration Not Loading

- Verify YAML file format
- Check for syntax errors
- Ensure file version compatibility

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

```bash
# Format code
black src/

# Lint code
pylint src/
```

## Support

For issues and feature requests, contact R2 m-sport.

## License

Proprietary - © 2025 R2 m-sport. All rights reserved.

This software is the property of R2 m-sport. Unauthorized copying, distribution, or use is prohibited.

---

**Version:** 1.0.0
**Last Updated:** 2025-12-21
