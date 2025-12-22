# Test Cases

**Version:** 1.0
**Date:** December 2024

---

## 1. Channel System Test Cases

### TC-CH-001: Channel Registration

| Field | Value |
|-------|-------|
| **ID** | TC-CH-001 |
| **Title** | Register new channel |
| **Priority** | High |
| **Preconditions** | System initialized |
| **Steps** | 1. Call PMU_Channel_Register(50, "Test", TYPE_ANALOG)<br>2. Verify return status<br>3. Read channel info |
| **Expected** | Channel registered, info matches |

### TC-CH-002: Channel Read/Write

| Field | Value |
|-------|-------|
| **ID** | TC-CH-002 |
| **Title** | Read and write channel values |
| **Priority** | High |
| **Steps** | 1. Write value 1234 to channel 100<br>2. Read channel 100 |
| **Expected** | Read value equals 1234 |

### TC-CH-003: Invalid Channel Access

| Field | Value |
|-------|-------|
| **ID** | TC-CH-003 |
| **Title** | Access non-existent channel |
| **Priority** | Medium |
| **Steps** | 1. Read channel 9999<br>2. Write to channel 9999 |
| **Expected** | Returns 0 / HAL_ERROR |

### TC-CH-004: Channel Flags

| Field | Value |
|-------|-------|
| **ID** | TC-CH-004 |
| **Title** | Enable/disable channel flags |
| **Steps** | 1. Enable channel 100<br>2. Check ENABLED flag<br>3. Set FAULT flag<br>4. Check FAULT flag |
| **Expected** | Flags set correctly |

---

## 2. Logic Function Test Cases

### TC-LF-001: ADD Function

| Field | Value |
|-------|-------|
| **ID** | TC-LF-001 |
| **Title** | Addition function |
| **Steps** | 1. Set CH200=100, CH201=50<br>2. Execute ADD(200,201)->210 |
| **Expected** | CH210 = 150 |

### TC-LF-002: Divide by Zero

| Field | Value |
|-------|-------|
| **ID** | TC-LF-002 |
| **Title** | Division by zero handling |
| **Steps** | 1. Set CH200=100, CH201=0<br>2. Execute DIVIDE(200,201)->210 |
| **Expected** | CH210 = INT32_MAX |

### TC-LF-003: Greater Than Comparison

| Field | Value |
|-------|-------|
| **ID** | TC-LF-003 |
| **Title** | Greater comparison true/false |
| **Steps** | 1. CH200=100, CH201=50, Execute GREATER<br>2. CH200=50, CH201=100, Execute GREATER |
| **Expected** | 1. Output=1<br>2. Output=0 |

### TC-LF-004: AND Logic

| Field | Value |
|-------|-------|
| **ID** | TC-LF-004 |
| **Title** | Multi-input AND |
| **Steps** | 1. All inputs=1, Execute AND<br>2. One input=0, Execute AND |
| **Expected** | 1. Output=1<br>2. Output=0 |

### TC-LF-005: Toggle Function

| Field | Value |
|-------|-------|
| **ID** | TC-LF-005 |
| **Title** | Toggle on rising edge |
| **Steps** | 1. Input 0->1, check output<br>2. Input 1->0, check output<br>3. Input 0->1, check output |
| **Expected** | 1. Output=1<br>2. Output=1 (no change)<br>3. Output=0 (toggled) |

### TC-LF-006: PID Controller

| Field | Value |
|-------|-------|
| **ID** | TC-LF-006 |
| **Title** | PID settles to setpoint |
| **Steps** | 1. Set PV=750, SP=850<br>2. Execute PID 100 times<br>3. Check output stable |
| **Expected** | Output stabilizes, error < 5 |

### TC-LF-007: Hysteresis

| Field | Value |
|-------|-------|
| **ID** | TC-LF-007 |
| **Title** | Hysteresis on/off thresholds |
| **Steps** | 1. Input rises past ON threshold<br>2. Input falls between thresholds<br>3. Input falls past OFF threshold |
| **Expected** | 1. Output=1<br>2. Output=1 (holds)<br>3. Output=0 |

### TC-LF-008: Moving Average

| Field | Value |
|-------|-------|
| **ID** | TC-LF-008 |
| **Title** | Moving average calculation |
| **Steps** | 1. Input values: 100,200,300,400 (window=4)<br>2. Check output |
| **Expected** | Output = 250 |

### TC-LF-009: Table Lookup

| Field | Value |
|-------|-------|
| **ID** | TC-LF-009 |
| **Title** | 1D table interpolation |
| **Steps** | 1. Table: [0,100,200] -> [0,500,1000]<br>2. Input=50, check output<br>3. Input=150, check output |
| **Expected** | 1. Output=250 (interpolated)<br>2. Output=750 |

### TC-LF-010: Delay Functions

| Field | Value |
|-------|-------|
| **ID** | TC-LF-010 |
| **Title** | Delay ON/OFF timing |
| **Steps** | 1. Delay ON 500ms, trigger, check at 250ms<br>2. Check at 600ms<br>3. Delay OFF 500ms, release, check at 250ms<br>4. Check at 600ms |
| **Expected** | 1. Output=0<br>2. Output=1<br>3. Output=1<br>4. Output=0 |

---

## 3. Output Driver Test Cases

### TC-OUT-001: PWM Duty Cycle

| Field | Value |
|-------|-------|
| **ID** | TC-OUT-001 |
| **Title** | PWM duty cycle accuracy |
| **Steps** | 1. Set duty 0, 250, 500, 750, 1000<br>2. Measure actual duty cycle |
| **Expected** | Actual within ±2% of set value |

### TC-OUT-002: Soft Start

| Field | Value |
|-------|-------|
| **ID** | TC-OUT-002 |
| **Title** | Soft start ramp |
| **Steps** | 1. Set soft start 100ms<br>2. Set output 100%<br>3. Measure at 0, 50, 100ms |
| **Expected** | Ramps linearly from 0 to 100% |

### TC-OUT-003: Overcurrent Protection

| Field | Value |
|-------|-------|
| **ID** | TC-OUT-003 |
| **Title** | Overcurrent shutdown |
| **Steps** | 1. Set current limit 10A<br>2. Apply 12A load<br>3. Check output state |
| **Expected** | Output disabled, FAULT flag set |

### TC-OUT-004: Fault Retry

| Field | Value |
|-------|-------|
| **ID** | TC-OUT-004 |
| **Title** | Automatic retry after fault |
| **Steps** | 1. Trigger fault<br>2. Clear fault condition<br>3. Wait retry period |
| **Expected** | Output re-enables after retry delay |

### TC-OUT-005: Open Load Detection

| Field | Value |
|-------|-------|
| **ID** | TC-OUT-005 |
| **Title** | Open load warning |
| **Steps** | 1. Enable output<br>2. Disconnect load<br>3. Check diagnostics |
| **Expected** | OPEN_LOAD flag set |

---

## 4. H-Bridge Test Cases

### TC-HB-001: Forward/Reverse

| Field | Value |
|-------|-------|
| **ID** | TC-HB-001 |
| **Title** | Direction control |
| **Steps** | 1. Set value +800<br>2. Check state<br>3. Set value -800<br>4. Check state |
| **Expected** | 1. State=FORWARD<br>2. State=REVERSE |

### TC-HB-002: Brake Function

| Field | Value |
|-------|-------|
| **ID** | TC-HB-002 |
| **Title** | Active braking |
| **Steps** | 1. Set forward motion<br>2. Call brake function<br>3. Check motor deceleration |
| **Expected** | Motor stops quickly, State=BRAKE |

### TC-HB-003: Dead Time

| Field | Value |
|-------|-------|
| **ID** | TC-HB-003 |
| **Title** | Dead time prevents shoot-through |
| **Steps** | 1. Rapidly switch direction<br>2. Monitor high/low side timing |
| **Expected** | No overlap in switching |

---

## 5. CAN Bus Test Cases

### TC-CAN-001: Message Reception

| Field | Value |
|-------|-------|
| **ID** | TC-CAN-001 |
| **Title** | CAN RX signal parsing |
| **Steps** | 1. Send CAN msg ID 0x360, data [0xE8,0x03...]<br>2. Read mapped channel |
| **Expected** | Channel value = 1000 |

### TC-CAN-002: Message Transmission

| Field | Value |
|-------|-------|
| **ID** | TC-CAN-002 |
| **Title** | CAN TX periodic |
| **Steps** | 1. Configure TX 100ms interval<br>2. Monitor CAN bus for 1 second |
| **Expected** | ~10 messages received |

### TC-CAN-003: Timeout Detection

| Field | Value |
|-------|-------|
| **ID** | TC-CAN-003 |
| **Title** | CAN RX timeout |
| **Steps** | 1. Configure timeout 100ms<br>2. Send message<br>3. Wait 150ms without message |
| **Expected** | TIMEOUT flag set |

### TC-CAN-004: Signal Endianness

| Field | Value |
|-------|-------|
| **ID** | TC-CAN-004 |
| **Title** | Big/little endian parsing |
| **Steps** | 1. Send [0x01,0x02] as little endian<br>2. Send [0x01,0x02] as big endian |
| **Expected** | 1. Value=0x0201<br>2. Value=0x0102 |

---

## 6. Protection Test Cases

### TC-PROT-001: Undervoltage

| Field | Value |
|-------|-------|
| **ID** | TC-PROT-001 |
| **Title** | Undervoltage detection |
| **Steps** | 1. Set battery to 8V<br>2. Check system response |
| **Expected** | Warning issued, outputs may be limited |

### TC-PROT-002: Overvoltage

| Field | Value |
|-------|-------|
| **ID** | TC-PROT-002 |
| **Title** | Overvoltage protection |
| **Steps** | 1. Set battery to 20V<br>2. Check system response |
| **Expected** | Outputs disabled, protection active |

### TC-PROT-003: Thermal Derating

| Field | Value |
|-------|-------|
| **ID** | TC-PROT-003 |
| **Title** | Temperature-based derating |
| **Steps** | 1. Request 100% output<br>2. Raise board temp to 90°C<br>3. Check actual output |
| **Expected** | Output reduced proportionally |

### TC-PROT-004: Crash Detection

| Field | Value |
|-------|-------|
| **ID** | TC-PROT-004 |
| **Title** | IMU crash detection |
| **Steps** | 1. Simulate 5g acceleration for 50ms<br>2. Check system response |
| **Expected** | Safe shutdown initiated |

---

## 7. Configuration Test Cases

### TC-CFG-001: Load Configuration

| Field | Value |
|-------|-------|
| **ID** | TC-CFG-001 |
| **Title** | Load JSON configuration |
| **Steps** | 1. Upload valid config<br>2. Verify settings applied |
| **Expected** | All settings match config |

### TC-CFG-002: Invalid Configuration

| Field | Value |
|-------|-------|
| **ID** | TC-CFG-002 |
| **Title** | Reject invalid config |
| **Steps** | 1. Upload config with invalid values<br>2. Check response |
| **Expected** | Error returned, old config retained |

### TC-CFG-003: Save to Flash

| Field | Value |
|-------|-------|
| **ID** | TC-CFG-003 |
| **Title** | Persist config across reboot |
| **Steps** | 1. Upload config<br>2. Save to flash<br>3. Power cycle<br>4. Verify config |
| **Expected** | Config retained after reboot |

---

## 8. Performance Test Cases

### TC-PERF-001: Logic Execution Time

| Field | Value |
|-------|-------|
| **ID** | TC-PERF-001 |
| **Title** | 64 functions in <2ms |
| **Steps** | 1. Configure 64 logic functions<br>2. Measure execution time |
| **Expected** | Average <1.5ms, Max <2ms |

### TC-PERF-002: ADC Sample Rate

| Field | Value |
|-------|-------|
| **ID** | TC-PERF-002 |
| **Title** | ADC samples at 1kHz |
| **Steps** | 1. Monitor ADC timestamps<br>2. Calculate sample rate |
| **Expected** | 1000 ±1% samples/second |

### TC-PERF-003: CAN Throughput

| Field | Value |
|-------|-------|
| **ID** | TC-PERF-003 |
| **Title** | CAN message throughput |
| **Steps** | 1. Configure 20 RX, 10 TX messages<br>2. Saturate CAN bus<br>3. Check message loss |
| **Expected** | No message loss at 80% bus load |

---

## 9. Test Coverage Matrix

| Module | Unit | Integration | System |
|--------|------|-------------|--------|
| Channel System | ✓ | ✓ | ✓ |
| Logic Functions | ✓ | ✓ | ✓ |
| PROFET Driver | ✓ | ✓ | ✓ |
| H-Bridge Driver | ✓ | ✓ | ✓ |
| CAN Manager | ✓ | ✓ | ✓ |
| Protection | ✓ | ✓ | ✓ |
| Configuration | ✓ | ✓ | ✓ |

---

## See Also

- [Unit Testing Guide](unit-testing-guide.md)
- [Integration Testing Guide](integration-testing-guide.md)
- [Troubleshooting](../operations/troubleshooting-guide.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024
