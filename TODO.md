# PMU-30 Task List

## In Progress

- [ ] **Clean up repository**
  - Delete emulator files (already marked as deleted in git)
  - Delete debug scripts in tests/
  - Remove obsolete Lua documentation

## Pending

### High Priority

- [ ] **Run Config Roundtrip test**
  - `python tests/test_config_roundtrip.py COM11 tests/configs/logic_and_full.pmu30`
  - Verify: upload → readback → flash save → readback

- [ ] **Auto-restart telemetry after config upload**
  - After `upload_binary_config()`, `save_to_flash()`, `_send_config_to_device_silent()`
  - Automatically call `subscribe_telemetry(rate_hz=10)`

### Testing

- [ ] **Full test coverage: capabilities, system channels, telemetry sync**
  - System channels transmission from device
  - Device capabilities query
  - Telemetry updates for system channels (same as user channels)
  - After config load/update (full/partial)
  - After device restart
  - **Minimum 10 integration test runs at 100% stability**

- [ ] **Test partial config changes (create/edit/delete channels)**
  - Create channel → verify in firmware config → verify in telemetry
  - Edit channel settings → verify updates propagate
  - Delete channel → verify removal
  - **Minimum 10 consecutive runs at 100% stability**

- [ ] **Verify all system channels implemented in firmware**
  System channels from `ChannelDisplayService.SYSTEM_CHANNELS`:
  - [ ] `pmu.batteryVoltage` (1000) - Battery Voltage (mV)
  - [ ] `pmu.totalCurrent` (1001) - Total Current (mA)
  - [ ] `pmu.mcuTemperature` (1002) - MCU Temperature (°C)
  - [ ] `pmu.boardTemperatureL` (1003) - Board Temperature L (°C)
  - [ ] `pmu.boardTemperatureR` (1004) - Board Temperature R (°C)
  - [ ] `pmu.boardTemperatureMax` (1005) - Board Temperature Max (°C)
  - [ ] `pmu.uptime` (1006) - Uptime (s)
  - [ ] `pmu.status` (1007) - System Status
  - [ ] `pmu.userError` (1008) - User Error
  - [ ] `pmu.5VOutput` (1009) - 5V Output (mV)
  - [ ] `pmu.3V3Output` (1010) - 3.3V Output (mV)
  - [ ] `pmu.isTurningOff` (1011) - Is Turning Off
  - [ ] `zero` (1012) - Constant 0
  - [ ] `one` (1013) - Constant 1
  - [ ] RTC channels (1020-1027)
  - [ ] Serial number channels (1030-1031)
  - [ ] Hardware analog inputs `pmu.a{1-10}.voltage` (1220-1239)
  - [ ] Hardware digital inputs `pmu.d{1-20}.state` (0-19)
  - [ ] Output status `pmu.o{1-30}.status` (1100-1129)
  - [ ] Output current `pmu.o{1-30}.current` (1130-1159)
  - [ ] Output voltage `pmu.o{1-30}.voltage` (1160-1189)
  - [ ] Output active `pmu.o{1-30}.active` (1190-1219)
  - [ ] Output duty cycle `pmu.o{1-30}.dutyCycle` (1250-1279)

  All channels must be tested regularly after firmware changes.

- [ ] **GET_CAPABILITIES must return real Nucleo-F446RE capabilities**
  - Add device type = NUCLEO_F446RE (0x10) to distinguish dev board from production
  - Real Nucleo-F446RE capabilities:
    - Outputs: 6 (PA5-LED, PB0, PB1, PC8, PC9, PA8 PWM)
    - Analog inputs: 3 (PA0, PA1, PA4 - ADC1)
    - Digital inputs: 1 (PC13 - User button B1)
    - H-Bridges: 0 (no H-Bridge drivers)
    - CAN buses: 1 (CAN1 on PB8/PB9)
  - Update `pmu_min_port.h` defines for `nucleo_f446re` target
  - Document Nucleo pinout in `docs/hardware/nucleo-pinout.md`

- [ ] **Full CAN bus test coverage**
  - Enable STM32 CAN loopback mode for testing without physical transceiver
  - **CAN channels as first-class channels**:
    - CAN Input channels work like other input channels (readable, telemetry)
    - CAN Output channels work like other output channels (writable, source linking)
    - CAN channel values update in telemetry same as analog/digital
  - **Integration tests**:
    - CAN message TX → loopback RX → verify data integrity
    - CAN filter matching (standard/extended ID, mask filtering)
    - CAN Input channel reads data from CAN message
    - CAN Output channel sends data to CAN bus
    - CAN channel linking (e.g., Logic channel source = CAN Input)
  - **Physical bus emulation**:
    - Loopback mode simulates physical CAN transceiver
    - Test bitrates: 1Mbps, 500kbps, 250kbps, 125kbps (support up to 1-2Mbps)
    - Error frame handling and bus-off recovery
  - **CAN FD support** (future):
    - STM32F446 supports CAN 2.0B (not CAN FD)
    - For CAN FD, need STM32H7 or similar with FDCAN peripheral
  - **10 consecutive runs at 100% stability**

### Code Quality

- [ ] **Refactor magic numbers and sleeps**
  - Move all magic numbers to constants file
  - Remove duplication
  - Replace dumb sleeps with smart waiting logic where possible

- [ ] **Maximum log coverage + live log monitoring**
  - Log all configurator operations
  - Monitor logs on startup for error tracking
  - Auto-detect and report errors (not just on app close)

- [ ] **Global error handling with detailed log analysis**
  - Catch all unhandled exceptions
  - Write to log with full stack trace
  - Enable detailed post-mortem analysis

### UI/UX

- [ ] **Progress bar and modal screen for long operations**
  - Config load/save operations
  - Connection and reconnection
  - Show progress to user

## Completed

- [x] **Implement Device Capabilities Protocol (0x30)**
  - Firmware: GET_CAPABILITIES (0x30) and CAPABILITIES (0x31) handlers
  - Configurator: DeviceCapabilities dataclass and get_capabilities() method
  - Tests: get_capabilities() helper function in protocol_helpers.py
  - Tested: PMU-30, v1.0.0, 30 outputs, 10 analog, 8 digital, 2 H-bridges, 2 CAN

- [x] **Add IWDG watchdog to firmware** (commit 256068a)
  - 2-second timeout for crash protection
  - Auto-reset on hang

- [x] **Fix T-MIN response retransmit loop** (commit 256068a)
  - Changed all MIN responses from reliable to unreliable
  - Prevents infinite retransmits when client doesn't ACK

- [x] **USB VCP timing fixes in tests** (commit 256068a)
  - Added 20ms delay after send for USB buffering
  - Reduced read timeout to 50ms for responsive polling

---
Last updated: 2026-01-03
