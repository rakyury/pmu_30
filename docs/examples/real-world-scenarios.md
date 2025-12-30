# Real-World Scenarios

**Version:** 2.0
**Date:** December 2025

Practical examples of PMU-30 configurations for common motorsport applications using JSON configuration v3.0 format.

---

## Channel ID Reference

| Range | Type | Description |
|-------|------|-------------|
| 0-49 | Digital Inputs | d1-d20 physical digital inputs |
| 50-99 | Analog Inputs | a1-a20 physical analog inputs |
| 100-199 | Physical Outputs | o1-o30 power outputs, hb1-hb4 H-bridges |
| 200-999 | Virtual Channels | Logic, numbers, tables, CAN RX/TX, timers |
| 1000-1023 | System Channels | Battery voltage, temperatures, status |

---

## 1. Race Car Cooling System

### Requirements
- Radiator fan based on coolant temperature
- Electric water pump control
- Oil cooler fan for track use
- Dashboard warning light

### Configuration (v3.0)

```json
{
  "version": "3.0",
  "device": {
    "name": "CoolingSystem"
  },
  "can_messages": [],
  "channels": [
    {
      "type": "analog_input",
      "channel_id": 50,
      "channel_name": "CoolantTemp",
      "pin": 1,
      "sensor_type": "ntc_10k"
    },
    {
      "type": "analog_input",
      "channel_id": 51,
      "channel_name": "OilTemp",
      "pin": 2,
      "sensor_type": "ntc_10k"
    },
    {
      "type": "digital_input",
      "channel_id": 0,
      "channel_name": "TrackMode",
      "pin": 1,
      "debounce_ms": 50
    },
    {
      "type": "logic",
      "channel_id": 200,
      "channel_name": "FanControl",
      "operator": "hysteresis",
      "input_a_channel_id": 50,
      "threshold_on": 900,
      "threshold_off": 850
    },
    {
      "type": "table_2d",
      "channel_id": 201,
      "channel_name": "WaterPumpDuty",
      "input_channel_id": 50,
      "x_axis": [600, 700, 800, 900, 1000],
      "values": [300, 500, 700, 900, 1000]
    },
    {
      "type": "logic",
      "channel_id": 210,
      "channel_name": "OilTempHigh",
      "operator": "greater_than",
      "input_a_channel_id": 51,
      "threshold": 1100
    },
    {
      "type": "logic",
      "channel_id": 211,
      "channel_name": "OilFanEnable",
      "operator": "and",
      "input_a_channel_id": 210,
      "input_b_channel_id": 0
    },
    {
      "type": "logic",
      "channel_id": 212,
      "channel_name": "CoolantHigh",
      "operator": "greater_than",
      "input_a_channel_id": 50,
      "threshold": 1050
    },
    {
      "type": "logic",
      "channel_id": 213,
      "channel_name": "OilHigh",
      "operator": "greater_than",
      "input_a_channel_id": 51,
      "threshold": 1300
    },
    {
      "type": "logic",
      "channel_id": 214,
      "channel_name": "TempWarning",
      "operator": "or",
      "input_a_channel_id": 212,
      "input_b_channel_id": 213
    },
    {
      "type": "power_output",
      "channel_id": 100,
      "channel_name": "RadiatorFan",
      "pins": [1],
      "source_channel_id": 200,
      "current_limit_a": 25
    },
    {
      "type": "power_output",
      "channel_id": 101,
      "channel_name": "WaterPump",
      "pins": [2],
      "source_channel_id": 201,
      "pwm_enabled": true,
      "pwm_frequency": 1000,
      "current_limit_a": 10
    },
    {
      "type": "power_output",
      "channel_id": 102,
      "channel_name": "OilFan",
      "pins": [3],
      "source_channel_id": 211,
      "current_limit_a": 15
    },
    {
      "type": "power_output",
      "channel_id": 103,
      "channel_name": "TempWarningLight",
      "pins": [4],
      "source_channel_id": 214,
      "current_limit_a": 1
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

### Configuration (v3.0)

```json
{
  "version": "3.0",
  "device": {
    "name": "FuelSystem"
  },
  "can_messages": [
    {
      "message_id": 864,
      "name": "ECU_Engine",
      "can_bus": 1,
      "signals": [
        {"name": "RPM", "start_bit": 0, "length": 16, "scale": 1, "offset": 0}
      ]
    }
  ],
  "channels": [
    {
      "type": "analog_input",
      "channel_id": 52,
      "channel_name": "FuelPressure",
      "pin": 3,
      "sensor_type": "voltage",
      "scaling": {"factor": 244, "offset": -122}
    },
    {
      "type": "digital_input",
      "channel_id": 1,
      "channel_name": "Ignition",
      "pin": 2,
      "debounce_ms": 50
    },
    {
      "type": "can_rx",
      "channel_id": 300,
      "channel_name": "EngineRPM",
      "message_id": 864,
      "signal_name": "RPM"
    },
    {
      "type": "logic",
      "channel_id": 220,
      "channel_name": "EngineRunning",
      "operator": "greater_than",
      "input_a_channel_id": 300,
      "threshold": 300
    },
    {
      "type": "timer",
      "channel_id": 221,
      "channel_name": "PrimePulse",
      "timer_mode": "pulse",
      "trigger_channel_id": 1,
      "duration_ms": 3000
    },
    {
      "type": "logic",
      "channel_id": 222,
      "channel_name": "FuelPumpLogic",
      "operator": "or",
      "input_a_channel_id": 220,
      "input_b_channel_id": 221
    },
    {
      "type": "logic",
      "channel_id": 230,
      "channel_name": "LowPressure",
      "operator": "less_than",
      "input_a_channel_id": 52,
      "threshold": 300
    },
    {
      "type": "logic",
      "channel_id": 231,
      "channel_name": "PressWarning",
      "operator": "and",
      "input_a_channel_id": 230,
      "input_b_channel_id": 220
    },
    {
      "type": "power_output",
      "channel_id": 104,
      "channel_name": "FuelPump",
      "pins": [5],
      "source_channel_id": 222,
      "current_limit_a": 15
    },
    {
      "type": "power_output",
      "channel_id": 105,
      "channel_name": "LowFuelPressLight",
      "pins": [6],
      "source_channel_id": 231,
      "current_limit_a": 1
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
- Reverse lights

### Configuration (v3.0)

```json
{
  "version": "3.0",
  "device": {
    "name": "LightingSystem"
  },
  "can_messages": [],
  "channels": [
    {
      "type": "switch",
      "channel_id": 240,
      "channel_name": "LightSwitch",
      "input_channel_ids": [2, 3],
      "output_values": [0, 1, 2, 3]
    },
    {
      "type": "digital_input",
      "channel_id": 3,
      "channel_name": "HighBeamBtn",
      "pin": 4,
      "debounce_ms": 50
    },
    {
      "type": "digital_input",
      "channel_id": 4,
      "channel_name": "LeftSignalBtn",
      "pin": 5,
      "debounce_ms": 50
    },
    {
      "type": "digital_input",
      "channel_id": 5,
      "channel_name": "RightSignalBtn",
      "pin": 6,
      "debounce_ms": 50
    },
    {
      "type": "digital_input",
      "channel_id": 6,
      "channel_name": "HazardBtn",
      "pin": 7,
      "debounce_ms": 50
    },
    {
      "type": "digital_input",
      "channel_id": 7,
      "channel_name": "BrakePedal",
      "pin": 8,
      "debounce_ms": 10
    },
    {
      "type": "digital_input",
      "channel_id": 8,
      "channel_name": "ReverseGear",
      "pin": 9,
      "debounce_ms": 50
    },
    {
      "type": "logic",
      "channel_id": 241,
      "channel_name": "LightsOn",
      "operator": "greater_than",
      "input_a_channel_id": 240,
      "threshold": 0
    },
    {
      "type": "logic",
      "channel_id": 242,
      "channel_name": "HighBeamEnable",
      "operator": "and",
      "input_a_channel_id": 241,
      "input_b_channel_id": 3
    },
    {
      "type": "logic",
      "channel_id": 243,
      "channel_name": "LeftFlash",
      "operator": "or",
      "input_a_channel_id": 4,
      "input_b_channel_id": 6
    },
    {
      "type": "logic",
      "channel_id": 244,
      "channel_name": "RightFlash",
      "operator": "or",
      "input_a_channel_id": 5,
      "input_b_channel_id": 6
    },
    {
      "type": "timer",
      "channel_id": 245,
      "channel_name": "LeftSignalFlasher",
      "timer_mode": "flasher",
      "trigger_channel_id": 243,
      "on_time_ms": 500,
      "off_time_ms": 500
    },
    {
      "type": "timer",
      "channel_id": 246,
      "channel_name": "RightSignalFlasher",
      "timer_mode": "flasher",
      "trigger_channel_id": 244,
      "on_time_ms": 500,
      "off_time_ms": 500
    },
    {
      "type": "power_output",
      "channel_id": 106,
      "channel_name": "LowBeamL",
      "pins": [7],
      "source_channel_id": 241,
      "current_limit_a": 8
    },
    {
      "type": "power_output",
      "channel_id": 107,
      "channel_name": "LowBeamR",
      "pins": [8],
      "source_channel_id": 241,
      "current_limit_a": 8
    },
    {
      "type": "power_output",
      "channel_id": 108,
      "channel_name": "HighBeamL",
      "pins": [9],
      "source_channel_id": 242,
      "current_limit_a": 8
    },
    {
      "type": "power_output",
      "channel_id": 109,
      "channel_name": "HighBeamR",
      "pins": [10],
      "source_channel_id": 242,
      "current_limit_a": 8
    },
    {
      "type": "power_output",
      "channel_id": 110,
      "channel_name": "SignalL",
      "pins": [11],
      "source_channel_id": 245,
      "current_limit_a": 5
    },
    {
      "type": "power_output",
      "channel_id": 111,
      "channel_name": "SignalR",
      "pins": [12],
      "source_channel_id": 246,
      "current_limit_a": 5
    },
    {
      "type": "power_output",
      "channel_id": 112,
      "channel_name": "BrakeL",
      "pins": [13],
      "source_channel_id": 7,
      "current_limit_a": 5
    },
    {
      "type": "power_output",
      "channel_id": 113,
      "channel_name": "BrakeR",
      "pins": [14],
      "source_channel_id": 7,
      "current_limit_a": 5
    },
    {
      "type": "power_output",
      "channel_id": 114,
      "channel_name": "Reverse",
      "pins": [15],
      "source_channel_id": 8,
      "current_limit_a": 5
    }
  ]
}
```

---

## 4. Wiper Control with Speed-Sensitive Intermittent

### Requirements
- Off/Intermittent/Low/High modes
- Park position detection
- Washer with auto-wipe
- Speed-sensitive intermittent

### Configuration (v3.0)

```json
{
  "version": "3.0",
  "device": {
    "name": "WiperSystem"
  },
  "can_messages": [
    {
      "message_id": 865,
      "name": "ECU_Vehicle",
      "can_bus": 1,
      "signals": [
        {"name": "VehicleSpeed", "start_bit": 0, "length": 16, "scale": 0.1, "offset": 0}
      ]
    }
  ],
  "channels": [
    {
      "type": "switch",
      "channel_id": 250,
      "channel_name": "WiperSwitch",
      "input_channel_ids": [9, 10],
      "output_values": [0, 1, 2, 3]
    },
    {
      "type": "digital_input",
      "channel_id": 11,
      "channel_name": "ParkSwitch",
      "pin": 12,
      "debounce_ms": 50
    },
    {
      "type": "digital_input",
      "channel_id": 12,
      "channel_name": "WasherButton",
      "pin": 13,
      "debounce_ms": 50
    },
    {
      "type": "can_rx",
      "channel_id": 301,
      "channel_name": "VehicleSpeed",
      "message_id": 865,
      "signal_name": "VehicleSpeed"
    },
    {
      "type": "table_2d",
      "channel_id": 251,
      "channel_name": "IntermittentDelay",
      "input_channel_id": 301,
      "x_axis": [0, 300, 600, 1000, 1500],
      "values": [6000, 5000, 4000, 3000, 2000]
    },
    {
      "type": "handler",
      "channel_id": 252,
      "channel_name": "WiperHandler",
      "handler_type": "wiper",
      "switch_channel_id": 250,
      "park_channel_id": 11,
      "washer_channel_id": 12,
      "intermittent_delay_channel_id": 251,
      "wash_wipes": 3,
      "wash_delay_ms": 500
    },
    {
      "type": "hbridge",
      "channel_id": 130,
      "channel_name": "WiperMotor",
      "pins": [1, 2],
      "source_channel_id": 252,
      "current_limit_a": 15
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

### Configuration (v3.0)

```json
{
  "version": "3.0",
  "device": {
    "name": "NitrousSystem"
  },
  "can_messages": [
    {
      "message_id": 864,
      "name": "ECU_Engine",
      "can_bus": 1,
      "signals": [
        {"name": "RPM", "start_bit": 0, "length": 16, "scale": 1, "offset": 0},
        {"name": "TPS", "start_bit": 16, "length": 16, "scale": 0.1, "offset": 0}
      ]
    }
  ],
  "channels": [
    {
      "type": "analog_input",
      "channel_id": 54,
      "channel_name": "FuelPressure",
      "pin": 5,
      "sensor_type": "voltage"
    },
    {
      "type": "digital_input",
      "channel_id": 13,
      "channel_name": "ArmSwitch",
      "pin": 14,
      "debounce_ms": 50
    },
    {
      "type": "digital_input",
      "channel_id": 14,
      "channel_name": "ActivateButton",
      "pin": 15,
      "debounce_ms": 10
    },
    {
      "type": "can_rx",
      "channel_id": 300,
      "channel_name": "EngineRPM",
      "message_id": 864,
      "signal_name": "RPM"
    },
    {
      "type": "can_rx",
      "channel_id": 302,
      "channel_name": "TPS",
      "message_id": 864,
      "signal_name": "TPS"
    },
    {
      "type": "logic",
      "channel_id": 260,
      "channel_name": "RPMInWindow",
      "operator": "in_range",
      "input_a_channel_id": 300,
      "min_value": 4000,
      "max_value": 7500
    },
    {
      "type": "logic",
      "channel_id": 261,
      "channel_name": "TPSHigh",
      "operator": "greater_than",
      "input_a_channel_id": 302,
      "threshold": 900
    },
    {
      "type": "logic",
      "channel_id": 262,
      "channel_name": "FuelOK",
      "operator": "greater_than",
      "input_a_channel_id": 54,
      "threshold": 400
    },
    {
      "type": "logic",
      "channel_id": 263,
      "channel_name": "AllConditions",
      "operator": "and",
      "input_a_channel_id": 260,
      "input_b_channel_id": 261,
      "input_c_channel_id": 262,
      "input_d_channel_id": 13
    },
    {
      "type": "logic",
      "channel_id": 264,
      "channel_name": "NitrousEnabled",
      "operator": "and",
      "input_a_channel_id": 263,
      "input_b_channel_id": 14
    },
    {
      "type": "timer",
      "channel_id": 265,
      "channel_name": "ProgressiveRamp",
      "timer_mode": "ramp",
      "trigger_channel_id": 264,
      "start_value": 200,
      "end_value": 1000,
      "ramp_time_ms": 2000
    },
    {
      "type": "logic",
      "channel_id": 266,
      "channel_name": "NitrousOutput",
      "operator": "conditional",
      "condition_channel_id": 264,
      "true_channel_id": 265,
      "false_channel_id": 1012
    },
    {
      "type": "power_output",
      "channel_id": 115,
      "channel_name": "N2OSolenoid",
      "pins": [16],
      "source_channel_id": 266,
      "pwm_enabled": true,
      "pwm_frequency": 20,
      "current_limit_a": 5
    },
    {
      "type": "power_output",
      "channel_id": 116,
      "channel_name": "FuelSolenoid",
      "pins": [17],
      "source_channel_id": 266,
      "pwm_enabled": true,
      "pwm_frequency": 20,
      "current_limit_a": 5
    },
    {
      "type": "power_output",
      "channel_id": 117,
      "channel_name": "ArmLED",
      "pins": [18],
      "source_channel_id": 13,
      "current_limit_a": 0.5
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

### Configuration (v3.0)

```json
{
  "version": "3.0",
  "device": {
    "name": "StarterSystem"
  },
  "can_messages": [
    {
      "message_id": 864,
      "name": "ECU_Engine",
      "can_bus": 1,
      "signals": [
        {"name": "RPM", "start_bit": 0, "length": 16, "scale": 1, "offset": 0}
      ]
    }
  ],
  "channels": [
    {
      "type": "digital_input",
      "channel_id": 15,
      "channel_name": "StartButton",
      "pin": 16,
      "debounce_ms": 50
    },
    {
      "type": "digital_input",
      "channel_id": 16,
      "channel_name": "NeutralSwitch",
      "pin": 17,
      "debounce_ms": 50
    },
    {
      "type": "can_rx",
      "channel_id": 300,
      "channel_name": "EngineRPM",
      "message_id": 864,
      "signal_name": "RPM"
    },
    {
      "type": "logic",
      "channel_id": 270,
      "channel_name": "EngineRunning",
      "operator": "greater_than",
      "input_a_channel_id": 300,
      "threshold": 400
    },
    {
      "type": "logic",
      "channel_id": 271,
      "channel_name": "NotRunning",
      "operator": "not",
      "input_a_channel_id": 270
    },
    {
      "type": "logic",
      "channel_id": 272,
      "channel_name": "StartRequest",
      "operator": "and",
      "input_a_channel_id": 15,
      "input_b_channel_id": 16,
      "input_c_channel_id": 271
    },
    {
      "type": "timer",
      "channel_id": 273,
      "channel_name": "CrankTimer",
      "timer_mode": "timeout",
      "trigger_channel_id": 272,
      "timeout_ms": 5000
    },
    {
      "type": "logic",
      "channel_id": 274,
      "channel_name": "StarterEnable",
      "operator": "and",
      "input_a_channel_id": 272,
      "input_b_channel_id": 273
    },
    {
      "type": "power_output",
      "channel_id": 118,
      "channel_name": "StarterMotor",
      "pins": [19],
      "source_channel_id": 274,
      "current_limit_a": 40,
      "soft_start_ms": 0
    }
  ]
}
```

---

## 7. Pit Lane Speed Limiter

### Requirements
- Activated by button
- Limits speed via output signal
- LED indicator
- Auto-disable above threshold

### Configuration (v3.0)

```json
{
  "version": "3.0",
  "device": {
    "name": "PitLimiter"
  },
  "can_messages": [
    {
      "message_id": 865,
      "name": "ECU_Vehicle",
      "can_bus": 1,
      "signals": [
        {"name": "VehicleSpeed", "start_bit": 0, "length": 16, "scale": 0.1, "offset": 0}
      ]
    }
  ],
  "channels": [
    {
      "type": "digital_input",
      "channel_id": 17,
      "channel_name": "PitButton",
      "pin": 18,
      "debounce_ms": 50
    },
    {
      "type": "can_rx",
      "channel_id": 301,
      "channel_name": "VehicleSpeed",
      "message_id": 865,
      "signal_name": "VehicleSpeed"
    },
    {
      "type": "number",
      "channel_id": 280,
      "channel_name": "PitSpeedLimit",
      "value": 600
    },
    {
      "type": "logic",
      "channel_id": 281,
      "channel_name": "SpeedLow",
      "operator": "less_than",
      "input_a_channel_id": 301,
      "threshold": 100
    },
    {
      "type": "logic",
      "channel_id": 282,
      "channel_name": "CanEnablePit",
      "operator": "and",
      "input_a_channel_id": 17,
      "input_b_channel_id": 281
    },
    {
      "type": "logic",
      "channel_id": 283,
      "channel_name": "SpeedHigh",
      "operator": "greater_than",
      "input_a_channel_id": 301,
      "threshold": 800
    },
    {
      "type": "logic",
      "channel_id": 284,
      "channel_name": "DisablePit",
      "operator": "and",
      "input_a_channel_id": 17,
      "input_b_channel_id": 283
    },
    {
      "type": "logic",
      "channel_id": 285,
      "channel_name": "PitActive",
      "operator": "latch_sr",
      "set_channel_id": 282,
      "reset_channel_id": 284
    },
    {
      "type": "timer",
      "channel_id": 286,
      "channel_name": "PitLEDFlasher",
      "timer_mode": "flasher",
      "trigger_channel_id": 285,
      "on_time_ms": 200,
      "off_time_ms": 200
    },
    {
      "type": "power_output",
      "channel_id": 119,
      "channel_name": "SpeedLimitOutput",
      "pins": [20],
      "source_channel_id": 285,
      "current_limit_a": 2
    },
    {
      "type": "power_output",
      "channel_id": 120,
      "channel_name": "PitLED",
      "pins": [21],
      "source_channel_id": 286,
      "current_limit_a": 0.5
    }
  ]
}
```

---

## 8. Power Window with Auto-Up/Down

### Requirements
- One-touch up/down
- Pinch protection
- Position memory
- Thermal protection

### Configuration (v3.0)

```json
{
  "version": "3.0",
  "device": {
    "name": "PowerWindow"
  },
  "can_messages": [],
  "channels": [
    {
      "type": "digital_input",
      "channel_id": 18,
      "channel_name": "WindowUpBtn",
      "pin": 19,
      "debounce_ms": 50
    },
    {
      "type": "digital_input",
      "channel_id": 19,
      "channel_name": "WindowDownBtn",
      "pin": 20,
      "debounce_ms": 50
    },
    {
      "type": "digital_input",
      "channel_id": 20,
      "channel_name": "WindowUpLimit",
      "pin": 21,
      "debounce_ms": 10
    },
    {
      "type": "digital_input",
      "channel_id": 21,
      "channel_name": "WindowDownLimit",
      "pin": 22,
      "debounce_ms": 10
    },
    {
      "type": "logic",
      "channel_id": 290,
      "channel_name": "UpCommand",
      "operator": "and",
      "input_a_channel_id": 18,
      "input_b_channel_id": 21
    },
    {
      "type": "logic",
      "channel_id": 291,
      "channel_name": "NotAtUpLimit",
      "operator": "not",
      "input_a_channel_id": 20
    },
    {
      "type": "logic",
      "channel_id": 292,
      "channel_name": "UpAllowed",
      "operator": "and",
      "input_a_channel_id": 290,
      "input_b_channel_id": 291
    },
    {
      "type": "logic",
      "channel_id": 293,
      "channel_name": "DownCommand",
      "operator": "and",
      "input_a_channel_id": 19,
      "input_b_channel_id": 20
    },
    {
      "type": "logic",
      "channel_id": 294,
      "channel_name": "NotAtDownLimit",
      "operator": "not",
      "input_a_channel_id": 21
    },
    {
      "type": "logic",
      "channel_id": 295,
      "channel_name": "DownAllowed",
      "operator": "and",
      "input_a_channel_id": 293,
      "input_b_channel_id": 294
    },
    {
      "type": "handler",
      "channel_id": 296,
      "channel_name": "WindowHandler",
      "handler_type": "window",
      "up_channel_id": 292,
      "down_channel_id": 295,
      "up_limit_channel_id": 20,
      "down_limit_channel_id": 21,
      "auto_duration_ms": 10000,
      "thermal_limit_a": 15
    },
    {
      "type": "hbridge",
      "channel_id": 131,
      "channel_name": "WindowMotor",
      "pins": [3, 4],
      "source_channel_id": 296,
      "current_limit_a": 20
    }
  ]
}
```

---

## See Also

- [Channel Examples](channel-examples.md)
- [Logic Function Examples](logic-function-examples.md)
- [JSON Configuration](../../firmware/JSON_CONFIG.md) - Configuration format v3.0

---

**Document Version:** 2.0
**Last Updated:** December 2025
