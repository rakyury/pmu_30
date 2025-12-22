# Troubleshooting Guide

**Version:** 1.0
**Date:** December 2024

---

## 1. Quick Diagnostics

### Initial Checklist

1. Check power LED - should be solid green
2. Verify battery voltage (9-18V nominal)
3. Check for fault LEDs on channels
4. Review fault log via configurator

---

## 2. Power Issues

### 2.1 Device Won't Power On

| Symptom | Possible Cause | Solution |
|---------|---------------|----------|
| No LEDs | No power supply | Check battery connection |
| No LEDs | Blown main fuse | Check/replace main fuse |
| No LEDs | Reverse polarity | Check wiring polarity |
| Red LED only | Undervoltage | Check battery voltage (>9V) |

### 2.2 Undervoltage Warnings

```
Fault: UNDERVOLTAGE - Battery at 8.5V
```

**Solutions:**
1. Check battery charge state
2. Check for voltage drop in wiring
3. Verify wire gauge adequate for current
4. Check main ground connection

### 2.3 Overvoltage Protection

```
Fault: OVERVOLTAGE - Battery at 19.2V
```

**Solutions:**
1. Check alternator regulator
2. Verify battery type matches charger
3. Check for loose battery connections

---

## 3. Output Problems

### 3.1 Output Won't Turn On

| Check | How | Expected |
|-------|-----|----------|
| Channel enabled | Configurator | Enabled = true |
| Fault status | Status LED | Green, not red |
| Logic function | Logic tab | Correct output |
| PWM value | Monitor | >0 for ON |

**Diagnostic Steps:**
```c
// Check output state
PMU_OutputDiag_t diag;
PMU_GetOutputDiagnostics(100, &diag);
printf("State: %d, Fault: %d\n", diag.state, diag.fault_code);
```

### 3.2 Overcurrent Faults

```
Fault: CH102 OVERCURRENT - 16.5A (limit 15A)
```

**Solutions:**
1. Check for short circuit in load
2. Verify current limit setting
3. Check for pinched wires
4. Reduce PWM duty cycle

### 3.3 Open Load Detection

```
Fault: CH105 OPEN_LOAD - No current detected
```

**Solutions:**
1. Check load connection
2. Verify ground connection
3. Check for blown load fuse
4. Test load with multimeter

### 3.4 Short Circuit

```
Fault: CH103 SHORT_CIRCUIT
```

**Immediate Actions:**
1. Output automatically disabled
2. Check wiring for damage
3. Disconnect load and test
4. Repair wiring before retry

**To Clear:**
1. Fix the short circuit cause
2. Clear fault in configurator
3. Output will attempt retry

---

## 4. Input Problems

### 4.1 Analog Input Reading Wrong

| Issue | Check | Solution |
|-------|-------|----------|
| Always 0 | Wiring | Check signal wire |
| Always max | Pull-up | Check if enabled |
| Noisy | Shielding | Add filtering |
| Wrong value | Scaling | Check factor/offset |

### 4.2 Temperature Sensor Issues

**NTC Reading Too High/Low:**
```
// Verify NTC type matches config
// NTC 10K: ~10K at 25°C
// NTC 2.2K: ~2.2K at 25°C
```

**Solutions:**
1. Verify sensor type in config
2. Check B-value parameter
3. Verify pull-up resistor
4. Check wiring continuity

### 4.3 Digital Input Not Working

**Checklist:**
- [ ] Input type set to "digital"
- [ ] Pull-up/pull-down configured
- [ ] Invert setting correct
- [ ] Switch connected properly

---

## 5. H-Bridge Issues

### 5.1 Motor Not Moving

| Check | Expected | If Not |
|-------|----------|--------|
| Enable | HIGH | Check config |
| PWM | >0 | Check logic |
| Current | >0 | Check motor |
| Fault | None | See fault |

### 5.2 Motor Only One Direction

**Causes:**
1. One half-bridge failed
2. Wiring issue
3. Dead-time too long

**Test:**
```c
// Test forward
PMU_Channel_SetValue(130, 500);
HAL_Delay(2000);
// Test reverse
PMU_Channel_SetValue(130, -500);
```

### 5.3 H-Bridge Overheating

**Solutions:**
1. Reduce PWM frequency
2. Check motor current
3. Add cooling
4. Reduce duty cycle

---

## 6. CAN Bus Issues

### 6.1 No Communication

**Diagnostic Steps:**
```
PMU> can status 0
CAN0: ERROR - Bus Off
TX Errors: 255, RX Errors: 0
```

| Symptom | Cause | Solution |
|---------|-------|----------|
| Bus Off | No termination | Add 120Ω |
| Bus Off | Wrong bitrate | Match ECU |
| TX errors | Wiring | Check CAN-H/L |
| RX errors | Signal quality | Check cabling |

### 6.2 Message Timeouts

```
Fault: CAN1 TIMEOUT - MSG 0x360
```

**Checklist:**
1. Verify ECU is transmitting
2. Check message ID matches
3. Verify bus configuration
4. Check timeout setting

### 6.3 Wrong Signal Values

**Common Causes:**
- Wrong start bit
- Wrong byte order (endianness)
- Wrong factor/offset
- Signed vs unsigned mismatch

**Debug:**
```
PMU> can monitor 0x360
[0x360] 00 1F 40 00 00 00 00 00
        ^^ ^^ RPM raw = 0x1F40 = 8000
```

---

## 7. Logic Function Issues

### 7.1 Function Not Executing

**Checklist:**
- [ ] Function enabled
- [ ] Input channels valid
- [ ] Output channel configured
- [ ] No circular dependencies

### 7.2 Wrong Output Value

**Debug Process:**
1. Check input values
2. Verify function type
3. Check parameters
4. Monitor intermediate values

```c
// Enable debug mode
PMU_LogicFunctions_SetDebug(func_id, true);
// Now function logs inputs/outputs
```

### 7.3 Timing Issues

**If outputs are delayed:**
1. Check execution priority
2. Reduce function chain length
3. Optimize complex functions
4. Check CPU load

---

## 8. Communication Issues

### 8.1 Configurator Won't Connect

| Interface | Check | Solution |
|-----------|-------|----------|
| USB | Cable | Try different cable |
| USB | Driver | Install STM32 driver |
| WiFi | AP mode | Look for PMU-30-XXXX |
| WiFi | Password | Default: pmu30admin |
| Bluetooth | Pairing | Re-pair device |

### 8.2 Firmware Update Fails

**Recovery Steps:**
1. Power cycle device
2. Hold BOOT button during power-on
3. Connect via USB
4. Use recovery tool

---

## 9. LED Error Codes

### System LED Patterns

| Pattern | Meaning | Action |
|---------|---------|--------|
| 3 red blinks | Boot failure | Check firmware |
| 5 red blinks | Config error | Reset to default |
| Continuous red | Critical fault | Check fault log |
| Red/Green alt | Update mode | Wait for completion |

### Fault Codes (Binary on LEDs)

| Code | Meaning |
|------|---------|
| 0001 | Overcurrent |
| 0010 | Short circuit |
| 0011 | Open load |
| 0100 | Overtemperature |
| 0101 | Undervoltage |
| 0110 | Overvoltage |
| 0111 | CAN error |
| 1000 | Config error |

---

## 10. Recovery Procedures

### 10.1 Factory Reset

Via configurator: Settings > Factory Reset

Via hardware:
1. Power off
2. Hold CH1 + CH30 buttons
3. Power on
4. Wait for 3 beeps
5. Release buttons

### 10.2 Firmware Recovery

1. Download recovery firmware
2. Hold BOOT during power-on
3. Connect USB
4. Run: `dfu-util -a 0 -D recovery.bin`
5. Power cycle

### 10.3 Clear All Faults

```c
PMU_Fault_ClearAll();
PMU_PROFET_ClearAllFaults();
PMU_HBridge_ClearAllFaults();
```

Or via configurator: Diagnostics > Clear All Faults

---

## 11. Common Error Messages

| Message | Cause | Solution |
|---------|-------|----------|
| E001 | Config CRC error | Reload config |
| E002 | Flash write fail | Check memory |
| E003 | Watchdog reset | Check CPU load |
| E004 | Stack overflow | Reduce functions |
| E005 | DMA error | Power cycle |

---

## See Also

- [Monitoring & Diagnostics](monitoring-diagnostics.md)
- [Configuration Reference](configuration-reference.md)
- [State Machines](../design/state-machines.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024
