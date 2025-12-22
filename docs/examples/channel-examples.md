# Channel Examples

**Version:** 1.0
**Date:** December 2024

Practical code examples for common channel operations.

---

## Table of Contents

1. [Basic Read/Write](#1-basic-readwrite)
2. [Analog Input Processing](#2-analog-input-processing)
3. [Digital Input Handling](#3-digital-input-handling)
4. [Output Control](#4-output-control)
5. [H-Bridge Control](#5-h-bridge-control)
6. [CAN Integration](#6-can-integration)
7. [Error Handling](#7-error-handling)
8. [Concurrent Operations](#8-concurrent-operations)

---

## 1. Basic Read/Write

### Read Single Channel

```c
#include "pmu_channel.h"

void example_read_channel(void) {
    // Read by ID
    int32_t value = PMU_Channel_GetValue(0);
    printf("Channel 0 value: %ld\n", value);

    // Read system channel
    int32_t battery = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BATTERY_V);
    printf("Battery: %ld mV\n", battery);
}
```

### Write Single Channel

```c
void example_write_channel(void) {
    // Set output ON
    PMU_Channel_SetValue(100, 1);

    // Set PWM duty cycle (50%)
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
    const PMU_Channel_t* ch = PMU_Channel_GetByName("Coolant Temp");

    if (ch != NULL) {
        printf("%s = %ld %s\n", ch->name, ch->value, ch->unit);
    } else {
        printf("Channel not found\n");
    }
}
```

---

## 2. Analog Input Processing

### Simple ADC Reading

```c
void example_adc_read(void) {
    // Raw ADC value (0-4095)
    int32_t raw = PMU_Channel_GetValue(0);

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
    int32_t adc = PMU_Channel_GetValue(2);  // NTC on ADC2
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
    int32_t raw = PMU_Channel_GetValue(3);
    float voltage = raw * 5.0f / 4095.0f;
    float pressure = pressure_from_voltage(voltage);
    printf("Oil Pressure: %.1f PSI\n", pressure);
}
```

### Throttle Position (Dual Sensor)

```c
void example_throttle_read(void) {
    int32_t tps1 = PMU_Channel_GetValue(4);  // TPS 1 (0.5-4.5V)
    int32_t tps2 = PMU_Channel_GetValue(5);  // TPS 2 (4.5-0.5V, inverted)

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
    int32_t state = PMU_Channel_GetValue(20);

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
    uint8_t raw = PMU_Channel_GetValue(21);
    uint8_t stable = debounce_read(&button_db, raw, 50);

    printf("Button: %s\n", stable ? "PRESSED" : "RELEASED");
}
```

### Edge Detection

```c
static uint8_t last_state = 0;

void example_edge_detect(void) {
    uint8_t current = PMU_Channel_GetValue(22);

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
    int32_t position = PMU_Channel_GetValue(23);

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
    // Turn on
    PMU_Channel_SetValue(100, 1);
    HAL_Delay(1000);

    // Turn off
    PMU_Channel_SetValue(100, 0);
}
```

### PWM Output

```c
void example_pwm_control(void) {
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
    int32_t temp = PMU_Channel_GetValue(0);  // Temperature in 0.1 C

    int32_t duty = 0;

    if (temp < 600) {
        duty = 0;  // Off below 60 C
    } else if (temp > 900) {
        duty = 1000;  // 100% above 90 C
    } else {
        // Linear 0-100% between 60-90 C
        duty = (temp - 600) * 1000 / 300;
    }

    PMU_Channel_SetValue(100, duty);
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
    // Forward at 80%
    PMU_Channel_SetValue(130, 800);
    HAL_Delay(2000);

    // Stop
    PMU_Channel_SetValue(130, 0);
    HAL_Delay(500);

    // Reverse at 80%
    PMU_Channel_SetValue(130, -800);
    HAL_Delay(2000);

    // Stop
    PMU_Channel_SetValue(130, 0);
}
```

### Window Motor with Buttons

```c
void example_window_control(void) {
    int32_t up_btn = PMU_Channel_GetValue(24);
    int32_t down_btn = PMU_Channel_GetValue(25);

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
    // Assuming CAN signal configured as channel 200
    int32_t rpm = PMU_Channel_GetValue(200);

    printf("Engine RPM: %ld\n", rpm);

    // Rev limiter
    if (rpm > 7000) {
        PMU_Channel_SetValue(102, 0);  // Cut ignition
    } else {
        PMU_Channel_SetValue(102, 1);  // Normal
    }
}
```

### Multi-Signal Dashboard

```c
void example_dashboard_display(void) {
    // Read all CAN signals
    int32_t rpm = PMU_Channel_GetValue(200);
    int32_t speed = PMU_Channel_GetValue(201);
    int32_t coolant = PMU_Channel_GetValue(202);
    int32_t oil_press = PMU_Channel_GetValue(203);
    int32_t fuel = PMU_Channel_GetValue(204);

    printf("=== Dashboard ===\n");
    printf("RPM: %ld\n", rpm);
    printf("Speed: %ld km/h\n", speed);
    printf("Coolant: %ld.%ld C\n", coolant/10, coolant%10);
    printf("Oil: %ld.%ld bar\n", oil_press/100, oil_press%100);
    printf("Fuel: %ld%%\n", fuel/10);
}
```

---

## 7. Error Handling

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
    int32_t temp = safe_channel_read(0, 0);
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

---

## 8. Concurrent Operations

### Batch Read

```c
void example_batch_read(void) {
    // Read multiple channels efficiently
    int32_t values[10];
    uint16_t channels[] = {0, 1, 2, 3, 4, 100, 101, 200, 201, 1000};

    for (int i = 0; i < 10; i++) {
        values[i] = PMU_Channel_GetValue(channels[i]);
    }

    // Process values
    for (int i = 0; i < 10; i++) {
        printf("Channel %d: %ld\n", channels[i], values[i]);
    }
}
```

### Atomic Update

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

---

## See Also

- [Channel API Reference](../api/channel-api.md)
- [Logic Function Examples](logic-function-examples.md)
- [Real-World Scenarios](real-world-scenarios.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024
