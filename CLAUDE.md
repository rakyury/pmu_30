# PMU-30 Project Instructions

## Important Rules

**Single source of truth is `docs/` folder**. For any questions about architecture, protocol, or data formats - always read the documentation in `docs/` first.

**No backwards compatibility**. We don't support legacy code, old formats, or deprecated features. Delete old code instead of keeping it around. No migration paths, no shims, no compatibility layers.

**Testing on real hardware only**. We don't use the emulator (`pmu30_emulator`) for testing. All tests run on the physical Nucleo-F446RE board connected via **COM11**.

**Run telemetry tests after firmware changes**. After any modification to firmware code, run the comprehensive telemetry test suite:
```bash
python tests/test_firmware_telemetry.py COM11
```

**Delete configurator logs before debugging**. Always clear the log file before launching the configurator for debugging sessions:
```bash
del "C:\Users\User\.pmu30\logs\pmu30.log"
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

### Serial Communication Instability

**KNOWN BUG**: Firmware protocol handling is timing-sensitive and unreliable. Commands may fail randomly.

Key issues:
1. **STOP_STREAM breaks subsequent commands**: After STOP_STREAM, PING/GET_CONFIG success becomes random
2. **Commands require retries**: Any command may fail and need 3-5 retries with delays
3. **Fresh firmware is most stable**: Tests work best immediately after `platformio run -t upload`
4. **Sequential operations cause instability**: Running multiple tests in succession often fails

```python
# WORKAROUND - skip STOP_STREAM, use retries instead
for attempt in range(5):
    ser.reset_input_buffer()
    ser.write(build_frame(CMD_GET_CONFIG))
    time.sleep(0.5)
    resp = ser.read(1000)
    if resp:
        break
    time.sleep(1.0)  # Wait before retry
```

**TODO**: Investigate and fix protocol handler reliability in `pmu_protocol.c`. Possible causes:
- Race condition between RX polling and TX in bare-metal loop
- Buffer corruption during long responses (chunked GET_CONFIG)
- State machine issues after STOP_STREAM command

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

## Deprecated (removed)

- `pmu_config_json.c` - JSON config parsing
- `pmu_logic_functions.c` - Old logic engine
- cJSON dependency
