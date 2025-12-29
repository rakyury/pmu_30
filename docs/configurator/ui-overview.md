# UI Overview

The PMU-30 Configurator uses a dock-based layout optimized for professional automotive configuration and real-time monitoring.

## Main Window Layout

```
+------------------------------------------------------------------+
|                           Menu Bar                                |
+------------------+-----------------------------------------------+
|                  |                                               |
|   Configuration  |              Monitor Panel                    |
|      Panel       |              (Tabbed)                         |
|   (Left Dock)    |                                               |
|                  |   Tabs: PMU | OUT | AIN | DIN | HB | VAR |   |
|   Contains:      |         CAN | LOG | LOGS | EMU | PID          |
|   Project Tree   |                                               |
|                  |   Shows real-time data from device            |
|                  |                                               |
+------------------+-----------------------------------------------+
|                        Status Bar                                 |
|  [Status Message]  [Output LEDs]  [System LEDs]  [Connection]    |
+------------------------------------------------------------------+
```

## Window Properties

| Property | Value |
|----------|-------|
| Default Size | 70% of screen dimensions |
| Position | Centered on launch |
| Minimum Width | 1024px |
| Minimum Height | 768px |

## Dock System Features

- **Animated docks** with smooth transitions
- **Magnetic snapping** when dragging panels
- **Nested docking** - panels can be docked inside each other
- **Tabbed docking** - multiple panels can share space as tabs
- **Resizable** - drag borders to resize panels
- **Detachable** - panels can float as separate windows

## Menu Bar

### File Menu
| Item | Shortcut | Description |
|------|----------|-------------|
| New | Ctrl+N | Create empty configuration |
| Open | Ctrl+O | Load JSON configuration file |
| Save | Ctrl+S | Save current configuration |
| Save As | Ctrl+Shift+S | Save to new file |
| Exit | Ctrl+Q | Close application |

### Edit Menu
| Item | Shortcut | Description |
|------|----------|-------------|
| Undo | Ctrl+Z | Undo last change |
| Redo | Ctrl+Y | Redo undone change |
| Search Channels | Ctrl+F | Find channels by name |
| CAN Messages | Ctrl+M | Open CAN message manager |
| CAN Import | Ctrl+I | Import DBC/KCD files |
| Settings | - | Application settings |

### Device Menu
| Item | Shortcut | Description |
|------|----------|-------------|
| Connect | Ctrl+D | Connect to PMU-30 device |
| Connect to Emulator | Ctrl+E | Connect to software emulator |
| Disconnect | - | Close device connection |
| Save to Flash | F2 | Write config to permanent storage |
| Compare Configurations | Ctrl+Shift+C | Diff device vs file config |
| Restart | Ctrl+Shift+R | Restart connected device |
| WiFi Settings | - | Configure WiFi parameters |
| Bluetooth Settings | - | Configure Bluetooth parameters |

### Windows Menu
| Item | Shortcut | Description |
|------|----------|-------------|
| Configuration Panel | F7 | Toggle left dock visibility |
| Monitor Panel | F8 | Toggle right dock visibility |
| PMU Monitor | F9 | Switch to PMU Monitor tab |
| Outputs Monitor | F10 | Switch to Outputs tab |
| Analog Monitor | F11 | Switch to Analog tab |
| Variables Inspector | F12 | Switch to Variables tab |
| Reset Layout | - | Restore default panel layout |

### Help Menu
| Item | Description |
|------|-------------|
| Documentation | Open user manual |
| About | Version and license info |

## Status Bar

The status bar at the bottom displays:

### 1. Status Message (left)
Dynamic text showing current operation status:
- "Ready" - idle state
- "Connected to [device]" - connection established
- "Saving configuration..." - during save operation
- Error messages in red

### 2. Output LED Bar (center-left)
Visual indicator showing state of all 40 power outputs:

```
[O1][O2][O3]...[O40]
```

| Color | State |
|-------|-------|
| Gray | OFF or unconfigured |
| Green | ON (active) |
| Blue | PWM mode |
| Red | Fault condition |
| Yellow | Warning |

### 3. System LED Panel (center-right)
Firmware-style status indicators:

| LED | Indicates |
|-----|-----------|
| PWR | Power good |
| CAN1 | CAN bus 1 active |
| CAN2 | CAN bus 2 active |
| ERR | System error |
| COMM | Communication active |

### 4. Connection Status (right)
Shows current connection state:
- **Offline** - No connection (gray)
- **Device: COM3** - Connected to hardware (green)
- **Emulator** - Connected to software emulator (blue)
- Includes telemetry rate indicator (e.g., "10 Hz")

## Panel Visibility

Both dock panels can be hidden/shown:

| Panel | Toggle | Default |
|-------|--------|---------|
| Configuration (Left) | F7 | Visible |
| Monitor (Right) | F8 | Visible |

When both panels are hidden, only the menu bar and status bar remain visible.

## Theme Colors

| Element | Color | Hex |
|---------|-------|-----|
| Background | Black | #000000 |
| Text | White | #FFFFFF |
| Headers | Dark Gray | #2D2D2D |
| Borders | Very Dark Gray | #333333 |
| Selection | Windows Blue | #0078D4 |
| Active/ON | Dark Green | #325032 |
| Fault/Error | Dark Red | #503028 |
| PWM Mode | Dark Blue | #003250 |
| Warning | Dark Orange | #643C00 |
| Disabled | Gray | #3C3C3C |

## Update Rates

| Component | Refresh Rate |
|-----------|--------------|
| Monitor Tables | 10 Hz (100ms) |
| Output LEDs | 10 Hz (100ms) |
| System LEDs | 10 Hz (100ms) |
| Variables Inspector | 4 Hz (250ms) color decay |
| Data Logger | 50-500 Hz (configurable) |
