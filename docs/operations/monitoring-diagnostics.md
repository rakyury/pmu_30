# Monitoring & Diagnostics

**Version:** 1.0
**Date:** December 2024

---

## 1. Real-Time Monitoring

### 1.1 System Status Channels

| Channel ID | Name | Unit | Description |
|------------|------|------|-------------|
| 1000 | Battery Voltage | mV | Main supply voltage |
| 1001 | Total Current | mA | Sum of all outputs |
| 1002 | Board Temperature | 0.1°C | PCB temperature |
| 1003 | Uptime | s | Time since boot |
| 1004 | CPU Load | % | Processor utilization |
| 1005 | Memory Free | bytes | Available RAM |

### 1.2 Reading System Status

```c
void monitor_system_status(void) {
    int32_t battery_mv = PMU_Channel_GetValue(1000);
    int32_t current_ma = PMU_Channel_GetValue(1001);
    int32_t temp_c10 = PMU_Channel_GetValue(1002);

    printf("Battery: %ld.%02ld V\n", battery_mv/1000, (battery_mv%1000)/10);
    printf("Current: %ld.%02ld A\n", current_ma/1000, (current_ma%1000)/10);
    printf("Temperature: %ld.%ld C\n", temp_c10/10, temp_c10%10);
}
```

---

## 2. Channel Diagnostics

### 2.1 Channel Status Flags

```c
typedef enum {
    PMU_FLAG_ENABLED     = 0x01,  // Channel active
    PMU_FLAG_FAULT       = 0x02,  // Error detected
    PMU_FLAG_TIMEOUT     = 0x04,  // CAN timeout
    PMU_FLAG_OVERCURRENT = 0x08,  // Current limit
    PMU_FLAG_OVERTEMP    = 0x10,  // Temperature limit
    PMU_FLAG_OPEN_LOAD   = 0x20,  // No load detected
    PMU_FLAG_SHORT       = 0x40   // Short circuit
} PMU_ChannelFlags_t;
```

### 2.2 Checking Channel Health

```c
bool is_channel_healthy(uint16_t channel_id) {
    const PMU_Channel_t* ch = PMU_Channel_GetInfo(channel_id);
    if (ch == NULL) return false;

    // Check for any fault condition
    uint8_t fault_mask = PMU_FLAG_FAULT | PMU_FLAG_OVERCURRENT |
                         PMU_FLAG_OVERTEMP | PMU_FLAG_SHORT;

    return (ch->flags & fault_mask) == 0;
}
```

### 2.3 Output Diagnostics

```c
typedef struct {
    uint16_t channel_id;
    uint16_t duty_cycle;        // 0-1000
    uint16_t actual_current_ma;
    uint16_t temperature_c;
    uint8_t state;              // PROFET state
    uint8_t fault_code;
    uint8_t retry_count;
} PMU_OutputDiag_t;

void PMU_GetOutputDiagnostics(uint16_t channel, PMU_OutputDiag_t* diag);
```

---

## 3. CAN Bus Diagnostics

### 3.1 Bus Statistics

```c
typedef struct {
    uint32_t tx_count;
    uint32_t rx_count;
    uint32_t tx_errors;
    uint32_t rx_errors;
    uint32_t bus_off_count;
    uint8_t tx_error_counter;
    uint8_t rx_error_counter;
    uint8_t state;  // Active, Passive, Bus-Off
} PMU_CAN_Stats_t;

void PMU_CAN_GetStatistics(uint8_t bus, PMU_CAN_Stats_t* stats);
```

### 3.2 Message Monitoring

```c
typedef struct {
    uint32_t msg_id;
    uint32_t last_rx_time;
    uint32_t rx_count;
    uint32_t timeout_count;
    bool is_timeout;
} PMU_CAN_MsgStats_t;

void PMU_CAN_GetMessageStats(uint32_t msg_id, PMU_CAN_MsgStats_t* stats);
```

---

## 4. Fault Logging

### 4.1 Fault Event Structure

```c
typedef struct {
    uint32_t timestamp;
    uint16_t channel_id;
    uint8_t fault_type;
    uint8_t severity;
    int32_t value;
    char description[32];
} PMU_FaultEvent_t;
```

### 4.2 Fault Types

| Code | Type | Severity | Description |
|------|------|----------|-------------|
| 0x01 | OVERCURRENT | High | Current exceeded limit |
| 0x02 | SHORT_CIRCUIT | Critical | Short to ground |
| 0x03 | OPEN_LOAD | Low | No load detected |
| 0x04 | OVERTEMP | High | Temperature limit |
| 0x05 | UNDERVOLTAGE | Medium | Battery low |
| 0x06 | OVERVOLTAGE | High | Battery high |
| 0x07 | CAN_TIMEOUT | Medium | Message timeout |
| 0x08 | SENSOR_FAULT | Medium | ADC out of range |

### 4.3 Reading Fault Log

```c
// Get fault count
uint32_t PMU_Fault_GetCount(void);

// Get fault by index (newest first)
HAL_StatusTypeDef PMU_Fault_GetEvent(uint32_t index, PMU_FaultEvent_t* event);

// Clear all faults
void PMU_Fault_ClearAll(void);
```

---

## 5. Performance Monitoring

### 5.1 Execution Timing

```c
typedef struct {
    uint32_t adc_update_us;
    uint32_t logic_exec_us;
    uint32_t can_process_us;
    uint32_t output_update_us;
    uint32_t total_cycle_us;
    uint32_t max_cycle_us;
} PMU_Timing_t;

void PMU_GetTiming(PMU_Timing_t* timing);
```

### 5.2 Resource Usage

```c
typedef struct {
    uint32_t heap_total;
    uint32_t heap_used;
    uint32_t stack_used;
    uint8_t cpu_load_percent;
    uint8_t channel_count;
    uint8_t function_count;
} PMU_Resources_t;

void PMU_GetResources(PMU_Resources_t* res);
```

---

## 6. LED Status Indicators

### 6.1 System LED

| Pattern | Color | Meaning |
|---------|-------|---------|
| Solid | Green | Normal operation |
| Slow blink | Green | Idle/standby |
| Fast blink | Yellow | Warning condition |
| Solid | Yellow | Configuration mode |
| Slow blink | Red | Fault detected |
| Fast blink | Red | Critical error |
| Alternating | Red/Green | Firmware update |

### 6.2 Channel LEDs

| State | Color | Meaning |
|-------|-------|---------|
| Off | - | Channel disabled |
| Solid | Green | Output ON, normal |
| PWM | Green | PWM active |
| Solid | Red | Fault condition |
| Blink | Red | Retry pending |

---

## 7. Diagnostic Commands

### 7.1 Via CAN

| Command ID | Name | Response |
|------------|------|----------|
| 0x7E0 | Read Status | System status |
| 0x7E1 | Read Channel | Channel value |
| 0x7E2 | Read Faults | Fault list |
| 0x7E3 | Clear Faults | Acknowledgment |
| 0x7E4 | Read Stats | Statistics |

### 7.2 Via USB/Serial

```
PMU> status
Battery: 13.8V, Current: 45.2A, Temp: 42C

PMU> channel 100
CH100: Fuel Pump, Value=1000, Current=8.5A, State=ON

PMU> faults
[001] 12:34:56 CH102 OVERCURRENT 15.2A
[002] 12:35:01 CAN1 TIMEOUT MSG 0x360

PMU> stats
Uptime: 3h 24m 15s
Cycles: 12,234,567
Max cycle: 1.8ms
```

---

## 8. Web Interface Monitoring

### 8.1 Dashboard Widgets

- **System Overview**: Battery, current, temperature
- **Output Status**: All 30 outputs with state/current
- **Input Values**: All 20 inputs with units
- **CAN Traffic**: Message rates, errors
- **Fault History**: Recent faults
- **Performance**: CPU load, cycle time

### 8.2 Live Data API

```
GET /api/status
GET /api/channels
GET /api/channels/{id}
GET /api/faults
GET /api/can/stats
```

---

## 9. Data Export

### 9.1 Snapshot Export

```c
// Export current state to JSON
HAL_StatusTypeDef PMU_Export_Snapshot(char* buffer, size_t size);
```

### 9.2 Log Export

```c
// Export log file
HAL_StatusTypeDef PMU_Export_Log(const char* filename, PMU_LogFormat_t format);
```

Supported formats: CSV, JSON, MoTeC LD, AiM

---

## See Also

- [Configuration Reference](configuration-reference.md)
- [Troubleshooting Guide](troubleshooting-guide.md)
- [Channel API](../api/channel-api.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024
