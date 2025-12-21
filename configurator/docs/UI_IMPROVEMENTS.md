# UI Improvements

## Latest Changes - 2025-12-21

### 1. Fluent Design (Windows 11) Theme Applied

Применена тема Microsoft Fluent Design для Windows 11 с современным и профессиональным внешним видом.

**Цветовая палитра Windows 11:**
- Background: `#202020` (App Background)
- Surface: `#2c2c2c` (Card Background)
- Text: `#ffffff` (Primary Text)
- Secondary Text: `#a0a0a0`
- Accent: `#0078d4` (Windows Blue)
- Borders: `#3d3d3d` (Subtle)
- Disabled: `#7a7a7a`

**Ключевые особенности Fluent Design:**
- **Acrylic Material**: Полупрозрачные фоны для QGroupBox - `rgba(44, 44, 44, 180)`
- **Rounded Corners**: Закругленные углы 8px для карточек, 4px для контролов
- **Reveal Highlight**: Subtle hover эффекты с `rgba(255, 255, 255, 0.05-0.08)`
- **Depth & Shadows**: Визуальная глубина через градации фона
- **Accent Color**: Windows Blue (#0078d4) для интерактивных элементов

**Компоненты:**
- **QPushButton**: Windows Blue (#0078d4), hover: #1a86d9, pressed: #005a9e
- **QGroupBox**: Acrylic фон с закруглением 8px, padding 16px
- **QCheckBox**: Индикаторы 20x20px с Windows Blue заливкой при выборе
- **QLineEdit/QSpinBox/QComboBox**:
  - Темный фон (#2c2c2c) с нижней границей
  - Hover: подсветка нижней границы
  - Focus: нижняя граница Windows Blue
  - Стрелки: серые (#a0a0a0), белые при hover
- **QMenuBar/QMenu**:
  - Темный фон с subtle hover эффектами
  - Закругленные углы 8px для меню
  - Separator линии между элементами
- **QTabBar**:
  - Прозрачный фон
  - Активная вкладка: 3px синее подчеркивание снизу
  - Subtle hover эффект
- **QScrollBar**:
  - Прозрачный track
  - Закругленные handle серого цвета
  - Минимальный размер 12px
- **QTableWidget**:
  - Альтернативные строки (#2c2c2c / #282828)
  - Selection: полупрозрачный Windows Blue
  - Hover: subtle подсветка строки

**Размеры и отступы:**
- Окно по умолчанию: 40% от размера экрана, центрировано
- Padding контролов: 8px
- Border radius: 4px (контролы), 8px (карточки)
- Font size: 14px (основной), 13px (вторичный)

### 2. Toolbar Removed - All Functions in Menu

Убран toolbar для чистого интерфейса. Все функции перенесены в меню:

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

### 6. User Experience Improvements

**Before:**
- Cluttered interface with toolbar duplicating menu functions
- Users could select any channel number, even if already in use
- Required manual tracking of which channels were available
- Inconsistent colors and visual appearance
- Harsh blue accents that didn't match well

**After:**
- Clean interface without toolbar - all functions organized in menu
- Users only see available channels in dropdown
- Impossible to create duplicate channel assignments
- Professional Catppuccin Mocha theme with harmonious colors
- Smooth transitions and hover effects
- Perfect visual consistency across all components
- Labels properly inherit parent backgrounds
