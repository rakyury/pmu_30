# Project Tree

The Project Tree is the main configuration panel that displays all channels organized in a hierarchical structure. It's located in the left dock panel.

## Tree Structure

```
Inputs/
  +-- Digital Inputs
  |     +-- [D1] Ignition Switch
  |     +-- [D2] Door Sensor
  |     ...
  +-- Analog Inputs
  |     +-- [A1] Fuel Level
  |     +-- [A2] Oil Pressure
  |     ...
  +-- CAN Inputs (CAN_RX)
        +-- Engine RPM
        +-- Coolant Temp
        ...

Outputs/
  +-- Power Outputs
  |     +-- [O1-O3] Headlights (merged)
  |     +-- [O4] Tail Lights
  |     ...
  +-- H-Bridge Motors
  |     +-- [HB1] Window Motor
  |     ...
  +-- CAN Outputs (CAN_TX)
        +-- Dashboard Message
        ...

Functions/
  +-- Logic
  |     +-- Headlight Logic
  |     ...
  +-- Math (Number channels)
  |     +-- Voltage Average
  |     ...
  +-- Filters
  |     +-- Fuel Level Filter
  |     ...
  +-- PID Controllers
        +-- Fan Speed PID
        ...

Tables/
  +-- 2D Tables
  |     +-- PWM Curve
  |     ...
  +-- 3D Tables
        +-- Fuel Map
        ...

State/
  +-- Switches
  |     +-- Mode Selector
  |     ...
  +-- Timers
        +-- Turn Signal Timer
        ...

Scripts/
  +-- Lua Scripts
        +-- Custom Logic
        ...

Handlers/
  +-- Event Handlers
        +-- Fault Handler
        ...

Peripherals/
  +-- CAN Keypads
        +-- BlinkMarine Keypad
        ...
```

## Display Columns

| Column | Content | Example |
|--------|---------|---------|
| Name | Channel display name with status icon | `[*] Headlights` |
| Details | Configuration summary | `O1-O3, PWM 1kHz` |
| Source | Input channel references | `Digital Input 1` |

## Status Icons

Each channel type has a colored status indicator:

| Type | Color | Hex |
|------|-------|-----|
| Digital Input | Blue | #4A90D9 |
| Analog Input | Blue | #4A90D9 |
| Power Output | Purple | #9B59B6 |
| H-Bridge | Purple | #9B59B6 |
| Logic | Cyan | #00BCD4 |
| Math/Number | Cyan | #00BCD4 |
| Tables | Teal | #009688 |
| CAN Input/Output | Orange | #FF9800 |
| Lua Script | Lime | #8BC34A |
| Timer | Pink | #E91E63 |
| Switch | Pink | #E91E63 |
| Peripheral | Violet | #673AB7 |
| Handler | Red-Pink | #F44336 |

## Toolbar Buttons

Located above the tree:

| Button | Action |
|--------|--------|
| **Add** | Add new channel (opens type selector) |
| **Edit** | Edit selected channel |
| **Delete** | Remove selected channel |
| **Duplicate** | Copy selected channel |

## Context Menu (Right-Click)

| Item | Description |
|------|-------------|
| Add | Add new channel of same type |
| Edit | Open configuration dialog |
| Duplicate | Create copy with new ID |
| Show Dependents | List channels that use this one |
| Delete | Remove channel (with confirmation) |

## Interactions

### Single Click
- Selects the item
- Updates status bar with item info
- Disabled for folder items (only channels selectable)

### Double Click
- Opens the edit dialog for the channel
- Same as clicking Edit button

### Drag and Drop
- Channels can be reordered within their category
- Cannot move channels between categories

## Name Display Priority

The tree displays channel names using this priority:

1. `channel_name` field (user-friendly name)
2. `name` field (fallback)
3. `id` field (last resort)

## Details Column Format

The Details column shows configuration summary based on channel type:

| Channel Type | Details Format |
|--------------|----------------|
| Digital Input | `Pin D{n}, {pull_mode}, {subtype}` |
| Analog Input | `Pin A{n}, {type}, {range}` |
| Power Output | `O{pins}, {frequency}Hz` |
| H-Bridge | `HB{n}, {mode}` |
| Logic | `{function_type}` |
| Timer | `{delay}ms` |
| CAN Input | `0x{id}, {signal}` |

## Source Column

Shows which channels are used as inputs:

```
Logic: Headlight Logic
  Source: "Ignition Switch, Light Sensor"

Filter: Fuel Average
  Source: "Fuel Level Sensor"

Table 2D: PWM Curve
  Source: "Throttle Position"
```

## Auto-Collapse Behavior

- Top-level folders (Inputs, Outputs, etc.) start expanded
- Subfolders with more than 10 items auto-collapse on load
- Collapse state is preserved during the session

## Search Functionality

Press `Ctrl+F` to open the channel search dialog:

- Case-insensitive search
- Searches in name and ID
- Results highlight matching items
- Enter jumps to first match

## Adding New Channels

1. Click **Add** button or right-click folder
2. Select channel type from dialog
3. Configure channel in type-specific dialog
4. Click OK to add to tree

### Channel Type Selector

When adding, you choose from:

| Category | Types |
|----------|-------|
| Inputs | Digital Input, Analog Input, CAN Input |
| Outputs | Power Output, H-Bridge, CAN Output |
| Functions | Logic, Number, Filter, PID |
| Tables | 2D Table, 3D Table |
| State | Switch, Timer |
| Advanced | Lua Script, Handler, CAN Keypad |

## Channel ID Assignment

- IDs are auto-generated sequentially
- Digital Inputs: 1-20
- Analog Inputs: 21-40
- Power Outputs: 100-139
- H-Bridges: 150-153
- Logic/Virtual: 200+
- CAN: 300+

## Validation

The tree validates:
- **Unique names** - Warning on duplicate names
- **Valid references** - Error if source channel doesn't exist
- **Circular dependencies** - Prevents self-referencing loops

## Styling

```
Font: Sans-serif, 11px
Row Height: 24px
Icon Size: 12px circles
Indent: 20px per level
```

### Folder Styling
- **Top-level folders**: Bold text
- **Type subfolders**: Italic text
- **Empty folders**: Grayed out

### Selected Item
- Background: #0078D4 (Windows Blue)
- Text: White
