# Channel System Refactoring Plan

**Version:** 2.0 | **Created:** January 2026

---

## 🚨 КРИТИЧЕСКИЕ ТРЕБОВАНИЯ

> **НИКАКОЙ ОБРАТНОЙ СОВМЕСТИМОСТИ!** Всё с нуля.

### Архитектурные принципы

1. **Никакого хардкода под конкретные платы**
   - Протоколы работают одинаково на dev-бордах и готовых устройствах
   - Нет `#ifdef NUCLEO_F446RE` или подобных проверок
   - Всё определяется через Device Capabilities

2. **Device Capabilities определяют всё**
   - При подключении устройство отправляет свои возможности
   - Конфигуратор адаптирует UI под полученные capabilities
   - То, чего нет — не отображается или показывается заблокированным

3. **Максимальная производительность**
   - Минимальное использование RAM
   - Минимальное использование CPU
   - Zero-copy где возможно
   - Никаких динамических аллокаций в firmware

4. **Поддержка Debug информации**
   - Протокол должен передавать debug данные с устройства
   - Конфигуратор отображает debug в реальном времени
   - Разные уровни детализации (ERROR → TRACE)

5. **Logic Engine = Pure Functions (КРИТИЧНО!)**
   - Логика, таблицы, PID, арифметика — полностью абстрагированы от железа
   - Движок НЕ обращается к каналам напрямую
   - Может работать в desktop-приложении без каналов вообще
   - Чистые функции: `output = logic_evaluate(inputs)` — никаких side effects
   - Firmware передаёт значения в движок и забирает результаты
   - Это упрощает тестирование и отладку

```
┌─────────────────────────────────────────────────────────────────┐
│                      Firmware Architecture                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Channels                Logic Engine               Hardware   │
│   ┌──────────┐           ┌──────────────┐          ┌─────────┐ │
│   │ Timer 1  │──value───>│              │          │ ADC     │ │
│   │ Logic 1  │           │  Pure        │          │ GPIO    │ │
│   │ PID 1    │<──result──│  Functions   │          │ PROFET  │ │
│   │ Table 2D │           │              │          │ H-Bridge│ │
│   └──────────┘           │  No channel  │          └─────────┘ │
│                          │  access!     │                │     │
│   Channel Manager        │              │          HAL Layer   │
│   ┌──────────────────┐   └──────────────┘          ┌─────────┐ │
│   │ Read HW values   │←─────────────────────────── │ Read    │ │
│   │ Feed to engine   │                             │ Write   │ │
│   │ Apply results    │────────────────────────────>│ Control │ │
│   └──────────────────┘                             └─────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Что определяется через Capabilities

| Возможность | Если есть | Если нет |
|-------------|-----------|----------|
| Power Outputs (PROFET) | Показать Output Monitor | Скрыть полностью |
| H-Bridge | Показать H-Bridge Monitor | Скрыть полностью |
| PID Controllers | Показать PID Tuner | Заблокировать |
| 2D/3D Tables | Показать Table Editor | Заблокировать |
| CAN Bus | Показать CAN Monitor | Скрыть полностью |
| WiFi | Показать WiFi настройки | Скрыть полностью |
| Bluetooth | Показать BT настройки | Скрыть полностью |
| GPS | Показать GPS данные | Скрыть полностью |
| Data Logging | Показать Data Logger | Заблокировать |
| Lua Scripting | Показать Lua Editor | Заблокировать |

---

## Executive Summary

Полный рефакторинг системы каналов PMU-30:
- **Унификация**: Все каналы виртуальные (нет разделения на physical/virtual)
- **Бинарный формат**: JSON → Binary для конфигурации
- **Shared Library**: Единая логика для конфигуратора и прошивки
- **Capability-Driven**: Всё определяется возможностями устройства

---

## 1. Текущие проблемы

### 1.1 Архитектурные проблемы

| Проблема | Описание | Влияние |
|----------|----------|---------|
| **Разделение каналов** | Physical (0-199) vs Virtual (200-999) | Разный код для разных платформ |
| **ID Ranges** | Жёсткие диапазоны в коде | Nucleo не влезает, нужны хаки |
| **hw_class confusion** | hw_class используется для разных целей | Путаница в телеметрии |
| **JSON parsing** | Огромный pmu_config_json.c (~3500 строк) | Сложность, баги, RAM |
| **Дублирование** | Парсинг в конфигураторе и прошивке | Рассинхронизация |

### 1.2 Текущая структура (проблемная)

```
Channel ID Ranges (current - hardcoded):
├── 0-49     Digital Inputs (physical)
├── 50-99    Analog Inputs (physical)
├── 100-129  Power Outputs (physical)
├── 150-157  H-Bridge (physical)
├── 200-999  Virtual (timer, logic, math, tables...)
└── 1000+    System channels

Problems:
- На Nucleo PMU_CHANNEL_MAX_CHANNELS=64, не влезает в эту схему
- hw_class >= 0x60 используется для фильтрации "виртуальных"
- JSON парсинг 3000+ строк кода, огромное потребление RAM
```

---

## 2. Новая унифицированная модель

### 2.1 Концепция

**ВСЕ каналы являются виртуальными.** У некоторых есть привязка к физическому железу, у некоторых нет.

```
Channel = {
    id: uint16_t,           // Уникальный ID (user-defined или builtin)
    type: ChannelType,      // Определяет поведение
    name: string[32],       // Человекочитаемое имя
    value: int32_t,         // Текущее значение
    flags: uint8_t,         // enabled, readonly, builtin, inverted...

    // Опциональная привязка к железу
    hw_binding: {
        pin: int8_t,        // -1 = нет привязки, 0-19 = номер пина
        device: HwDevice,   // GPIO, ADC, PWM, DAC, CAN...
    },

    // Type-specific config (union)
    config: TypeSpecificConfig,
}
```

### 2.2 Типы каналов (ChannelType)

```c
typedef enum {
    // Inputs (могут иметь hw_binding)
    CH_TYPE_DIGITAL_INPUT    = 0x01,  // Digital switch/button
    CH_TYPE_ANALOG_INPUT     = 0x02,  // Analog 0-5V sensor
    CH_TYPE_FREQUENCY_INPUT  = 0x03,  // Frequency/RPM
    CH_TYPE_CAN_INPUT        = 0x04,  // CAN bus receive

    // Outputs (могут иметь hw_binding)
    CH_TYPE_POWER_OUTPUT     = 0x10,  // PROFET high-side
    CH_TYPE_PWM_OUTPUT       = 0x11,  // PWM output
    CH_TYPE_HBRIDGE          = 0x12,  // H-Bridge motor
    CH_TYPE_CAN_OUTPUT       = 0x13,  // CAN bus transmit

    // Virtual (без hw_binding)
    CH_TYPE_TIMER            = 0x20,  // Timer/delay
    CH_TYPE_LOGIC            = 0x21,  // Logic function (AND, OR, etc.)
    CH_TYPE_MATH             = 0x22,  // Math operations
    CH_TYPE_TABLE_2D         = 0x23,  // 2D lookup table
    CH_TYPE_TABLE_3D         = 0x24,  // 3D lookup table
    CH_TYPE_FILTER           = 0x25,  // Signal filter
    CH_TYPE_PID              = 0x26,  // PID controller
    CH_TYPE_NUMBER           = 0x27,  // Constant number
    CH_TYPE_SWITCH           = 0x28,  // Multi-state switch
    CH_TYPE_ENUM             = 0x29,  // Enumeration

    // System (builtin, readonly)
    CH_TYPE_SYSTEM           = 0xF0,  // Battery, temp, uptime...
} ChannelType_t;
```

### 2.3 Источники каналов

```
┌─────────────────────────────────────────────────────────────┐
│                    Channel Sources                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Built-in (прошивка)           User-defined (конфигурация) │
│  ├── System.BatteryVoltage     ├── DigitalInput.Button1    │
│  ├── System.MCU_Temp           ├── AnalogInput.Coolant     │
│  ├── System.BoardTemp          ├── Output.Headlights       │
│  ├── System.Uptime             ├── Timer.HeadlightDelay    │
│  ├── Output[0-29].Current      ├── Logic.HeadlightLogic    │
│  ├── Output[0-29].Status       └── ...                     │
│  └── ...                                                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Зависимости между каналами (source_channel)

### 3.1 Каналы, которые зависят от других

| Тип канала | Зависимость | Описание |
|------------|-------------|----------|
| **Power Output** | `source_channel_id` | Управление вкл/выкл |
| **PWM Output** | `source_channel_id` | Duty cycle от канала |
| **H-Bridge** | `source_channel_id` | Направление/позиция |
| **Timer** | `start_channel`, `stop_channel`, `reset_channel` | Триггеры |
| **Logic** | `source_channel_ids[]` | Входы логики |
| **Math** | `source_channel_ids[]` | Операнды |
| **Table 2D** | `source_channel_id` | Ось X |
| **Table 3D** | `x_channel_id`, `y_channel_id` | Оси X и Y |
| **Filter** | `source_channel_id` | Входной сигнал |
| **PID** | `input_channel`, `setpoint_channel` | PV и SP |
| **CAN TX** | `signals[].source_channel_id` | Данные для отправки |

### 3.2 Бинарное представление зависимостей

```c
// Dependency reference (2 bytes)
typedef struct {
    uint16_t channel_id;  // 0xFFFF = не используется
} ChannelRef_t;

// Multiple dependencies (variable length)
typedef struct {
    uint8_t count;              // 0-8
    uint16_t channel_ids[8];    // Max 8 source channels
} ChannelRefList_t;
```

---

## 4. Типы данных и отображение

### 4.1 Data Types (для CAN и расчётов)

```c
typedef enum {
    DATA_TYPE_UINT8     = 0x01,
    DATA_TYPE_INT8      = 0x02,
    DATA_TYPE_UINT16    = 0x03,
    DATA_TYPE_INT16     = 0x04,
    DATA_TYPE_UINT32    = 0x05,
    DATA_TYPE_INT32     = 0x06,
    DATA_TYPE_FLOAT32   = 0x07,
    DATA_TYPE_BOOL      = 0x08,
} DataType_t;
```

### 4.2 Display Settings

```c
typedef struct {
    char unit[8];           // "RPM", "°C", "V", "A", "%"...
    uint8_t decimal_places; // 0-6
    int32_t min_display;    // Минимум для отображения
    int32_t max_display;    // Максимум для отображения
} DisplaySettings_t;
```

### 4.3 Применение по типам каналов

| Тип | data_type | decimal_places | unit |
|-----|-----------|----------------|------|
| Analog Input | INT32 (scaled) | 0-3 | User-defined |
| CAN Input | Any | 0-6 | User-defined |
| Power Output | UINT16 (mA) | - | "A" |
| Temperature | INT16 (0.1°C) | 1 | "°C" |
| Timer | UINT32 (ms) | 0 | "ms" / "s" |
| PID | INT32 | 0-3 | User-defined |

---

## 5. Бинарный формат конфигурации

### 5.1 Общая структура

```
Configuration File (binary):
┌─────────────────────────────────────────────────────┐
│ Header (16 bytes)                                   │
├─────────────────────────────────────────────────────┤
│ Device Settings (32 bytes)                          │
├─────────────────────────────────────────────────────┤
│ CAN Messages Section                                │
│   count (2 bytes) + messages[]                      │
├─────────────────────────────────────────────────────┤
│ Channels Section                                    │
│   count (2 bytes) + channels[]                      │
├─────────────────────────────────────────────────────┤
│ String Table (names, units)                         │
│   count (2 bytes) + strings[]                       │
├─────────────────────────────────────────────────────┤
│ CRC32 (4 bytes)                                     │
└─────────────────────────────────────────────────────┘
```

### 5.2 Header

```c
typedef struct __attribute__((packed)) {
    uint32_t magic;           // 0x504D5533 ("PMU3")
    uint16_t version;         // Format version (1)
    uint16_t flags;           // Reserved
    uint32_t total_size;      // Total file size
    uint16_t channel_count;   // Number of channels
    uint16_t reserved;
} ConfigHeader_t;  // 16 bytes
```

### 5.3 Channel Entry (базовая структура)

```c
typedef struct __attribute__((packed)) {
    uint16_t channel_id;      // Unique ID
    uint8_t  channel_type;    // ChannelType_t
    uint8_t  flags;           // enabled, inverted, builtin...
    uint16_t name_offset;     // Offset in string table

    // Hardware binding (optional)
    int8_t   hw_pin;          // -1 = none
    uint8_t  hw_device;       // HwDevice_t

    // Display settings
    uint16_t unit_offset;     // Offset in string table (0 = none)
    uint8_t  decimal_places;  // 0-6
    uint8_t  data_type;       // DataType_t

    // Type-specific config follows (variable length)
    uint16_t config_size;     // Size of config data
    // uint8_t config_data[config_size];
} ChannelEntry_t;  // 14 bytes + variable config
```

### 5.4 Type-Specific Configs

#### Digital Input Config (4 bytes)
```c
typedef struct __attribute__((packed)) {
    uint8_t  subtype;         // active_low, active_high, frequency
    uint8_t  pullup;          // Pullup option
    uint16_t debounce_ms;     // 0-10000
} DigitalInputConfig_t;
```

#### Analog Input Config (16 bytes)
```c
typedef struct __attribute__((packed)) {
    uint8_t  subtype;         // linear, calibrated, rotary
    uint8_t  pullup;          // Pullup option
    int32_t  scale_multiplier;// Fixed-point scaling
    int32_t  scale_offset;
    // For calibrated: separate calibration table entry
} AnalogInputConfig_t;
```

#### Power Output Config (8 bytes)
```c
typedef struct __attribute__((packed)) {
    uint16_t source_channel_id;  // Control source (0xFFFF = none)
    uint16_t current_limit_ma;   // 0-30000
    uint8_t  output_mode;        // on_off, pwm, soft_start
    uint8_t  pwm_frequency;      // PWM freq index
    uint16_t inrush_time_ms;     // Soft-start time
} PowerOutputConfig_t;
```

#### Timer Config (12 bytes)
```c
typedef struct __attribute__((packed)) {
    uint8_t  timer_mode;         // delay_on, delay_off, pulse, etc.
    uint8_t  start_edge;         // rising, falling, both
    uint16_t start_channel_id;   // Start trigger
    uint16_t stop_channel_id;    // Stop trigger (0xFFFF = none)
    uint16_t reset_channel_id;   // Reset trigger (0xFFFF = none)
    uint32_t duration_ms;        // Timer duration
} TimerConfig_t;
```

#### Logic Config (variable)
```c
typedef struct __attribute__((packed)) {
    uint8_t  logic_type;         // and, or, xor, not, gt, lt, eq...
    uint8_t  source_count;       // 1-8
    uint16_t source_channels[8]; // Source channel IDs
    int32_t  threshold;          // For comparisons
    uint8_t  hysteresis;         // For analog comparisons
} LogicConfig_t;
```

#### CAN Input Config (16 bytes)
```c
typedef struct __attribute__((packed)) {
    uint16_t message_index;      // Index in CAN messages section
    uint8_t  frame_offset;       // 0-7 for multi-frame
    uint8_t  byte_offset;        // Start byte
    uint8_t  bit_offset;         // Start bit within byte
    uint8_t  bit_length;         // 1-32
    uint8_t  byte_order;         // little/big endian
    uint8_t  data_type;          // DataType_t
    int32_t  multiplier_fp;      // Fixed-point multiplier
    int32_t  offset_fp;          // Fixed-point offset
} CANInputConfig_t;
```

### 5.5 String Table

```c
typedef struct __attribute__((packed)) {
    uint16_t count;              // Number of strings
    uint16_t offsets[count];     // Offset to each string
    // Null-terminated strings follow
    // char strings[];
} StringTable_t;
```

---

## 6. Shared Library Architecture

### 6.1 Компоненты

```
shared/
├── channel_types.h          # Enum, struct definitions
├── channel_config.h/.c      # Binary config read/write
├── channel_registry.h/.c    # Channel management
├── channel_deps.h/.c        # Dependency resolution
├── protocol_codec.h/.c      # Binary protocol encode/decode
├── telemetry_codec.h/.c     # Telemetry build/parse (NEW)
└── crc32.h/.c               # CRC calculation
```

### 6.2 Build Targets

```
┌──────────────────────────────────────────────────────────────┐
│                    shared/ library                           │
├──────────────────────────────────────────────────────────────┤
│  Firmware (C):                                               │
│  ├── #include "shared/channel_config.h"                     │
│  ├── Compiles with: -DPLATFORM_FIRMWARE                     │
│  └── Statically linked                                       │
│                                                              │
│  Configurator (Python):                                      │
│  ├── ctypes/cffi bindings OR                                │
│  ├── Pure Python port of shared/ logic                      │
│  └── Import: from pmu_shared import ChannelConfig           │
│                                                              │
│  Emulator (C):                                               │
│  ├── Same as firmware                                        │
│  └── Compiles with: -DPLATFORM_EMULATOR                     │
└──────────────────────────────────────────────────────────────┘
```

### 6.3 API

```c
// Configuration loading
ConfigResult_t Config_Load(const uint8_t* data, size_t size);
ConfigResult_t Config_Save(uint8_t* buffer, size_t max_size, size_t* out_size);

// Channel access
Channel_t* Channel_Get(uint16_t id);
int32_t Channel_GetValue(uint16_t id);
void Channel_SetValue(uint16_t id, int32_t value);

// Dependency resolution
void Channel_UpdateDependencies(void);
uint16_t* Channel_GetDependents(uint16_t id, uint8_t* count);

// Iteration
typedef void (*ChannelCallback)(Channel_t* ch, void* ctx);
void Channel_ForEach(ChannelCallback cb, void* ctx);
void Channel_ForEachByType(ChannelType_t type, ChannelCallback cb, void* ctx);

// Telemetry (shared codec)
size_t Telemetry_Build(uint8_t* buffer, size_t max_size, const TelemetryConfig_t* cfg);
TelemetryResult_t Telemetry_Parse(const uint8_t* data, size_t size, TelemetryPacket_t* out);
```

### 6.4 Telemetry Codec (Shared)

Телеметрия — один из главных кандидатов на shared library:
- Firmware: строит пакет телеметрии
- Configurator: парсит пакет телеметрии
- **Одинаковый формат = один код**

#### Текущие проблемы

| Проблема | Описание |
|----------|----------|
| **Дублирование** | `pmu_protocol.c` (C) и `telemetry.py` (Python) — две реализации |
| **Рассинхрон** | Изменение формата требует правки в двух местах |
| **Разные платформы** | Nucleo vs Full PMU-30 — разные структуры телеметрии |

#### Unified Telemetry Format

```c
typedef struct __attribute__((packed)) {
    // Header (8 bytes)
    uint32_t stream_counter;     // Packet sequence number
    uint32_t timestamp_ms;       // System time

    // Core data (fixed, always present)
    uint16_t input_voltage_mv;   // Battery voltage
    int16_t  mcu_temp_c10;       // MCU temp × 10
    int16_t  board_temp_c10;     // Board temp × 10
    uint32_t total_current_ma;   // Total current

    // Sections (presence controlled by flags)
    uint16_t flags;              // What sections are present
    // Followed by variable sections...
} TelemetryHeader_t;

// Section flags
#define TELEM_HAS_ADC           0x0001  // ADC values section
#define TELEM_HAS_OUTPUTS       0x0002  // Output states section
#define TELEM_HAS_HBRIDGE       0x0004  // H-Bridge section
#define TELEM_HAS_DIN           0x0008  // Digital inputs section
#define TELEM_HAS_VIRTUALS      0x0010  // Virtual channels section
#define TELEM_HAS_FAULTS        0x0020  // Fault status section
```

#### Section: Virtual Channels

```c
// Virtual channels section (variable length)
typedef struct __attribute__((packed)) {
    uint16_t count;              // Number of virtual channels
    // Followed by count × VirtualChannelEntry
} VirtualChannelsHeader_t;

typedef struct __attribute__((packed)) {
    uint16_t channel_id;         // Channel ID
    int32_t  value;              // Current value
} VirtualChannelEntry_t;  // 6 bytes each
```

#### Telemetry API

```c
// === Firmware (build) ===
typedef struct {
    bool include_adc;
    bool include_outputs;
    bool include_hbridge;
    bool include_din;
    bool include_virtuals;
    bool include_faults;
} TelemetryConfig_t;

// Build telemetry packet, returns size written
size_t Telemetry_Build(uint8_t* buffer, size_t max_size, const TelemetryConfig_t* cfg);

// === Configurator (parse) ===
typedef struct {
    uint32_t stream_counter;
    uint32_t timestamp_ms;
    uint16_t input_voltage_mv;
    int16_t  mcu_temp_c10;
    int16_t  board_temp_c10;
    uint32_t total_current_ma;

    // Optional sections (NULL if not present)
    uint16_t* adc_values;        // [20] ADC raw values
    uint8_t*  output_states;     // [30] Output states
    int32_t*  virtual_values;    // Dynamic: channel_id -> value map
    uint16_t  virtual_count;
    // ... other sections
} TelemetryPacket_t;

typedef enum {
    TELEM_OK = 0,
    TELEM_ERR_TOO_SHORT,
    TELEM_ERR_BAD_CRC,
    TELEM_ERR_BAD_FLAGS,
} TelemetryResult_t;

TelemetryResult_t Telemetry_Parse(const uint8_t* data, size_t size, TelemetryPacket_t* out);
```

#### Python Bindings

```python
# Option 1: ctypes wrapper
from pmu_shared import telemetry_parse, TelemetryPacket

packet = TelemetryPacket()
result = telemetry_parse(raw_bytes, len(raw_bytes), ctypes.byref(packet))

# Option 2: Pure Python port (auto-generated from C structs)
from pmu_shared.telemetry import parse_telemetry

packet = parse_telemetry(raw_bytes)
print(f"Voltage: {packet.input_voltage_mv}mV")
print(f"Virtuals: {packet.virtual_channels}")
```

---

## 7. Миграция

### 7.1 Этапы

| Этап | Описание | Риск |
|------|----------|------|
| **1** | Создать shared/ библиотеку с новыми структурами | Низкий |
| **2** | Добавить конвертер JSON → Binary в конфигуратор | Низкий |
| **3** | Добавить бинарный парсер в прошивку | Средний |
| **4** | Тестирование: JSON load → convert → binary load | Средний |
| **5** | Переключить прошивку на бинарный формат | Высокий |
| **6** | Удалить JSON парсер из прошивки | Низкий |
| **7** | Обновить протокол (LOAD_CONFIG binary) | Средний |

### 7.2 Совместимость

```
Переходный период:
┌─────────────────────────────────────────────────────────────┐
│  Configurator                                               │
│  ├── Сохраняет: JSON (legacy) + Binary (new)               │
│  ├── Загружает: JSON (legacy) + Binary (new)               │
│  └── Отправляет: Binary (new) по протоколу                 │
│                                                             │
│  Firmware                                                    │
│  ├── v3.x: JSON parser (current)                           │
│  └── v4.x: Binary parser only                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Преимущества

### 8.1 Размер конфигурации

| Формат | Пример конфигурации | Размер |
|--------|---------------------|--------|
| JSON | 50 каналов | ~15 KB |
| Binary | 50 каналов | ~2 KB |
| **Экономия** | | **~85%** |

### 8.2 Производительность

| Операция | JSON | Binary |
|----------|------|--------|
| Parse 50 channels | ~500 ms | ~5 ms |
| RAM для парсинга | ~20 KB | ~2 KB |
| Code size (parser) | ~30 KB | ~3 KB |

### 8.3 Надёжность

- **Единая логика**: Конфигуратор и прошивка используют один код
- **CRC32**: Валидация целостности
- **Fixed-size structures**: Предсказуемое поведение
- **No string parsing**: Меньше edge cases

---

## 9. Open Questions

1. **Python bindings**: ctypes vs cffi vs pure Python port?
2. **Versioning**: Как обрабатывать разные версии формата?
3. **Calibration tables**: Отдельная секция или inline?
4. **Lua scripts**: Включать в бинарный формат или отдельно?
5. **Max channels**: Статический лимит или динамический?

---

## 10. References

- [Current Channel Reference](../reference/channels.md)
- [Configuration Reference](../operations/configuration-reference.md)
- [Protocol Specification](../protocol_specification.md)
- [Shared Protocol Library](../SHARED_PROTOCOL_LIBRARY.md)

---

## 11. Device Capabilities Protocol

### 11.1 Получение Capabilities

При подключении конфигуратор **ОБЯЗАН** запросить capabilities:

```
Configurator                    Device
    |                              |
    |--- CMD_GET_CAPS ------------>|
    |                              |
    |<-- CMD_CAPS_RESP (64 bytes) -|
    |                              |
    |  [Adapt UI based on caps]    |
    |                              |
```

### 11.2 Структура DeviceCaps (64 bytes)

```c
typedef struct __attribute__((packed)) {
    uint16_t magic;              // 0x4350 = "CP"
    uint8_t  version;            // Structure version
    uint8_t  device_type;        // PMU30, NUCLEO_F446, EMULATOR...

    // Hardware revision and firmware version
    uint8_t  hw_revision;
    uint16_t fw_version[3];      // major, minor, patch
    uint32_t serial_number;

    // Capability flags (32-bit bitmask)
    uint32_t hw_flags;           // HAS_PROFET, HAS_HBRIDGE, HAS_CAN1...
    uint32_t sw_flags;           // PID, TABLES, LUA, DATALOG...

    // Channel counts (determined by hardware)
    uint8_t  profet_count;       // 0-30
    uint8_t  hbridge_count;      // 0-4
    uint8_t  adc_count;          // 0-20
    uint8_t  din_count;          // 0-20
    uint8_t  freq_count;         // 0-4
    uint8_t  pwm_count;          // 0-8
    uint8_t  can_count;          // 0-4
    uint8_t  lin_count;          // 0-2

    // Limits
    uint16_t max_channels;       // Total channel limit
    uint16_t max_logic;          // Logic channels limit
    uint16_t max_timers;         // Timer channels limit
    uint16_t max_tables;         // Table channels limit

    // Memory
    uint32_t flash_size_kb;
    uint32_t ram_size_kb;

    // Current limits
    uint16_t max_current_ma;
    uint16_t per_channel_ma;
    uint16_t hbridge_current_ma;
} DeviceCaps_t;
```

### 11.3 Hardware Capability Flags

```c
typedef enum {
    // I/O Hardware
    CAPS_HAS_PROFET     = (1 << 0),   // PROFET power outputs
    CAPS_HAS_HBRIDGE    = (1 << 1),   // H-Bridge motor drivers
    CAPS_HAS_ADC        = (1 << 2),   // Analog inputs
    CAPS_HAS_DAC        = (1 << 3),   // Analog outputs
    CAPS_HAS_DIN        = (1 << 4),   // Digital inputs
    CAPS_HAS_DOUT       = (1 << 5),   // Digital outputs
    CAPS_HAS_FREQ       = (1 << 6),   // Frequency inputs
    CAPS_HAS_PWM        = (1 << 7),   // PWM outputs

    // Communication
    CAPS_HAS_CAN1       = (1 << 8),
    CAPS_HAS_CAN2       = (1 << 9),
    CAPS_HAS_CAN3       = (1 << 10),
    CAPS_HAS_CAN4       = (1 << 11),
    CAPS_HAS_LIN        = (1 << 12),

    // Wireless
    CAPS_HAS_WIFI       = (1 << 16),
    CAPS_HAS_BLUETOOTH  = (1 << 17),
    CAPS_HAS_GPS        = (1 << 18),
    CAPS_HAS_GSM        = (1 << 19),

    // Storage
    CAPS_HAS_SDCARD     = (1 << 20),
    CAPS_HAS_USB        = (1 << 21),
    CAPS_HAS_ETHERNET   = (1 << 22),
    CAPS_HAS_RTC        = (1 << 24),
    CAPS_HAS_EEPROM     = (1 << 25),
} DeviceCapsFlags_t;
```

### 11.4 Software Capability Flags

```c
typedef enum {
    CAPS_SW_PID         = (1 << 0),   // PID controllers
    CAPS_SW_TABLES_2D   = (1 << 1),   // 2D lookup tables
    CAPS_SW_TABLES_3D   = (1 << 2),   // 3D lookup tables
    CAPS_SW_LOGIC       = (1 << 3),   // Logic channels
    CAPS_SW_TIMERS      = (1 << 4),   // Timer channels
    CAPS_SW_FILTERS     = (1 << 5),   // Filter channels
    CAPS_SW_MATH        = (1 << 6),   // Math channels
    CAPS_SW_LUA         = (1 << 7),   // Lua scripting
    CAPS_SW_DATALOG     = (1 << 8),   // Data logging
    CAPS_SW_BLINKMARINE = (1 << 9),   // BlinkMarine keypad support
    CAPS_SW_WIPER_PARK  = (1 << 10),  // Wiper park mode
    CAPS_SW_CAN_STREAM  = (1 << 11),  // CAN streaming output
} DeviceCapsSwFlags_t;
```

---

## 12. Debug Protocol

### 12.1 Debug Message Format

```c
typedef struct __attribute__((packed)) {
    uint8_t  type;          // DebugMsgType_t
    uint8_t  flags;
    uint16_t seq;           // Sequence number
    uint32_t timestamp_us;  // Microsecond timestamp
    // Payload follows (type-specific)
} DebugMsgHeader_t;
```

### 12.2 Debug Message Types

```c
typedef enum {
    // Text messages
    DEBUG_MSG_LOG          = 0x01,   // Log message
    DEBUG_MSG_ERROR        = 0x02,   // Error message
    DEBUG_MSG_WARNING      = 0x03,   // Warning message

    // Variable monitoring
    DEBUG_MSG_VAR_INT      = 0x10,   // Integer variable
    DEBUG_MSG_VAR_FLOAT    = 0x11,   // Float variable

    // Channel debug
    DEBUG_MSG_CH_STATE     = 0x20,   // Channel state change
    DEBUG_MSG_CH_VALUE     = 0x21,   // Channel value update

    // Logic/Timer debug
    DEBUG_MSG_LOGIC_EVAL   = 0x30,   // Logic evaluation
    DEBUG_MSG_TIMER_STATE  = 0x40,   // Timer state change

    // Protocol debug
    DEBUG_MSG_PROTO_RX     = 0x50,   // Frame received
    DEBUG_MSG_PROTO_TX     = 0x51,   // Frame sent

    // Performance
    DEBUG_MSG_PERF_CPU     = 0x60,   // CPU usage
    DEBUG_MSG_PERF_MEM     = 0x61,   // Memory usage
    DEBUG_MSG_PERF_LOOP    = 0x62,   // Main loop timing

    // CAN debug
    DEBUG_MSG_CAN_RX       = 0x80,   // CAN frame received
    DEBUG_MSG_CAN_TX       = 0x81,   // CAN frame sent

    // Lua debug
    DEBUG_MSG_LUA_PRINT    = 0x90,   // Lua print()
    DEBUG_MSG_LUA_ERROR    = 0x91,   // Lua error
} DebugMsgType_t;
```

### 12.3 Debug Configuration

Configurator отправляет `CMD_DEBUG_CONFIG` для настройки:

```c
typedef struct __attribute__((packed)) {
    uint8_t  level;         // DEBUG_LEVEL_ERROR..TRACE
    uint8_t  channel_mask;  // Which debug streams to enable
    uint16_t rate_limit_ms; // Min interval between messages
    uint32_t module_mask;   // Which modules to debug
} DebugConfig_t;
```

### 12.4 Debug Levels

```c
typedef enum {
    DEBUG_LEVEL_NONE     = 0,   // No output
    DEBUG_LEVEL_ERROR    = 1,   // Errors only
    DEBUG_LEVEL_WARNING  = 2,   // + warnings
    DEBUG_LEVEL_INFO     = 3,   // + info
    DEBUG_LEVEL_DEBUG    = 4,   // + debug
    DEBUG_LEVEL_TRACE    = 5,   // Maximum verbosity
} DebugLevel_t;
```

---

## 13. Unified Telemetry Format

### 13.1 Capability-Driven Telemetry

Формат телеметрии **НЕ** зависит от платы. Он определяется capabilities:

```c
// Configurator requests telemetry with sections based on device caps
TelemConfig_t config = {
    .rate_ms = 100,
    .sections = TELEM_SEC_HEADER;  // Always

    if (caps.hw_flags & CAPS_HAS_PROFET)
        config.sections |= TELEM_SEC_OUTPUTS | TELEM_SEC_CURRENTS;

    if (caps.hw_flags & CAPS_HAS_HBRIDGE)
        config.sections |= TELEM_SEC_HBRIDGE;

    if (caps.hw_flags & CAPS_HAS_ADC)
        config.sections |= TELEM_SEC_ADC;

    if (caps.hw_flags & CAPS_HAS_DIN)
        config.sections |= TELEM_SEC_DIN;

    // Virtual channels always available
    config.sections |= TELEM_SEC_VIRTUALS;
};

Proto_SendFrame(CMD_TELEM_CONFIG, &config, sizeof(config));
```

### 13.2 Telemetry Sections

| Section | Size | Present if |
|---------|------|------------|
| Header | 16 bytes | Always |
| Outputs | profet_count bytes | CAPS_HAS_PROFET |
| Currents | profet_count × 2 bytes | CAPS_HAS_PROFET |
| ADC | adc_count × 2 bytes | CAPS_HAS_ADC |
| Digital In | 4 bytes (bitmask) | CAPS_HAS_DIN |
| H-Bridge | hbridge_count × 8 bytes | CAPS_HAS_HBRIDGE |
| Virtuals | 2 + count × 6 bytes | Always |
| Faults | 4 bytes | On fault |

### 13.3 Telemetry Header (16 bytes, always present)

```c
typedef struct __attribute__((packed)) {
    uint32_t seq;               // Sequence number
    uint32_t timestamp_ms;      // Uptime
    uint16_t voltage_mv;        // Input voltage
    int16_t  mcu_temp_c10;      // MCU temp × 10
    uint16_t sections;          // Section flags
    uint16_t reserved;
} TelemHeader_t;
```

---

## 14. Logic Engine (Pure Functions)

### 14.1 Принцип

Logic Engine — это **чистая библиотека функций**, которая:
- НЕ знает о каналах
- НЕ обращается к железу
- НЕ имеет состояния (stateless, кроме PID/Timer которым нужна память)
- Может запускаться в любом контексте: firmware, desktop app, тесты

```c
// Logic Engine API - PURE FUNCTIONS

// Logic operations
int32_t Logic_AND(const int32_t* inputs, uint8_t count);
int32_t Logic_OR(const int32_t* inputs, uint8_t count);
int32_t Logic_XOR(const int32_t* inputs, uint8_t count);
int32_t Logic_NOT(int32_t input);
int32_t Logic_GT(int32_t a, int32_t b);    // a > b
int32_t Logic_LT(int32_t a, int32_t b);    // a < b
int32_t Logic_EQ(int32_t a, int32_t b);    // a == b
int32_t Logic_RANGE(int32_t value, int32_t min, int32_t max);

// Math operations
int32_t Math_Add(const int32_t* inputs, uint8_t count);
int32_t Math_Multiply(int32_t a, int32_t b);
int32_t Math_Divide(int32_t a, int32_t b);
int32_t Math_Clamp(int32_t value, int32_t min, int32_t max);
int32_t Math_Map(int32_t value, int32_t in_min, int32_t in_max,
                 int32_t out_min, int32_t out_max);

// Table lookup (pure - table data passed as parameter)
int32_t Table2D_Lookup(const Table2D_t* table, int32_t x);
int32_t Table3D_Lookup(const Table3D_t* table, int32_t x, int32_t y);

// PID controller (needs state, but state passed as parameter)
int32_t PID_Update(PID_State_t* state, const PID_Config_t* config,
                   int32_t input, int32_t setpoint, uint32_t dt_ms);

// Timer (needs state, but state passed as parameter)
int32_t Timer_Update(Timer_State_t* state, const Timer_Config_t* config,
                     int32_t trigger, uint32_t now_ms);

// Filter (needs state)
int32_t Filter_Update(Filter_State_t* state, const Filter_Config_t* config,
                      int32_t input);

// Switch/Selector (stateless - pure selection)
int32_t Switch_Select(const int32_t* values, uint8_t count, int32_t selector);
int32_t Switch_Case(int32_t input, const SwitchCase_t* cases, uint8_t count,
                    int32_t default_value);

// Counter (needs state)
int32_t Counter_Update(Counter_State_t* state, const Counter_Config_t* config,
                       int32_t increment_trigger, int32_t decrement_trigger,
                       int32_t reset_trigger);

// Flip-Flop / Latch (needs state)
int32_t FlipFlop_Update(FlipFlop_State_t* state, int32_t set, int32_t reset);
int32_t Latch_Update(Latch_State_t* state, int32_t input, int32_t enable);

// Edge detection (needs state)
int32_t Edge_Rising(Edge_State_t* state, int32_t input);
int32_t Edge_Falling(Edge_State_t* state, int32_t input);
int32_t Edge_Both(Edge_State_t* state, int32_t input);

// Hysteresis comparator (needs state)
int32_t Hysteresis_Update(Hyst_State_t* state, int32_t input,
                          int32_t threshold_high, int32_t threshold_low);
```

### 14.2 Stateful Functions

Некоторые функции требуют сохранения состояния между вызовами:

```c
// PID State (passed BY POINTER, modified by function)
typedef struct {
    int32_t integral;      // Accumulated integral term
    int32_t last_error;    // Previous error (for derivative)
    int32_t last_output;   // Previous output
    uint32_t last_time_ms; // Last update time
} PID_State_t;

// Timer State
typedef struct {
    uint8_t  state;        // IDLE, RUNNING, EXPIRED
    uint32_t start_time_ms;
    uint32_t elapsed_ms;
} Timer_State_t;

// Filter State
typedef struct {
    int32_t buffer[8];     // Sample buffer
    uint8_t  index;        // Current index
    int32_t sum;           // Running sum (for moving average)
} Filter_State_t;

// Counter State
typedef struct {
    int32_t value;         // Current counter value
    uint8_t  last_inc;     // Last increment trigger state
    uint8_t  last_dec;     // Last decrement trigger state
    uint8_t  last_reset;   // Last reset trigger state
} Counter_State_t;

// Counter Config
typedef struct {
    int32_t min_value;     // Minimum value (clamp)
    int32_t max_value;     // Maximum value (clamp)
    int32_t step;          // Increment/decrement step
    uint8_t  wrap;         // Wrap around at limits
} Counter_Config_t;

// Switch Case definition
typedef struct {
    int32_t match_value;   // Value to match
    int32_t output_value;  // Output when matched
} SwitchCase_t;

// Flip-Flop State
typedef struct {
    uint8_t  output;       // Current Q output (0 or 1)
} FlipFlop_State_t;

// Latch State
typedef struct {
    int32_t latched_value; // Latched value
} Latch_State_t;

// Edge Detection State
typedef struct {
    int32_t last_input;    // Previous input value
} Edge_State_t;

// Hysteresis State
typedef struct {
    uint8_t  output;       // Current output (0 or 1)
} Hyst_State_t;
```

### 14.3 Использование в Firmware

```c
// Channel Manager собирает значения, вызывает Logic Engine, применяет результаты

void ChannelManager_Update(uint32_t now_ms) {
    // 1. Read all hardware inputs
    for (int i = 0; i < caps.adc_count; i++) {
        channels[adc_ids[i]].value = HAL_ADC_Read(i);
    }
    for (int i = 0; i < caps.din_count; i++) {
        channels[din_ids[i]].value = HAL_GPIO_Read(i);
    }

    // 2. Process all virtual channels (order by dependency)
    for (int i = 0; i < virtual_channel_count; i++) {
        Channel_t* ch = &channels[virtual_order[i]];

        // Gather inputs
        int32_t inputs[8];
        for (int j = 0; j < ch->input_count; j++) {
            inputs[j] = channels[ch->input_ids[j]].value;
        }

        // Call Logic Engine (PURE FUNCTION)
        switch (ch->type) {
            case CH_TYPE_LOGIC:
                ch->value = Logic_Evaluate(ch->logic_op, inputs, ch->input_count);
                break;
            case CH_TYPE_TIMER:
                ch->value = Timer_Update(&ch->state.timer, &ch->config.timer,
                                         inputs[0], now_ms);
                break;
            case CH_TYPE_PID:
                ch->value = PID_Update(&ch->state.pid, &ch->config.pid,
                                       inputs[0], inputs[1], now_ms - last_update_ms);
                break;
            case CH_TYPE_TABLE_2D:
                ch->value = Table2D_Lookup(&ch->config.table2d, inputs[0]);
                break;
            // ... etc
        }
    }

    // 3. Apply outputs to hardware
    for (int i = 0; i < caps.profet_count; i++) {
        HAL_Profet_SetState(i, channels[output_ids[i]].value);
    }
}
```

### 14.4 Desktop Testing (без железа!)

```python
# Python desktop app может использовать тот же Logic Engine

import ctypes
from pmu_shared import logic_engine

# Load the compiled logic engine library
engine = ctypes.CDLL("./logic_engine.so")

# Test logic functions without any hardware
inputs = [1, 0, 1, 1]
result = engine.Logic_AND(inputs, len(inputs))
print(f"AND({inputs}) = {result}")  # 0

# Test PID without hardware
pid_state = PID_State()
pid_config = PID_Config(kp=100, ki=10, kd=5)
output = engine.PID_Update(ctypes.byref(pid_state), ctypes.byref(pid_config),
                           input_value=1000, setpoint=2000, dt_ms=100)
print(f"PID output: {output}")

# Test 2D table lookup
table = Table2D(points=[(0, 0), (1000, 100), (2000, 200)])
result = engine.Table2D_Lookup(ctypes.byref(table), x=1500)
print(f"Table lookup at 1500: {result}")  # 150 (interpolated)
```

### 14.5 Unit Testing

```c
// Pure functions = easy testing!

void test_logic_and() {
    int32_t inputs[] = {1, 1, 1};
    assert(Logic_AND(inputs, 3) == 1);

    inputs[1] = 0;
    assert(Logic_AND(inputs, 3) == 0);
}

void test_pid_step_response() {
    PID_State_t state = {0};
    PID_Config_t config = {.kp = 100, .ki = 10, .kd = 0};

    int32_t setpoint = 1000;
    int32_t input = 0;

    for (int i = 0; i < 100; i++) {
        int32_t output = PID_Update(&state, &config, input, setpoint, 10);
        input += output / 10;  // Simulated plant response
    }

    // Should converge to setpoint
    assert(abs(input - setpoint) < 10);
}

void test_table2d_interpolation() {
    Table2D_t table = {
        .count = 3,
        .x = {0, 1000, 2000},
        .y = {0, 100, 200}
    };

    assert(Table2D_Lookup(&table, 0) == 0);
    assert(Table2D_Lookup(&table, 500) == 50);   // Interpolated
    assert(Table2D_Lookup(&table, 1000) == 100);
    assert(Table2D_Lookup(&table, 1500) == 150); // Interpolated
    assert(Table2D_Lookup(&table, 2000) == 200);
    assert(Table2D_Lookup(&table, 3000) == 200); // Clamped
}
```

---

## 15. Implementation Files (shared/)

```
shared/
├── channel_types.h          # Type definitions (created)
├── crc32.h/.c               # CRC-32 and CRC-16 (created)
├── device_caps.h/.c         # Device capabilities (created)
├── debug_protocol.h         # Debug protocol (created)
├── protocol.h               # Unified binary protocol (created)
├── telemetry_codec.h/.c     # Telemetry build/parse (created)
│
├── engine/                   # Logic Engine (PURE FUNCTIONS)
│   ├── logic.h/.c           # Logic operations (AND, OR, NOT, GT, LT, etc.)
│   ├── math.h/.c            # Math operations (Add, Multiply, Map, Clamp)
│   ├── table.h/.c           # Table lookup (2D, 3D interpolation)
│   ├── pid.h/.c             # PID controller
│   ├── timer.h/.c           # Timer functions
│   ├── filter.h/.c          # Signal filters (moving avg, low-pass, etc.)
│   ├── switch.h/.c          # Switch/Selector, Case statements
│   ├── counter.h/.c         # Counter with inc/dec/reset
│   ├── flipflop.h/.c        # Flip-Flop, Latch, SR, Toggle
│   ├── edge.h/.c            # Edge detection (rising, falling, both)
│   └── hysteresis.h/.c      # Hysteresis comparator
│
└── python/
    ├── __init__.py          # Package exports (created)
    ├── channel_types.py     # Type definitions (created)
    ├── crc.py               # CRC functions (created)
    ├── device_caps.py       # Device capabilities (created)
    ├── telemetry.py         # Telemetry parser (created)
    │
    └── engine/              # Python port of Logic Engine
        ├── __init__.py
        ├── logic.py         # Logic operations
        ├── math.py          # Math operations
        ├── table.py         # Table lookup
        ├── pid.py           # PID controller
        ├── timer.py         # Timer functions
        ├── filter.py        # Signal filters
        ├── switch.py        # Switch/Selector, Case
        ├── counter.py       # Counter
        ├── flipflop.py      # Flip-Flop, Latch
        ├── edge.py          # Edge detection
        └── hysteresis.py    # Hysteresis comparator
```

---

## 15. Implementation Status

### ✅ Completed Components

| Component | C Files | Python Files | Commit |
|-----------|---------|--------------|--------|
| **Logic Engine** | `shared/engine/*.h/.c` | `shared/python/engine/*.py` | `92c8632` |
| **Binary Config** | `shared/channel_config.h/.c` | `shared/python/channel_config.py` | `e4923d5` |
| **Protocol** | `shared/protocol.h/.c` | `shared/python/protocol.py` | `3e71d5b` |
| **Device Caps** | `shared/device_caps.h/.c` | `shared/python/device_caps.py` | `6ef7785` |
| **Debug Protocol** | `shared/debug_protocol.h` | — | `6ef7785` |
| **Channel Types** | `shared/channel_types.h` | — | Earlier |
| **CRC32** | `shared/crc32.h/.c` | (in channel_config) | Earlier |

### Logic Engine Modules

| Module | C | Python | Description |
|--------|---|--------|-------------|
| logic | ✅ | ✅ | AND, OR, XOR, comparisons |
| math_ops | ✅ | ✅ | Add, Mul, Map, Clamp, Lerp |
| timer | ✅ | ✅ | Delay, pulse, blink |
| table | ✅ | ✅ | 2D/3D lookup with interpolation |
| switch | ✅ | ✅ | Selector, case, mux |
| counter | ✅ | ✅ | Inc/dec/reset |
| pid | ✅ | ✅ | PID with anti-windup |
| filter | ✅ | ✅ | SMA, EMA, LPF, Median |
| flipflop | ✅ | ✅ | SR, D, T, JK triggers |
| hysteresis | ✅ | ✅ | Schmitt trigger |

### 🔄 In Progress

- [ ] Integration of Logic Engine with Channel System
- [ ] Firmware update to use binary config
- [ ] Configurator update to use binary protocol

### 📋 Pending

- [ ] Telemetry builder implementation
- [ ] Config chunked transfer
- [ ] Firmware update protocol
- [ ] Data logging protocol

---

**Document Status:** Active Development
**Last Updated:** January 2026
**Version:** 2.1 - Added Implementation Status section
