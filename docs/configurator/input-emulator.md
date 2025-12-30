# Input Emulator

The Input Emulator allows testing by injecting simulated inputs when connected to the software emulator (not available with real hardware).

## Overview

This widget provides controls to simulate digital inputs, analog voltages, and CAN messages for testing configurations without physical hardware.

## Availability

| Connection | Status |
|------------|--------|
| Real Device | Disabled (grayed out) |
| Emulator | Fully functional |
| Offline | Disabled |

## Tab Layout

```
+----------------------------------------------------------+
| [Digital Inputs] [Analog Inputs] [CAN Messages]          |
+----------------------------------------------------------+
|                                                          |
|  Tab-specific content                                    |
|                                                          |
+----------------------------------------------------------+
```

## Digital Inputs Tab

Simulate the physical voltage level of digital input pins.

### Table Layout

| Pin | Level | Toggle |
|-----|-------|--------|
| D1 | HIGH | [Toggle] |
| D2 | LOW | [Toggle] |
| D3 | HIGH | [Toggle] |
| ... | ... | ... |
| D20 | LOW | [Toggle] |

### Column Definitions

| Column | Description |
|--------|-------------|
| **Pin** | Digital input identifier (D1-D20) |
| **Level** | Physical voltage level (HIGH/LOW) |
| **Toggle** | Button to switch level |

### Important Note

The Level column shows **physical voltage**, not logical state:
- **HIGH** = 3.3V at the pin
- **LOW** = 0V at the pin

The configured input type (active high/low) determines the logical interpretation.

### Bulk Controls

| Button | Action |
|--------|--------|
| **All HIGH** | Set all pins to HIGH |
| **All LOW** | Set all pins to LOW |

### Default State

All digital inputs initialize to **HIGH** in emulator mode (simulating pull-up resistors).

### Example

```
Configuration: D1 = "Ignition", type = switch_active_high
Emulator: D1 = HIGH
Result: Ignition shows "ON" in Digital Monitor

Configuration: D2 = "Door Open", type = switch_active_low
Emulator: D2 = HIGH
Result: Door Open shows "OFF" in Digital Monitor
```

## Analog Inputs Tab

Set precise voltage levels for analog input simulation.

### Table Layout

| Pin | Current | Voltage | Set |
|-----|---------|---------|-----|
| A1 | 2.48V | [2.50] | [Set] |
| A2 | 1.65V | [1.65] | [Set] |
| A3 | 0.00V | [3.30] | [Set] |
| ... | ... | ... | ... |

### Column Definitions

| Column | Description |
|--------|-------------|
| **Pin** | Analog input identifier (A1-A20) |
| **Current** | Currently simulated voltage |
| **Voltage** | Spinbox to enter new voltage |
| **Set** | Button to apply voltage |

### Voltage Range

| Parameter | Value |
|-----------|-------|
| Minimum | 0.00V |
| Maximum | 5.00V |
| Step | 0.10V |
| Decimals | 2 |

### Behavior

1. Enter voltage in spinbox
2. Click **Set** to apply
3. Value sent to emulator immediately
4. Analog Monitor reflects new value

### Signal Emitted

```python
analog_input_changed(pin: int, voltage: float)
# Example: analog_input_changed(1, 2.50)
```

### Common Test Scenarios

| Scenario | Pin | Voltage |
|----------|-----|---------|
| Fuel tank empty | A1 | 0.5V |
| Fuel tank full | A1 | 4.5V |
| TPS closed | A2 | 0.5V |
| TPS WOT | A2 | 4.5V |
| MAP idle | A3 | 1.0V |
| MAP boost | A3 | 4.0V |

## CAN Messages Tab

Inject CAN messages to simulate external ECU communication.

### Layout

```
+----------------------------------------------------------+
| Bus: [CAN1 ▼]                                            |
|                                                          |
| Message ID: [0x___] (hex)                                |
|                                                          |
| DLC: [8 ▼]                                               |
|                                                          |
| Data Bytes:                                              |
| [00] [00] [00] [00] [00] [00] [00] [00]                  |
|                                                          |
| Frame Type: [● Standard] [○ Extended]                    |
|                                                          |
| [Inject Message]                                         |
+----------------------------------------------------------+
```

### Fields

| Field | Description |
|-------|-------------|
| **Bus** | CAN bus selector (CAN1-CAN4) |
| **Message ID** | Arbitration ID in hexadecimal |
| **DLC** | Data Length Code (0-8) |
| **Data Bytes** | 8 hex byte fields |
| **Frame Type** | Standard (11-bit) or Extended (29-bit) |

### Inject Button

Sends the configured CAN message to the emulator as if received from an external device.

### Signal Emitted

```python
can_message_injected(bus_id: int, can_id: int, data: bytes)
# Example: can_message_injected(1, 0x100, bytes([0x00, 0x0D, 0xAC...]))
```

### Example: Engine RPM Simulation

```
Configuration:
  CAN Input: "Engine_RPM"
  CAN ID: 0x100
  Start Bit: 0
  Length: 16 bits
  Scale: 0.25
  Offset: 0

Inject:
  Bus: CAN1
  ID: 0x100
  DLC: 8
  Data: [20] [4E] [00] [00] [00] [00] [00] [00]

  Calculation: 0x4E20 = 20000
  RPM = 20000 × 0.25 = 5000 RPM
```

### Preset Messages

Common test messages (future feature):
- Engine off (RPM = 0)
- Engine idle (RPM = 800)
- Engine cruise (RPM = 2500)
- Engine redline (RPM = 7000)

## Update Behavior

Changes take effect immediately:
- Digital state changes → instant
- Analog voltage changes → instant
- CAN message injection → instant

The emulator processes injected values in its next update cycle (typically 1ms).

## Use Cases

### Testing Logic Functions

1. Configure logic with digital input trigger
2. Toggle input in emulator
3. Verify output activates correctly

### Analog Scaling Verification

1. Configure analog input with scaling
2. Set known voltage values
3. Check processed values in Variables Inspector

### CAN Signal Decoding

1. Configure CAN input with signal extraction
2. Inject message with known data
3. Verify decoded value matches expectation

### Full System Simulation

1. Configure complete vehicle setup
2. Simulate driving scenario with inputs
3. Verify all outputs respond correctly

## Styling

```css
Tab {
  background: #1a1a1a;
}

Table {
  background: #000000;
  gridline-color: #333333;
}

SpinBox {
  background: #2d2d2d;
  border: 1px solid #404040;
  color: white;
}

Button {
  background: #404040;
  border: 1px solid #505050;
  color: white;
  padding: 4px 12px;
}

Button:hover {
  background: #505050;
}

Button.inject {
  background: #0078D4;
}
```

## Limitations

| Limitation | Description |
|------------|-------------|
| Emulator only | Cannot inject to real hardware |
| No persistence | Values reset on emulator restart |
| Single-shot CAN | No periodic CAN injection (yet) |
| No frequency inputs | Digital inputs are level-only |
