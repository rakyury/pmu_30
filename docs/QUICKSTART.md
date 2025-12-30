# PMU-30 Quick Start Guide

Get up and running with PMU-30 in 5 minutes.

**Version:** 3.0 | **Hardware:** 30 outputs, 20 analog inputs, 20 digital inputs, 4 H-bridges

---

## 1. Hardware Setup

### Power Connection
- Battery positive to **BAT+** terminal
- Ground to **GND** terminal
- Operating voltage: **6-22V DC**

### CAN Bus
- Connect **CAN_H** and **CAN_L** to your ECU/logger
- Add 120Ω termination if at end of bus
- PMU-30 has 4 CAN buses: 2× CAN FD + 2× CAN 2.0

### Outputs
- Wire loads to PROFET outputs (up to **40A each**)
- Use appropriate wire gauge for current
- Total system current: up to **200A**

---

## 2. Software Installation

### Configurator (Windows)

```bash
# Download and run installer
PMU30_Configurator_Setup.exe
```

Or run from source:
```bash
cd configurator
pip install -r requirements.txt
python main.py
```

### Firmware Update

1. Connect USB-C cable
2. Open Configurator
3. Click **Device** → **Update Firmware**
4. Select latest firmware file (.bin)

---

## 3. Connection Options

### USB-C (Recommended)
1. Connect USB-C cable to PMU-30
2. Open Configurator
3. Select COM port from dropdown
4. Click **Connect**

### WiFi
1. Connect to PMU-30 WiFi network: `PMU30_XXXX`
2. Default IP: `192.168.4.1`
3. Select WiFi connection in Configurator
4. Click **Connect**

### Bluetooth (Mobile)
- Connect via Bluetooth Classic or BLE
- Use PMU-30 mobile app for monitoring

---

## 4. Channel ID Ranges

| Range | Type | Description |
|-------|------|-------------|
| **0-49** | Digital Inputs | Physical switch/button inputs |
| **50-99** | Analog Inputs | 0-5V sensor inputs (10-bit) |
| **100-129** | Power Outputs | PROFET high-side outputs |
| **150-157** | H-Bridge Outputs | Motor control outputs |
| **200-999** | Virtual Channels | Logic, Math, Timers, Tables, PID |
| **1000-1023** | System Channels | Battery, temperatures, status |

---

## 5. First Configuration

### Step 1: Create Digital Input

Digital input on pin D0 (channel ID must be in 0-49 range):

```json
{
  "channel_id": 0,
  "channel_type": "digital_input",
  "channel_name": "Headlight Switch",
  "input_pin": 0,
  "subtype": "switch_active_low",
  "debounce_ms": 50
}
```

### Step 2: Create Power Output

Output referencing the input (channel ID must be in 100-129 range):

```json
{
  "channel_id": 100,
  "channel_type": "power_output",
  "channel_name": "Headlights",
  "output_pins": [0],
  "source_channel_id": 0,
  "current_limit": 15000
}
```

> **Note:** `source_channel_id: 0` references the digital input with `channel_id: 0`.

### Step 3: Upload Configuration

1. Click **Upload** in Configurator
2. Configuration is saved to PMU flash
3. Changes take effect immediately

---

## 6. Temperature-Controlled Fan Example

**Scenario:** Turn on cooling fan when temperature > 80°C with hysteresis

```json
{
  "version": "3.0",
  "channels": [
    {
      "channel_id": 50,
      "channel_type": "analog_input",
      "channel_name": "Coolant Temp",
      "input_pin": 0,
      "subtype": "calibrated",
      "calibration_points": [
        {"voltage": 0.5, "value": -400},
        {"voltage": 4.5, "value": 1200}
      ]
    },
    {
      "channel_id": 200,
      "channel_type": "logic",
      "channel_name": "Fan Enable",
      "operation": "hysteresis",
      "source_channel_id": 50,
      "upper_value": 850,
      "lower_value": 750
    },
    {
      "channel_id": 100,
      "channel_type": "power_output",
      "channel_name": "Cooling Fan",
      "output_pins": [0],
      "source_channel_id": 200,
      "current_limit": 25000
    }
  ]
}
```

> **Note:** Values are in tenths of degrees (850 = 85.0°C). The logic channel (ID 200) references the analog input (ID 50), and the output (ID 100) references the logic channel.

---

## 7. CAN Bus Integration

### Receive ECU Data

```json
{
  "channel_id": 300,
  "channel_type": "can_rx",
  "channel_name": "Engine RPM",
  "can_bus": 1,
  "message_id": 256,
  "start_bit": 0,
  "length": 16,
  "byte_order": "little_endian",
  "factor": 1.0,
  "offset": 0,
  "timeout_ms": 500
}
```

### Transmit PMU Status

PMU-30 uses a two-level CAN architecture with separate `can_messages` array:

```json
{
  "version": "3.0",
  "channels": [...],
  "can_messages": [
    {
      "message_id": 1792,
      "can_bus": 1,
      "cycle_time_ms": 100,
      "signals": [
        {"source_channel_id": 1000, "start_bit": 0, "length": 16},
        {"source_channel_id": 1001, "start_bit": 16, "length": 16}
      ]
    }
  ]
}
```

---

## 8. Basic Firmware API

### Read Channel Value

```c
// Get any channel value by ID
int32_t switch_state = PMU_Channel_GetValue(0);      // Digital input
int32_t temp = PMU_Channel_GetValue(50);             // Analog input
int32_t battery = PMU_Channel_GetValue(1000);        // System channel
```

### Control Output

```c
// Turn on/off output
PMU_Channel_SetValue(100, 1);      // ON
PMU_Channel_SetValue(100, 0);      // OFF

// Set PWM duty (0-1000 = 0.0-100.0%)
PMU_Channel_SetValue(100, 500);    // 50% PWM
```

### Update Input (for sync)

```c
// Update input channel value (used by hardware drivers)
PMU_Channel_UpdateValue(0, new_value);
```

---

## 9. Monitoring

### LED Indicators

| LED Color | Meaning |
|-----------|---------|
| Green | Output ON, normal operation |
| Red | Fault condition (overcurrent, thermal, short) |
| Off | Output OFF |
| Blinking | PWM active |

### Web Dashboard

When connected to PMU WiFi, open `http://192.168.4.1` for real-time monitoring:
- Output states and currents
- Input values
- System temperatures
- CAN bus traffic

### Configurator Monitors

- **PMU Monitor** - System overview
- **Output Monitor** - All 30 outputs with current/status
- **Analog Monitor** - All 20 analog inputs
- **Digital Monitor** - All 20 digital inputs
- **H-Bridge Monitor** - 4 motor outputs

---

## 10. Output Status Codes

| Code | Name | Description |
|------|------|-------------|
| 0 | OFF | Output disabled |
| 1 | ON | Output active (fully on) |
| 2 | OC | Overcurrent protection |
| 3 | OT | Over-temperature protection |
| 4 | SC | Short circuit detected |
| 5 | OL | Open load (no current) |
| 6 | PWM | PWM mode active |
| 7 | DISABLED | Programmatically disabled |

---

## 11. Troubleshooting

| Issue | Solution |
|-------|----------|
| No connection | Check USB cable, try different port, verify drivers |
| Output not working | Check `source_channel_id`, verify current limit, look for fault status |
| CAN not receiving | Check termination (120Ω), verify baud rate, check CAN_H/CAN_L wiring |
| Erratic readings | Check sensor wiring, add filtering channel, verify calibration |
| Output in OC state | Reduce load, check for short circuit, increase current limit |
| Output in OT state | Reduce duty cycle, improve cooling, check ambient temperature |

---

## 12. Protocol Commands

| Command | ID | Description |
|---------|----|----|
| PING | 0x01 | Connection test |
| GET_CONFIG | 0x10 | Download configuration |
| SET_CONFIG | 0x11 | Upload configuration |
| SAVE_CONFIG | 0x12 | Save to flash |
| GET_CHANNEL | 0x20 | Get channel value |
| SET_CHANNEL | 0x21 | Set channel value |
| SET_CHANNEL_CONFIG | 0x66 | Update single channel (atomic) |

---

## Next Steps

- [Getting Started with Channels](guides/getting-started-channels.md)
- [Logic Functions Integration](guides/logic-functions-integration.md)
- [Full Configuration Reference](operations/configuration-reference.md)
- [Protocol Specification](protocol_specification.md)
- [Channel API Reference](api/channel-api.md)

---

**Need help?** See [Troubleshooting Guide](operations/troubleshooting-guide.md) or contact support.
