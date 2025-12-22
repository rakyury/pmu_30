# PMU-30 Standard CAN Stream

## Overview

Standard CAN Stream provides **real-time broadcast of key PMU parameters** over CAN bus for monitoring and data logging. The stream uses a **predefined set of CAN frames** with configurable Base ID and CAN bus selection.

This feature allows external devices (dashboards, loggers, ECUs) to monitor PMU status without custom configuration.

---

## PMU-30 Hardware

| Resource | Count | Description |
|----------|-------|-------------|
| Power Outputs | 30 | o1-o30 (PROFET high-side switches) |
| Analog Inputs | 20 | a1-a20 (0-5V, 12-bit ADC) |
| Digital Inputs | 8 | d1-d8 (5-30V tolerant) |
| H-Bridges | 4 | hb1-hb4 (dual H-bridge drivers) |
| Low-Side Outputs | 6 | l1-l6 (ground switching) |

---

## Configuration Options

| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| **Enabled** | On/Off | Off | Enable Standard CAN Stream |
| **CAN Bus** | CAN A / CAN B | CAN A | Which CAN bus to transmit on |
| **Base ID** | 0x000 - 0x7F0 | 0x600 | Base CAN ID |
| **Extended ID** | Yes/No | No | Use 29-bit extended CAN IDs |
| **Include Extended** | Yes/No | No | Include PMU-30 extended frames (8-15) |

---

## Frame Structure

### Standard Frames (Ecumaster Compatible)

8 frames covering first 16 outputs and 16 analog inputs:

| Frame | CAN ID | Rate | Content |
|-------|--------|------|---------|
| 0 | BaseID + 0 | 20 Hz | System Status & Temperatures |
| 1 | BaseID + 1 | 20 Hz | Output States o1-o16 |
| 2 | BaseID + 2 | 62.5 Hz | Analog Inputs a1-a8 |
| 3 | BaseID + 3 | 62.5 Hz | Analog Inputs a9-a16 |
| 4 | BaseID + 4 | 20 Hz | Output Currents o1-o8 |
| 5 | BaseID + 5 | 20 Hz | Output Currents o9-o16 |
| 6 | BaseID + 6 | 20 Hz | Output Voltages o1-o8 |
| 7 | BaseID + 7 | 20 Hz | Output Voltages o9-o16 |

### PMU-30 Extended Frames

8 additional frames for full hardware coverage:

| Frame | CAN ID | Rate | Content |
|-------|--------|------|---------|
| 8 | BaseID + 8 | 20 Hz | Output States o17-o30 |
| 9 | BaseID + 9 | 20 Hz | Output Currents o17-o24 |
| 10 | BaseID + 10 | 20 Hz | Output Currents o25-o30 + reserved |
| 11 | BaseID + 11 | 20 Hz | Output Voltages o17-o24 |
| 12 | BaseID + 12 | 20 Hz | Output Voltages o25-o30 + reserved |
| 13 | BaseID + 13 | 62.5 Hz | Analog Inputs a17-a20 |
| 14 | BaseID + 14 | 20 Hz | Digital Inputs d1-d8 |
| 15 | BaseID + 15 | 20 Hz | H-Bridge Status hb1-hb4 |

---

## Frame 0: System Status & Temperatures (BaseID + 0, 20 Hz)

General system health, power status, and board temperatures.

| Byte | Signal | Bits | Mask | Range | Resolution | Formula |
|------|--------|------|------|-------|------------|---------|
| 0 | PMU Status | 0-2 | 0x07 | 0-7 | - | See status codes |
| 0 | User Error | 3 | 0x08 | 0-1 | - | Boolean flag |
| 0 | Reserved | 4-7 | 0xF0 | - | - | - |
| 1 | Total Current | 0-7 | 0xFF | 0-255 A | 1 A/bit | A = raw |
| 2 | Battery Voltage | 0-7 | 0xFF | 0-27.75 V | 0.1088 V/bit | V = raw × 0.1088 |
| 3 | Board Temp Left | 0-7 | 0xFF | 0-255 °C | 1 °C/bit | °C = raw |
| 4 | Board Temp Right | 0-7 | 0xFF | 0-255 °C | 1 °C/bit | °C = raw |
| 5 | MCU Temperature | 0-7 | 0xFF | 0-255 °C | 1 °C/bit | °C = raw |
| 6 | Low-Side Active | 0-5 | 0x3F | - | - | Bitfield (l1-l6) |
| 6 | Reserved | 6-7 | 0xC0 | - | - | - |
| 7 | Low-Side Error | 0-5 | 0x3F | - | - | Bitfield (l1-l6) |
| 7 | Reserved | 6-7 | 0xC0 | - | - | - |

### PMU Status Codes (Byte 0, bits 0-2)

| Value | Status | Description |
|-------|--------|-------------|
| 0 | OK | All outputs operating normally |
| 1 | WARNING | Minor issue detected |
| 2 | UNDERCURRENT | One or more outputs in undercurrent |
| 3 | OVERCURRENT | One or more outputs in overcurrent |
| 4 | SHORT_CIRCUIT | Short circuit detected |
| 5 | OVERTEMP | Temperature warning |
| 6 | CRITICAL | Critical fault |
| 7 | THERMAL_SHUTDOWN | Thermal shutdown active |

### Low-Side Bitfields (Bytes 6-7)

| Bit | Mask | Low-Side Output |
|-----|------|-----------------|
| 0 | 0x01 | l1 |
| 1 | 0x02 | l2 |
| 2 | 0x04 | l3 |
| 3 | 0x08 | l4 |
| 4 | 0x10 | l5 |
| 5 | 0x20 | l6 |

---

## Frame 1: Output States o1-o16 (BaseID + 1, 20 Hz)

Status and active state for outputs 1-16. Each byte contains data for 2 outputs.

### Byte Layout

| Byte | High Nibble (bits 4-7) | Low Nibble (bits 0-3) |
|------|------------------------|----------------------|
| 0 | o1 | o2 |
| 1 | o3 | o4 |
| 2 | o5 | o6 |
| 3 | o7 | o8 |
| 4 | o9 | o10 |
| 5 | o11 | o12 |
| 6 | o13 | o14 |
| 7 | o15 | o16 |

### Nibble Format (Odd outputs - High nibble)

| Bits | Mask | Signal |
|------|------|--------|
| 7-5 | 0xE0 | oX.status (3 bits) |
| 4 | 0x10 | oX.active (1 bit) |

### Nibble Format (Even outputs - Low nibble)

| Bits | Mask | Signal |
|------|------|--------|
| 3-1 | 0x0E | oX.status (3 bits) |
| 0 | 0x01 | oX.active (1 bit) |

### Output Status Codes

| Value | Status | Description |
|-------|--------|-------------|
| 0 | OFF | Output is off |
| 1 | ACTIVE | Output is on and operating normally |
| 2 | UNDERCURRENT | Output current below expected level |
| 3 | OVERCURRENT | Output current exceeds limit |
| 4 | SHORT_GND | Short to ground detected |
| 5 | SHORT_VBAT | Short to battery detected |
| 6 | OPEN_LOAD | Open load detected |
| 7 | THERMAL_SHUTDOWN | Output disabled due to overtemperature |

---

## Frame 2: Analog Inputs a1-a8 (BaseID + 2, 62.5 Hz)

Raw voltage readings from analog inputs 1-8.

| Byte | Signal | Range | Resolution | Formula |
|------|--------|-------|------------|---------|
| 0 | a1.voltage | 0-5.0 V | 0.0196 V/bit | V = raw × 0.0196 |
| 1 | a2.voltage | 0-5.0 V | 0.0196 V/bit | V = raw × 0.0196 |
| 2 | a3.voltage | 0-5.0 V | 0.0196 V/bit | V = raw × 0.0196 |
| 3 | a4.voltage | 0-5.0 V | 0.0196 V/bit | V = raw × 0.0196 |
| 4 | a5.voltage | 0-5.0 V | 0.0196 V/bit | V = raw × 0.0196 |
| 5 | a6.voltage | 0-5.0 V | 0.0196 V/bit | V = raw × 0.0196 |
| 6 | a7.voltage | 0-5.0 V | 0.0196 V/bit | V = raw × 0.0196 |
| 7 | a8.voltage | 0-5.0 V | 0.0196 V/bit | V = raw × 0.0196 |

**Note:** Resolution 0.0196 V/bit = 5.0V / 255 ≈ 19.6 mV per count

---

## Frame 3: Analog Inputs a9-a16 (BaseID + 3, 62.5 Hz)

Raw voltage readings from analog inputs 9-16.

| Byte | Signal | Range | Resolution | Formula |
|------|--------|-------|------------|---------|
| 0 | a9.voltage | 0-5.0 V | 0.0196 V/bit | V = raw × 0.0196 |
| 1 | a10.voltage | 0-5.0 V | 0.0196 V/bit | V = raw × 0.0196 |
| 2 | a11.voltage | 0-5.0 V | 0.0196 V/bit | V = raw × 0.0196 |
| 3 | a12.voltage | 0-5.0 V | 0.0196 V/bit | V = raw × 0.0196 |
| 4 | a13.voltage | 0-5.0 V | 0.0196 V/bit | V = raw × 0.0196 |
| 5 | a14.voltage | 0-5.0 V | 0.0196 V/bit | V = raw × 0.0196 |
| 6 | a15.voltage | 0-5.0 V | 0.0196 V/bit | V = raw × 0.0196 |
| 7 | a16.voltage | 0-5.0 V | 0.0196 V/bit | V = raw × 0.0196 |

---

## Frame 4: Output Currents o1-o8 (BaseID + 4, 20 Hz)

Current draw measurements for outputs 1-8.

| Byte | Signal | Range | Resolution | Formula |
|------|--------|-------|------------|---------|
| 0 | o1.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 1 | o2.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 2 | o3.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 3 | o4.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 4 | o5.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 5 | o6.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 6 | o7.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 7 | o8.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |

---

## Frame 5: Output Currents o9-o16 (BaseID + 5, 20 Hz)

Current draw measurements for outputs 9-16.

| Byte | Signal | Range | Resolution | Formula |
|------|--------|-------|------------|---------|
| 0 | o9.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 1 | o10.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 2 | o11.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 3 | o12.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 4 | o13.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 5 | o14.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 6 | o15.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 7 | o16.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |

---

## Frame 6: Output Voltages o1-o8 (BaseID + 6, 20 Hz)

Voltage measurements at output pins for outputs 1-8.

| Byte | Signal | Range | Resolution | Formula |
|------|--------|-------|------------|---------|
| 0 | o1.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 1 | o2.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 2 | o3.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 3 | o4.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 4 | o5.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 5 | o6.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 6 | o7.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 7 | o8.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |

---

## Frame 7: Output Voltages o9-o16 (BaseID + 7, 20 Hz)

Voltage measurements at output pins for outputs 9-16.

| Byte | Signal | Range | Resolution | Formula |
|------|--------|-------|------------|---------|
| 0 | o9.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 1 | o10.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 2 | o11.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 3 | o12.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 4 | o13.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 5 | o14.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 6 | o15.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 7 | o16.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |

---

## Frame 8: Output States o17-o30 (BaseID + 8, 20 Hz) - Extended

Status and active state for outputs 17-30. Same nibble format as Frame 1.

| Byte | High Nibble (bits 4-7) | Low Nibble (bits 0-3) |
|------|------------------------|----------------------|
| 0 | o17 | o18 |
| 1 | o19 | o20 |
| 2 | o21 | o22 |
| 3 | o23 | o24 |
| 4 | o25 | o26 |
| 5 | o27 | o28 |
| 6 | o29 | o30 |
| 7 | reserved | reserved |

---

## Frame 9: Output Currents o17-o24 (BaseID + 9, 20 Hz) - Extended

| Byte | Signal | Range | Resolution | Formula |
|------|--------|-------|------------|---------|
| 0 | o17.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 1 | o18.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 2 | o19.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 3 | o20.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 4 | o21.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 5 | o22.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 6 | o23.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 7 | o24.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |

---

## Frame 10: Output Currents o25-o30 (BaseID + 10, 20 Hz) - Extended

| Byte | Signal | Range | Resolution | Formula |
|------|--------|-------|------------|---------|
| 0 | o25.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 1 | o26.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 2 | o27.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 3 | o28.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 4 | o29.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 5 | o30.current | 0-63.75 A | 0.25 A/bit | A = raw × 0.25 |
| 6 | reserved | - | - | - |
| 7 | reserved | - | - | - |

---

## Frame 11: Output Voltages o17-o24 (BaseID + 11, 20 Hz) - Extended

| Byte | Signal | Range | Resolution | Formula |
|------|--------|-------|------------|---------|
| 0 | o17.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 1 | o18.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 2 | o19.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 3 | o20.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 4 | o21.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 5 | o22.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 6 | o23.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 7 | o24.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |

---

## Frame 12: Output Voltages o25-o30 (BaseID + 12, 20 Hz) - Extended

| Byte | Signal | Range | Resolution | Formula |
|------|--------|-------|------------|---------|
| 0 | o25.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 1 | o26.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 2 | o27.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 3 | o28.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 4 | o29.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 5 | o30.voltage | 0-16.19 V | 0.0635 V/bit | V = raw × 0.0635 |
| 6 | reserved | - | - | - |
| 7 | reserved | - | - | - |

---

## Frame 13: Analog Inputs a17-a20 (BaseID + 13, 62.5 Hz) - Extended

| Byte | Signal | Range | Resolution | Formula |
|------|--------|-------|------------|---------|
| 0 | a17.voltage | 0-5.0 V | 0.0196 V/bit | V = raw × 0.0196 |
| 1 | a18.voltage | 0-5.0 V | 0.0196 V/bit | V = raw × 0.0196 |
| 2 | a19.voltage | 0-5.0 V | 0.0196 V/bit | V = raw × 0.0196 |
| 3 | a20.voltage | 0-5.0 V | 0.0196 V/bit | V = raw × 0.0196 |
| 4 | reserved | - | - | - |
| 5 | reserved | - | - | - |
| 6 | reserved | - | - | - |
| 7 | reserved | - | - | - |

---

## Frame 14: Digital Inputs (BaseID + 14, 20 Hz) - Extended

Digital input states and frequency/pulse counters for inputs d1-d8.

| Byte | Signal | Description |
|------|--------|-------------|
| 0 | Digital States | Bitfield for d1-d8 (bit 0 = d1) |
| 1 | d1 counter LSB | Frequency/pulse counter low byte |
| 2 | d1 counter MSB | Frequency/pulse counter high byte |
| 3 | d2 counter LSB | Frequency/pulse counter low byte |
| 4 | d2 counter MSB | Frequency/pulse counter high byte |
| 5 | reserved | - |
| 6 | reserved | - |
| 7 | reserved | - |

### Digital States Bitfield (Byte 0)

| Bit | Mask | Input |
|-----|------|-------|
| 0 | 0x01 | d1 |
| 1 | 0x02 | d2 |
| 2 | 0x04 | d3 |
| 3 | 0x08 | d4 |
| 4 | 0x10 | d5 |
| 5 | 0x20 | d6 |
| 6 | 0x40 | d7 |
| 7 | 0x80 | d8 |

---

## Frame 15: H-Bridge Status (BaseID + 15, 20 Hz) - Extended

Status and current for all 4 H-Bridge motor drivers.

| Byte | Signal | Range | Resolution | Description |
|------|--------|-------|------------|-------------|
| 0 | hb1.status | 0-7 | - | H-Bridge 1 status code |
| 1 | hb1.current | 0-63.75 A | 0.25 A/bit | H-Bridge 1 current |
| 2 | hb2.status | 0-7 | - | H-Bridge 2 status code |
| 3 | hb2.current | 0-63.75 A | 0.25 A/bit | H-Bridge 2 current |
| 4 | hb3.status | 0-7 | - | H-Bridge 3 status code |
| 5 | hb3.current | 0-63.75 A | 0.25 A/bit | H-Bridge 3 current |
| 6 | hb4.status | 0-7 | - | H-Bridge 4 status code |
| 7 | hb4.current | 0-63.75 A | 0.25 A/bit | H-Bridge 4 current |

### H-Bridge Status Codes

| Value | Status | Description |
|-------|--------|-------------|
| 0 | IDLE | Motor stopped |
| 1 | FORWARD | Running forward |
| 2 | REVERSE | Running reverse |
| 3 | BRAKE | Active braking |
| 4 | COAST | Coasting (free-wheel) |
| 5 | OVERCURRENT | Overcurrent fault |
| 6 | STALL | Stall detected |
| 7 | THERMAL | Thermal shutdown |

---

## Coverage Summary

| Resource | Standard (0-7) | Extended (8-15) | Total |
|----------|----------------|-----------------|-------|
| Outputs States | o1-o16 | o17-o30 | 30/30 |
| Output Currents | o1-o16 | o17-o30 | 30/30 |
| Output Voltages | o1-o16 | o17-o30 | 30/30 |
| Analog Inputs | a1-a16 | a17-a20 | 20/20 |
| Digital Inputs | - | d1-d8 | 8/8 |
| H-Bridges | - | hb1-hb4 | 4/4 |
| Low-Side | l1-l6 | - | 6/6 |

---

## DBC File Export

The configurator can export a DBC file for the Standard CAN Stream. Example:

```dbc
VERSION ""

NS_ :

BS_:

BU_: PMU30

BO_ 1536 PMU_SystemStatus: 8 PMU30
 SG_ PMU_Status : 0|3@1+ (1,0) [0|7] "" Vector__XXX
 SG_ UserError : 3|1@1+ (1,0) [0|1] "" Vector__XXX
 SG_ TotalCurrent : 8|8@1+ (1,0) [0|255] "A" Vector__XXX
 SG_ BatteryVoltage : 16|8@1+ (0.1088,0) [0|27.75] "V" Vector__XXX
 SG_ BoardTempLeft : 24|8@1+ (1,0) [0|255] "degC" Vector__XXX
 SG_ BoardTempRight : 32|8@1+ (1,0) [0|255] "degC" Vector__XXX
 SG_ MCUTemperature : 40|8@1+ (1,0) [0|255] "degC" Vector__XXX
 SG_ LowSideActive : 48|6@1+ (1,0) [0|63] "" Vector__XXX
 SG_ LowSideError : 56|6@1+ (1,0) [0|63] "" Vector__XXX

BO_ 1537 PMU_OutputStates: 8 PMU30
 SG_ O1_Status : 5|3@1+ (1,0) [0|7] "" Vector__XXX
 SG_ O1_Active : 4|1@1+ (1,0) [0|1] "" Vector__XXX
 SG_ O2_Status : 1|3@1+ (1,0) [0|7] "" Vector__XXX
 SG_ O2_Active : 0|1@1+ (1,0) [0|1] "" Vector__XXX
 ...

BO_ 1538 PMU_AnalogInputs1: 8 PMU30
 SG_ A1_Voltage : 0|8@1+ (0.0196,0) [0|5] "V" Vector__XXX
 SG_ A2_Voltage : 8|8@1+ (0.0196,0) [0|5] "V" Vector__XXX
 ...
```

---

## Configuration JSON Example

```json
{
  "settings": {
    "standard_can_stream": {
      "enabled": true,
      "can_bus": 1,
      "base_id": 1536,
      "is_extended": false,
      "include_extended_frames": true
    }
  }
}
```

---

## Timing Considerations

- **20 Hz frames** are transmitted every 50 ms
- **62.5 Hz frames** are transmitted every 16 ms
- All frames are transmitted in sequence with minimum inter-frame gap

### Bus Load

| Mode | Frames | At 500 kbps | At 1 Mbps |
|------|--------|-------------|-----------|
| Standard only | 8 | ~2% | ~1% |
| With extended | 16 | ~4% | ~2% |

---

## Compatibility

The Standard CAN Stream format (frames 0-7) is compatible with:
- Ecumaster PMU series
- AiM data loggers
- MoTeC systems
- Generic CAN analyzers

Extended frames (8-15) are PMU-30 specific.
