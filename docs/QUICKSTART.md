# PMU-30 Quick Start Guide

Get up and running with PMU-30 in 5 minutes.

---

## 1. Hardware Setup

1. **Connect Power**
   - Battery positive to BAT+ terminal
   - Ground to GND terminal
   - Operating voltage: 6-22V DC

2. **Connect CAN Bus**
   - CAN_H and CAN_L to your ECU/logger
   - Add 120Ω termination if at end of bus

3. **Connect Outputs**
   - Wire loads to PROFET outputs (up to 40A each)
   - Use appropriate wire gauge for current

---

## 2. Software Installation

### Configurator (Windows)

```bash
# Download and run installer
PMU30_Configurator_Setup.exe
```

### Firmware Update

1. Connect USB-C cable
2. Open Configurator
3. Click "Firmware" → "Update"
4. Select latest firmware file

---

## 3. First Configuration

### Connect to PMU

1. Power on PMU-30
2. Open Configurator
3. Select COM port or WiFi connection
4. Click "Connect"

### Create Input First

Digital input on pin D1:

```json
{
  "channel_id": 1,
  "channel_type": "digital_input",
  "channel_name": "Headlight Switch",
  "input_pin": 0,
  "subtype": "switch_active_low",
  "debounce_ms": 50
}
```

### Create Output Referencing the Input

```json
{
  "channel_id": 100,
  "channel_type": "power_output",
  "channel_name": "Headlights",
  "output_pins": [0],
  "source_channel_id": 1
}
```

> **Note:** Use `source_channel_id: 1` to reference the digital input with `channel_id: 1`.

### Upload Configuration

1. Click "Upload" in Configurator
2. Configuration is saved to PMU flash
3. Changes take effect immediately

---

## 4. Basic Channel Operations

### Read Input Value

```c
// In firmware or via protocol
int32_t switch_state = PMU_Channel_GetValue(channel_id);
```

### Control Output

```c
// Turn on output
PMU_Channel_SetValue(100, 1);

// Set PWM duty (0-1000 = 0-100%)
PMU_Channel_SetValue(101, 500);  // 50%
```

---

## 5. Simple Logic Example

**Scenario:** Turn on fan when temperature > 80°C

### Configuration

```json
{
  "channels": [
    {
      "channel_id": 21,
      "channel_type": "analog_input",
      "channel_name": "Temperature Sensor",
      "input_pin": 0,
      "subtype": "calibrated",
      "calibration_points": [
        {"voltage": 0.5, "value": -40},
        {"voltage": 4.5, "value": 120}
      ]
    },
    {
      "channel_id": 200,
      "channel_type": "logic",
      "channel_name": "Fan Enable",
      "operation": "hysteresis",
      "source_channel_id": 21,
      "upper_value": 85,
      "lower_value": 75
    },
    {
      "channel_id": 100,
      "channel_type": "power_output",
      "channel_name": "Cooling Fan",
      "output_pins": [0],
      "source_channel_id": 200
    }
  ]
}
```

> **Note:** The logic channel references the analog input via `source_channel_id: 21`, and the power output references the logic channel via `source_channel_id: 200`.

---

## 6. CAN Bus Integration

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
  "factor": 1.0,
  "timeout_ms": 500
}
```

### Transmit PMU Status

```json
{
  "channel_id": 500,
  "channel_type": "can_tx",
  "channel_name": "PMU Status",
  "can_bus": 1,
  "message_id": 768,
  "cycle_time_ms": 100,
  "signals": [
    {"source_channel_id": 5, "start_bit": 0, "length": 8}
  ]
}
```

---

## 7. Monitoring

### LED Indicators

| LED Color | Meaning |
|-----------|---------|
| Green | Output ON, normal |
| Red | Fault condition |
| Off | Output OFF |

### Dashboard

Open `http://192.168.4.1` when connected to PMU WiFi for real-time monitoring.

---

## 8. Troubleshooting

| Issue | Solution |
|-------|----------|
| No connection | Check USB cable, try different port |
| Output not working | Check current limit, look for fault LED |
| CAN not receiving | Check termination, verify baud rate |
| Erratic readings | Check wiring, add filtering |

---

## Next Steps

- [Getting Started with Channels](guides/getting-started-channels.md)
- [Logic Functions Integration](guides/logic-functions-integration.md)
- [Full Configuration Reference](operations/configuration-reference.md)

---

**Need help?** See [Troubleshooting Guide](operations/troubleshooting-guide.md) or contact support.
