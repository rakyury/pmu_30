## PMU-30 Configurator - Professional UI Design

### Architecture

The new interface design follows a professional PDM client concept with a central project tree and docked monitoring panels.

### Main Components

#### 1. Project Tree (Central Project Tree)
**File:** `src/ui/widgets/project_tree.py`

**Tree Structure:**
```
├─ OUT (Outputs 0-29)
│  ├─ o_IgnitionCoils
│  ├─ o_Injectors
│  └─ o_WaterPump
│
├─ IN (Inputs 0-19)
│  ├─ in.Wipers
│  ├─ in.BrakeSwitch
│  └─ in.ClutchSwitch
│
├─ Functions (Logic Functions)
│  ├─ s_boost_counter
│  ├─ s_als_1
│  └─ s_als_2
│
├─ Switches
├─ CAN
├─ Timers
├─ Tables
├─ Numbers
├─ H-Bridge (4 channels)
├─ PID Controllers
└─ Lua Scripts
```

**Features:**
- Drag & Drop for reorganization
- Grouping into folders (Group/Ungroup)
- Context menu (Add, Edit, Delete, Duplicate)
- Control buttons: Add, Duplicate, Delete, Edit, Move up/down, Group, Ungroup

#### 2. Output Monitor
**File:** `src/ui/widgets/output_monitor.py`

**Table:**
| Pin | Name | Status | V | Load |
|-----|------|--------|---|------|
| O1  | o_IgnitionCoils | ? | ? | ? |
| O2  | o_Injectors | ? | ? | ? |
| O3  | o_WaterPump | ? | ? | ? |

**Real-time data** (when connected to device):
- Status: ON/OFF/FAULT
- V: Voltage
- Load: Current (A)

#### 3. Analog Monitor
**File:** `src/ui/widgets/analog_monitor.py`

**Table:**
| Pin | Name | Value | V |
|-----|------|-------|---|
| A1  | in.Wipers | ? | ? |
| A2  | in.BrakeSwitch | ? | ? |
| A3  | in.ClutchSwitch | ? | ? |

**Real-time data:**
- Value: Current value (0-100, True/False, etc.)
- V: Voltage

#### 4. Variables Inspector
**File:** `src/ui/widgets/variables_inspector.py`

**Structure:**
```
Variables Inspector
├─ CAN Variables
│  ├─ c_ecu_rpm (? rpm)
│  ├─ c_ecu_map (? kPa)
│  ├─ c_ecu_boost (? bar)
│  ├─ c_ecu_tps (? %)
│  ├─ c_ecu_clt (? °C)
│  ├─ c_ecu_batt (? V)
│  └─ ...
│
└─ PMU
   ├─ Board temperature 1 (? °C)
   ├─ Battery voltage (? V)
   ├─ Board temperature 2 (? °C)
   ├─ 5V output (? V)
   └─ Flash temperature (? °C)
```

### Layout (QDockWidget)

```
┌────────────────────────────────────────────────────┐
│  Menu Bar: File | Edit | Desktops | Devices | ...  │
├────────────────────────────────────────────────────┤
│                                                    │
│  ┌──────────────┐  ┌────────────────────────────┐ │
│  │              │  │   Output Monitor           │ │
│  │              │  │  ┌──────┬─────┬──┬──┬────┐ │ │
│  │              │  │  │ O1   │ ... │  │  │    │ │ │
│  │  Project     │  │  └──────┴─────┴──┴──┴────┘ │ │
│  │  Tree        │  ├────────────────────────────┤ │
│  │              │  │   Analog Monitor           │ │
│  │ ├─ OUT       │  │  ┌──────┬─────┬────┬──┐   │ │
│  │ ├─ IN        │  │  │ A1   │ ... │    │  │   │ │
│  │ ├─ Functions │  │  └──────┴─────┴────┴──┘   │ │
│  │ ├─ CAN       │  └────────────────────────────┘ │
│  │ └─ ...       │                                  │
│  │              │  ┌────────────────────────────┐ │
│  │ [Add]        │  │  Variables Inspector       │ │
│  │ [Edit]       │  │  ├─ CAN Variables          │ │
│  │ [Delete]     │  │  │  ├─ c_ecu_rpm           │ │
│  │ [Move up]    │  │  │  └─ ...                 │ │
│  │ [Group]      │  │  └─ PMU                    │ │
│  │              │  │     ├─ Battery voltage     │ │
│  └──────────────┘  │     └─ ...                 │ │
│                    └────────────────────────────┘ │
├────────────────────────────────────────────────────┤
│  Status: OFFLINE │ CAN1: │ CAN2: ? │ OUTPUTS:    │
└────────────────────────────────────────────────────┘
```

### Capabilities

1. **Drag & Drop**
   - Dock widgets can be dragged
   - Can be docked left, right, top, bottom
   - Can be made floating windows

2. **Resize**
   - All panels are resizable
   - Proportions are maintained when resizing main window

3. **Hide/Show**
   - Each panel can be hidden via View menu
   - "X" button on panel closes it
   - View → Panels for toggling

4. **Layout Saving**
   - Layout is saved on exit
   - Restored on startup
   - Can be reset to default

### Integration with Existing Tabs

Old tabs (Settings, Configuration) are accessible via menu or buttons:
- **Tools → Configuration** - opens settings as dialog
- **Device → Settings** - opens device settings

### Advantages of New Approach

1. **More compact** - everything on one screen
2. **Professional interface** - familiar interface for users
3. **Real-time monitoring** - see everything at once
4. **Flexible layout** - can be customized to preference
5. **Grouping** - easy to organize large configurations

### Implementation

**Files:**
- `src/ui/widgets/project_tree.py` - Project tree
- `src/ui/widgets/output_monitor.py` - Output monitor
- `src/ui/widgets/analog_monitor.py` - Input monitor
- `src/ui/widgets/variables_inspector.py` - Variables inspector
- `src/ui/main_window_professional.py` - Main window

**Status:**
- Project Tree - implemented
- Output Monitor - implemented
- Analog Monitor - implemented
- Variables Inspector - implemented
- Main Window Integration - implemented
- Dock Widgets Setup - implemented
- Layout Saving/Restore - implemented
- Real-time Updates - TODO (requires device connection)

### Next Steps

1. Connect real-time updates from device
2. Add CAN Monitor tool
3. Add Data Logger tool
4. Testing with configurations
