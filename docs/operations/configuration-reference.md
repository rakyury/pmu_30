# Configuration Reference

**Version:** 1.0
**Date:** December 2024

---

## 1. Configuration Overview

PMU-30 configuration is stored in JSON format and manages all aspects of device operation.

### Configuration Structure

```json
{
  "version": "1.0.0",
  "device": { ... },
  "channels": { ... },
  "logic_functions": { ... },
  "can_bus": { ... },
  "protection": { ... },
  "logging": { ... }
}
```

---

## 2. Device Configuration

```json
{
  "device": {
    "name": "PMU-30-001",
    "serial": "R2M-2024-00001",
    "firmware_version": "1.0.0",
    "hardware_revision": "A",
    "boot_delay_ms": 500,
    "watchdog_timeout_ms": 1000
  }
}
```

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| name | string | 32 chars | Device identifier |
| serial | string | 20 chars | Serial number |
| boot_delay_ms | uint16 | 0-5000 | Startup delay |
| watchdog_timeout_ms | uint16 | 100-5000 | Watchdog period |

---

## 3. Channel Configuration

### 3.1 Input Channels (0-19)

```json
{
  "channels": {
    "inputs": [
      {
        "id": 0,
        "name": "Coolant Temp",
        "type": "ntc_10k",
        "enabled": true,
        "pull_up": true,
        "filter_samples": 8,
        "scale": 1.0,
        "offset": 0,
        "unit": "C",
        "min_value": -40,
        "max_value": 150,
        "default_value": 25
      }
    ]
  }
}
```

#### Input Types

| Type | Description | Parameters |
|------|-------------|------------|
| voltage | 0-5V analog | scale, offset |
| ntc_10k | NTC 10K thermistor | B-value |
| ntc_2k2 | NTC 2.2K thermistor | B-value |
| resistance | Resistance measurement | range |
| frequency | Frequency input | min_freq, max_freq |
| digital | Digital input | pull_up, invert |

### 3.2 Output Channels (100-129)

```json
{
  "channels": {
    "outputs": [
      {
        "id": 100,
        "name": "Fuel Pump",
        "enabled": true,
        "type": "profet",
        "pwm_frequency": 200,
        "soft_start_ms": 100,
        "current_limit_a": 15.0,
        "retry_count": 3,
        "retry_delay_ms": 1000,
        "invert": false,
        "default_state": 0
      }
    ]
  }
}
```

#### Output Parameters

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| pwm_frequency | uint16 | 50-20000 | PWM frequency Hz |
| soft_start_ms | uint16 | 0-5000 | Soft start duration |
| current_limit_a | float | 0.1-40.0 | Current limit |
| retry_count | uint8 | 0-10 | Fault retry count |
| retry_delay_ms | uint16 | 100-10000 | Retry delay |

### 3.3 H-Bridge Channels (130-133)

```json
{
  "channels": {
    "hbridges": [
      {
        "id": 130,
        "name": "Wiper Motor",
        "enabled": true,
        "pwm_frequency": 1000,
        "current_limit_a": 20.0,
        "dead_time_ns": 500,
        "brake_mode": "low_side",
        "park_enabled": true,
        "park_input": 26,
        "park_position": 0
      }
    ]
  }
}
```

---

## 4. Logic Functions Configuration

```json
{
  "logic_functions": [
    {
      "id": 0,
      "name": "Fan Control",
      "enabled": true,
      "type": "greater",
      "inputs": [0, 200],
      "output": 100,
      "parameters": {
        "threshold": 850
      },
      "priority": 5
    }
  ]
}
```

### Function Types Reference

| Type ID | Name | Inputs | Parameters |
|---------|------|--------|------------|
| 0x00 | add | 2 | - |
| 0x01 | subtract | 2 | - |
| 0x02 | multiply | 2 | scale_factor |
| 0x03 | divide | 2 | - |
| 0x20 | greater | 2 | - |
| 0x21 | less | 2 | - |
| 0x22 | equal | 2 | tolerance |
| 0x40 | and | 2-8 | - |
| 0x41 | or | 2-8 | - |
| 0x80 | moving_avg | 1 | window_size |
| 0xA0 | pid | 1 | kp, ki, kd |

---

## 5. CAN Bus Configuration

### 5.1 Bus Settings

```json
{
  "can_bus": {
    "buses": [
      {
        "id": 0,
        "name": "CAN1",
        "enabled": true,
        "type": "can_fd",
        "bitrate": 500000,
        "data_bitrate": 2000000,
        "termination": true,
        "silent_mode": false
      }
    ]
  }
}
```

### 5.2 RX Messages

```json
{
  "can_bus": {
    "rx_messages": [
      {
        "id": "0x360",
        "bus": 0,
        "name": "ECU_Status",
        "timeout_ms": 100,
        "signals": [
          {
            "name": "RPM",
            "start_bit": 0,
            "length": 16,
            "byte_order": "little_endian",
            "value_type": "unsigned",
            "factor": 1.0,
            "offset": 0,
            "channel": 200
          }
        ]
      }
    ]
  }
}
```

### 5.3 TX Messages

```json
{
  "can_bus": {
    "tx_messages": [
      {
        "id": "0x600",
        "bus": 0,
        "name": "PMU_Status",
        "interval_ms": 100,
        "signals": [
          {
            "name": "Output1_State",
            "start_bit": 0,
            "length": 8,
            "channel": 100
          }
        ]
      }
    ]
  }
}
```

---

## 6. Protection Configuration

```json
{
  "protection": {
    "battery": {
      "undervoltage_v": 9.0,
      "overvoltage_v": 18.0,
      "undervoltage_action": "warning",
      "overvoltage_action": "shutdown"
    },
    "temperature": {
      "warning_c": 85,
      "shutdown_c": 105,
      "derate_start_c": 80,
      "derate_end_c": 100
    },
    "total_current": {
      "limit_a": 200,
      "action": "derate"
    },
    "crash_detection": {
      "enabled": true,
      "threshold_g": 5.0,
      "duration_ms": 50,
      "action": "safe_shutdown"
    }
  }
}
```

---

## 7. Logging Configuration

```json
{
  "logging": {
    "enabled": true,
    "rate_hz": 100,
    "channels": [0, 1, 2, 100, 101, 200, 201],
    "trigger": {
      "type": "always",
      "pre_trigger_s": 5,
      "post_trigger_s": 30
    },
    "storage": {
      "max_file_size_mb": 100,
      "max_files": 50,
      "auto_delete_oldest": true
    }
  }
}
```

---

## 8. Configuration File Operations

### Load Configuration

```c
HAL_StatusTypeDef PMU_Config_Load(const char* filename);
HAL_StatusTypeDef PMU_Config_LoadFromFlash(void);
```

### Save Configuration

```c
HAL_StatusTypeDef PMU_Config_Save(const char* filename);
HAL_StatusTypeDef PMU_Config_SaveToFlash(void);
```

### Validate Configuration

```c
PMU_ConfigError_t PMU_Config_Validate(const PMU_Config_t* config);
```

---

## 9. Default Values

| Category | Parameter | Default |
|----------|-----------|---------|
| Device | boot_delay_ms | 500 |
| Device | watchdog_timeout_ms | 1000 |
| Input | filter_samples | 4 |
| Output | pwm_frequency | 200 |
| Output | soft_start_ms | 50 |
| Output | retry_count | 3 |
| CAN | timeout_ms | 100 |
| Protection | undervoltage_v | 9.0 |
| Protection | overvoltage_v | 18.0 |
| Logging | rate_hz | 100 |

---

## See Also

- [Monitoring & Diagnostics](monitoring-diagnostics.md)
- [Troubleshooting Guide](troubleshooting-guide.md)
- [Channel Types](../api/channel-types.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024
