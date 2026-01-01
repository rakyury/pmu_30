# Channel System Refactoring Plan

**Version:** 1.0 | **Created:** January 2026

---

## Executive Summary

Полный рефакторинг системы каналов PMU-30:
- **Унификация**: Все каналы виртуальные (нет разделения на physical/virtual)
- **Бинарный формат**: JSON → Binary для конфигурации
- **Shared Library**: Единая логика для конфигуратора и прошивки

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

**Document Status:** Draft
**Last Updated:** January 2026
