# PMU-30 Configurator Documentation

The PMU-30 Configurator is a professional desktop application for configuring and monitoring the PMU-30 Power Management Unit. It provides real-time monitoring, configuration editing, and device communication capabilities.

## Documentation Index

### Channel Configuration
| Document | Description |
|----------|-------------|
| [Analog Inputs](analog-inputs.md) | Analog input configuration (sensors, switches, calibration) |
| [Digital Inputs](digital-inputs.md) | Digital input configuration (frequency, RPM, FlexFuel) |
| [Power Outputs](power-outputs.md) | Power output configuration (PWM, soft start, current limits) |
| [Power Output Merging](power-output-merging.md) | Merge multiple pins for higher current (40A-120A) |
| [Project Tree](project-tree.md) | Configuration tree view and channel management |

### Control Elements
| Document | Description |
|----------|-------------|
| [Control Elements](control-elements.md) | PID controllers, Timers, and 2D/3D Tables |
| [PID Tuner](pid-tuner.md) | Real-time PID tuning with live graph visualization |

### User Interface
| Document | Description |
|----------|-------------|
| [UI Overview](ui-overview.md) | Main window structure and layout |
| [PMU Monitor](pmu-monitor.md) | System-wide real-time monitoring |
| [Output Monitor](output-monitor.md) | Power output channel monitoring |
| [Analog Monitor](analog-monitor.md) | Analog input monitoring |
| [Digital Monitor](digital-monitor.md) | Digital input monitoring |
| [H-Bridge Monitor](hbridge-monitor.md) | Motor controller monitoring |
| [Variables Inspector](variables-inspector.md) | All system variables display |
| [CAN Monitor](can-monitor.md) | CAN bus live traffic viewer |
| [Data Logger](data-logger.md) | Multi-channel data recording |
| [Input Emulator](input-emulator.md) | Test inputs for emulator mode |

## Quick Start

1. **Launch the application** - Run `main.py` from the configurator directory
2. **Connect to device** - Use `Device > Connect` or press `Ctrl+D`
3. **Open configuration** - Use `File > Open` or press `Ctrl+O`
4. **Monitor real-time data** - Switch between monitor tabs (F9-F12)
5. **Save to device** - Press `F2` to write configuration to flash

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New configuration |
| Ctrl+O | Open configuration |
| Ctrl+S | Save configuration |
| Ctrl+D | Connect to device |
| Ctrl+E | Connect to emulator |
| F2 | Save to flash |
| F7 | Toggle Configuration panel |
| F8 | Toggle Monitor panel |
| F9 | PMU Monitor tab |
| F10 | Outputs Monitor tab |
| F11 | Analog Monitor tab |
| F12 | Variables Inspector tab |

## Architecture Overview

```
+------------------------------------------------------------------+
|                        Main Window                                |
+------------------------------------------------------------------+
|  Menu Bar: File | Edit | Device | Windows | Help                 |
+------------------+-----------------------------------------------+
|                  |                                               |
|   Project Tree   |              Monitor Tabs                     |
|   (Left Dock)    |              (Right Dock)                     |
|                  |                                               |
|   - Inputs       |   [PMU] [OUT] [AIN] [DIN] [HB] [VAR] [CAN]   |
|   - Outputs      |   [LOG] [LOGS] [EMU] [PID]                   |
|   - Functions    |                                               |
|   - Tables       |   +---------------------------------------+   |
|   - State        |   |                                       |   |
|   - Scripts      |   |     Real-time monitoring content      |   |
|   - Handlers     |   |                                       |   |
|   - Peripherals  |   +---------------------------------------+   |
|                  |                                               |
+------------------+-----------------------------------------------+
|  Status Bar: [Message] [Output LEDs] [System LEDs] [Connection]  |
+------------------------------------------------------------------+
```

## Theme

The configurator uses a dark theme optimized for automotive/industrial use:

- **Background**: Pure black (#000000)
- **Text**: White (#FFFFFF)
- **Headers**: Dark gray (#2D2D2D)
- **Selection**: Windows blue (#0078D4)
- **Active states**: Green (#325032)
- **Fault states**: Red (#503028)
- **PWM states**: Blue (#003250)
