# PMU-30 Project Instructions

## Important Rules

**Single source of truth is `docs/` folder**. For any questions about architecture, protocol, or data formats - always read the documentation in `docs/` first.

**No backwards compatibility**. We don't support legacy code, old formats, or deprecated features. Delete old code instead of keeping it around. No migration paths, no shims, no compatibility layers.

**Testing on real hardware only**. We don't use the emulator (`pmu30_emulator`) for testing. All tests run on the physical Nucleo-F446RE board connected via **COM11**.

**Run telemetry tests after firmware changes**. After any modification to firmware code, run the comprehensive telemetry test suite:
```bash
python tests/test_firmware_telemetry.py COM11
```

## Quick Commands

### Build & Upload Firmware (Nucleo-F446RE)
```bash
cmd //c "set PATH=C:\\msys64\\ucrt64\\bin;%PATH% && cd c:\\Projects\\pmu_30\\firmware && python -m platformio run -e nucleo_f446re -t upload"
```

### Build Only (no upload)
```bash
cmd //c "set PATH=C:\\msys64\\ucrt64\\bin;%PATH% && cd c:\\Projects\\pmu_30\\firmware && python -m platformio run -e nucleo_f446re"
```

### Run Configurator
```bash
cd c:/Projects/pmu_30/configurator/src && start "" python main.py
```

## Architecture

- **Firmware**: Binary config only (no JSON), Channel Executor for virtual channels
- **Protocol**: LOAD_BINARY_CONFIG (0x68) for channel configuration
- **Shared library**: `shared/` - Logic Engine, channel types, validation

## Key Files

- `firmware/src/main_nucleo_f446.c` - Main entry point
- `firmware/src/pmu_protocol.c` - Protocol handler
- `firmware/src/pmu_channel_exec.c` - Channel Executor adapter
- `configurator/src/models/binary_config.py` - Binary serialization

## Memory Usage (after optimization)

- RAM: ~38% (from 95%)
- Flash: ~5% (from 15%)

## Debugging Notes

### Channel System Architecture

There are **two separate systems** for digital inputs:
1. **ADC Input System** (`pmu_adc.c`): `inputs[].digital_state` - for ADC-based inputs with thresholds
2. **GPIO Digital Inputs** (`main_nucleo_f446.c`): `g_digital_inputs[]` - for direct GPIO buttons

**IMPORTANT**: `PMU_Channel_GetValue()` for `INPUT_SWITCH` class must return cached `ch->value`, NOT `PMU_ADC_GetDigitalState()`. The cached value is updated by `DigitalInputs_Read()` via `PMU_Channel_UpdateValue()`.

### Channel Linking Flow

```
DigitalInputs_Read() → g_digital_inputs[0] = 1 (button pressed)
        ↓
PMU_Channel_UpdateValue(50, 1) → ch->value = 1
        ↓
PMU_ChannelExec_Update() → PMU_Channel_GetValue(50) → ch->value (NOT ADC!)
        ↓
NucleoOutput_SetState(1, 1) → output_state[1] = 1, LED ON
```

### LED Control (PA5)

The LED on PA5 is shared between:
- Power Output 1 (`output_state[1]`)
- Status LED patterns (`PMU_LED_Update()`)

**Priority**: `output_state[1]` takes priority - if output is ON, status LED is skipped.

### Protocol Single ACK

For chunked config upload, send only ONE final ACK when all chunks received, not intermediate ACKs per chunk (for single-chunk uploads this caused double-ACK issue).

### Virtual Channels in Telemetry

**ВАЖНО**: Virtual channels (Logic, Timer, Filter, etc.) хранятся в **Channel Executor** (`exec_state.channels[]`), а НЕ в Channel Registry (`PMU_Channel`).

Для получения данных о виртуальных каналах в телеметрии нужно использовать:
```c
// ПРАВИЛЬНО - через Channel Executor
uint16_t count = PMU_ChannelExec_GetChannelCount();
for (uint16_t i = 0; i < count; i++) {
    uint16_t ch_id;
    int32_t value;
    PMU_ChannelExec_GetChannelInfo(i, &ch_id, &value);
}

// НЕПРАВИЛЬНО - Channel Registry не содержит виртуальные каналы
PMU_Channel_GetInfo(ch_id);  // Вернёт NULL для виртуальных каналов
```

Телеметрия добавляет виртуальные каналы в конец пакета:
- Offset 104-105: `virtual_count` (2 bytes)
- Offset 106+: массив `[channel_id (2) + value (4)]` × count

### SysTick and Timing

SysTick is **disabled** in bare-metal mode (`SysTick->CTRL = 0`). A custom `HAL_GetTick()` returns `g_soft_tick_ms`:

```c
// main_nucleo_f446.c
static volatile uint32_t g_soft_tick_ms = 0;

uint32_t HAL_GetTick(void) {
    return g_soft_tick_ms;
}

// Incremented every 200 loop iterations (~1ms)
if (++input_count >= 200) {
    input_count = 0;
    g_soft_tick_ms++;
    // ...
}
```

**Timer accuracy**: ~10% faster than real time (10000ms ≈ 9 real seconds). This is because 200 loop iterations complete slightly faster than 1ms.

### Telemetry Packet Format (Nucleo-F446RE)

**IMPORTANT**: Configurator's telemetry parser must match firmware format EXACTLY.

Firmware telemetry format (`pmu_protocol.c` → `PMU_Protocol_SendTelemetry()`):
```
Offset   Size   Field
------   ----   -----
0        4      stream_counter (uint32)
4        4      timestamp_ms (uint32)
8        30     output_states[30] (1 byte each) - pmu.o1-o30
38       40     adc_values[20] (uint16 each = 40 bytes) - pmu.ai1-ai10
78       1      digital_inputs (packed bitmask, 8 bits) - pmu.di1-di8
--- System Info (15 bytes) ---
79       4      uptime_sec (uint32) - device uptime in seconds
83       4      ram_used (uint32) - stack bytes used
87       4      flash_used (uint32) - program size in bytes
91       2      channel_count (uint16) - runtime channel count
93       1      reserved
--- End System Info ---
94       2      voltage_mv (uint16)
96       2      current_ma (uint16)
98       2      mcu_temp_c (int16)
100      2      board_temp_c (int16)
102      1      fault_status (uint8)
103      1      fault_flags (uint8)
104      2      virtual_count (uint16)
106+     6*N    virtual_channels: [id(2) + value(4)] × count
```

Parser file: `configurator/src/communication/telemetry.py` → `_parse_telemetry_nucleo()`

### Variables Inspector Channel ID Mapping

**CRITICAL**: Variables Inspector MUST use actual `channel_id` from config, NOT sequential IDs.

```python
# ПРАВИЛЬНО - use actual channel_id from config
runtime_id = ch.get('channel_id')  # e.g., 200, 203, 207

# НЕПРАВИЛЬНО - sequential assignment breaks telemetry mapping
virtual_channel_id = 200
virtual_channel_id += 1  # DON'T DO THIS
```

Channel IDs are assigned by `BaseChannelDialog` using `get_next_channel_id()` and stored in config. Firmware uses these exact IDs in telemetry.

### Protocol CRC

CRC16-CCITT (init: 0xFFFF, poly: 0x1021) calculated over `[Length_L, Length_H, CMD, Payload]` - excludes 0xAA start byte.

Shared implementation: `shared/python/protocol.py` → `calc_crc16()`

**DO NOT** create custom CRC implementations in configurator - import from shared.

### Flash Config Persistence

- Firmware saves to Sector 7 (0x08060000) with header: `[magic:4][size:2][crc16:2]`
- `PMU_Protocol_LoadSavedConfig()` loads at startup
- Configurator uses `device_controller.save_to_flash()` which waits for FLASH_ACK

### Output Telemetry Sync (PROFET API)

**CRITICAL**: `pmu_channel_exec.c` must use `PMU_PROFET_SetState()` NOT `NucleoOutput_SetState()` for output control.

```c
// ПРАВИЛЬНО - обновляет и физический выход, и stub_channels[] для телеметрии
PMU_PROFET_SetState(link->hw_index, state);

// НЕПРАВИЛЬНО - обновляет только физический выход, телеметрия покажет 0
NucleoOutput_SetState(link->hw_index, state);
```

Flow: `PMU_PROFET_SetState()` → `stub_channels[ch].state = ON/OFF` → telemetry reads `stub_channels[]`

### Configurator Widgets Require Config

**Output Monitor** and **Variables Inspector** require channels to be configured BEFORE showing telemetry updates:

1. **Output Monitor** (`output_monitor.py`): `set_outputs()` populates table with Power Output channels. Empty table = no config loaded.

2. **Variables Inspector** (`variables_inspector.py`): `set_channels()` builds `_channel_id_map[runtime_id] = ch_id`. Without this mapping, `update_from_telemetry()` silently skips all updates.

3. **Telemetry Mixin** (`telemetry_mixin.py:64-73`): Only calls `variables_inspector.update_from_telemetry()` if `telemetry.virtual_channels` is not empty.

**Симптом**: "статус вариейблов/выходов не обновляется" → проверить что конфигурация загружена в конфигуратор.

### Protocol Command IDs

Firmware uses these command IDs (NOT 0x10, 0x11, 0x20):

| Command | ID | Notes |
|---------|-----|-------|
| START_STREAM | 0x30 | Subscribe to telemetry |
| STOP_STREAM | 0x31 | Unsubscribe |
| DATA | 0x32 | Telemetry packet |
| LOAD_BINARY_CONFIG | 0x68 | Channel config upload |
| BINARY_CONFIG_ACK | 0x69 | Config acknowledgment |
| ACK | 0xE0 | Generic ACK |

See `firmware/include/pmu_protocol.h` and `configurator/src/communication/protocol.py`.

### Quick Firmware Test Script

For testing firmware telemetry directly (bypassing configurator):

```python
import serial, struct, time

def crc16(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = (crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1
        crc &= 0xFFFF
    return crc

def build_packet(cmd, payload=b''):
    header = struct.pack('<BHB', 0xAA, len(payload), cmd)
    crc = crc16(struct.pack('<HB', len(payload), cmd) + payload)
    return header + payload + struct.pack('<H', crc)

ser = serial.Serial('COM11', 115200, timeout=0.2)
ser.write(build_packet(0x30))  # START_STREAM
# Parse responses: cmd=0x32 is DATA, byte 78 is DIN bitmask, bytes 8-37 are output states
```

### Config Sync on Connection

**CRITICAL**: При подключении конфигуратор должен **ЧИТАТЬ** конфиг с устройства, а НЕ загружать пустой локальный.

```python
# ПРАВИЛЬНО - device_mixin.py:_auto_sync_config()
def _auto_sync_config(self):
    self.read_from_device()  # Device is source of truth

# НЕПРАВИЛЬНО - затрёт сохранённый в flash конфиг пустым!
def _auto_sync_config(self):
    self._send_config_to_device_silent()  # DON'T DO THIS
```

**Симптом**: "конфиг пустой после перезапуска конфигуратора" → проверить что auto_sync читает с устройства.

### Channel References: Names vs IDs

**CRITICAL**: В конфиге каналов ссылки на другие каналы хранятся как **строки (имена)**, а НЕ числовые ID.

```python
# ПРАВИЛЬНО - LogicDialog.get_config() использует _get_channel_name_from_edit()
config["channel"] = self._get_channel_name_from_edit(edit)  # Returns "one", "Digital Input 1"

# НЕПРАВИЛЬНО - _get_channel_id_from_edit() возвращает int из property!
config["channel"] = self._get_channel_id_from_edit(edit)  # Returns 50, 51 (numeric IDs)
```

Валидация (`shared/python/channel_validation.py`) ожидает строки:
```python
if not isinstance(input_id, str) or not input_id:
    return error(ValidationError.LOGIC_INVALID_INPUT_ID, ...)  # Error 403
```

**Симптом**: "Validation error 403 for inputs[0]" → диалог возвращает int вместо str.

### Telemetry Restart After Config

**CRITICAL**: Firmware останавливает telemetry stream во время `LOAD_BINARY_CONFIG`. Конфигуратор ОБЯЗАН перезапустить после:

1. `upload_binary_config()` - загрузка конфига
2. `save_to_flash()` - сохранение в flash
3. `_send_config_to_device_silent()` - silent sync

```python
# После ЛЮБОЙ операции с конфигом:
self.device_controller.subscribe_telemetry(rate_hz=10)
```

**Симптом**: "телеметрия не обновляется после загрузки конфига" → не перезапустили stream.

### System Channels

Системные каналы "one" и "zero" - это предопределённые каналы с постоянными значениями 1 и 0. Используются как константы в логике. Их имена валидны для валидации.

### Config Serialization - User-Created Channels Only

**CRITICAL**: В прошивку отправляются ТОЛЬКО каналы, созданные пользователем. НЕ отправлять системные пины устройства!

```python
# ПРАВИЛЬНО - отправляем только user-created каналы
for ch in config["channels"]:
    if ch.get("user_created", True):  # Если явно создан пользователем
        serialize_channel(ch)

# НЕПРАВИЛЬНО - отправлять все системные Digital Input пины
# config_manager добавляет 8 системных DIN при загрузке - это для UI, не для firmware!
for i in range(8):
    channels.append({"id": f"DIN{i}", ...})  # НЕ отправлять в firmware!
```

**Что отправляется в firmware:**
1. Digital Inputs - только те, которые пользователь создал (не все 10 пинов!)
2. Analog Inputs - только созданные пользователем
3. Power Outputs - только с настроенным source_id (линковка)
4. Virtual channels - Logic, Timer, Math, Filter, Table, Switch, etc.
5. CAN Inputs/Outputs - только созданные

**Что НЕ отправляется:**
- Системные пины устройства (10 аналоговых, 8 цифровых входов как потенциальные)
- Каналы без конфигурации
- UI-only каналы (для отображения в интерфейсе)

**Симптом**: "config upload timeout" с большим конфигом → проверить что не сериализуем лишние системные каналы.

### Config Persistence - All Channel Types

**CRITICAL**: `serialize_ui_channels_for_executor()` должен включать ВСЕ типы каналов для полной персистентности.

```python
# ПРАВИЛЬНО - все типы для полного сохранения конфига
ALL_CHANNEL_TYPES = {
    "digital_input": ChannelType.DIGITAL_INPUT,
    "analog_input": ChannelType.ANALOG_INPUT,
    "power_output": ChannelType.POWER_OUTPUT,
    "timer": ChannelType.TIMER,
    "logic": ChannelType.LOGIC,
    # ... все типы
}

# НЕПРАВИЛЬНО - только executor types → Digital Inputs теряются при чтении
EXECUTOR_TYPES = {"timer": ..., "logic": ...}  # Без digital_input!
```

**Важно**: Сериализация должна включать имена каналов (`name_bytes`) для UI.

**Форматы struct должны точно соответствовать** `shared/python/channel_config.py`:
- `CfgDigitalInput`: `FORMAT = "<BBH"` (4 bytes)
- `CfgAnalogInput`: `FORMAT = "<iiiiHBB"` (20 bytes)
- `CfgPowerOutput`: `FORMAT = "<HHHBBHBB"` (12 bytes)

**Симптом**: "конфиг загружается битый, нет Digital Inputs" → проверить что все типы сериализуются.

## Deprecated (removed)

- `pmu_config_json.c` - JSON config parsing
- `pmu_logic_functions.c` - Old logic engine
- cJSON dependency
