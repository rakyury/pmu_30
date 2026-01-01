# PMU-30 Project Instructions

## Important Rules

**Single source of truth is `docs/` folder**. For any questions about architecture, protocol, or data formats - always read the documentation in `docs/` first.

**No backwards compatibility**. We don't support legacy code, old formats, or deprecated features. Delete old code instead of keeping it around. No migration paths, no shims, no compatibility layers.

**Testing on real hardware only**. We don't use the emulator (`pmu30_emulator`) for testing. All tests run on the physical Nucleo-F446RE board connected via **COM11**.

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

## Deprecated (removed)

- `pmu_config_json.c` - JSON config parsing
- `pmu_logic_functions.c` - Old logic engine
- cJSON dependency
