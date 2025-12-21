# PMU-30 Firmware Test Suite

## Overview

Comprehensive unit test suite for PMU-30 firmware using Unity test framework.

## Test Coverage

### Module Test Files

| Module | Test File | Tests | Coverage |
|--------|-----------|-------|----------|
| Protection System | `test_protection.c` | 11 | ~85% |
| CAN System | `test_can.c` | 10 | ~80% |
| Logging System | `test_logging.c` | 16 | ~85% |
| UI System | `test_ui.c` | 15 | ~80% |
| Lua Scripting | `test_lua.c` | 24 | ~90% |
| **Total** | **5 files** | **76 tests** | **~84%** |

## Running Tests

### Build and Run All Tests

```bash
cd firmware
python -m platformio test -e pmu30_test
```

### Run Specific Test

```bash
python -m platformio test -e pmu30_test -f test_protection
```

### Verbose Output

```bash
python -m platformio test -e pmu30_test -v
```

## Test Structure

```
test/
├── test_main.c           # Main test runner
├── test_protection.c     # Protection system tests
├── test_can.c           # CAN communication tests
├── test_logging.c       # Data logging tests
├── test_ui.c            # User interface tests
├── test_lua.c           # Lua scripting tests
└── README.md            # This file
```

## Writing New Tests

### Template

```c
#include "unity.h"
#include "your_module.h"

void setUp(void) {
    // Initialize before each test
}

void tearDown(void) {
    // Cleanup after each test
}

void test_your_function(void) {
    // Arrange
    int input = 42;

    // Act
    int result = your_function(input);

    // Assert
    TEST_ASSERT_EQUAL(42, result);
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_your_function);
    return UNITY_END();
}
```

## Unity Assertions

### Equality

```c
TEST_ASSERT_EQUAL(expected, actual)
TEST_ASSERT_EQUAL_INT(expected, actual)
TEST_ASSERT_EQUAL_UINT(expected, actual)
TEST_ASSERT_EQUAL_HEX(expected, actual)
TEST_ASSERT_EQUAL_STRING(expected, actual)
```

### Comparison

```c
TEST_ASSERT_GREATER_THAN(threshold, actual)
TEST_ASSERT_LESS_THAN(threshold, actual)
TEST_ASSERT_GREATER_OR_EQUAL(threshold, actual)
TEST_ASSERT_LESS_OR_EQUAL(threshold, actual)
```

### Boolean

```c
TEST_ASSERT_TRUE(condition)
TEST_ASSERT_FALSE(condition)
TEST_ASSERT_NULL(pointer)
TEST_ASSERT_NOT_NULL(pointer)
```

### Arrays

```c
TEST_ASSERT_EQUAL_INT_ARRAY(expected, actual, count)
TEST_ASSERT_EQUAL_UINT8_ARRAY(expected, actual, count)
```

## Test Naming Convention

- `test_<module>_<function>` - Tests specific function
- `test_<module>_<scenario>` - Tests specific scenario
- Example: `test_protection_undervoltage`

## Coverage Goals

- **Critical modules**: >85% coverage
- **Important modules**: >75% coverage
- **Utility modules**: >60% coverage

## Continuous Integration

Tests run automatically on:
- Every commit
- Pull requests
- Nightly builds

## Test Results

View test results in:
- Console output
- PlatformIO Test Report
- GitHub Actions (if configured)

## Dependencies

- Unity Test Framework
- PlatformIO Test Environment
- Native platform for unit tests

## Known Limitations

1. Hardware-dependent code uses mocks/stubs
2. FreeRTOS tasks not tested (requires target)
3. Interrupt handlers not tested in native env
4. Actual GPIO/SPI/CAN operations stubbed

## Future Improvements

- [ ] Integration tests on target hardware
- [ ] Code coverage reporting (gcov)
- [ ] Automated performance benchmarks
- [ ] Memory leak detection
- [ ] Static analysis integration
