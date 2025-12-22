# PMU-30 Configurator - Professional UI

## Launch

Two interface options are available:

### 1. Professional Style (Recommended)
```bash
cd configurator
python src/main_professional.py
```

**Features:**
- Dock-based layout
- Project Tree with hierarchical structure
- Real-time monitoring (Output Monitor, Analog Monitor)
- Variables Inspector for CAN data and PMU status
- Panel drag & drop
- Save/restore layout
- More compact - everything on one screen

### 2. Classic Style (Tabs)
```bash
cd configurator
python src/main.py
```

**Features:**
- Traditional tabbed interface
- Each function on a separate tab
- Suitable for detailed configuration

## Professional Style - Main Components

### Project Tree (Central Panel)
Hierarchical tree of all configuration elements:

```
├─ OUT
│  ├─ o_IgnitionCoils
│  ├─ o_Injectors
│  └─ o_WaterPump
├─ IN
│  ├─ in.Wipers
│  ├─ in.BrakeSwitch
│  └─ in.ClutchSwitch
├─ Functions
│  └─ s_boost_counter
├─ H-Bridge
├─ PID Controllers
└─ Lua Scripts
```

**Control Buttons:**
- **Add** - Add new element
- **Duplicate** - Duplicate selected
- **Delete** - Delete
- **Edit** - Edit
- **Move up/down** - Move up/down
- **Group** - Create group/folder
- **Ungroup** - Ungroup

**Context Menu:** Right-click on element

### Output Monitor
Real-time output channel monitoring:

| Pin | Name | Status | V | Load |
|-----|------|--------|---|------|
| O1  | o_IgnitionCoils | ? | ? | ? |
| O2  | o_Injectors | ? | ? | ? |

**When connected to device:**
- Status: ON/OFF/FAULT
- V: Voltage
- Load: Current (A)

### Analog Monitor
Analog input monitoring:

| Pin | Name | Value | V |
|-----|------|-------|---|
| A1  | in.Wipers | ? | ? |
| A2  | in.BrakeSwitch | ? | ? |

### Variables Inspector
Variable inspector:
- **CAN Variables** - c_ecu_rpm, c_ecu_map, c_ecu_boost, etc.
- **PMU** - Board temperature, Battery voltage, Flash temperature

## Working with Panels

### Drag & Drop
1. Grab panel header
2. Drag to desired location:
   - Left of center
   - Right of center
   - Top
   - Bottom
   - Or make it floating

### Resize
- Drag border between panels
- Proportions will be preserved

### Hide/Show
- **Windows → Output Monitor** - toggle visibility
- **Windows → Analog Monitor**
- **Windows → Variables Inspector**
- **X** button on panel closes it

### Saving Layout
1. **Desktops → Save Layout** - save current arrangement
2. **Desktops → Restore Default Layout** - restore to default
3. Layout is automatically saved on close

## Keyboard Shortcuts

### File
- **Ctrl+N** - New Configuration
- **Ctrl+O** - Open Configuration
- **Ctrl+S** - Save Configuration
- **Ctrl+Shift+S** - Save As
- **Ctrl+Q** - Exit

### Device
- **Ctrl+D** - Connect to Device

## Menu

### File
- New Configuration
- Open Configuration
- Save Configuration
- Save Configuration As
- Exit

### Edit
- Settings

### Desktops
- Save Layout
- Restore Default Layout

### Devices
- Connect
- Disconnect
- Read Configuration
- Write Configuration

### Tools
- CAN Monitor
- Data Logger

### Windows
- Output Monitor
- Analog Monitor
- Variables Inspector

### View
- Dark Mode (on/off)
- Application Style
  - Fluent Design (Custom)
  - windows11
  - windowsvista
  - Windows
  - Fusion

### Help
- Documentation
- About

## Adding Elements

### Method 1: Via Buttons
1. Select folder in tree (e.g., OUT)
2. Click **Add** button
3. Fill in dialog
4. Click OK

### Method 2: Context Menu
1. Right-click on folder
2. Select "Add Item"
3. Fill in dialog

### Method 3: Double-click
- Double-click on element opens editor

## Element Grouping

### Create Group
1. Select folder or element
2. Click **Group** button
3. "New Group" will appear
4. Rename with double-click

### Ungroup
1. Select group
2. Click **Ungroup** button
3. All elements will move to parent folder

## Status Bar

Bottom panel shows:
- Device status: **OFFLINE** / **ONLINE**
- CAN1: CAN bus 1 status
- CAN2: CAN bus 2 status
- OUTPUTS: Output channel status

## Differences Between Classic and Professional Style

| Feature | Classic | Professional |
|---------|---------|--------------|
| Layout | Tabs | Dock widgets |
| Monitoring | Separate tab | Always visible |
| Organization | By type | Hierarchical tree |
| Grouping | No | Yes (folders) |
| Drag & Drop | No | Yes |
| Compactness | Medium | High |
| All on screen | No | Yes |

## Recommendations

### For Beginners
**Classic Style** - easier for first introduction

### For Experienced Users
**Professional Style** - more features, more compact, more convenient

### For Large Configurations
**Professional Style** - grouping and tree help organize

### For Monitoring
**Professional Style** - real-time monitoring is always visible

## Known Limitations

1. Real-time data requires device connection (not yet implemented)
2. Some features will be added later:
   - CAN Monitor
   - Data Logger
   - Live Tuning

## Compatibility

Both interfaces use the same configuration format (JSON).
You can open a file created in Classic in Professional and vice versa.

## Feedback

If you find problems or have suggestions:
- GitHub Issues: https://github.com/r2msport/pmu-30-configurator/issues

---

**© 2025 R2 m-sport. All rights reserved.**
