# UI Improvements

## Changes Made - 2025-12-21

### 1. Channel Selection Dropdown

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

### 2. Visual Consistency - Label Colors

**Problem**: Labels in dialogs had different background color than their parent QGroupBox controls, breaking visual consistency.

**Solution**: Updated [theme.py](../src/utils/theme.py:150-153) to make QLabel backgrounds transparent:
```css
QLabel {
    color: #d4d4d4;
    background-color: transparent;
}
```

This ensures labels inherit the background color from their parent widgets, creating a seamless, professional appearance.

### 3. Implementation Details

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

### 4. Testing

All 28 unit tests passing:
- 13 tests for ConfigManager
- 15 tests for JSON validation

Tests verify:
- Configuration save/load with validation
- Duplicate channel detection
- Array size limits (20 inputs, 30 outputs)
- Type validation
- Error message formatting

### 5. User Experience Improvements

**Before:**
- Users could select any channel number, even if already in use
- Required manual tracking of which channels were available
- Labels had visible background color mismatch in dark mode

**After:**
- Users only see available channels in dropdown
- Impossible to create duplicate channel assignments
- Clean, consistent visual appearance
- Professional dark theme with proper color inheritance
