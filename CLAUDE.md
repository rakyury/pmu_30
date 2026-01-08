# PMU-30 Project Instructions

## Important Rules

**Single source of truth is `docs/` folder**. For any questions about architecture, protocol, or data formats - always read the documentation in `docs/` first.

**All documentation in English**. Every document, comment, and README must be written in English. No mixed languages.

**Consolidate docs in `docs/` folder**. After any refactoring:
1. Update relevant documentation
2. Remove outdated information
3. Move any scattered docs from other folders to `docs/`
4. Keep docs structure clean and organized

**No backwards compatibility**. We don't support legacy code, old formats, or deprecated features. Delete old code instead of keeping it around. No migration paths, no shims, no compatibility layers.

**Clean code only**. No garbage code for supporting old versions. When refactoring:
- Delete old implementations completely, don't keep them "just in case"
- Don't add compatibility wrappers or adapters for old interfaces
- No `# TODO: remove legacy` comments - remove it now
- No fallback code paths for deprecated features
- New code must be clean and focused, not wrapped around old patterns

**Testing on real hardware only**. We don't use the emulator (`pmu30_emulator`) for testing. All tests run on the physical Nucleo-F446RE board connected via **COM11**.

**Fresh firmware before each test session**. Before running integration tests:
```bash
cmd //c "set PATH=C:\\msys64\\ucrt64\\bin;%PATH% && cd c:\\Projects\\pmu_30\\firmware && python -m platformio run -e nucleo_f446re -t upload"
```

**All channel types must have integration tests**. Integration tests must cover:
- Digital Input, Analog Input, Frequency Input, CAN Input
- Power Output, PWM Output, H-Bridge, CAN Output
- Timer, Logic, Math, Filter, Table 2D/3D, PID
- Number, Switch, Enum, Counter, Hysteresis, FlipFlop

**Reflash on connection loss**. If device stops responding during tests:
1. Power cycle the Nucleo board (unplug/replug USB)
2. Reflash firmware using the build & upload command
3. Resume tests from the beginning

**Run telemetry tests after firmware changes**. After any modification to firmware code, run the comprehensive telemetry test suite:
```bash
python tests/test_firmware_telemetry.py COM11
```

**Delete configurator logs before debugging**. Always clear the log file before launching the configurator for debugging sessions:
```bash
del "C:\Users\User\.pmu30\logs\pmu30.log"
```

**Clear pycache before running tests or configurator**. Remove cached bytecode to avoid stale module issues:
```bash
# Before running tests
cd c:/Projects/pmu_30 && rm -rf __pycache__ tests/__pycache__ configurator/src/**/__pycache__

# Or using find (Git Bash)
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
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

### Virtual Channel Execution - Inline vs Shared Library

**CRITICAL**: Shared library functions `Exec_Logic()`, `Exec_ProcessChannel()` from `shared/channel_executor.c` **cause firmware hangs** when called from bare-metal main loop!

**Root cause**: Callback chain through `ctx->get_value` has context/stack issues in bare-metal environment without RTOS.

**Solution**: Use **inline evaluators** in `pmu_channel_exec.c` that call `PMU_Channel_GetValue()` directly:

```c
// CORRECT - inline evaluation works
if (ch->runtime.type == CH_TYPE_LOGIC && ch->runtime.config != NULL) {
    CfgLogic_t* logic = (CfgLogic_t*)ch->runtime.config;
    if (logic->input_count > 0 && logic->inputs[0] != 0 && logic->inputs[0] != 0xFFFF) {
        int32_t input_val = PMU_Channel_GetValue(logic->inputs[0]);
        if (logic->operation == 0x06) {  /* IS_TRUE */
            result = (input_val != 0) ? 1 : 0;
        } else if (logic->operation == 0x07) {  /* IS_FALSE */
            result = (input_val == 0) ? 1 : 0;
        }
    }
}

// WRONG - hangs firmware!
Exec_Logic(&exec_ctx, ch);  // Uses callback chain, causes hang
Exec_ProcessChannel(&exec_ctx, ch);  // Same problem
```

**Logic operation codes** (from `shared/engine/logic.h`):
| Operation | Code | Description |
|-----------|------|-------------|
| IS_TRUE | 0x06 | Returns 1 if input != 0 |
| IS_FALSE | 0x07 | Returns 1 if input == 0 (NOT) |
| AND | 0x00 | All inputs must be true |
| OR | 0x01 | Any input must be true |
| GT | 0x10 | a > b |
| LT | 0x12 | a < b |
| EQ | 0x14 | a == b |

**Files**:
- `firmware/src/pmu_channel_exec.c` - Inline evaluators (working)
- `shared/channel_executor.c` - Shared library (DON'T call from firmware)
- `shared/engine/logic.h` - Logic operation definitions

### IWDG Watchdog and Long Operations

**CRITICAL**: STM32 IWDG watchdog is configured with ~2 second timeout. Any operation taking longer than 2 seconds without `HAL_IWDG_Refresh()` will cause MCU reset!

**Flash operations require IWDG refresh**:
```c
// Config_SaveToFlash() - add refresh every 16 words during write
for (uint32_t i = 0; i < words; i++) {
    HAL_FLASH_Program(...);
    if ((i & 0x0F) == 0x0F) {
        HAL_IWDG_Refresh(&hiwdg);  // Every 16 words
    }
}
HAL_IWDG_Refresh(&hiwdg);  // After write complete

// handle_save_config() - refresh before/after flash operation
HAL_IWDG_Refresh(&hiwdg);
Config_SaveToFlash();
HAL_IWDG_Refresh(&hiwdg);

// handle_clear_config() - same pattern (128KB sector erase = 1-2 seconds!)
HAL_IWDG_Refresh(&hiwdg);
HAL_FLASHEx_Erase(...);
HAL_IWDG_Refresh(&hiwdg);
```

**Symptom**: "firmware hangs after flash save" → add IWDG refresh during long operations.

### STOP_STREAM TX Completion

**CRITICAL**: `handle_stop_stream()` must wait for TX completion before returning, otherwise subsequent commands may fail due to TX/RX race condition.

```c
static void handle_stop_stream(void)
{
    HAL_IWDG_Refresh(&hiwdg);
    min_stream_active = false;

    // Wait for any in-progress telemetry TX to complete
    while (min_tx_in_progress) {}

    uint8_t ack[1] = {MIN_CMD_STOP_STREAM};
    min_send_frame(&g_min_ctx, MIN_CMD_ACK, ack, 1);

    // Wait for ACK TX to complete
    while (!(USART2->SR & USART_SR_TC)) {}

    HAL_IWDG_Refresh(&hiwdg);
}
```

**Symptom**: "firmware unresponsive after STOP_STREAM" → ensure TX completion wait.

**Key file**: `firmware/src/pmu_min_port.c` lines 487-507

### ST-LINK VCP Timing and Startup Debugging

**CRITICAL**: The ST-LINK Virtual COM Port (VCP) needs ~500ms-1s to stabilize after connection. Early UART output sent before host opens port will be **lost**.

**Startup markers**: The firmware sends progress markers A-P during initialization:
- A: main() reached
- B: HAL_Init done
- C: SystemClock_Config done
- D-H: Peripheral init (GPIO, USART, ADC, TIM, IWDG)
- I-L: PMU core modules (Config, CAN, ADC, Protection, Channel, PROFET)
- M-N: PMU logic modules (Logic, ChannelExec, LED, Logging)
- O-P: SerialTransfer init and config load

**Symptom**: "firmware appears unresponsive, no UART output" → markers were sent before VCP stabilized. Add delay before reading or check for telemetry stream.

**Telemetry stream interference**: If firmware has saved config with telemetry enabled, it will auto-start streaming DATA packets (0x22). PING commands may get lost in stream.

**Solution**: Always stop telemetry stream before sending commands:
```python
pmu = PMUSerialTransfer('COM11')
pmu.connect()
pmu.stop_stream()  # Stop any auto-started telemetry
result = pmu.ping()  # Now PING will work
```

**Debugging firmware startup**:
1. If no output at all → check if `minimal_test` environment works (proves hardware OK)
2. If `minimal_test` works but `nucleo_f446re` doesn't → issue is in PMU module init
3. Use incremental approach: disable modules one by one to find culprit
4. Add test loops between init steps to isolate hanging module

**Key file**: `firmware/src/main_nucleo_f446.c` - startup markers at lines 175-258

### LED Control (PA5)

The LED on PA5 is shared between:
- Power Output 1 (`output_state[1]`)
- Status LED patterns (`PMU_LED_Update()`)

**Priority**: `output_state[1]` takes priority - if output is ON, status LED is skipped.

### Protocol Single ACK

For chunked config upload, send only ONE final ACK when all chunks received, not intermediate ACKs per chunk (for single-chunk uploads this caused double-ACK issue).

### Two Separate Telemetry Builders

**CRITICAL**: Firmware has TWO completely separate telemetry code paths:

1. **`pmu_protocol.c:PMU_Protocol_SendTelemetry()`** - Main protocol telemetry (CAN bus, full PMU-30)
2. **`pmu_min_port.c:build_telemetry_packet()`** - MIN serial protocol telemetry (Nucleo, USB)

When adding debug variables or modifying telemetry format, **BOTH files must be updated**! The MIN path is what test scripts and configurator use via USB serial.

```c
// pmu_min_port.c - MIN telemetry path
static void build_telemetry_packet(uint8_t* buf, uint16_t* len)
{
    // ... completely separate implementation from pmu_protocol.c
}

// pmu_protocol.c - Main protocol path
HAL_StatusTypeDef PMU_Protocol_SendTelemetry(void)
{
    // ... different implementation
}
```

**Debug variables for Channel Executor tracing** (in `pmu_channel_exec.c`):
- `g_dbg_link_count` - Output link count after config load
- `g_dbg_parsed_type`, `g_dbg_parsed_source` - Config parsing trace
- `g_dbg_addlink_called`, `g_dbg_addlink_result` - AddOutputLink result
- `g_dbg_source_value`, `g_dbg_output_state` - Runtime execution trace
- `g_dbg_getsrc_ch_found` - Channel registry lookup result

### Virtual Channels in Telemetry

**IMPORTANT**: Virtual channels (Logic, Timer, Filter, etc.) are stored in **Channel Executor** (`exec_state.channels[]`), NOT in Channel Registry (`PMU_Channel`).

To get virtual channel data in telemetry, use:
```c
// CORRECT - via Channel Executor
uint16_t count = PMU_ChannelExec_GetChannelCount();
for (uint16_t i = 0; i < count; i++) {
    uint16_t ch_id;
    int32_t value;
    PMU_ChannelExec_GetChannelInfo(i, &ch_id, &value);
}

// WRONG - Channel Registry doesn't contain virtual channels
PMU_Channel_GetInfo(ch_id);  // Returns NULL for virtual channels
```

Telemetry appends virtual channels to the end of packet:
- Offset 104-105: `virtual_count` (2 bytes)
- Offset 106+: array `[channel_id (2) + value (4)]` × count

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
# CORRECT - use actual channel_id from config
runtime_id = ch.get('channel_id')  # e.g., 200, 203, 207

# WRONG - sequential assignment breaks telemetry mapping
virtual_channel_id = 200
virtual_channel_id += 1  # DON'T DO THIS
```

Channel IDs are assigned by `BaseChannelDialog` using `get_next_channel_id()` and stored in config. Firmware uses these exact IDs in telemetry.

### T-MIN Protocol (Transport MIN)

Firmware and configurator use **T-MIN (Transport MIN)** for reliable serial communication with automatic retransmission.

**T-MIN vs Simple MIN:**
| Feature | Simple MIN | T-MIN |
|---------|------------|-------|
| CRC32 | ✓ | ✓ |
| Byte stuffing | ✓ | ✓ |
| Auto-retransmit | ✗ | ✓ |
| ACK/NACK | ✗ | ✓ |
| Sliding window | ✗ | ✓ |
| Sequence tracking | ✗ | ✓ |

**Frame Format:**
```
┌────────────────┬────────────┬────────┬─────────────┬───────┬─────┐
│ 0xAA 0xAA 0xAA │ ID/Control │ Length │   Payload   │ CRC32 │ EOF │
│    3 bytes     │   1 byte   │   1B   │   0-255B    │  4B   │ 1B  │
└────────────────┴────────────┴────────┴─────────────┴───────┴─────┘
```

**ID/Control byte for T-MIN:**
- Bit 7 = 1: Transport frame (with sequence number)
- Bits 0-5: Command ID (0-63)
- 0xFF = ACK frame
- 0xFE = RESET frame

**Key features:**
- Triple 0xAA header (not single byte!)
- CRC32 (big-endian), not CRC16
- Byte stuffing: Insert 0x55 after two consecutive 0xAA in payload
- EOF marker: 0x55
- Automatic retransmission with exponential backoff
- Sliding window (up to 8 frames in flight)

**Firmware T-MIN Configuration** (`firmware/lib/MIN/min_config.h`):
```c
#define MAX_PAYLOAD 255
#define TRANSPORT_FIFO_SIZE_FRAMES_BITS 4      // 16 frames queue
#define TRANSPORT_FIFO_SIZE_FRAME_DATA_BITS 10 // 1KB buffer
#define TRANSPORT_ACK_RETRANSMIT_TIMEOUT_MS 25
#define TRANSPORT_FRAME_RETRANSMIT_TIMEOUT_MS 50
#define TRANSPORT_MAX_WINDOW_SIZE 8
#define TRANSPORT_IDLE_TIMEOUT_MS 3000
```

**When to use T-MIN vs Simple MIN:**
- `queue_frame()` - T-MIN: for commands requiring ACK (config upload, save, set output)
- `send_frame()` - Simple MIN: for high-frequency data (telemetry - no ACK needed)

**Telemetry packet loss is acceptable**. Telemetry uses `min_send_frame()` without acknowledgment. Occasional lost packets are OK - next packet arrives in 100ms at 10Hz rate.

**Command processing is highest priority**. When processing commands, they take priority over telemetry. Firmware must always respond to commands promptly, even during telemetry streaming.

**Implementation files:**
- `firmware/lib/MIN/` - MIN library (min.c, min.h, min_config.h)
- `firmware/src/pmu_min_port.c` - MIN port adapter for STM32
- `shared/python/min_protocol.py` - Python T-MIN implementation
- `configurator/src/controllers/transport.py` - MINSerialTransport wrapper
- `configurator/src/communication/protocol.py` - Protocol frames and parsing

### Flash Config Persistence

- Firmware saves to Sector 7 (0x08060000) with header: `[magic:4][size:2][crc16:2]`
- `PMU_Protocol_LoadSavedConfig()` loads at startup
- Configurator uses `device_controller.save_to_flash()` which waits for FLASH_ACK

### Output Telemetry Sync (PROFET API)

**CRITICAL**: `pmu_channel_exec.c` must use `PMU_PROFET_SetState()` NOT `NucleoOutput_SetState()` for output control.

```c
// CORRECT - updates both physical output and stub_channels[] for telemetry
PMU_PROFET_SetState(link->hw_index, state);

// WRONG - updates only physical output, telemetry will show 0
NucleoOutput_SetState(link->hw_index, state);
```

Flow: `PMU_PROFET_SetState()` → `stub_channels[ch].state = ON/OFF` → telemetry reads `stub_channels[]`

### Configurator Widgets Require Config

**Output Monitor** and **Variables Inspector** require channels to be configured BEFORE showing telemetry updates:

1. **Output Monitor** (`output_monitor.py`): `set_outputs()` populates table with Power Output channels. Empty table = no config loaded.

2. **Variables Inspector** (`variables_inspector.py`): `set_channels()` builds `_channel_id_map[runtime_id] = ch_id`. Without this mapping, `update_from_telemetry()` silently skips all updates.

3. **Telemetry Mixin** (`telemetry_mixin.py:64-73`): Only calls `variables_inspector.update_from_telemetry()` if `telemetry.virtual_channels` is not empty.

**Symptom**: "variables/outputs status not updating" → check that configuration is loaded into configurator.

### UI Channel ID → Name Lookup (Rebind)

**CRITICAL**: When loading configuration into UI, channels are added sequentially. If channel A references channel B (by channel_id), but channel B is not yet loaded - name lookup will fail.

**Solution**: `project_tree.rebind_channel_references()` is called AFTER all channels are fully loaded.

```python
# project_tree.py
def load_channels(self, channels: List[Dict[str, Any]]):
    self.clear_all()
    for channel in channels:
        self.add_channel(channel_type, channel, emit_signal=False)

    # IMPORTANT: rebind after full load!
    self.rebind_channel_references()  # Updates Details and Source columns

def rebind_channel_references(self):
    # Builds channel_id → name map from all loaded channels
    channel_name_map = self._build_channel_name_map()
    # Updates all tree items with resolved names
    for item in all_items:
        item.setText(1, self._format_channel_details_with_names(..., channel_name_map))
        item.setText(2, self._format_channel_source_with_names(..., channel_name_map))
```

**For dialogs**: `_get_available_channels()` collects all channels from project_tree. Dialog must receive `available_channels` AFTER config is fully loaded.

**Key files**:
- `project_tree.py`: `rebind_channel_references()`, `_build_channel_name_map()`, `_resolve_channel_id()`
- `base_channel_dialog.py`: `_set_channel_edit_value()`, `_get_channel_display_name()`
- `channel_display_service.py`: `ChannelDisplayService.get_display_name()`

### MIN Protocol Command IDs

MIN protocol command IDs (0-63 range). Defined in `firmware/include/pmu_min_port.h`:

| Command | ID | Notes |
|---------|-----|-------|
| PING | 0x01 | Connection test |
| PONG | 0x02 | PING response |
| GET_CONFIG | 0x10 | Request config from device |
| CONFIG_DATA | 0x11 | Config data response |
| SAVE_CONFIG | 0x14 | Save to flash |
| FLASH_ACK | 0x15 | Flash save acknowledgment |
| CLEAR_CONFIG | 0x16 | Clear config |
| CLEAR_CONFIG_ACK | 0x17 | Clear acknowledgment |
| LOAD_BINARY | 0x18 | Upload binary config |
| BINARY_ACK | 0x19 | Binary config acknowledgment |
| START_STREAM | 0x20 | Subscribe to telemetry |
| STOP_STREAM | 0x21 | Unsubscribe |
| DATA | 0x22 | Telemetry packet |
| SET_OUTPUT | 0x28 | Set output state |
| OUTPUT_ACK | 0x29 | Output set acknowledgment |
| ACK | 0x3E | Generic ACK |
| NACK | 0x3F | Generic NACK |

See `firmware/include/pmu_min_port.h` and `configurator/src/communication/protocol.py`.

### Quick Firmware Test Script

For testing firmware telemetry directly (bypassing configurator), use MIN protocol:

```python
import serial, struct
from binascii import crc32

def build_min_frame(cmd, payload=b''):
    """Build MIN protocol frame."""
    prolog = bytes([cmd, len(payload)]) + payload
    crc = crc32(prolog, 0)
    raw = prolog + struct.pack(">I", crc)

    # Byte stuffing
    stuffed = bytearray([0xAA, 0xAA, 0xAA])
    count = 0
    for b in raw:
        stuffed.append(b)
        if b == 0xAA:
            count += 1
            if count == 2:
                stuffed.append(0x55)
                count = 0
        else:
            count = 0
    stuffed.append(0x55)  # EOF
    return bytes(stuffed)

ser = serial.Serial('COM11', 115200, timeout=0.2)
ser.write(build_min_frame(0x20, struct.pack('<H', 10)))  # START_STREAM at 10Hz
# Parse responses using MINFrameParser from tests/protocol_helpers.py
```

### Config Sync on Connection

**CRITICAL**: On connection, configurator must **READ** config from device, NOT upload empty local config.

```python
# CORRECT - device_mixin.py:_auto_sync_config()
def _auto_sync_config(self):
    self.read_from_device()  # Device is source of truth

# WRONG - will overwrite flash-saved config with empty!
def _auto_sync_config(self):
    self._send_config_to_device_silent()  # DON'T DO THIS
```

**Symptom**: "config empty after configurator restart" → check that auto_sync reads from device.

### Channel References: Names vs IDs

**CRITICAL**: In channel config, references to other channels are stored as **strings (names)**, NOT numeric IDs.

```python
# CORRECT - LogicDialog.get_config() uses _get_channel_name_from_edit()
config["channel"] = self._get_channel_name_from_edit(edit)  # Returns "one", "Digital Input 1"

# WRONG - _get_channel_id_from_edit() returns int from property!
config["channel"] = self._get_channel_id_from_edit(edit)  # Returns 50, 51 (numeric IDs)
```

Validation (`shared/python/channel_validation.py`) expects strings:
```python
if not isinstance(input_id, str) or not input_id:
    return error(ValidationError.LOGIC_INVALID_INPUT_ID, ...)  # Error 403
```

**Symptom**: "Validation error 403 for inputs[0]" → dialog returns int instead of str.

### Telemetry Restart After Config

**CRITICAL**: Firmware stops telemetry stream during `LOAD_BINARY_CONFIG`. Configurator MUST restart after:

1. `upload_binary_config()` - config upload
2. `save_to_flash()` - flash save
3. `_send_config_to_device_silent()` - silent sync

```python
# After ANY config operation:
self.device_controller.subscribe_telemetry(rate_hz=10)
```

**Symptom**: "telemetry not updating after config upload" → stream not restarted.

### Device Capabilities Architecture

**CRITICAL**: Configurator is **universal** - knows NOTHING about device hardware until connected. All capabilities come from device on connection.

**On connection, device sends its capabilities:**
1. **System channels** - (id, name, description) for one, zero, pmu.*, etc.
2. **Output pins** - available power output pins (O1-O30 for PMU-30, fewer for Mini)
3. **Analog input pins** - available analog inputs (A1-A10, etc.)
4. **Digital input pins** - available digital inputs (D1-D8, etc.)
5. **H-Bridge channels** - available motor driver channels
6. **CAN buses** - available CAN interfaces

**NO HARDCODING in configurator!** All dialog dropdowns, channel selectors, and pin lists populated from device capabilities.

**Device variants**: PMU-30 Pro, PMU-30, PMU-16 Mini - same configurator, different capabilities.

**Current workaround**: `ChannelDisplayService.SYSTEM_CHANNELS` is temporarily hardcoded. Must be replaced with device-provided data.

**Implementation TODO**:
```python
# Protocol: GET_DEVICE_CAPABILITIES (0x70)
# Response format:
{
    "device_type": "PMU-30",
    "firmware_version": "1.0.0",
    "system_channels": [(1012, "zero", "Constant 0"), (1013, "one", "Constant 1"), ...],
    "output_pins": [(0, "O1", 40), (1, "O2", 40), ...],  # (index, name, max_current_a)
    "analog_inputs": [(0, "A1", "voltage"), (1, "A2", "voltage"), ...],
    "digital_inputs": [(0, "D1"), (1, "D2"), ...],
    "hbridges": [(0, "HB1"), (1, "HB2"), ...],
    "can_buses": [1, 2]
}

# Configurator stores in DeviceCapabilities singleton
# All dialogs query DeviceCapabilities instead of hardcoded lists
```

**UI Lookup order** in `project_tree._resolve_channel_id()`:
1. User channels (from `_build_channel_name_map()`)
2. System channels (from device capabilities / `ChannelDisplayService` fallback)
3. Fallback to `#{id}`

### Config Serialization - User-Created Channels Only

**CRITICAL**: Only user-created channels are sent to firmware. Do NOT send system device pins!

```python
# CORRECT - send only user-created channels
for ch in config["channels"]:
    if ch.get("user_created", True):  # If explicitly created by user
        serialize_channel(ch)

# WRONG - sending all system Digital Input pins
# config_manager adds 8 system DINs on load - this is for UI, not firmware!
for i in range(8):
    channels.append({"id": f"DIN{i}", ...})  # DON'T send to firmware!
```

**What IS sent to firmware:**
1. Digital Inputs - only user-created ones (not all 10 pins!)
2. Analog Inputs - only user-created
3. Power Outputs - only with configured source_id (linking)
4. Virtual channels - Logic, Timer, Math, Filter, Table, Switch, etc.
5. CAN Inputs/Outputs - only user-created

**What is NOT sent:**
- System device pins (10 analog, 8 digital inputs as potential)
- Channels without configuration
- UI-only channels (for display in interface)

**Symptom**: "config upload timeout" with large config → check not serializing extra system channels.

### Config Persistence - All Channel Types

**CRITICAL**: `serialize_ui_channels_for_executor()` must include ALL channel types for full persistence.

```python
# CORRECT - all types for full config save
ALL_CHANNEL_TYPES = {
    "digital_input": ChannelType.DIGITAL_INPUT,
    "analog_input": ChannelType.ANALOG_INPUT,
    "power_output": ChannelType.POWER_OUTPUT,
    "timer": ChannelType.TIMER,
    "logic": ChannelType.LOGIC,
    # ... all types
}

# WRONG - only executor types → Digital Inputs lost on read
EXECUTOR_TYPES = {"timer": ..., "logic": ...}  # Missing digital_input!
```

**Important**: Serialization must include channel names (`name_bytes`) for UI.

**Struct formats must exactly match** `shared/python/channel_config.py`:
- `CfgDigitalInput`: `FORMAT = "<BBH"` (4 bytes)
- `CfgAnalogInput`: `FORMAT = "<iiiiHBB"` (20 bytes)
- `CfgPowerOutput`: `FORMAT = "<HHHBBHBB"` (12 bytes)

**Symptom**: "config loads corrupted, no Digital Inputs" → check all types are serialized.

### Config Reference Validation

**Firmware validates channel references**. If Logic/Timer/Filter references a channel not in the uploaded config - config is rejected.

```python
# CORRECT - all referenced channels included
channels = [
    {"id": 50, "type": "digital_input", ...},  # Referenced by Logic
    {"id": 51, "type": "digital_input", ...},  # Referenced by Logic
    {"id": 200, "type": "logic", "inputs": [50, 51], ...},
    {"id": 100, "type": "power_output", "source": 200, ...},
]

# WRONG - Logic references channels 50, 51 which don't exist
channels = [
    {"id": 200, "type": "logic", "inputs": [50, 51], ...},  # FAIL!
    {"id": 100, "type": "power_output", "source": 200, ...},
]
```

**Symptom**: "config upload OK but readback empty" → check all referenced channels are included in config.

### Roundtrip Test

To verify config persistence, use the test:
```bash
python tests/test_config_roundtrip.py COM11 tests/configs/logic_and_full.pmu30
```

Test verifies: upload → readback → flash save → readback. All channels must persist 1:1.

## Current Debugging Status (2026-01-06)

### Button → Logic → LED Chain: WORKING ✓

The channel executor chain is **verified working**:
- **Digital Input** (PC13, channel 50) detects button press
- **Logic channel** (IS_TRUE, channel 200) evaluates button state
- **Power Output** (PA5 LED, channel 100) follows logic output

Test command to verify:
```bash
timeout 30 python -c "
import sys, time, struct
sys.path.insert(0, 'c:/Projects/pmu_30/shared/python')
from serial_transfer_protocol import PMUSerialTransfer, Command
pmu = PMUSerialTransfer('COM11', 115200)
pmu.connect()
pmu.send(Command.STOP_STREAM, b'')
time.sleep(0.2)
pmu.send(Command.START_STREAM, struct.pack('<H', 10))
print('Press BLUE B1 button...')
start = time.time()
while time.time() - start < 25:
    pkt = pmu.receive(timeout=0.2)
    if pkt and pkt.cmd == 0x22 and len(pkt.payload) >= 106:
        din = (pkt.payload[78] >> 0) & 1
        led = pkt.payload[9]
        if din: print(f'PRESSED! LED={\"ON\" if led else \"off\"}')
pmu.disconnect()
"
```

### Config Serialization Roundtrip: FIXED ✓

**Problem**: Config read from device → parsed to UI → re-serialized produced different bytes, causing upload failures.

**Root causes found and fixed**:

1. **`_parse_channel_config()` bool() conversion** (`device_controller.py:1216-1220`):
   - Bug: `bool(getattr(config, 'use_pullup', 1))` converted `10` to `True` (1)
   - Fix: Use `int()` instead of `bool()` to preserve raw values

2. **`_serialize_digital_input()` debounce fallback** (`binary_config.py:1094-1103`):
   - Bug: `config.get('debounce_time', 50) or config.get('debounce_ms', 50)` always defaulted to 50
   - Fix: Check key existence explicitly before using defaults

3. **`_parse_channel_config()` power_output missing fields** (`device_controller.py:1243-1252`):
   - Bug: Only extracted 3 fields, missing `retry_count`, `retry_delay_s`, `pwm_frequency`, etc.
   - Fix: Extract ALL CfgPowerOutput_t fields for roundtrip compatibility

4. **`_serialize_power_output()` non-zero defaults** (`binary_config.py:1216-1234`):
   - Bug: Used defaults like `retry_count=3` which changed zero values
   - Fix: Use `0` as default for all fields

**Verification**: Config roundtrip now produces identical bytes (106 → 106, MATCH).

### Configurator Config Sync: FIXED ✓

**Problem**: Configurator showed "Config sync failed - no ACK from device" while test scripts worked.

**Root causes and fixes**:

1. **Firmware bug: LOAD_BINARY fails when config exists**
   - Symptom: Upload times out if device already has config
   - Workaround: Always call `CLEAR_CONFIG` before upload
   - Proper fix: Firmware should handle re-upload (TODO)

2. **Parser resync after disconnect/reconnect**
   - Symptom: After configurator reconnects, commands fail
   - Cause: Firmware parser in bad state from partial packet
   - Fix: Send garbage bytes `\x81\x81\x81\x81` to trigger stale packet timeout (50ms)

3. **Magic sleeps replaced with ACK-based waiting**
   - Bad: `time.sleep(2.5)` hoping flash erase is done
   - Good: `pmu.clear_config()` waits for `CLEAR_CONFIG_ACK` (timeout=3s)
   - Rule: **Always wait for ACK, never use magic sleep for protocol operations**

**Code pattern for reliable config upload** (`device_controller.py:upload_binary_config()`):
```python
# 1. Resync parser (trigger stale packet timeout)
pmu._port.write(b'\x81\x81\x81\x81')
time.sleep(0.1)  # 50ms stale timeout + margin

# 2. Stop telemetry (method drains buffer)
pmu.stop_stream()

# 3. Verify connectivity
pmu.ping(timeout=1.0)

# 4. Clear config with ACK wait (NOT magic sleep!)
pmu.clear_config()  # Waits for CLEAR_CONFIG_ACK

# 5. Upload
pmu.upload_config(binary_data)  # Waits for BINARY_ACK
```

**Key files**:
- `device_controller.py:upload_binary_config()` - config upload with resync
- `device_controller.py:read_configuration()` - config read with resync
- `serial_transfer_protocol.py:clear_config()` - ACK-based clear

### Nucleo Telemetry Voltage: TODO

**Issue**: Output Monitor shows ~60V in V/Vltg columns - garbage data.

**Cause**: Nucleo-F446RE has no voltage sensing ADC. Firmware sends uninitialized `voltage_mv` field.

**Fix needed**:
- Firmware: Send 0 or valid mock value for `voltage_mv` on Nucleo
- Or: UI should show "-" when voltage is clearly invalid (>50V)

### ESP32 WiFi Bridge

**Architecture**: ESP32 acts as transparent SerialTransfer bridge over WiFi.

```
┌─────────────────┐  USART1  ┌─────────────────┐  WiFi/TCP  ┌─────────────────┐
│  Nucleo-F446RE  │  PA9/10  │   ESP32 KS0413  │ Port 8266  │  Configurator   │
│     (PMU-30)    │◄────────►│  GPIO 25/26     │◄──────────►│  (or browser)   │
└─────────────────┘          └─────────────────┘            └─────────────────┘
```

**Hardware wiring**:
| Nucleo | Function | ESP32 | Function |
|--------|----------|-------|----------|
| D8 (PA9) | USART1_TX | GPIO25 | RX |
| D2 (PA10) | USART1_RX | GPIO26 | TX |
| GND | Ground | GND | Ground |

**CRITICAL - GPIO Alternate Function Conflict (PA9)**:

PA9 is shared between USART1 (AF7) and TIM1_CH2 (AF1). If TIM_PWM_Init() is called AFTER USART1_Init(), it will overwrite PA9 from AF7 to AF1!

**Symptom**: ESP32 receives only a few bytes then stops, PA9 state=0 (should be 1 when UART idle).

**Diagnosis via telemetry debug fields** (added at offset 94-103):
```c
// pmu_serial_transfer_port.c - telemetry debug fields
buf[idx++] = (GPIOA->IDR & GPIO_IDR_ID9) ? 1 : 0;  // PA9 state
buf[idx++] = (GPIOA->MODER >> 18) & 0x3;           // PA9 MODER (should be 2)
buf[idx++] = (GPIOA->AFR[1] >> 4) & 0xF;           // PA9 AFR (should be 7)
```

**If AFR shows 1 instead of 7** → TIM1 overwriting USART1 config!

**Fix** (`main_nucleo_f446.c` TIM_PWM_Init):
```c
// WRONG - conflicts with USART1 TX on PA9
GPIO_InitStruct.Pin = GPIO_PIN_8 | GPIO_PIN_9;

// CORRECT - PA9 reserved for USART1
GPIO_InitStruct.Pin = GPIO_PIN_8;  // Only PA8 for TIM1_CH1
```

**ESP32 GPIO selection notes**:
- GPIO4/5 - boot strapping, may cause issues
- GPIO16/17 - PSRAM on some boards
- GPIO25/26 - DAC pins, always free, recommended for UART

**ESP32 project**: `firmware/esp32_bridge/`
- `platformio.ini` - build config for esp32dev
- `src/main.cpp` - WiFi AP/STA + TCP server on port 8266
- Web dashboard on port 80 with auto-refresh

**Build & Upload ESP32**:
```bash
cd c:/Projects/pmu_30/firmware/esp32_bridge && python -m platformio run -e esp32dev -t upload
```

## Deprecated (removed)

- `pmu_config_json.c` - JSON config parsing
- `pmu_logic_functions.c` - Old logic engine
- cJSON dependency

### Timer Mode Mapping

**CRITICAL**: Configurator UI modes must map to firmware's `TimerMode_t` enum values correctly.

**Firmware Timer modes** (from `shared/engine/timer.h`):
| Mode | Value | Description |
|------|-------|-------------|
| DELAY_ON | 0x00 | Delay before output goes ON |
| DELAY_OFF | 0x01 | Delay before output goes OFF |
| PULSE | 0x02 | Output ON immediately, OFF after delay (countdown) |
| BLINK | 0x03 | Toggle at interval |
| ONESHOT | 0x04 | Single pulse, requires manual reset |
| RETRIGGERABLE | 0x05 | Restarts on each trigger |
| MONOSTABLE | 0x06 | Like oneshot but auto-resets |

**Configurator MODE_MAP** (in `binary_config.py:_serialize_timer()`):
```python
MODE_MAP = {
    "count_up": 0,      # DELAY_ON: wait duration, then ON
    "count_down": 2,    # PULSE: ON immediately, OFF after duration
    "one_shot": 4,      # ONESHOT
    "retriggerable": 5, # RETRIGGERABLE
    "pulse": 2,         # PULSE (alias)
    "blink": 3,         # BLINK
}
```

**Symptom**: "Timer doesn't activate on button press" → check mode mapping. If UI sends "count_down" but MODE_MAP doesn't have it, mode defaults to wrong value.

### Channel Type Values

**CRITICAL**: Binary config channel types must use correct hex values from `shared/python/channel_validation.py`.

| Channel Type | Value | Notes |
|--------------|-------|-------|
| DIGITAL_INPUT | 0x01 | GPIO inputs |
| ANALOG_INPUT | 0x02 | ADC inputs |
| FREQUENCY_INPUT | 0x03 | Frequency counter |
| CAN_INPUT | 0x04 | CAN RX signals |
| POWER_OUTPUT | 0x10 | PROFET outputs |
| PWM_OUTPUT | 0x11 | PWM outputs |
| TIMER | 0x20 | Timer channels |
| LOGIC | 0x21 | Logic operations |
| MATH | 0x22 | Math operations |
| TABLE_2D | 0x23 | 2D lookup tables |
| FILTER | 0x25 | Signal filters |
| PID | 0x26 | PID controllers |
| NUMBER | 0x27 | Constants |
| SWITCH | 0x28 | Multi-way switch |
| COUNTER | 0x2A | Event counters |
| HYSTERESIS | 0x2B | Hysteresis blocks |
| FLIPFLOP | 0x2C | SR/D flip-flops |

**Firmware LoadConfig filter** (in `pmu_channel_exec.c:PMU_ChannelExec_LoadConfig()`):
```c
// Only virtual channels in range [TIMER, FLIPFLOP] are added to executor
if (type >= CH_TYPE_TIMER && type <= CH_TYPE_FLIPFLOP) {
    PMU_ChannelExec_AddChannel(channel_id, type, &data[offset]);
}

// Power outputs create output links (source_id → hw_index)
if (type == CH_TYPE_POWER_OUTPUT && source_id != 0xFFFF) {
    PMU_ChannelExec_AddOutputLink(channel_id, source_id, hw_index);
}
```

**Symptom**: "channels=0 after upload" → check channel type values. Wrong type (e.g., 10 instead of 0x20 for Timer) causes channel to be skipped.

### Timer Sub-Channels

**Architecture**: Timer channels have 3 sub-channels accessible via telemetry for monitoring and as source references:

| Sub-Channel | ID Offset | Value | Description |
|-------------|-----------|-------|-------------|
| \ | 0x8000 | ms | Time elapsed since trigger |
| \ | 0x8001 | ms | Time remaining until expiration |
| \ | 0x8002 | enum | 0=IDLE, 1=RUNNING, 2=DONE |

**Sub-channel ID calculation**: - Timer ID 200 → \ = 200 | 0x8000 = 32968
- Timer ID 200 → \ = 200 | 0x8001 = 32969
- Timer ID 200 → \ = 200 | 0x8002 = 32970

**Firmware implementation** (\):
**Telemetry format** (\):
- \ at offset 104 includes sub-channels
- For 1 Timer: virt_count=4 (main + 3 sub-channels)
- Each entry: 
**Configurator display** (\):
- Timer sub-channels auto-created with channel_type: \, \, - Display names: \, \, 
**Key files**:
- \ - sub-channel functions, inline Timer evaluator
- \ - telemetry builder with sub-channels
- \ - UI display and formatting

### Channel Config Serialization Pitfalls

**Logic channel serialization** uses these field names (in priority order):
1. `input_channels` - list of channel IDs or names
2. `channel` / `channel_2` - single input channel names
3. `set_channel` / `reset_channel` / `toggle_channel` - for specific operations

**WRONG**: `inputs: ['Button']` - this field is IGNORED!
**CORRECT**: `channel: 'Button'` or `input_channels: ['Button']`

**Timer mode mapping** (`binary_config.py:_serialize_timer()`):
| UI Mode | Firmware Mode | Behavior |
|---------|---------------|----------|
| count_up | 0 | output = elapsed_ms |
| count_down | 1 | output = remaining_ms (only when RUNNING, 0 when IDLE) |
| pulse | 2 | output = 1 while RUNNING, 0 when IDLE |

**Symptom**: "Timer shows delay_ms when IDLE" → firmware needs `if (state == RUNNING)` check, not just elapsed < delay.

**Config field name consistency** - must match across:
- Dialog (`timer_dialog.py`): uses `mode`, `limit_hours`, `start_channel`
- Device Controller (`device_controller.py`): returns `timer_mode`, `limit_hours`, `start_channel`
- Serialization (`binary_config.py`): expects `timer_mode`, `limit_hours`, `start_channel`

**Dialog may expect different names!** Check `_populate_from_existing()` and `get_config()` methods.

### Debugging Config Upload

**Always verify config by reading back**:
```python
# After upload, read config and check parsed values
pmu.send(Command.GET_CONFIG, b'')
data = pmu.receive().payload[4:]  # Skip 4-byte chunk header
count = struct.unpack('<H', data[0:2])[0]
# Parse each channel header + config...
```

**Common issues**:
- `input_count=0` in Logic → wrong field name used (inputs vs channel)
- `trigger_id=0xFFFF` in Timer → start_channel not resolved to ID
- `source_id=0` in PowerOutput → source_channel reference not found
