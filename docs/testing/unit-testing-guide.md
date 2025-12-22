# Unit Testing Guide

**Version:** 1.0
**Date:** December 2024

---

## 1. Overview

Unit tests verify individual components of the PMU-30 firmware in isolation.

### Test Framework

- **Framework:** Unity (embedded C testing)
- **Runner:** PlatformIO test runner
- **Coverage:** gcov/lcov

---

## 2. Test Structure

### Directory Layout

```
firmware/
├── test/
│   ├── test_channel/
│   │   ├── test_channel_read.c
│   │   ├── test_channel_write.c
│   │   └── test_channel_registry.c
│   ├── test_logic/
│   │   ├── test_arithmetic.c
│   │   ├── test_comparison.c
│   │   └── test_state.c
│   ├── test_drivers/
│   │   ├── test_profet.c
│   │   └── test_hbridge.c
│   └── mocks/
│       ├── mock_hal.h
│       └── mock_adc.h
```

---

## 3. Writing Tests

### Basic Test Structure

```c
#include "unity.h"
#include "pmu_channel.h"

void setUp(void) {
    // Initialize before each test
    PMU_Channel_Init();
}

void tearDown(void) {
    // Cleanup after each test
    PMU_Channel_DeInit();
}

void test_channel_read_valid_id(void) {
    // Arrange
    PMU_Channel_SetValue(0, 1234);

    // Act
    int32_t value = PMU_Channel_GetValue(0);

    // Assert
    TEST_ASSERT_EQUAL_INT32(1234, value);
}

void test_channel_read_invalid_id(void) {
    // Arrange - nothing

    // Act
    int32_t value = PMU_Channel_GetValue(9999);

    // Assert
    TEST_ASSERT_EQUAL_INT32(0, value);
}
```

### Running Tests

```bash
# Run all tests
pio test

# Run specific test
pio test -f test_channel

# With verbose output
pio test -v
```

---

## 4. Channel System Tests

### Channel Read/Write

```c
// test_channel_read.c

void test_channel_write_and_read(void) {
    PMU_Channel_SetValue(100, 500);
    TEST_ASSERT_EQUAL_INT32(500, PMU_Channel_GetValue(100));
}

void test_channel_write_negative(void) {
    PMU_Channel_SetValue(130, -800);
    TEST_ASSERT_EQUAL_INT32(-800, PMU_Channel_GetValue(130));
}

void test_channel_write_max_value(void) {
    PMU_Channel_SetValue(100, INT32_MAX);
    TEST_ASSERT_EQUAL_INT32(INT32_MAX, PMU_Channel_GetValue(100));
}

void test_channel_get_by_name(void) {
    PMU_Channel_Register(0, "TestChannel", PMU_CHANNEL_INPUT_ANALOG);
    const PMU_Channel_t* ch = PMU_Channel_GetByName("TestChannel");
    TEST_ASSERT_NOT_NULL(ch);
    TEST_ASSERT_EQUAL_UINT16(0, ch->id);
}

void test_channel_get_by_name_not_found(void) {
    const PMU_Channel_t* ch = PMU_Channel_GetByName("NonExistent");
    TEST_ASSERT_NULL(ch);
}
```

### Channel Flags

```c
// test_channel_flags.c

void test_channel_enable_flag(void) {
    PMU_Channel_Enable(100);
    const PMU_Channel_t* ch = PMU_Channel_GetInfo(100);
    TEST_ASSERT_TRUE(ch->flags & PMU_CHANNEL_FLAG_ENABLED);
}

void test_channel_fault_flag(void) {
    PMU_Channel_SetFault(100, true);
    const PMU_Channel_t* ch = PMU_Channel_GetInfo(100);
    TEST_ASSERT_TRUE(ch->flags & PMU_CHANNEL_FLAG_FAULT);
}

void test_channel_clear_fault(void) {
    PMU_Channel_SetFault(100, true);
    PMU_Channel_SetFault(100, false);
    const PMU_Channel_t* ch = PMU_Channel_GetInfo(100);
    TEST_ASSERT_FALSE(ch->flags & PMU_CHANNEL_FLAG_FAULT);
}
```

---

## 5. Logic Function Tests

### Arithmetic Functions

```c
// test_arithmetic.c

void test_func_add(void) {
    PMU_Channel_SetValue(200, 100);
    PMU_Channel_SetValue(201, 50);

    PMU_LogicFunction_t func = {
        .type = PMU_FUNC_ADD,
        .input_channels = {200, 201},
        .input_count = 2,
        .output_channel = 210
    };

    PMU_LogicFunctions_Execute(&func);

    TEST_ASSERT_EQUAL_INT32(150, PMU_Channel_GetValue(210));
}

void test_func_divide_by_zero(void) {
    PMU_Channel_SetValue(200, 100);
    PMU_Channel_SetValue(201, 0);

    PMU_LogicFunction_t func = {
        .type = PMU_FUNC_DIVIDE,
        .input_channels = {200, 201},
        .output_channel = 210
    };

    PMU_LogicFunctions_Execute(&func);

    TEST_ASSERT_EQUAL_INT32(INT32_MAX, PMU_Channel_GetValue(210));
}

void test_func_multiply_overflow(void) {
    PMU_Channel_SetValue(200, 1000000);
    PMU_Channel_SetValue(201, 1000000);

    PMU_LogicFunction_t func = {
        .type = PMU_FUNC_MULTIPLY,
        .input_channels = {200, 201},
        .params.scale_factor = 1000000,
        .output_channel = 210
    };

    PMU_LogicFunctions_Execute(&func);

    // Should not overflow due to scaling
    TEST_ASSERT_EQUAL_INT32(1000000, PMU_Channel_GetValue(210));
}
```

### Comparison Functions

```c
// test_comparison.c

void test_func_greater_true(void) {
    PMU_Channel_SetValue(200, 100);
    PMU_Channel_SetValue(201, 50);

    PMU_LogicFunction_t func = {
        .type = PMU_FUNC_GREATER,
        .input_channels = {200, 201},
        .output_channel = 210
    };

    PMU_LogicFunctions_Execute(&func);

    TEST_ASSERT_EQUAL_INT32(1, PMU_Channel_GetValue(210));
}

void test_func_greater_false(void) {
    PMU_Channel_SetValue(200, 50);
    PMU_Channel_SetValue(201, 100);

    PMU_LogicFunction_t func = {
        .type = PMU_FUNC_GREATER,
        .input_channels = {200, 201},
        .output_channel = 210
    };

    PMU_LogicFunctions_Execute(&func);

    TEST_ASSERT_EQUAL_INT32(0, PMU_Channel_GetValue(210));
}

void test_func_in_range(void) {
    PMU_Channel_SetValue(200, 850);

    PMU_LogicFunction_t func = {
        .type = PMU_FUNC_IN_RANGE,
        .input_channels = {200},
        .params.min = 800,
        .params.max = 900,
        .output_channel = 210
    };

    PMU_LogicFunctions_Execute(&func);

    TEST_ASSERT_EQUAL_INT32(1, PMU_Channel_GetValue(210));
}
```

### State Functions

```c
// test_state.c

void test_func_toggle(void) {
    PMU_Channel_SetValue(20, 0);  // Initial: OFF

    PMU_LogicFunction_t func = {
        .type = PMU_FUNC_TOGGLE,
        .input_channels = {20},
        .output_channel = 100
    };

    // First press
    PMU_Channel_SetValue(20, 1);
    PMU_LogicFunctions_Execute(&func);
    TEST_ASSERT_EQUAL_INT32(1, PMU_Channel_GetValue(100));

    // Release
    PMU_Channel_SetValue(20, 0);
    PMU_LogicFunctions_Execute(&func);
    TEST_ASSERT_EQUAL_INT32(1, PMU_Channel_GetValue(100));

    // Second press
    PMU_Channel_SetValue(20, 1);
    PMU_LogicFunctions_Execute(&func);
    TEST_ASSERT_EQUAL_INT32(0, PMU_Channel_GetValue(100));
}

void test_func_latch_sr(void) {
    PMU_LogicFunction_t func = {
        .type = PMU_FUNC_LATCH_SR,
        .input_channels = {210, 211},  // Set, Reset
        .output_channel = 220
    };

    // Set
    PMU_Channel_SetValue(210, 1);
    PMU_Channel_SetValue(211, 0);
    PMU_LogicFunctions_Execute(&func);
    TEST_ASSERT_EQUAL_INT32(1, PMU_Channel_GetValue(220));

    // Clear inputs, should hold
    PMU_Channel_SetValue(210, 0);
    PMU_LogicFunctions_Execute(&func);
    TEST_ASSERT_EQUAL_INT32(1, PMU_Channel_GetValue(220));

    // Reset
    PMU_Channel_SetValue(211, 1);
    PMU_LogicFunctions_Execute(&func);
    TEST_ASSERT_EQUAL_INT32(0, PMU_Channel_GetValue(220));
}
```

---

## 6. Driver Tests

### PROFET Driver

```c
// test_profet.c

void test_profet_set_duty(void) {
    PMU_PROFET_SetDuty(0, 500);
    TEST_ASSERT_EQUAL_UINT16(500, PMU_PROFET_GetDuty(0));
}

void test_profet_current_limit(void) {
    PMU_PROFET_SetCurrentLimit(0, 15000);  // 15A
    // Simulate overcurrent
    mock_profet_set_current(0, 16000);
    PMU_PROFET_Update();

    TEST_ASSERT_TRUE(PMU_PROFET_IsFault(0));
}

void test_profet_soft_start(void) {
    PMU_PROFET_SetSoftStart(0, 100);  // 100ms
    PMU_PROFET_SetDuty(0, 1000);

    // At t=0, should be low
    TEST_ASSERT_LESS_THAN(500, PMU_PROFET_GetActualDuty(0));

    // At t=50ms, should be ramping
    mock_advance_time(50);
    PMU_PROFET_Update();
    TEST_ASSERT_GREATER_THAN(400, PMU_PROFET_GetActualDuty(0));
    TEST_ASSERT_LESS_THAN(600, PMU_PROFET_GetActualDuty(0));

    // At t=100ms, should be at target
    mock_advance_time(50);
    PMU_PROFET_Update();
    TEST_ASSERT_EQUAL_UINT16(1000, PMU_PROFET_GetActualDuty(0));
}
```

### H-Bridge Driver

```c
// test_hbridge.c

void test_hbridge_forward(void) {
    PMU_HBridge_SetValue(0, 800);
    TEST_ASSERT_EQUAL(HBRIDGE_STATE_FORWARD, PMU_HBridge_GetState(0));
}

void test_hbridge_reverse(void) {
    PMU_HBridge_SetValue(0, -800);
    TEST_ASSERT_EQUAL(HBRIDGE_STATE_REVERSE, PMU_HBridge_GetState(0));
}

void test_hbridge_brake(void) {
    PMU_HBridge_SetValue(0, 800);
    PMU_HBridge_Brake(0);
    TEST_ASSERT_EQUAL(HBRIDGE_STATE_BRAKE, PMU_HBridge_GetState(0));
}

void test_hbridge_coast(void) {
    PMU_HBridge_SetValue(0, 800);
    PMU_HBridge_Coast(0);
    TEST_ASSERT_EQUAL(HBRIDGE_STATE_COAST, PMU_HBridge_GetState(0));
}
```

---

## 7. Mock Objects

### HAL Mock

```c
// mock_hal.h

#ifndef MOCK_HAL_H
#define MOCK_HAL_H

#include <stdint.h>

static uint32_t mock_tick = 0;

uint32_t HAL_GetTick(void) {
    return mock_tick;
}

void mock_advance_time(uint32_t ms) {
    mock_tick += ms;
}

void mock_reset_time(void) {
    mock_tick = 0;
}

#endif
```

### ADC Mock

```c
// mock_adc.h

#ifndef MOCK_ADC_H
#define MOCK_ADC_H

static uint16_t mock_adc_values[20] = {0};

void mock_adc_set_value(uint8_t channel, uint16_t value) {
    if (channel < 20) {
        mock_adc_values[channel] = value;
    }
}

uint16_t mock_adc_get_value(uint8_t channel) {
    return (channel < 20) ? mock_adc_values[channel] : 0;
}

#endif
```

---

## 8. Test Coverage

### Generate Coverage Report

```bash
# Build with coverage
pio test --coverage

# Generate HTML report
lcov --capture --directory . --output-file coverage.info
genhtml coverage.info --output-directory coverage_report
```

### Coverage Targets

| Module | Target | Minimum |
|--------|--------|---------|
| Channel System | 90% | 80% |
| Logic Functions | 95% | 85% |
| Drivers | 85% | 75% |
| Protection | 95% | 90% |

---

## See Also

- [Integration Testing Guide](integration-testing-guide.md)
- [Test Cases](test-cases.md)
- [Logic Functions Reference](../api/logic-functions-reference.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024
