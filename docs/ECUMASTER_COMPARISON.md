# PMU-30 vs Ecumaster PMU Comparison

**Date:** 2025-12-29
**Ecumaster Document Version:** 101.1.5
**Ecumaster Models:** PMU-16, PMU-16DL, PMU-16AS, PMU-24DL
**PMU-30 Version:** v3.0

---

## 1. Hardware Specifications

| Parameter | Ecumaster PMU-16/24 | PMU-30 | Status |
|-----------|---------------------|--------|--------|
| **High-Side Outputs** | 10×25A + 6×15A (PMU-16) | 30×40A (PROFET) | ✅ Superior |
| **Low-Side Outputs** | 6×1A (AS model only) | — | ❌ Not supported |
| **H-Bridge** | — | 4× dual (30A each) | ✅ Additional |
| **Analog Inputs** | 16× (0-5V/0-20V) | 20× (10-bit, 0-5V) | ✅ More |
| **Digital Inputs** | — (via analog) | 20× dedicated | ✅ Additional |
| **ADC Resolution** | 10-bit (0-5V), 12-bit (0-20V) | 10-bit | ⚠️ Less for 20V |
| **Voltage Range** | 6-22V | 6-22V DC | ✅ Equal |
| **Pull-up/Pull-down** | 10K selectable | Configurable | ✅ OK |
| **+5V Output** | 400-500mA | 500mA | ✅ OK |
| **Total Current** | 150A (PMU-16), 200A (AS) | 200A | ✅ OK |

---

## 2. CAN Bus

| Parameter | Ecumaster PMU | PMU-30 | Status |
|-----------|---------------|--------|--------|
| **CAN Buses** | 2× CAN 2.0 A/B | 2× CAN FD + 2× CAN 2.0 | ✅ Superior |
| **Data Rate** | 125/250/500/1000 kbps | Up to 5 Mbps (CAN FD) | ✅ Superior |
| **CAN1 Speed** | Fixed 1Mbps | Configurable | ✅ More flexible |
| **Termination** | CAN1 none, CAN2 software | Software on all | ✅ Better |
| **CAN Message Objects** | Up to 100 incoming | Up to 64 | ⚠️ Less |
| **Bit Masking** | Yes | Yes | ✅ OK |
| **DBC/CANX Import** | Yes | Yes | ✅ OK |
| **Compound Messages** | Yes (multiplexed) | Yes | ✅ OK |
| **Byte Order** | Intel/Motorola | Intel/Motorola | ✅ OK |

### CAN Keypad Support

| Keypad | Ecumaster PMU | PMU-30 | Status |
|--------|---------------|--------|--------|
| Ecumaster 4/6/8/12 keys | ✅ 2 units | ❌ | ❌ Not supported |
| LifeRacing PDU Keypad | ✅ | ❌ | ❌ Not supported |
| MoTeC/RaceGrade | ✅ 1 unit | ❌ | ❌ Not supported |
| Grayhill | ✅ 1 unit | ❌ | ❌ Not supported |
| BlinkMarine PKP-2600/2800 | ❌ | ✅ Full support | ✅ Unique |

---

## 3. Logic Functions

| Parameter | Ecumaster PMU | PMU-30 | Status |
|-----------|---------------|--------|--------|
| **Function Count** | 100 | 100 (channel IDs 200-999) | ✅ OK |
| **Operation Count** | 250 | ~64 types | ⚠️ Different architecture |
| **Update Frequency** | 500 Hz | 500 Hz | ✅ OK |

### Logic Operations

| Operation | Ecumaster | PMU-30 | Status |
|-----------|-----------|--------|--------|
| AND | ✅ | ✅ | ✅ OK |
| OR | ✅ | ✅ | ✅ OK |
| XOR | ✅ | ✅ | ✅ OK |
| NOT | ✅ (IsFalse) | ✅ | ✅ OK |
| NAND | ❌ | ✅ | ✅ Additional |
| NOR | ❌ | ✅ | ✅ Additional |
| IsTrue | ✅ | ✅ (passthrough) | ✅ OK |
| =, ≠, <, ≤, >, ≥ | ✅ | ✅ | ✅ OK |
| in_range | ❌ | ✅ | ✅ Additional |
| Flash | ✅ | ✅ | ✅ OK |
| Pulse | ✅ | ✅ (retriggerable) | ✅ OK |
| Toggle | ✅ | ✅ | ✅ OK |
| Set/Reset Latch | ✅ | ✅ | ✅ OK |
| Hysteresis | ✅ | ✅ (with polarity) | ✅ OK |
| Changed | ✅ | ✅ (Rising/Falling/Both) | ✅ OK |

---

## 4. Data Processing

| Parameter | Ecumaster PMU | PMU-30 | Status |
|-----------|---------------|--------|--------|
| **PID Controllers** | Yes | 16 max | ✅ OK |
| **PID Anti-Windup** | Not specified | Yes | ✅ Better |
| **PID Derivative Filter** | Not specified | Yes | ✅ Better |
| **2D Tables** | Yes | Up to 16 points | ✅ OK |
| **3D Tables** | Yes | Up to 16×16 | ✅ OK |
| **Timers** | Yes | 16 max | ✅ OK |
| **Timer Modes** | Not specified | Count up/down, retriggerable | ✅ OK |
| **Switch Channels** | Yes | Yes (multi-position) | ✅ OK |
| **Number (Math)** | Yes | 14 operations | ✅ OK |
| **Lua Scripts** | ❌ | 8 scripts × 32KB | ✅ Unique |
| **Filters** | Not specified | Low-pass, moving average | ✅ Additional |

### Math Operations (Number Channels)

| Operation | Ecumaster | PMU-30 | Status |
|-----------|-----------|--------|--------|
| Constant | ✅ | ✅ | ✅ OK |
| Add (+) | ✅ | ✅ | ✅ OK |
| Subtract (-) | ✅ | ✅ | ✅ OK |
| Multiply (*) | ✅ | ✅ | ✅ OK |
| Divide (/) | ✅ | ✅ | ✅ OK |
| Modulo (%) | ❌ | ✅ | ✅ Additional |
| Min | ✅ | ✅ | ✅ OK |
| Max | ✅ | ✅ | ✅ OK |
| Average | ✅ | ✅ | ✅ OK |
| Abs | ✅ | ✅ | ✅ OK |
| Scale | ✅ | ✅ | ✅ OK |
| Clamp | ✅ | ✅ | ✅ OK |
| Lookup | ✅ | ✅ (2-5 inputs) | ✅ OK |
| Bitwise AND/OR | ❌ | ✅ | ✅ Additional |

---

## 5. Protection Features

| Parameter | Ecumaster PMU | PMU-30 | Status |
|-----------|---------------|--------|--------|
| **Overcurrent** | Yes, per output | Yes, per output + inrush | ✅ Better |
| **Undercurrent** | Yes | Open-load detection | ✅ OK |
| **Thermal Shutdown** | Yes | Yes, per output | ✅ OK |
| **Short-Circuit** | Yes | Yes (SC state) | ✅ OK |
| **Reverse Polarity** | Up to 16V | Up to 16V | ✅ OK |
| **Inrush Current** | Soft Start | Soft Start + Inrush limit | ✅ Better |
| **Battery Monitoring** | Yes | Yes (min/max thresholds) | ✅ OK |
| **Temperature Sensors** | 3× on board (TL, TR, TF) | 2× on board (L, R) | ⚠️ Less |
| **Inertia Switch** | Yes (accelerometer/gyroscope) | 3D accelerometer + gyroscope | ✅ OK |

### Output Status Codes

| Status | Ecumaster | PMU-30 | Description |
|--------|-----------|--------|-------------|
| OFF | 0 | 0 | Output disabled |
| ACTIVE/ON | 1 | 1 | Output active |
| UNDERCURRENT | 2 | OL (5) | No load detected |
| OVERCURRENT | 3 | OC (2) | Current limit exceeded |
| THERMAL | 7 | OT (3) | Thermal protection |
| SHORT-CIRCUIT | — | SC (4) | Short circuit detected |
| PWM | — | 6 | PWM mode active |
| DISABLED | — | 7 | Programmatically disabled |

---

## 6. Data Logging

| Parameter | Ecumaster PMU | PMU-30 | Status |
|-----------|---------------|--------|--------|
| **Log Memory** | 256 MB | 512 MB | ✅ Better |
| **Log Rate** | Up to 500 Hz | 50-500 Hz | ✅ OK |
| **Custom Log** | Yes | Yes | ✅ OK |
| **PC Logging** | Up to 500 Hz | Yes (telemetry) | ✅ OK |
| **RTC** | Yes (supercapacitor 3 days) | Yes | ✅ OK |

---

## 7. Special Modules

| Module | Ecumaster PMU | PMU-30 | Status |
|--------|---------------|--------|--------|
| **Wipers Module** | O8 + park switch | H-Bridge + PID park | ✅ Better |
| **Blinkers Module** | Yes | Yes (flash logic) | ✅ OK |
| **Delayed Turn Off** | Yes | Yes (timer channels) | ✅ OK |
| **Autosaved Channels** | Yes | Yes | ✅ OK |
| **Multiple PMUs** | Up to 5 units | Via CAN bus | ✅ OK |

---

## 8. PWM and Soft Start

| Parameter | Ecumaster PMU | PMU-30 | Status |
|-----------|---------------|--------|--------|
| **PWM Frequency** | 4-400 Hz | 1 Hz - 20 kHz | ✅ Wider range |
| **PWM Resolution** | Not specified | 0.1% (0-1000) | ✅ OK |
| **PWM Outputs** | Only 25A outputs | All PROFET outputs | ✅ More |
| **Soft Start** | 25A outputs only | All outputs (0-5000ms) | ✅ Better |
| **Duty from Channel** | Yes | Yes (source_channel_id) | ✅ OK |

---

## 9. Communications

| Interface | Ecumaster PMU | PMU-30 | Status |
|-----------|---------------|--------|--------|
| **CAN** | 2× CAN 2.0 | 4× (2 FD + 2 Classic) | ✅ Better |
| **USB** | Via CAN adapter | USB-C native | ✅ Simpler |
| **WiFi** | ❌ | AP/STA mode | ✅ Unique |
| **Bluetooth** | ❌ | Classic + BLE | ✅ Unique |
| **LIN** | ❌ | LIN 2.x Master/Slave | ✅ Unique |
| **Web UI** | ❌ | Built-in (192.168.4.1) | ✅ Unique |

---

## 10. Channel System Architecture

PMU-30 uses a unified channel abstraction layer:

| Channel ID Range | Type | Description |
|------------------|------|-------------|
| 0-49 | Digital Inputs | Physical digital input channels |
| 50-99 | Analog Inputs | Physical analog input channels |
| 100-199 | Outputs | Power outputs (100-129), H-Bridges (150-157) |
| 200-999 | Virtual | Logic, Math, Timers, Tables, Filters, PID |
| 1000-1023 | System | Battery voltage, temperatures, status |
| 1100-1279 | Output Sub-channels | Per-output status, current, voltage, duty |

### System Channels (1000-1023)

| Channel ID | Name | Description |
|------------|------|-------------|
| 1000 | Battery Voltage | System battery voltage (mV) |
| 1001 | Total Current | Total system current (mA) |
| 1002 | MCU Temperature | Microcontroller temperature (°C×10) |
| 1003 | Board Temp Left | Left side board temperature |
| 1004 | Board Temp Right | Right side board temperature |
| 1005 | Board Temp Max | Maximum board temperature |
| 1006 | Uptime | System uptime (seconds) |
| 1007 | Status | System status flags |
| 1012 | Constant Zero | Always returns 0 |
| 1013 | Constant One | Always returns 1 |

---

## 11. Summary Comparison

### ✅ PMU-30 Advantages over Ecumaster PMU

| Area | PMU-30 Advantage |
|------|------------------|
| **Outputs** | 30×40A vs 16×25A - more power capacity |
| **H-Bridge** | 4× motor outputs - unique feature |
| **CAN FD** | Up to 5Mbps - modern protocol |
| **PWM Range** | 1Hz-20kHz vs 4-400Hz - more flexible |
| **Data Logging** | 512MB vs 256MB - more storage |
| **Lua Scripts** | Programmable logic - unique feature |
| **WiFi/BLE** | Wireless connectivity - unique feature |
| **LIN Bus** | Additional protocol support |
| **PID Extensions** | Anti-windup, derivative filter |
| **Logic Operations** | NAND, NOR, in_range, Modulo, Bitwise |
| **Digital Inputs** | 20× dedicated vs none (uses analog) |
| **USB** | Native USB-C vs CAN adapter required |
| **Web Interface** | Built-in monitoring dashboard |

### ⚠️ Areas for Consideration

| Area | Notes |
|------|-------|
| **CAN Keypads** | Only BlinkMarine supported (Ecumaster, MoTeC, Grayhill not supported) |
| **CAN Message Objects** | 64 vs 100 - less but usually sufficient |
| **ADC Resolution** | 10-bit only (no 12-bit 0-20V mode like PMU-24) |
| **Temperature Sensors** | 2× vs 3× on board |

### ❌ Not Available in PMU-30

1. **Ecumaster CAN Keypad Support** (4/6/8/12 buttons)
2. **MoTeC/RaceGrade Keypad** support
3. **Grayhill Keypad** support
4. **LifeRacing PDU Keypad** support
5. **Low-Side Outputs** (PMU-30 only has high-side PROFET outputs)

---

## 12. Configuration Format

PMU-30 uses JSON v3.0 configuration format:

```json
{
  "version": "3.0",
  "device_name": "PMU-30",
  "channels": [
    {
      "channel_id": 100,
      "channel_type": "power_output",
      "channel_name": "Headlights",
      "output_pins": [0, 1],
      "source_channel_id": 1,
      "current_limit": 15000,
      "pwm_frequency": 200
    }
  ],
  "can_messages": [
    {
      "message_id": 256,
      "can_bus": 1,
      "cycle_time_ms": 100,
      "signals": []
    }
  ]
}
```

---

## References

- [Ecumaster PMU Manual v101.1.5](https://www.ecumaster.com/files/PMU/)
- [PMU-16 Pinout](https://www.ecumaster.com/files/PMU/PMU-16_Pinout_v1.2.pdf)
- [PMU-16AS Pinout](https://www.ecumaster.com/files/PMU/PMU-16AS_Pinout_v1.3.pdf)
- [PMU-24 Pinout](https://www.ecumaster.com/files/PMU/PMU-24_Pinout_v1.3.pdf)
- [PMU-30 Protocol Specification](protocol_specification.md)
- [PMU-30 Channel API](api/channel-api.md)
