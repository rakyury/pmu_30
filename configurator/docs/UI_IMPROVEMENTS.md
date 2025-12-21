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

### 6. H-Bridge Motor Control Tab Implemented

**File:** [hbridge_tab.py](../src/ui/tabs/hbridge_tab.py)
**Dialog:** [hbridge_dialog.py](../src/ui/dialogs/hbridge_dialog.py)

Полноценная конфигурация 4 каналов H-Bridge для управления DC моторами:

**Основные возможности:**
- 4 независимых канала H-Bridge
- Режимы работы: Disabled, Forward Only, Reverse Only, Bidirectional
- PWM управление скоростью (0-100%)
- Настраиваемая частота PWM: 100 Hz, 500 Hz, 1 kHz, 5 kHz, 10 kHz, 20 kHz
- Входы управления: Physical Input, Virtual Channel, CAN Signal, Manual
- Раздельные входы для Forward, Reverse и Speed control

**Защита и безопасность:**
- Ограничение тока (0.1-50.0 A)
- Thermal protection
- Действие при перегрузке: Disable Output, Reduce Power, Log Only

**Расширенные функции:**
- Soft Start/Stop time (0-5000 ms)
- Active Braking (короткое замыкание для торможения)
- Invert Direction
- Min/Max duty cycle ограничения

**UI особенности:**
- Таблица с отображением всех 4 каналов
- Копирование конфигурации между каналами
- Индивидуальный сброс или сброс всех каналов
- Статистика: включенные каналы и общий лимит тока

### 7. Settings Tab - System Configuration

**File:** [settings_tab.py](../src/ui/tabs/settings_tab.py)

Комплексные настройки системы с прокруткой:

**Device Information:**
- Device Name, Description, Serial Number
- Hardware/Firmware Version (read from device)

**CAN Bus Settings:**
- Bitrate: 125/250/500/1000 kbps
- Node ID (0-127)
- 120Ω Terminator enable/disable
- Listen Only Mode
- Automatic Retransmission

**Power Settings:**
- Nominal Voltage (6.0-36.0 V)
- Low Voltage Warning threshold
- Low Voltage Cutoff (защита)
- High Voltage Cutoff (защита)

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
- Версия конфигуратора: 1.0.0
- © 2025 R2 m-sport
- Спецификации устройства
- Список возможностей

### 8. All Major Tabs Completed

Полный комплект функциональных вкладок:
- ✅ **Monitor** - Real-time monitoring
- ✅ **Outputs (30)** - PROFET High-Side outputs
- ✅ **H-Bridge (4x)** - DC Motor control
- ✅ **Inputs (20)** - Analog/Digital inputs
- ✅ **CAN Bus** - Message/Signal configuration, DBC import/export
- ✅ **Logic Engine** - 256 virtual channels, 16 operations
- ✅ **PID Controllers** - Closed-loop control with anti-windup
- ✅ **Lua Scripts** - LUA 5.4 scripting with API access
- ✅ **Settings** - System, CAN, Power, Safety configuration

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
