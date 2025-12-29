# Channel Examples

**Version:** 2.0
**Date:** December 2025

Practical code examples for common channel operations using the PMU-30 Channel Abstraction Layer.

---

## Table of Contents

1. [Basic Read/Write](#1-basic-readwrite)
2. [Analog Input Processing](#2-analog-input-processing)
3. [Digital Input Handling](#3-digital-input-handling)
4. [Output Control](#4-output-control)
5. [H-Bridge Control](#5-h-bridge-control)
6. [CAN Integration](#6-can-integration)
7. [Output Sub-Channels](#7-output-sub-channels)
8. [Error Handling](#8-error-handling)
9. [Concurrent Operations](#9-concurrent-operations)

---

## Channel ID Ranges

| Range | Type | Description |
|-------|------|-------------|
| 0-49 | Digital Inputs | d1-d20 physical digital inputs |
| 50-99 | Analog Inputs | a1-a20 physical analog inputs |
| 100-199 | Physical Outputs | o1-o30 power outputs, hb1-hb4 H-bridges |
| 200-999 | Virtual Channels | Logic, numbers, tables, CAN RX/TX, timers, etc. |
| 1000-1023 | System Channels | Battery voltage, temperatures, status |
| 1100-1279 | Output Sub-Channels | Per-output status, current, voltage, duty |

---

## 1. Basic Read/Write

### Read Single Channel

```c
#include "pmu_channel.h"

void example_read_channel(void) {
    // Read by ID
    int32_t value = PMU_Channel_GetValue(50);  // Analog input 1
    printf("Channel 50 value: %ld\n", value);

    // Read system channel
    int32_t battery = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BATTERY_V);  // 1000
    printf("Battery: %ld mV\n", battery);

    // Read board temperatures
    int32_t temp_l = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BOARD_TEMP_L);  // 1003
    int32_t temp_r = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BOARD_TEMP_R);  // 1004
    printf("Board temps: L=%ld R=%ld C\n", temp_l, temp_r);
}
```

### Write Single Channel

```c
void example_write_channel(void) {
    // Set output ON (output 1 = channel 100)
    PMU_Channel_SetValue(100, 1);

    // Set PWM duty cycle (50%) on output 2
    PMU_Channel_SetValue(101, 500);

    // With status check
    HAL_StatusTypeDef status = PMU_Channel_SetValue(100, 1);
    if (status != HAL_OK) {
        printf("Write failed!\n");
    }
}
```

### Read by Name

```c
void example_read_by_name(void) {
    const PMU_Channel_t* ch = PMU_Channel_GetByName("CoolantTemp");

    if (ch != NULL) {
        printf("%s = %ld %s\n", ch->name, ch->value, ch->unit);
    } else {
        printf("Channel not found\n");
    }
}
```

### Get Channel ID by String

```c
void example_get_channel_id(void) {
    // Parse channel ID from string (supports both numeric and name lookup)
    uint16_t id = PMU_Channel_GetIndexByID("FuelPump");  // Returns channel_id or 0xFFFF

    if (id != 0xFFFF) {
        int32_t value = PMU_Channel_GetValue(id);
        printf("FuelPump channel %d = %ld\n", id, value);
    }

    // Direct numeric string
    uint16_t id2 = PMU_Channel_GetIndexByID("105");  // Returns 105
}
```

---

## 2. Analog Input Processing

### Simple ADC Reading

```c
void example_adc_read(void) {
    // Analog input 1 (channel 50), raw ADC value (0-4095)
    int32_t raw = PMU_Channel_GetValue(50);

    // Convert to voltage (0-5V)
    float voltage = raw * 5.0f / 4095.0f;

    printf("ADC: %ld, Voltage: %.3f V\n", raw, voltage);
}
```

### Temperature Sensor (NTC)

```c
// NTC 10K B=3950 temperature calculation
float ntc_to_celsius(int32_t adc_value) {
    // Voltage divider with 10K pullup to 5V
    float resistance = 10000.0f * adc_value / (4095.0f - adc_value);

    // Steinhart-Hart simplified (B parameter)
    float steinhart = resistance / 10000.0f;
    steinhart = logf(steinhart);
    steinhart /= 3950.0f;
    steinhart += 1.0f / (25.0f + 273.15f);
    steinhart = 1.0f / steinhart;
    steinhart -= 273.15f;

    return steinhart;
}

void example_temperature_read(void) {
    int32_t adc = PMU_Channel_GetValue(52);  // Analog input 3 (channel 52)
    float temp = ntc_to_celsius(adc);
    printf("Temperature: %.1f C\n", temp);
}
```

### Pressure Sensor (0.5-4.5V = 0-100 PSI)

```c
float pressure_from_voltage(float voltage) {
    // Linear scaling: 0.5V = 0 PSI, 4.5V = 100 PSI
    if (voltage < 0.5f) return 0.0f;
    if (voltage > 4.5f) return 100.0f;
    return (voltage - 0.5f) * 25.0f;  // 100 / 4.0
}

void example_pressure_read(void) {
    int32_t raw = PMU_Channel_GetValue(53);  // Analog input 4
    float voltage = raw * 5.0f / 4095.0f;
    float pressure = pressure_from_voltage(voltage);
    printf("Oil Pressure: %.1f PSI\n", pressure);
}
```

### Throttle Position (Dual Sensor)

```c
void example_throttle_read(void) {
    int32_t tps1 = PMU_Channel_GetValue(54);  // Analog 5: TPS 1 (0.5-4.5V)
    int32_t tps2 = PMU_Channel_GetValue(55);  // Analog 6: TPS 2 (4.5-0.5V, inverted)

    // Convert to percentage
    float pct1 = (tps1 - 409.0f) / 3277.0f * 100.0f;   // 0.5V-4.5V
    float pct2 = (4095.0f - 409.0f - tps2) / 3277.0f * 100.0f;

    // Plausibility check
    if (fabsf(pct1 - pct2) > 10.0f) {
        printf("TPS ERROR: Sensors disagree!\n");
        return;
    }

    float throttle = (pct1 + pct2) / 2.0f;
    printf("Throttle: %.1f%%\n", throttle);
}
```

---

## 3. Digital Input Handling

### Simple Switch

```c
void example_switch_read(void) {
    // Digital input 1 (channel 0)
    int32_t state = PMU_Channel_GetValue(0);

    if (state) {
        printf("Switch ON\n");
    } else {
        printf("Switch OFF\n");
    }
}
```

### Debounced Button

```c
typedef struct {
    uint32_t last_change;
    uint8_t stable_state;
    uint8_t current_state;
} Debounce_t;

uint8_t debounce_read(Debounce_t* db, uint8_t raw, uint32_t debounce_ms) {
    uint32_t now = HAL_GetTick();

    if (raw != db->current_state) {
        db->current_state = raw;
        db->last_change = now;
    }

    if ((now - db->last_change) >= debounce_ms) {
        db->stable_state = db->current_state;
    }

    return db->stable_state;
}

static Debounce_t button_db = {0};

void example_debounced_button(void) {
    uint8_t raw = PMU_Channel_GetValue(1);  // Digital input 2
    uint8_t stable = debounce_read(&button_db, raw, 50);

    printf("Button: %s\n", stable ? "PRESSED" : "RELEASED");
}
```

### Edge Detection

```c
static uint8_t last_state = 0;

void example_edge_detect(void) {
    uint8_t current = PMU_Channel_GetValue(2);  // Digital input 3

    if (current && !last_state) {
        printf("Rising edge detected\n");
        // Do something on button press
    }

    if (!current && last_state) {
        printf("Falling edge detected\n");
        // Do something on button release
    }

    last_state = current;
}
```

### Rotary Switch

```c
void example_rotary_switch(void) {
    // Virtual switch channel (configured with rotary position)
    int32_t position = PMU_Channel_GetValue(240);

    switch (position) {
        case 0: printf("Mode: OFF\n"); break;
        case 1: printf("Mode: AUTO\n"); break;
        case 2: printf("Mode: LOW\n"); break;
        case 3: printf("Mode: HIGH\n"); break;
        default: printf("Mode: UNKNOWN\n"); break;
    }
}
```

---

## 4. Output Control

### Simple On/Off

```c
void example_output_onoff(void) {
    // Output 1 (channel 100)
    PMU_Channel_SetValue(100, 1);  // Turn on
    HAL_Delay(1000);

    PMU_Channel_SetValue(100, 0);  // Turn off
}
```

### PWM Output

```c
void example_pwm_control(void) {
    // Output 2 (channel 101)
    // Ramp up from 0 to 100%
    for (int duty = 0; duty <= 1000; duty += 10) {
        PMU_Channel_SetValue(101, duty);
        HAL_Delay(10);
    }

    // Hold at 100%
    HAL_Delay(1000);

    // Ramp down
    for (int duty = 1000; duty >= 0; duty -= 10) {
        PMU_Channel_SetValue(101, duty);
        HAL_Delay(10);
    }
}
```

### Temperature-Based Fan Control

```c
void example_fan_control(void) {
    // Temperature channel (virtual, scaled to 0.1 C)
    int32_t temp = PMU_Channel_GetValue(200);

    int32_t duty = 0;

    if (temp < 600) {
        duty = 0;  // Off below 60 C
    } else if (temp > 900) {
        duty = 1000;  // 100% above 90 C
    } else {
        // Linear 0-100% between 60-90 C
        duty = (temp - 600) * 1000 / 300;
    }

    // Fan output (channel 105)
    PMU_Channel_SetValue(105, duty);
}
```

### Blinking Output

```c
void example_blink(uint16_t channel, uint32_t period_ms) {
    static uint32_t last_toggle = 0;
    static uint8_t state = 0;

    if (HAL_GetTick() - last_toggle >= period_ms / 2) {
        state = !state;
        PMU_Channel_SetValue(channel, state);
        last_toggle = HAL_GetTick();
    }
}
```

---

## 5. H-Bridge Control

### Basic Motor Control

```c
void example_hbridge_basic(void) {
    // H-Bridge 1 (channel 130)
    // Positive value = forward, negative = reverse

    PMU_Channel_SetValue(130, 800);   // Forward at 80%
    HAL_Delay(2000);

    PMU_Channel_SetValue(130, 0);     // Stop
    HAL_Delay(500);

    PMU_Channel_SetValue(130, -800);  // Reverse at 80%
    HAL_Delay(2000);

    PMU_Channel_SetValue(130, 0);     // Stop
}
```

### Window Motor with Buttons

```c
void example_window_control(void) {
    int32_t up_btn = PMU_Channel_GetValue(4);    // Digital input 5
    int32_t down_btn = PMU_Channel_GetValue(5);  // Digital input 6

    // H-Bridge 1 (channel 130)
    if (up_btn && !down_btn) {
        PMU_Channel_SetValue(130, 800);   // Up
    } else if (down_btn && !up_btn) {
        PMU_Channel_SetValue(130, -800);  // Down
    } else {
        PMU_Channel_SetValue(130, 0);     // Stop
    }
}
```

### Soft Start/Stop Motor

```c
void motor_soft_start(uint16_t channel, int32_t target, uint32_t ramp_ms) {
    int32_t current = 0;
    int32_t step = target / (ramp_ms / 10);

    while (abs(current) < abs(target)) {
        current += step;
        if ((step > 0 && current > target) || (step < 0 && current < target)) {
            current = target;
        }
        PMU_Channel_SetValue(channel, current);
        HAL_Delay(10);
    }
}

void example_soft_motor(void) {
    // Soft start to 80% forward over 500ms
    motor_soft_start(130, 800, 500);

    HAL_Delay(2000);

    // Soft stop
    motor_soft_start(130, 0, 500);
}
```

---

## 6. CAN Integration

### Read ECU RPM

```c
void example_can_rpm(void) {
    // CAN RX channel configured for RPM signal (virtual channel 300)
    int32_t rpm = PMU_Channel_GetValue(300);

    printf("Engine RPM: %ld\n", rpm);

    // Rev limiter
    if (rpm > 7000) {
        PMU_Channel_SetValue(102, 0);  // Cut ignition output
    } else {
        PMU_Channel_SetValue(102, 1);  // Normal
    }
}
```

### Multi-Signal Dashboard

```c
void example_dashboard_display(void) {
    // Read all CAN RX signals (configured in virtual channel range)
    int32_t rpm = PMU_Channel_GetValue(300);      // CAN RX: RPM
    int32_t speed = PMU_Channel_GetValue(301);    // CAN RX: Vehicle Speed
    int32_t coolant = PMU_Channel_GetValue(302);  // CAN RX: Coolant Temp
    int32_t oil_press = PMU_Channel_GetValue(303); // CAN RX: Oil Pressure
    int32_t fuel = PMU_Channel_GetValue(304);     // CAN RX: Fuel Level

    printf("=== Dashboard ===\n");
    printf("RPM: %ld\n", rpm);
    printf("Speed: %ld km/h\n", speed);
    printf("Coolant: %ld.%ld C\n", coolant/10, coolant%10);
    printf("Oil: %ld.%ld bar\n", oil_press/100, oil_press%100);
    printf("Fuel: %ld%%\n", fuel/10);
}
```

---

## 7. Output Sub-Channels

The PMU-30 provides per-output telemetry via sub-channels:

| Base ID | Range | Description |
|---------|-------|-------------|
| 1100 | 1100-1129 | Output status (oY.status) |
| 1130 | 1130-1159 | Output current mA (oY.current) |
| 1160 | 1160-1189 | Output voltage mV (oY.voltage) |
| 1190 | 1190-1219 | Output active state (oY.active) |
| 1250 | 1250-1279 | Output duty cycle (oY.dutyCycle) |

### Read Output Telemetry

```c
void example_read_output_telemetry(void) {
    uint8_t output_idx = 0;  // Output 1

    // Read all sub-channels for output 1
    int32_t status = PMU_Channel_GetValue(PMU_CHANNEL_OUTPUT_STATUS_BASE + output_idx);   // 1100
    int32_t current = PMU_Channel_GetValue(PMU_CHANNEL_OUTPUT_CURRENT_BASE + output_idx); // 1130
    int32_t voltage = PMU_Channel_GetValue(PMU_CHANNEL_OUTPUT_VOLTAGE_BASE + output_idx); // 1160
    int32_t active = PMU_Channel_GetValue(PMU_CHANNEL_OUTPUT_ACTIVE_BASE + output_idx);   // 1190
    int32_t duty = PMU_Channel_GetValue(PMU_CHANNEL_OUTPUT_DUTY_BASE + output_idx);       // 1250

    printf("Output %d:\n", output_idx + 1);
    printf("  Status: %ld\n", status);
    printf("  Current: %ld mA\n", current);
    printf("  Voltage: %ld mV\n", voltage);
    printf("  Active: %s\n", active ? "YES" : "NO");
    printf("  Duty: %ld.%ld%%\n", duty / 10, duty % 10);
}
```

### Monitor All Outputs

```c
void example_monitor_all_outputs(void) {
    printf("Output | Status | Current | Voltage | Active | Duty\n");
    printf("-------|--------|---------|---------|--------|------\n");

    for (int i = 0; i < 30; i++) {
        int32_t status = PMU_Channel_GetValue(1100 + i);
        int32_t current = PMU_Channel_GetValue(1130 + i);
        int32_t voltage = PMU_Channel_GetValue(1160 + i);
        int32_t active = PMU_Channel_GetValue(1190 + i);
        int32_t duty = PMU_Channel_GetValue(1250 + i);

        printf("  %2d   |   %ld    |  %4ld   |  %5ld  |   %s   | %3ld.%ld\n",
               i + 1, status, current, voltage, active ? "Y" : "N",
               duty / 10, duty % 10);
    }
}
```

### Fault Detection Using Sub-Channels

```c
typedef enum {
    OUTPUT_STATUS_OFF = 0,
    OUTPUT_STATUS_ON = 1,
    OUTPUT_STATUS_UNDERCURRENT = 2,
    OUTPUT_STATUS_OVERCURRENT = 3,
    OUTPUT_STATUS_SHORT_GND = 4,
    OUTPUT_STATUS_SHORT_VBAT = 5,
    OUTPUT_STATUS_OPEN_LOAD = 6,
    OUTPUT_STATUS_THERMAL = 7
} OutputStatus_t;

void example_fault_detection(void) {
    for (int i = 0; i < 30; i++) {
        int32_t status = PMU_Channel_GetValue(1100 + i);

        if (status >= OUTPUT_STATUS_UNDERCURRENT) {
            printf("Output %d FAULT: ", i + 1);
            switch (status) {
                case OUTPUT_STATUS_UNDERCURRENT: printf("Undercurrent\n"); break;
                case OUTPUT_STATUS_OVERCURRENT: printf("Overcurrent\n"); break;
                case OUTPUT_STATUS_SHORT_GND: printf("Short to GND\n"); break;
                case OUTPUT_STATUS_SHORT_VBAT: printf("Short to VBAT\n"); break;
                case OUTPUT_STATUS_OPEN_LOAD: printf("Open load\n"); break;
                case OUTPUT_STATUS_THERMAL: printf("Thermal shutdown\n"); break;
            }
        }
    }
}
```

---

## 8. Error Handling

### Safe Channel Access

```c
int32_t safe_channel_read(uint16_t channel_id, int32_t default_value) {
    const PMU_Channel_t* ch = PMU_Channel_GetInfo(channel_id);

    if (ch == NULL) {
        return default_value;
    }

    if (ch->flags & PMU_CHANNEL_FLAG_FAULT) {
        return default_value;
    }

    if (!(ch->flags & PMU_CHANNEL_FLAG_ENABLED)) {
        return default_value;
    }

    return ch->value;
}

void example_safe_read(void) {
    // Returns 0 if channel missing or faulted
    int32_t temp = safe_channel_read(50, 0);
}
```

### Output with Fault Check

```c
void safe_output_set(uint16_t channel_id, int32_t value) {
    const PMU_Channel_t* ch = PMU_Channel_GetInfo(channel_id);

    if (ch == NULL) {
        printf("Error: Channel %d not found\n", channel_id);
        return;
    }

    if (ch->flags & PMU_CHANNEL_FLAG_FAULT) {
        printf("Warning: Channel %d has fault\n", channel_id);
        // Attempt to clear and retry
        PMU_PROFET_ClearFault(ch->physical_index);
    }

    PMU_Channel_SetValue(channel_id, value);
}
```

### Register Dynamic Channel

```c
void example_dynamic_channel(void) {
    // Generate unique ID in virtual range (200-999)
    uint16_t new_id = PMU_Channel_GenerateID();

    PMU_Channel_t new_channel = {
        .channel_id = new_id,
        .hw_class = PMU_CHANNEL_CLASS_OUTPUT_NUMBER,
        .direction = PMU_CHANNEL_DIR_VIRTUAL,
        .format = PMU_CHANNEL_FORMAT_SIGNED,
        .value = 0,
        .min_value = -1000,
        .max_value = 1000,
        .flags = PMU_CHANNEL_FLAG_ENABLED
    };
    strncpy(new_channel.name, "DynamicValue", sizeof(new_channel.name));
    strncpy(new_channel.unit, "", sizeof(new_channel.unit));

    HAL_StatusTypeDef status = PMU_Channel_Register(&new_channel);
    if (status == HAL_OK) {
        printf("Registered dynamic channel ID: %d\n", new_id);
    }
}
```

---

## 9. Concurrent Operations

### Batch Read

```c
void example_batch_read(void) {
    // Read multiple channels efficiently
    int32_t values[10];
    uint16_t channels[] = {50, 51, 52, 53, 54, 100, 101, 300, 301, 1000};

    for (int i = 0; i < 10; i++) {
        values[i] = PMU_Channel_GetValue(channels[i]);
    }

    // Process values
    for (int i = 0; i < 10; i++) {
        printf("Channel %d: %ld\n", channels[i], values[i]);
    }
}
```

### Atomic Update (RTOS)

```c
void example_atomic_update(void) {
    // Update multiple related outputs together
    taskENTER_CRITICAL();

    PMU_Channel_SetValue(100, new_value_1);
    PMU_Channel_SetValue(101, new_value_2);
    PMU_Channel_SetValue(102, new_value_3);

    taskEXIT_CRITICAL();
}
```

### Update Input Channel (Firmware Internal Use)

```c
// Used internally by ADC/digital input drivers to sync hardware state
void example_update_input_value(void) {
    // PMU_Channel_UpdateValue() allows setting INPUT channel values
    // Unlike SetValue() which is for outputs only
    PMU_Channel_UpdateValue(50, adc_raw_value);  // Analog input 1
    PMU_Channel_UpdateValue(0, digital_state);   // Digital input 1
}
```

---

## See Also

- [Channel Abstraction](../../firmware/CHANNEL_ABSTRACTION.md) - Full API reference
- [Logic Function Examples](logic-function-examples.md)
- [Real-World Scenarios](real-world-scenarios.md)
- [JSON Configuration](../../firmware/JSON_CONFIG.md) - Configuration format v3.0

---

**Document Version:** 2.0
**Last Updated:** December 2025
