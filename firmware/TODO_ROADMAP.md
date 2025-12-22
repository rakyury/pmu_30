# PMU-30 Firmware TODO Roadmap

**Generated**: 2025-12-21
**Total TODOs Found**: 78
**Status**: Categorized and Prioritized

---

## Priority Legend

- **P0 - CRITICAL**: Blocks basic functionality, requires immediate attention
- **P1 - HIGH**: Important functionality, required for production
- **P2 - MEDIUM**: Desirable functionality, improves system
- **P3 - LOW**: Optimizations and improvements, not critical

---

## Summary by Priority

| Priority | Count | Percentage |
|----------|-------|------------|
| P0 - Critical | 15 | 19% |
| P1 - High | 28 | 36% |
| P2 - Medium | 22 | 28% |
| P3 - Low | 13 | 17% |
| **Total** | **78** | **100%** |

---

## Summary by Category

| Category | Count | Key Items |
|----------|-------|-----------|
| Hardware Integration | 24 | ADC, GPIO, Timers, SPI, FDCAN |
| Lua Scripting | 16 | Library integration, API implementation |
| Flash/Logging | 12 | W25Q512JV driver, session management |
| FreeRTOS | 8 | Kernel integration, scheduler |
| Protection System | 6 | Load shedding, ADC monitoring |
| CAN System | 5 | Motorola byte order, filters |
| Configuration | 4 | Flash persistence |
| Other | 3 | Watchdog, misc |

---

## P0 - CRITICAL (Must Do First)

### 1. FreeRTOS Integration [P0]
**Impact**: Blocks system startup on real hardware
**Files**: `lib/FreeRTOS/*`
**Effort**: 2-4 hours

| File | Line | TODO |
|------|------|------|
| `lib/FreeRTOS/FreeRTOS_stub.c` | 4 | Replace with actual FreeRTOS kernel |
| `lib/FreeRTOS/include/*.h` | 3 | Replace stubs with real headers |
| `platformio.ini` | - | Add FreeRTOS to lib_deps |

**Action Items**:
```ini
# platformio.ini
lib_deps =
    FreeRTOS-Kernel @ ^10.5.1
```

**Estimated Time**: 3 hours

---

### 2. ADC Initialization [P0]
**Impact**: Without ADC, no reading of inputs, voltage, temperature
**Files**: `pmu_adc.c`, `pmu_protection.c`
**Effort**: 3-4 hours

| File | Line | TODO |
|------|------|------|
| `pmu_adc.c` | 83-85 | Initialize ADC1/ADC2/ADC3 with DMA |
| `pmu_adc.c` | 84 | Configure GPIO pins for analog inputs |
| `pmu_adc.c` | 85 | Configure external interrupt for frequency |
| `pmu_adc.c` | 429 | Implement actual ADC reading |
| `pmu_protection.c` | 97 | Initialize ADC for battery voltage |
| `pmu_protection.c` | 315 | Implement actual ADC read |
| `pmu_protection.c` | 342 | Implement STM32H7 temp sensor read |
| `pmu_protection.c` | 372 | Implement board temp sensor |

**Action Items**:
1. Configure ADC1/ADC2/ADC3 peripherals
2. Setup DMA for continuous conversion
3. Implement HAL_ADC_ConvCpltCallback
4. Add voltage divider calculations
5. Calibrate temperature sensors

**Estimated Time**: 4 hours

---

### 3. PROFET PWM Control [P0]
**Impact**: Without PWM, no output control
**Files**: `pmu_profet.c`
**Effort**: 2-3 hours

| File | Line | TODO |
|------|------|------|
| `pmu_profet.c` | 132 | Initialize timers for PWM (TIM1-4 @ 1kHz) |
| `pmu_profet.c` | 133 | Initialize ADC for current sensing |
| `pmu_profet.c` | 134 | Initialize ADC for status/diagnostic |
| `pmu_profet.c` | 263 | Configure timer PWM duty cycle |
| `pmu_profet.c` | 466 | Implement current sense ADC reading |
| `pmu_profet.c` | 479 | Implement status ADC reading |

**Action Items**:
1. Configure TIM1-4 for PWM generation (1kHz)
2. Setup GPIO for PROFET IN pins
3. Configure ADC for IS (current sense)
4. Implement diagnostic feedback

**Estimated Time**: 3 hours

---

### 4. H-Bridge PWM Control [P0]
**Impact**: Blocks motor control
**Files**: `pmu_hbridge.c`
**Effort**: 2-3 hours

| File | Line | TODO |
|------|------|------|
| `pmu_hbridge.c` | 114 | Initialize timers for PWM (TIM5-6 @ 1kHz) |
| `pmu_hbridge.c` | 115 | Initialize ADC for current sensing |
| `pmu_hbridge.c` | 513 | Implement PWM using timers |
| `pmu_hbridge.c` | 568 | Implement current ADC reading |
| `pmu_hbridge.c` | 579 | Implement position ADC reading |

**Action Items**:
1. Configure TIM5-6 for dual H-bridge PWM
2. Setup complementary PWM with dead-time
3. Implement current limiting
4. Add position feedback

**Estimated Time**: 3 hours

---

### 5. CAN FDCAN Initialization [P0]
**Impact**: No CAN communication
**Files**: `pmu_can.c`
**Effort**: 3-4 hours

| File | Line | TODO |
|------|------|------|
| `pmu_can.c` | 79 | Assign FDCAN4 handle if available |
| `pmu_can.c` | 112 | Configure FDCAN peripheral |
| `pmu_can.c` | 172 | Check for received messages (IRQ) |
| `pmu_can.c` | 211 | Transmit message via FDCAN |
| `pmu_can.c` | 508 | Configure FDCAN filter |

**Action Items**:
1. Configure FDCAN1-3 peripherals
2. Setup CAN FD bit timing (1Mbps nominal, 5Mbps data)
3. Implement TX/RX interrupt handlers
4. Configure message filters
5. Add error handling

**Estimated Time**: 4 hours

---

## P1 - HIGH (Important Features)

### 6. Flash Logging Implementation [P1]
**Impact**: Critical functionality for data logging
**Files**: `pmu_logging.c`
**Effort**: 6-8 hours

| File | Line | TODO |
|------|------|------|
| `pmu_logging.c` | 127 | Assign SPI handle for flash |
| `pmu_logging.c` | 147 | Initialize SPI communication W25Q512JV |
| `pmu_logging.c` | 354 | Implement session header |
| `pmu_logging.c` | 470 | Erase entire flash chip |
| `pmu_logging.c` | 492 | Implement session-specific erase |
| `pmu_logging.c` | 505 | Scan flash for session headers |
| `pmu_logging.c` | 525 | Implement session data download |
| `pmu_logging.c` | 535 | Scan flash to count sessions |
| `pmu_logging.c` | 547 | Send Write Enable command |
| `pmu_logging.c` | 557 | Poll status register until ready |
| `pmu_logging.c` | 570 | Implement page program |
| `pmu_logging.c` | 584 | Implement flash read |
| `pmu_logging.c` | 596 | Implement sector erase |

**Action Items**:
1. Implement W25Q512JV SPI driver:
   - `Flash_Init()` - Read JEDEC ID
   - `Flash_WritePage()` - Page program (256 bytes)
   - `Flash_ReadData()` - Fast read command
   - `Flash_EraseSector()` - 4KB sector erase
   - `Flash_EraseChip()` - Chip erase
   - `Flash_WaitReady()` - Poll status register
2. Implement session management:
   - Session header format
   - Session table in flash
   - Session scanning/indexing
3. Implement data download protocol

**Estimated Time**: 8 hours

---

### 7. Lua Library Integration [P1]
**Impact**: Unlocks scripting functionality
**Files**: `pmu_lua.c`, `platformio.ini`
**Effort**: 4-6 hours

| File | Line | TODO |
|------|------|------|
| `pmu_lua.c` | 32 | Include Lua headers |
| `pmu_lua.c` | 98 | Initialize Lua state |
| `pmu_lua.c` | 157 | Register PMU API functions |
| `pmu_lua.c` | 214 | Compile and load script |
| `pmu_lua.c` | 241 | Implement file loading from SD |
| `pmu_lua.c` | 293 | Execute script |
| `pmu_lua.c` | 343 | Execute code directly |
| `pmu_lua.c` | 374 | Garbage collection |
| `pmu_lua.c` | 518 | Register custom function |
| `pmu_lua.c` | 532-643 | Implement all 9 Lua API functions |
| `platformio.ini` | 54 | Add Lua library |

**Action Items**:
1. Add Lua 5.4 to platformio.ini:
```ini
lib_deps =
    Lua @ ^5.4.6
```
2. Uncomment all Lua API calls in pmu_lua.c (~50 locations)
3. Implement custom memory allocator for 128KB pool
4. Test all 9 Lua API functions
5. Test example scripts

**Estimated Time**: 5 hours

---

### 8. Load Shedding Implementation [P1]
**Impact**: Critical for fault recovery
**Files**: `pmu_protection.c`
**Effort**: 2-3 hours

| File | Line | TODO |
|------|------|------|
| `pmu_protection.c` | 298 | Implement intelligent load shedding |

**Action Items**:
1. Define channel priority levels (critical/normal/comfort)
2. Implement priority-based shutdown:
   - Keep: Fuel pump, ECU, ignition
   - Reduce: Lights PWM
   - Disable: Heated seats, aux
3. Add recovery logic
4. Implement gradual restoration

**Code Template**:
```c
static void Protection_HandleLoadShedding(void)
{
    // Define priorities (0=critical, 1=normal, 2=comfort)
    static const uint8_t channel_priority[30] = {
        0, 0, 0, 1, 1, 1, 1, 1, 2, 2, // Channels 0-9
        2, 2, 1, 1, 1, 1, 1, 1, 1, 1, // Channels 10-19
        2, 2, 2, 2, 2, 1, 1, 1, 1, 1  // Channels 20-29
    };

    // Disable comfort features first
    for (uint8_t i = 0; i < 30; i++) {
        if (channel_priority[i] == 2) {
            PMU_PROFET_SetChannel(i, 0, 0);
        }
    }

    // If still overloaded, reduce normal features
    if (protection_state.power.total_current_mA >
        protection_state.power.max_current_mA * 0.9f) {
        for (uint8_t i = 0; i < 30; i++) {
            if (channel_priority[i] == 1) {
                // Reduce PWM to 50%
                PMU_PROFET_Channel_t* ch = PMU_PROFET_GetChannelData(i);
                if (ch && ch->pwm_duty > 50) {
                    PMU_PROFET_SetChannel(i, 1, 50);
                }
            }
        }
    }
}
```

**Estimated Time**: 3 hours

---

### 9. Configuration Persistence [P1]
**Impact**: Saving settings between reboots
**Files**: `pmu_config.c`
**Effort**: 3-4 hours

| File | Line | TODO |
|------|------|------|
| `pmu_config.c` | 22 | Load configuration from flash |
| `pmu_config.c` | 43 | Initialize default output configs |
| `pmu_config.c` | 44 | Initialize default H-bridge configs |
| `pmu_config.c` | 45 | Initialize default input configs |
| `pmu_config.c` | 54 | Save configuration to flash |

**Action Items**:
1. Define flash sector for configuration (64KB)
2. Implement config serialization (binary format)
3. Add CRC32 validation
4. Implement load/save functions
5. Add factory reset

**Estimated Time**: 4 hours

---

### 10. Watchdog Implementation [P1]
**Impact**: System safety and reliability
**Files**: `main.c`
**Effort**: 1 hour

| File | Line | TODO |
|------|------|------|
| `main.c` | 206 | Initialize watchdog before enabling |

**Action Items**:
1. Configure IWDG with 1 second timeout
2. Refresh in control task (1kHz)
3. Add window watchdog for timing verification

**Code**:
```c
// In main():
MX_IWDG_Init();

// In control task:
HAL_IWDG_Refresh(&hiwdg);
```

**Estimated Time**: 1 hour

---

## P2 - MEDIUM (Desirable Features)

### 11. CAN Motorola Byte Order [P2]
**Impact**: Support for big-endian CAN signals
**Files**: `pmu_can.c`
**Effort**: 2 hours

| File | Line | TODO |
|------|------|------|
| `pmu_can.c` | 325 | Implement Motorola byte order extraction |
| `pmu_can.c` | 364 | Set virtual channel to fault/default on timeout |

**Action Items**:
1. Implement Motorola (MSB first) bit extraction
2. Add unit tests for both byte orders
3. Test with real DBC files

**Code Template**:
```c
if (signal->byte_order == 0) {  // Intel (LSB first)
    // Existing code
} else {  // Motorola (MSB first)
    uint8_t start_byte = signal->start_bit / 8;
    uint8_t start_bit_in_byte = 7 - (signal->start_bit % 8);

    // Extract bits in reverse order
    for (uint8_t i = 0; i < signal->length_bits; i++) {
        // Implementation...
    }
}
```

**Estimated Time**: 2 hours

---

### 12. UI System GPIO [P2]
**Impact**: LED and buzzer control
**Files**: `pmu_ui.c`
**Effort**: 2-3 hours

| File | Line | TODO |
|------|------|------|
| `pmu_ui.c` | 115 | Initialize GPIO for LEDs (60 pins) |
| `pmu_ui.c` | 118 | Initialize PWM for buzzer |
| `pmu_ui.c` | 120 | Initialize GPIO for buttons |
| `pmu_ui.c` | 229 | Set GPIO pins for LED |
| `pmu_ui.c` | 402 | Turn off buzzer GPIO/PWM |
| `pmu_ui.c` | 501 | Read GPIO pin for button |

**Action Items**:
1. Configure 60 GPIO for bicolor LEDs (30 channels × 2 colors)
2. Configure PWM for buzzer (TIM channel)
3. Configure 4 GPIO with pull-ups for buttons
4. Implement LED brightness via PWM or current control

**Estimated Time**: 3 hours

---

### 13. Virtual Channel System Enhancement [P2]
**Impact**: Improved virtual channel support
**Files**: `pmu_logic.c`
**Effort**: 2 hours

| File | Line | TODO |
|------|------|------|
| `pmu_logic.c` | 80 | Load logic configuration from flash |
| `pmu_logic.c` | 81 | Initialize predefined virtual channels |
| `pmu_logic.c` | 168 | Read system voltage from ADC |
| `pmu_logic.c` | 173 | Read board temperature |
| `pmu_logic.c` | 178 | Get CAN signal value |

**Action Items**:
1. Link system voltage to ADC
2. Link temperature to ADC
3. Integrate CAN signal mapping
4. Load logic config from flash

**Estimated Time**: 2 hours

---

### 14. Additional H-Bridge Features [P2]
**Files**: `pmu_hbridge.c`
**Effort**: 1 hour

| File | Line | TODO |
|------|------|------|
| `pmu_hbridge.c` | 204 | Add H-bridge current to protection |

**Action Items**:
1. Sum H-bridge currents in protection module
2. Add to total system current calculation

**Estimated Time**: 1 hour

---

## P3 - LOW (Optimizations)

### 15. Documentation TODOs [P3]
**Impact**: Documentation improvements
**Files**: Various markdown files
**Effort**: 1-2 hours

| File | TODO |
|------|------|
| `LUA_INTEGRATION_SUMMARY.md` | Multiple references to completing integration |
| `REFACTORING_SUMMARY.md` | Update with completed work |

**Action Items**:
1. Update all summary documents
2. Add completion status
3. Update roadmap

**Estimated Time**: 1 hour

---

## Implementation Plan

### Phase 1: Core Hardware (Week 1) - P0
**Goal**: Get basic system running on hardware

1. FreeRTOS Integration (3h)
2. ADC Initialization (4h)
3. PROFET PWM Control (3h)
4. H-Bridge PWM Control (3h)
5. CAN FDCAN Init (4h)
6. Watchdog (1h)

**Total**: ~18 hours (3-4 days)

---

### Phase 2: Critical Features (Week 2) - P1
**Goal**: Essential functionality

1. Flash Logging (8h)
2. Lua Integration (5h)
3. Load Shedding (3h)
4. Config Persistence (4h)

**Total**: ~20 hours (4-5 days)

---

### Phase 3: Enhancements (Week 3) - P2
**Goal**: Complete feature set

1. CAN Motorola (2h)
2. UI GPIO (3h)
3. Virtual Channels (2h)
4. Misc improvements (2h)

**Total**: ~9 hours (2 days)

---

### Phase 4: Polish (Week 4) - P3
**Goal**: Final touches

1. Documentation updates (1h)
2. Testing and validation (8h)
3. Performance optimization (4h)

**Total**: ~13 hours (2-3 days)

---

## Tracking Progress

### Status Legend
- Not Started
- In Progress
- Completed
- Blocked
- Cancelled

### Current Status (2025-12-21)

| Phase | Status | Progress |
|-------|--------|----------|
| Phase 1: Core Hardware | Not Started | 0% |
| Phase 2: Critical Features | Not Started | 0% |
| Phase 3: Enhancements | Not Started | 0% |
| Phase 4: Polish | Not Started | 0% |

---

## Dependencies

```
FreeRTOS Integration
    ├─► ADC Init (depends on HAL)
    ├─► Timers Init (depends on HAL)
    └─► CAN Init (depends on HAL)

ADC Init
    ├─► Protection Monitoring
    ├─► Input Processing
    └─► Current Sensing

Timers Init
    ├─► PROFET PWM
    └─► H-Bridge PWM

Flash Driver
    ├─► Logging System
    └─► Config Persistence

Lua Library
    └─► Script Execution
```

---

## Quick Start Guide

### To Begin Phase 1:

1. **Install FreeRTOS**:
```bash
cd firmware
# Add to platformio.ini
lib_deps = FreeRTOS-Kernel @ ^10.5.1
```

2. **Configure STM32CubeMX**:
   - Enable ADC1, ADC2, ADC3 with DMA
   - Configure TIM1-6 for PWM
   - Enable FDCAN1-3
   - Configure GPIO
   - Generate code

3. **Replace stubs**:
   - Copy HAL code to project
   - Remove stub files
   - Update includes

4. **Build and test**:
```bash
python -m platformio run -e pmu30_debug
```

---

## Notes

- Hardware access TODOs can only be completed with actual STM32H743 board
- Some TODOs (Lua, Flash) can be partially implemented in simulator
- Testing requires both unit tests and hardware integration tests
- Estimated times assume familiarity with STM32 HAL and peripherals

---

## Questions for Prioritization

1. **Do you have hardware available?**
   - If YES: Start with Phase 1 immediately
   - If NO: Focus on Lua integration and unit tests

2. **What is the target timeline?**
   - 1 month: Complete all P0 and P1
   - 2 months: Complete all phases
   - 3+ months: Add additional features

3. **What is the primary use case?**
   - Racing: Prioritize CAN and logging
   - Industrial: Prioritize protection and reliability
   - Prototyping: Prioritize Lua scripting

---

**Ready to start?** Let's tackle Phase 1!
