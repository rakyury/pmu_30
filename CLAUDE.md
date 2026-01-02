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

## Deprecated (removed)

- `pmu_config_json.c` - JSON config parsing
- `pmu_logic_functions.c` - Old logic engine
- cJSON dependency
