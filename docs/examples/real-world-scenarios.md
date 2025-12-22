# Real-World Scenarios

**Version:** 1.0
**Date:** December 2024

Practical examples of PMU-30 configurations for common motorsport applications.

---

## 1. Race Car Cooling System

### Requirements
- Radiator fan based on coolant temperature
- Electric water pump control
- Oil cooler fan for track use
- Dashboard warning light

### Configuration

```json
{
  "inputs": [
    {"id": 0, "name": "Coolant Temp", "type": "ntc_10k"},
    {"id": 1, "name": "Oil Temp", "type": "ntc_10k"},
    {"id": 20, "name": "Track Mode", "type": "digital"}
  ],
  "outputs": [
    {"id": 100, "name": "Radiator Fan", "current_limit": 25},
    {"id": 101, "name": "Water Pump", "pwm_frequency": 1000},
    {"id": 102, "name": "Oil Fan", "current_limit": 15},
    {"id": 103, "name": "Temp Warning", "current_limit": 1}
  ],
  "logic_functions": [
    {
      "id": 0, "name": "Fan Control",
      "type": "hysteresis",
      "input": 0,
      "output": 100,
      "parameters": {"threshold_on": 900, "threshold_off": 850}
    },
    {
      "id": 1, "name": "Water Pump",
      "type": "pwm_duty",
      "input": 0,
      "output": 101,
      "parameters": {"input_min": 600, "input_max": 1000, "duty_min": 300, "duty_max": 1000}
    },
    {
      "id": 2, "name": "Oil Fan Enable",
      "type": "and",
      "inputs": [210, 20],
      "output": 102
    },
    {
      "id": 3, "name": "Oil Temp High",
      "type": "greater",
      "inputs": [1, 1100],
      "output": 210
    },
    {
      "id": 4, "name": "Temp Warning",
      "type": "or",
      "inputs": [211, 212],
      "output": 103
    },
    {
      "id": 5, "name": "Coolant High",
      "type": "greater",
      "inputs": [0, 1050],
      "output": 211
    },
    {
      "id": 6, "name": "Oil High",
      "type": "greater",
      "inputs": [1, 1300],
      "output": 212
    }
  ]
}
```

---

## 2. Fuel System Control

### Requirements
- Fuel pump priming on ignition
- Fuel pump runs with engine
- Low fuel pressure warning
- Engine-off fuel pump timeout

### Configuration

```json
{
  "inputs": [
    {"id": 2, "name": "Fuel Pressure", "type": "voltage"},
    {"id": 21, "name": "Ignition", "type": "digital"}
  ],
  "can_rx": [
    {"id": "0x360", "signal": "RPM", "channel": 200}
  ],
  "outputs": [
    {"id": 104, "name": "Fuel Pump", "current_limit": 15},
    {"id": 105, "name": "Low Fuel Press", "current_limit": 1}
  ],
  "logic_functions": [
    {
      "id": 10, "name": "Engine Running",
      "type": "greater",
      "inputs": [200, 300],
      "output": 220
    },
    {
      "id": 11, "name": "Prime Pulse",
      "type": "pulse",
      "input": 21,
      "output": 221,
      "parameters": {"duration_ms": 3000}
    },
    {
      "id": 12, "name": "Fuel Pump Logic",
      "type": "or",
      "inputs": [220, 221],
      "output": 104
    },
    {
      "id": 13, "name": "Press Convert",
      "type": "channel_scale",
      "input": 2,
      "output": 230,
      "parameters": {"factor": 24.4, "offset": -12}
    },
    {
      "id": 14, "name": "Low Pressure",
      "type": "less",
      "inputs": [230, 300],
      "output": 231
    },
    {
      "id": 15, "name": "Press Warning",
      "type": "and",
      "inputs": [231, 220],
      "output": 105
    }
  ]
}
```

---

## 3. Lighting Control

### Requirements
- Headlights with high/low beam
- Turn signals with hazard mode
- Brake lights
- Reverse lights with auto-off

### Configuration

```json
{
  "inputs": [
    {"id": 22, "name": "Light Switch", "type": "rotary"},
    {"id": 23, "name": "High Beam", "type": "digital"},
    {"id": 24, "name": "Left Signal", "type": "digital"},
    {"id": 25, "name": "Right Signal", "type": "digital"},
    {"id": 26, "name": "Hazard", "type": "digital"},
    {"id": 27, "name": "Brake Pedal", "type": "digital"},
    {"id": 28, "name": "Reverse Gear", "type": "digital"}
  ],
  "outputs": [
    {"id": 106, "name": "Low Beam L", "current_limit": 8},
    {"id": 107, "name": "Low Beam R", "current_limit": 8},
    {"id": 108, "name": "High Beam L", "current_limit": 8},
    {"id": 109, "name": "High Beam R", "current_limit": 8},
    {"id": 110, "name": "Signal L", "current_limit": 5},
    {"id": 111, "name": "Signal R", "current_limit": 5},
    {"id": 112, "name": "Brake L", "current_limit": 5},
    {"id": 113, "name": "Brake R", "current_limit": 5},
    {"id": 114, "name": "Reverse", "current_limit": 5}
  ],
  "logic_functions": [
    {
      "id": 20, "name": "Lights On",
      "type": "greater",
      "inputs": [22, 0],
      "output": 240
    },
    {
      "id": 21, "name": "Low Beam",
      "type": "channel_sync",
      "input": 240,
      "outputs": [106, 107]
    },
    {
      "id": 22, "name": "High Beam",
      "type": "and",
      "inputs": [240, 23],
      "output": 241
    },
    {
      "id": 23, "name": "High Beam Out",
      "type": "channel_sync",
      "input": 241,
      "outputs": [108, 109]
    },
    {
      "id": 24, "name": "Left Flash",
      "type": "or",
      "inputs": [24, 26],
      "output": 242
    },
    {
      "id": 25, "name": "Right Flash",
      "type": "or",
      "inputs": [25, 26],
      "output": 243
    },
    {
      "id": 26, "name": "Left Signal",
      "type": "flasher",
      "input": 242,
      "output": 110,
      "parameters": {"on_time_ms": 500, "off_time_ms": 500}
    },
    {
      "id": 27, "name": "Right Signal",
      "type": "flasher",
      "input": 243,
      "output": 111,
      "parameters": {"on_time_ms": 500, "off_time_ms": 500}
    },
    {
      "id": 28, "name": "Brake Lights",
      "type": "channel_sync",
      "input": 27,
      "outputs": [112, 113]
    },
    {
      "id": 29, "name": "Reverse Light",
      "type": "channel_copy",
      "input": 28,
      "output": 114
    }
  ]
}
```

---

## 4. Wiper Control

### Requirements
- Off/Intermittent/Low/High modes
- Park position detection
- Washer with auto-wipe
- Speed-sensitive intermittent

### Configuration

```json
{
  "inputs": [
    {"id": 3, "name": "Wiper Switch", "type": "rotary"},
    {"id": 29, "name": "Park Switch", "type": "digital"},
    {"id": 30, "name": "Washer Button", "type": "digital"}
  ],
  "can_rx": [
    {"id": "0x361", "signal": "Vehicle Speed", "channel": 201}
  ],
  "outputs": [
    {"id": 130, "name": "Wiper Motor", "type": "hbridge", "current_limit": 15}
  ],
  "logic_functions": [
    {
      "id": 30, "name": "Speed Factor",
      "type": "table_1d",
      "input": 201,
      "output": 250,
      "parameters": {
        "x_values": [0, 30, 60, 100, 150],
        "y_values": [6000, 5000, 4000, 3000, 2000]
      }
    },
    {
      "id": 31, "name": "Wiper Mode",
      "type": "wiper",
      "inputs": [3, 29, 30],
      "output": 130,
      "parameters": {
        "intermittent_channel": 250,
        "wash_wipes": 3,
        "wash_delay_ms": 500
      }
    }
  ]
}
```

---

## 5. Nitrous Control (Progressive)

### Requirements
- Armed by switch
- RPM window activation
- TPS threshold
- Progressive ramp
- Fuel pressure safety

### Configuration

```json
{
  "inputs": [
    {"id": 4, "name": "Fuel Pressure", "type": "voltage"},
    {"id": 31, "name": "Arm Switch", "type": "digital"},
    {"id": 32, "name": "Activate Button", "type": "digital"}
  ],
  "can_rx": [
    {"id": "0x360", "signal": "RPM", "channel": 200},
    {"id": "0x361", "signal": "TPS", "channel": 202}
  ],
  "outputs": [
    {"id": 115, "name": "N2O Solenoid", "pwm_frequency": 20, "current_limit": 5},
    {"id": 116, "name": "Fuel Solenoid", "pwm_frequency": 20, "current_limit": 5},
    {"id": 117, "name": "Arm LED", "current_limit": 0.5}
  ],
  "logic_functions": [
    {
      "id": 40, "name": "RPM OK",
      "type": "in_range",
      "input": 200,
      "output": 260,
      "parameters": {"min": 4000, "max": 7500}
    },
    {
      "id": 41, "name": "TPS OK",
      "type": "greater",
      "inputs": [202, 900],
      "output": 261
    },
    {
      "id": 42, "name": "Fuel OK",
      "type": "greater",
      "inputs": [4, 400],
      "output": 262
    },
    {
      "id": 43, "name": "All Conditions",
      "type": "and",
      "inputs": [260, 261, 262, 31, 32],
      "output": 263
    },
    {
      "id": 44, "name": "Progressive Ramp",
      "type": "ramp_generator",
      "input": 263,
      "output": 264,
      "parameters": {
        "start_value": 200,
        "end_value": 1000,
        "duration_ms": 2000
      }
    },
    {
      "id": 45, "name": "N2O Enable",
      "type": "if_then_else",
      "inputs": [263, 264, 0],
      "output": 115
    },
    {
      "id": 46, "name": "Fuel Enable",
      "type": "channel_copy",
      "input": 115,
      "output": 116
    },
    {
      "id": 47, "name": "Arm LED",
      "type": "channel_copy",
      "input": 31,
      "output": 117
    }
  ]
}
```

---

## 6. Starter Control with Anti-Crank

### Requirements
- Start button activation
- Engine running detection
- Neutral safety
- Cranking timeout
- Starter motor protection

### Configuration

```json
{
  "inputs": [
    {"id": 33, "name": "Start Button", "type": "digital"},
    {"id": 34, "name": "Neutral Switch", "type": "digital"}
  ],
  "can_rx": [
    {"id": "0x360", "signal": "RPM", "channel": 200}
  ],
  "outputs": [
    {"id": 118, "name": "Starter Motor", "current_limit": 40, "soft_start_ms": 0}
  ],
  "logic_functions": [
    {
      "id": 50, "name": "Engine Running",
      "type": "greater",
      "inputs": [200, 400],
      "output": 270
    },
    {
      "id": 51, "name": "Not Running",
      "type": "not",
      "input": 270,
      "output": 271
    },
    {
      "id": 52, "name": "Start Request",
      "type": "and",
      "inputs": [33, 34, 271],
      "output": 272
    },
    {
      "id": 53, "name": "Crank Timer",
      "type": "timer",
      "inputs": [272, 270],
      "output": 273
    },
    {
      "id": 54, "name": "Crank Timeout",
      "type": "less",
      "inputs": [273, 5000],
      "output": 274
    },
    {
      "id": 55, "name": "Starter Enable",
      "type": "and",
      "inputs": [272, 274],
      "output": 118
    }
  ]
}
```

---

## 7. Pit Lane Speed Limiter

### Requirements
- Activated by button
- Limits speed via output
- LED indicator
- Auto-disable above threshold

### Configuration

```json
{
  "inputs": [
    {"id": 35, "name": "Pit Button", "type": "digital"}
  ],
  "can_rx": [
    {"id": "0x361", "signal": "Speed", "channel": 201}
  ],
  "outputs": [
    {"id": 119, "name": "Speed Limit", "current_limit": 2},
    {"id": 120, "name": "Pit LED", "current_limit": 0.5}
  ],
  "logic_functions": [
    {
      "id": 60, "name": "Speed Low",
      "type": "less",
      "inputs": [201, 100],
      "output": 280
    },
    {
      "id": 61, "name": "Pit Latch",
      "type": "latch_sr",
      "inputs": [281, 282],
      "output": 283
    },
    {
      "id": 62, "name": "Pit Set",
      "type": "and",
      "inputs": [35, 280],
      "output": 281
    },
    {
      "id": 63, "name": "Speed High",
      "type": "greater",
      "inputs": [201, 80],
      "output": 284
    },
    {
      "id": 64, "name": "Pit Reset",
      "type": "and",
      "inputs": [35, 284],
      "output": 282
    },
    {
      "id": 65, "name": "Pit Output",
      "type": "channel_copy",
      "input": 283,
      "output": 119
    },
    {
      "id": 66, "name": "Pit LED",
      "type": "flasher",
      "input": 283,
      "output": 120,
      "parameters": {"on_time_ms": 200, "off_time_ms": 200}
    }
  ]
}
```

---

## See Also

- [Channel Examples](channel-examples.md)
- [Logic Function Examples](logic-function-examples.md)
- [Configuration Reference](../operations/configuration-reference.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024
