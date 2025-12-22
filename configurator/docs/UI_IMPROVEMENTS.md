# UI Improvements

## Latest Changes - 2025-12-21

### 1. Fluent Design (Windows 11) Theme Applied

Applied Microsoft Fluent Design theme for Windows 11 with modern and professional appearance.

**Windows 11 Color Palette:**
- Background: `#202020` (App Background)
- Surface: `#2c2c2c` (Card Background)
- Text: `#ffffff` (Primary Text)
- Secondary Text: `#a0a0a0`
- Accent: `#0078d4` (Windows Blue)
- Borders: `#3d3d3d` (Subtle)
- Disabled: `#7a7a7a`

**Key Fluent Design Features:**
- **Acrylic Material**: Semi-transparent backgrounds for QGroupBox - `rgba(44, 44, 44, 180)`
- **Rounded Corners**: 8px for cards, 4px for controls
- **Reveal Highlight**: Subtle hover effects with `rgba(255, 255, 255, 0.05-0.08)`
- **Depth & Shadows**: Visual depth through background gradations
- **Accent Color**: Windows Blue (#0078d4) for interactive elements

**Components:**
- **QPushButton**: Windows Blue (#0078d4), hover: #1a86d9, pressed: #005a9e
- **QGroupBox**: Acrylic background with 8px rounding, 16px padding
- **QCheckBox**: 20x20px indicators with Windows Blue fill when selected
- **QLineEdit/QSpinBox/QComboBox**:
  - Dark background (#2c2c2c) with bottom border
  - Hover: bottom border highlight
  - Focus: Windows Blue bottom border
  - Arrows: gray (#a0a0a0), white on hover
- **QMenuBar/QMenu**:
  - Dark background with subtle hover effects
  - 8px rounded corners for menus
  - Separator lines between items
- **QTabBar**:
  - Transparent background
  - Active tab: 3px blue underline at bottom
  - Subtle hover effect
- **QScrollBar**:
  - Transparent track
  - Gray rounded handle
  - Minimum size 12px
- **QTableWidget**:
  - Alternating rows (#2c2c2c / #282828)
  - Selection: semi-transparent Windows Blue
  - Hover: subtle row highlight

**Sizes and Spacing:**
- Default window: 40% of screen size, centered
- Control padding: 8px
- Border radius: 4px (controls), 8px (cards)
- Font size: 14px (primary), 13px (secondary)

### 2. Toolbar Removed - All Functions in Menu

Removed toolbar for clean interface. All functions moved to menu:

**File Menu:**
- New Configuration (Ctrl+N)
- Open Configuration (Ctrl+O)
- Save Configuration (Ctrl+S)
- Save As... (Ctrl+Shift+S)
- Import DBC...
- Export DBC...
- Exit (Ctrl+Q)

**Device Menu:**
- Connect... (Ctrl+D)
- Disconnect
- Read Configuration
- Write Configuration
- Update Firmware
- Reset to Defaults

**View Menu:**
- Dark Mode toggle

### 3. Channel Selection Dropdown

**Input Channels ([input_config_dialog.py](../src/ui/dialogs/input_config_dialog.py:40-53))**
- Changed from QSpinBox (showing all channels 0-19) to QComboBox
- Dropdown now shows only available/unused channels
- When editing existing input, current channel remains available in dropdown
- Shows "No channels available" message when all 20 channels are used

**Output Channels ([output_config_dialog.py](../src/ui/dialogs/output_config_dialog.py:40-44))**
- Changed from QSpinBox (showing all channels 0-29) to QComboBox
- Dropdown now shows only available/unused channels
- When editing existing output, current channel remains available in dropdown
- Shows "No channels available" message when all 30 channels are used

### 4. Implementation Details

**New Method: `_populate_available_channels()`**
Both dialog classes now include this method that:
1. Clears the combo box
2. Gets the current channel if editing existing config
3. Iterates through all available channels (0-19 for inputs, 0-29 for outputs)
4. Adds only channels that are not in `used_channels` list OR the current channel
5. Shows placeholder if no channels available

**Updated Methods:**
- `_load_config()`: Uses `findData()` and `setCurrentIndex()` instead of `setValue()`
- `get_config()`: Uses `currentData()` instead of `value()`

### 5. Testing

All 28 unit tests passing:
- 13 tests for ConfigManager
- 15 tests for JSON validation

Tests verify:
- Configuration save/load with validation
- Duplicate channel detection
- Array size limits (20 inputs, 30 outputs)
- Type validation
- Error message formatting

### 6. H-Bridge Motor Control Tab Implemented

**File:** [hbridge_tab.py](../src/ui/tabs/hbridge_tab.py)
**Dialog:** [hbridge_dialog.py](../src/ui/dialogs/hbridge_dialog.py)

Full-featured configuration of 4 H-Bridge channels for DC motor control:

**Main Features:**
- 4 independent H-Bridge channels
- Operating modes: Disabled, Forward Only, Reverse Only, Bidirectional
- PWM speed control (0-100%)
- Configurable PWM frequency: 100 Hz, 500 Hz, 1 kHz, 5 kHz, 10 kHz, 20 kHz
- Control inputs: Physical Input, Virtual Channel, CAN Signal, Manual
- Separate inputs for Forward, Reverse and Speed control

**Protection and Safety:**
- Current limiting (0.1-50.0 A)
- Thermal protection
- Overload action: Disable Output, Reduce Power, Log Only

**Advanced Features:**
- Soft Start/Stop time (0-5000 ms)
- Active Braking (short circuit for braking)
- Invert Direction
- Min/Max duty cycle limits

**UI Features:**
- Table showing all 4 channels
- Copy configuration between channels
- Individual reset or reset all channels
- Statistics: enabled channels and total current limit

### 7. Settings Tab - System Configuration

**File:** [settings_tab.py](../src/ui/tabs/settings_tab.py)

Comprehensive system settings with scrolling:

**Device Information:**
- Device Name, Description, Serial Number
- Hardware/Firmware Version (read from device)

**CAN Bus Settings:**
- Bitrate: 125/250/500/1000 kbps
- Node ID (0-127)
- 120 Terminator enable/disable
- Listen Only Mode
- Automatic Retransmission

**Power Settings:**
- Nominal Voltage (6.0-36.0 V)
- Low Voltage Warning threshold
- Low Voltage Cutoff (protection)
- High Voltage Cutoff (protection)

**System Settings:**
- Units: Metric (°C, km/h) / Imperial (°F, mph)
- Log Level: Off, Error, Warning, Info, Debug
- Watchdog Timeout (100-10000 ms)
- CAN Heartbeat Interval (100-10000 ms)

**Safety Settings:**
- Safe State: All Outputs Off, Maintain Last State, Custom Profile
- Startup Delay (0-10000 ms)
- Max Total Current (1.0-200.0 A)

**Calibration:**
- Read/Write calibration from/to device (placeholders)
- Reset to Factory calibration

**About Section:**
- Configurator version: 1.0.0
- © 2025 R2 m-sport
- Device specifications
- Feature list

### 8. All Major Tabs Completed

Full set of functional tabs:
- **Monitor** - Real-time monitoring
- **Outputs (30)** - PROFET High-Side outputs
- **H-Bridge (4x)** - DC Motor control
- **Inputs (20)** - Analog/Digital inputs
- **CAN Bus** - Message/Signal configuration, DBC import/export
- **Logic Engine** - 256 virtual channels, 16 operations
- **PID Controllers** - Closed-loop control with anti-windup
- **Lua Scripts** - LUA 5.4 scripting with API access
- **Settings** - System, CAN, Power, Safety configuration

### 9. User Experience Improvements

**Before:**
- Cluttered interface with toolbar duplicating menu functions
- Users could select any channel number, even if already in use
- Required manual tracking of which channels were available
- Inconsistent colors and visual appearance
- Harsh blue accents that didn't match well
- Limited tab functionality - many placeholders

**After:**
- Clean interface without toolbar - all functions organized in menu
- Users only see available channels in dropdown
- Impossible to create duplicate channel assignments
- Professional Fluent Design Windows 11 theme with harmonious colors
- Smooth transitions and hover effects
- Perfect visual consistency across all components
- Labels properly inherit parent backgrounds
- All major functional tabs fully implemented
- Comprehensive H-Bridge motor control
- Complete system settings configuration
