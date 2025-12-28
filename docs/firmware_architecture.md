# PMU-30 Firmware Architecture

**Document Version:** 2.0
**Date:** 2025-12-29
**Target Platform:** STM32H743/H753
**Owner:** R2 m-sport
**Confidentiality:** Proprietary - Internal Use Only

---

**© 2025 R2 m-sport. All rights reserved.**

---

## 1. Overview

### 1.1 Purpose
This document describes the firmware architecture for the PMU-30 power distribution module, detailing the software structure, task organization, and module interactions.

### 1.2 Development Environment
- **IDE**: VSCode with PlatformIO
- **Framework**: STM32 HAL/LL + FreeRTOS
- **Language**: C (C11 standard)
- **Build System**: PlatformIO (CMake-based)
- **Debugger**: ST-Link V3 or J-Link

### 1.3 Key Requirements
- Real-time operation (RTOS-based)
- Deterministic 1kHz control loop
- Safety-critical protection systems
- Low latency communication
- Robust error handling
- Field-upgradeable (OTA)

---

## 2. System Architecture

### 2.1 Layered Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Application Layer                             │
│   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│   │ Logic   │ │ Lua     │ │ Config  │ │ Logging │ │ UI      │       │
│   │ Engine  │ │ Scripts │ │ Manager │ │ System  │ │ Handler │       │
│   └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘       │
├─────────────────────────────────────────────────────────────────────┤
│                        Channel Abstraction Layer                     │
│   ┌───────────────────────────────────────────────────────────────┐ │
│   │                   PMU Channel Manager                          │ │
│   │  - Unified API for all inputs/outputs                          │ │
│   │  - Physical and virtual channels                               │ │
│   │  - Name-based lookup                                           │ │
│   └───────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│                         Driver Layer                                 │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│   │ PROFET   │ │ H-Bridge │ │ ADC      │ │ CAN      │ │ Protocol │  │
│   │ Driver   │ │ Driver   │ │ Driver   │ │ Driver   │ │ Handler  │  │
│   └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│                      Protection Layer                                │
│   ┌───────────────────────────────────────────────────────────────┐ │
│   │               Protection Manager                               │ │
│   │  - Overcurrent detection                                       │ │
│   │  - Overtemperature monitoring                                  │ │
│   │  - Short circuit protection                                    │ │
│   │  - Voltage monitoring                                          │ │
│   └───────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│                     Hardware Abstraction Layer                       │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│   │ STM32H7  │ │ Timer    │ │ SPI      │ │ UART     │ │ GPIO     │  │
│   │ HAL      │ │ PWM      │ │ Flash    │ │ Debug    │ │ Pins     │  │
│   └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Module Hierarchy

```
firmware/
├── include/                    # Header files
│   ├── main.h                  # Main configuration and constants
│   ├── pmu_types.h             # Common type definitions
│   ├── pmu_config.h            # Configuration structures
│   ├── pmu_channel.h           # Channel abstraction API
│   ├── pmu_profet.h            # PROFET driver API
│   ├── pmu_hbridge.h           # H-Bridge driver API
│   ├── pmu_adc.h               # ADC driver API
│   ├── pmu_can.h               # CAN driver API
│   ├── pmu_logic.h             # Logic engine API
│   ├── pmu_protocol.h          # Communication protocol API
│   ├── pmu_protection.h        # Protection system API
│   └── ...
│
└── src/                        # Source files
    ├── main.c                  # Entry point and RTOS tasks
    ├── pmu_channel.c           # Channel abstraction implementation
    ├── pmu_profet.c            # PROFET driver
    ├── pmu_hbridge.c           # H-Bridge driver
    ├── pmu_adc.c               # ADC driver
    ├── pmu_can.c               # CAN bus driver
    ├── pmu_logic.c             # Logic engine
    ├── pmu_logic_functions.c   # Logic function implementations
    ├── pmu_lua.c               # Lua scripting engine
    ├── pmu_protocol.c          # Communication protocol
    ├── pmu_config_json.c       # JSON configuration parser
    ├── pmu_protection.c        # Protection systems
    ├── pmu_can_stream.c        # Standard CAN stream broadcast
    └── ...
```

---

## 3. FreeRTOS Task Architecture

### 3.1 Task Overview

| Task Name   | Priority | Stack Size | Frequency | Description |
|-------------|----------|------------|-----------|-------------|
| Control     | Highest  | 512 words  | 1000 Hz   | Main control loop, ADC, outputs |
| Protection  | High     | 384 words  | 1000 Hz   | Fault detection and response |
| CAN         | Medium   | 512 words  | 100 Hz    | CAN bus communication |
| Logging     | Low      | 512 words  | 500 Hz    | Data logging to flash |
| UI          | Lowest   | 256 words  | 20 Hz     | LED status, user interface |

### 3.2 Task Definitions (from main.c)

```c
#define TASK_CONTROL_PRIORITY       (configMAX_PRIORITIES - 1)  /* Highest */
#define TASK_PROTECTION_PRIORITY    (configMAX_PRIORITIES - 2)
#define TASK_CAN_PRIORITY           (configMAX_PRIORITIES - 3)
#define TASK_LOGGING_PRIORITY       (tskIDLE_PRIORITY + 1)
#define TASK_UI_PRIORITY            (tskIDLE_PRIORITY + 2)
```

### 3.3 Control Task (1 kHz)

The control task is the heart of the system, running at 1 kHz deterministic rate:

```c
static void vControlTask(void *pvParameters)
{
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = pdMS_TO_TICKS(1);  /* 1ms = 1kHz */
    uint8_t logic_counter = 0;

    for (;;) {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);

        /* Read all analog inputs */
        PMU_ADC_Update();

        /* Update channel abstraction layer */
        PMU_Channel_Update();

        /* Execute logic engine (500Hz, every 2nd cycle) */
        if (++logic_counter >= 2) {
            logic_counter = 0;
            PMU_Logic_Execute();
            PMU_LogicFunctions_Update();
            PMU_Lua_Update();
        }

        /* Update output channels */
        PMU_PROFET_Update();
        PMU_HBridge_Update();

        /* Update protocol handler */
        PMU_Protocol_Update();

        /* Watchdog refresh */
        HAL_IWDG_Refresh(&hiwdg);
    }
}
```

### 3.4 Data Flow Diagram

```
                    ┌────────────────┐
                    │ Physical Inputs│
                    │ (20 Analog +   │
                    │  20 Digital)   │
                    └───────┬────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  PMU_ADC_     │
                    │  Update()     │
                    │  @ 1000 Hz    │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  PMU_Channel_ │
                    │  Update()     │
                    │  @ 1000 Hz    │
                    └───────┬───────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
    ┌───────────────┐ ┌───────────┐ ┌───────────────┐
    │ Logic Engine  │ │ Lua       │ │ CAN RX        │
    │ @ 500 Hz      │ │ Scripts   │ │ Virtual       │
    └───────┬───────┘ │ @ 500 Hz  │ │ Channels      │
            │         └─────┬─────┘ └───────┬───────┘
            │               │               │
            └───────────────┼───────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  Output       │
                    │  Resolution   │
                    └───────┬───────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
    ┌───────────────┐ ┌───────────┐ ┌───────────────┐
    │ PROFET        │ │ H-Bridge  │ │ CAN TX        │
    │ Outputs (30)  │ │ (4 dual)  │ │ Broadcast     │
    └───────────────┘ └───────────┘ └───────────────┘
```

---

## 4. Core Subsystems

### 4.1 Channel Abstraction Layer

The channel system provides a unified interface for all inputs and outputs:

#### Channel ID Ranges

| Range | Type | Description |
|-------|------|-------------|
| 0-99 | Physical Inputs | Analog/Digital input channels |
| 100-199 | Physical Outputs | Power outputs, H-bridges |
| 200-999 | Virtual Channels | Logic, CAN RX/TX, tables, etc. |
| 1000-1023 | System Channels | Battery voltage, temperature, etc. |

#### System Channel IDs

```c
#define PMU_CHANNEL_SYSTEM_BATTERY_V        1000  /* pmuX.battery */
#define PMU_CHANNEL_SYSTEM_TOTAL_I          1001  /* pmuX.totalCurrent */
#define PMU_CHANNEL_SYSTEM_MCU_TEMP         1002  /* MCU temperature */
#define PMU_CHANNEL_SYSTEM_BOARD_TEMP_L     1003  /* pmuX.boardTemperatureL */
#define PMU_CHANNEL_SYSTEM_BOARD_TEMP_R     1004  /* pmuX.boardTemperatureR */
#define PMU_CHANNEL_SYSTEM_BOARD_TEMP_MAX   1005  /* pmuX.boardTemperatureMax */
#define PMU_CHANNEL_SYSTEM_UPTIME           1006  /* System uptime (s) */
#define PMU_CHANNEL_SYSTEM_STATUS           1007  /* pmuX.status */
#define PMU_CHANNEL_CONST_ZERO              1012  /* Constant 0 */
#define PMU_CHANNEL_CONST_ONE               1013  /* Constant 1 */
```

#### Output Sub-Channels

Each output has associated sub-channels (ECUMaster compatible):

```c
/* Use: BASE + output_index (0-29) */
#define PMU_CHANNEL_OUTPUT_STATUS_BASE      1100  /* oY.status (0-7 state) */
#define PMU_CHANNEL_OUTPUT_CURRENT_BASE     1130  /* oY.current (mA) */
#define PMU_CHANNEL_OUTPUT_VOLTAGE_BASE     1160  /* oY.voltage (mV) */
#define PMU_CHANNEL_OUTPUT_ACTIVE_BASE      1190  /* oY.active (bool) */
#define PMU_CHANNEL_OUTPUT_DUTY_BASE        1250  /* oY.dutyCycle (0-1000) */
```

### 4.2 Logic Engine

The logic engine evaluates conditional expressions and controls outputs:

#### Capabilities
- 100 virtual functions with up to 10 operations each
- 256 virtual channels for inputs/outputs/intermediate values
- Execution at 500 Hz (every 2ms)

#### Operations Supported

| Category | Operations |
|----------|------------|
| Logical | AND, OR, NOT, XOR, NAND, NOR |
| Comparison | >, <, ==, !=, >=, <=, IN_RANGE |
| Math | ADD, SUBTRACT, MULTIPLY, DIVIDE, MIN, MAX, ABS, CLAMP |
| Special | EDGE_RISING, EDGE_FALLING, HYSTERESIS, TOGGLE |
| State | SET, RESET, SET_RESET_LATCH, PULSE, FLASH |

### 4.3 PROFET Driver

Controls the 30 high-side power outputs (BTS7008-2EPA):

#### Specifications
- 40A continuous current per channel
- 160A inrush current capability
- PWM frequency: up to 20 kHz
- Current sense via kILIS ratio (4700:1)

#### Output States

```c
typedef enum {
    PMU_PROFET_STATE_OFF = 0,       /* Output disabled */
    PMU_PROFET_STATE_ON,            /* Output on (100%) */
    PMU_PROFET_STATE_FAULT_OC,      /* Overcurrent fault */
    PMU_PROFET_STATE_FAULT_OT,      /* Overtemperature */
    PMU_PROFET_STATE_FAULT_SC,      /* Short circuit */
    PMU_PROFET_STATE_FAULT_OL,      /* Open load */
    PMU_PROFET_STATE_PWM,           /* PWM active */
    PMU_PROFET_STATE_DISABLED       /* Channel disabled */
} PMU_PROFET_State_t;
```

### 4.4 H-Bridge Driver

Controls 4 dual H-bridge motor drivers:

#### Operating Modes

```c
typedef enum {
    PMU_HBRIDGE_MODE_COAST = 0,     /* Hi-Z (coast) */
    PMU_HBRIDGE_MODE_FORWARD,       /* Forward direction */
    PMU_HBRIDGE_MODE_REVERSE,       /* Reverse direction */
    PMU_HBRIDGE_MODE_BRAKE          /* Active brake */
} PMU_HBridge_Mode_t;
```

#### Features
- 30A continuous per bridge
- Position feedback support
- PID control for positioning
- Stall detection
- Park position for wipers

---

## 5. Communication Interfaces

### 5.1 Protocol Handler

The protocol handler manages all host communication:

#### Transport Types

```c
typedef enum {
    PMU_TRANSPORT_WIFI = 0,     /* WiFi via ESP32-C3 */
    PMU_TRANSPORT_UART,         /* Serial UART */
    PMU_TRANSPORT_USB,          /* USB CDC */
    PMU_TRANSPORT_SOCKET        /* Socket (emulator) */
} PMU_TransportType_t;
```

#### Key Protocol Commands

| Command | Code | Description |
|---------|------|-------------|
| GET_CONFIG | 0x20 | Read configuration from device |
| CONFIG_DATA | 0x21 | Configuration data chunk |
| SET_CONFIG | 0x22 | Write configuration to device |
| SAVE_TO_FLASH | 0x24 | Save config to flash |
| SUBSCRIBE_TELEMETRY | 0x30 | Start telemetry stream |
| TELEMETRY_DATA | 0x32 | Telemetry packet |
| SET_CHANNEL | 0x40 | Set channel value |
| RESTART_DEVICE | 0x70 | Restart device |
| BOOT_COMPLETE | 0x72 | Boot complete signal |

### 5.2 Standard CAN Stream

Periodic broadcast of PMU status on CAN bus:

```c
typedef struct {
    bool enabled;
    uint8_t can_bus;        /* CAN bus (1-4) */
    uint32_t base_id;       /* Base CAN ID (default: 0x600) */
    bool is_extended;       /* Use extended IDs */
    bool include_extended;  /* Include PMU-30 specific frames */
} PMU_CanStreamConfig_t;

#define PMU_CAN_STREAM_DEFAULT_BASE_ID  0x600
```

---

## 6. Configuration Management

### 6.1 Configuration Storage

Configuration is stored as JSON in flash memory:

```
┌─────────────────────────────────────────────┐
│              Flash Storage                   │
├─────────────────────────────────────────────┤
│  ┌─────────────────────────────────────┐   │
│  │     last_config.json (~32KB)        │   │
│  │     - All channel configurations    │   │
│  │     - System settings               │   │
│  │     - CAN messages                  │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │     Lua Scripts (128KB)             │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │     Data Logs (remaining)           │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

### 6.2 Channel Types

```c
typedef enum {
    PMU_CHANNEL_TYPE_DIGITAL_INPUT = 0,
    PMU_CHANNEL_TYPE_ANALOG_INPUT,
    PMU_CHANNEL_TYPE_POWER_OUTPUT,
    PMU_CHANNEL_TYPE_CAN_RX,
    PMU_CHANNEL_TYPE_CAN_TX,
    PMU_CHANNEL_TYPE_LIN_RX,
    PMU_CHANNEL_TYPE_LIN_TX,
    PMU_CHANNEL_TYPE_LOGIC,
    PMU_CHANNEL_TYPE_NUMBER,
    PMU_CHANNEL_TYPE_TABLE_2D,
    PMU_CHANNEL_TYPE_TABLE_3D,
    PMU_CHANNEL_TYPE_SWITCH,
    PMU_CHANNEL_TYPE_TIMER,
    PMU_CHANNEL_TYPE_FILTER,
    PMU_CHANNEL_TYPE_LUA_SCRIPT,
    PMU_CHANNEL_TYPE_PID,
    PMU_CHANNEL_TYPE_BLINKMARINE_KEYPAD,
    PMU_CHANNEL_TYPE_HANDLER
} PMU_ChannelType_t;
```

---

## 7. Boot Sequence

### 7.1 Initialization Order

```c
int main(void)
{
    /* 1. MCU initialization */
    MPU_Config();
    CPU_CACHE_Enable();
    HAL_Init();
    SystemClock_Config();  /* 480 MHz */
    GPIO_Init();
    IWDG_Init();           /* ~1 second watchdog */

    /* 2. Storage initialization */
    PMU_Flash_Init();

    /* 3. PMU subsystems initialization */
    PMU_Config_Init();
    PMU_PROFET_Init();
    PMU_HBridge_Init();
    PMU_CAN_Init();
    PMU_ADC_Init();
    PMU_Protection_Init();
    PMU_Channel_Init();
    PMU_LogicFunctions_Init();
    PMU_Logic_Init();
    PMU_Logging_Init();
    PMU_UI_Init();
    PMU_Lua_Init();
    PMU_JSON_Init();
    PMU_Protocol_Init(PMU_TRANSPORT_WIFI);
    PMU_CanStream_Init(&stream_config);

    /* 4. Clear boot counter */
    PMU_Bootloader_GetSharedData()->app_boot_count = 0;

    /* 5. Create FreeRTOS tasks and start scheduler */
    xTaskCreate(vControlTask, "Control", ...);
    xTaskCreate(vProtectionTask, "Protection", ...);
    xTaskCreate(vCANTask, "CAN", ...);
    xTaskCreate(vLoggingTask, "Logging", ...);
    xTaskCreate(vUITask, "UI", ...);

    vTaskStartScheduler();
}
```

### 7.2 Boot Complete Signal

After initialization, the device sends a BOOT_COMPLETE (0x72) message to inform the host that:
- Device has finished booting
- Configuration has been loaded from flash
- All subsystems are ready
- Telemetry can be subscribed

---

## 8. Safety and Fault Handling

### 8.1 Protection System

The protection task runs at 1 kHz monitoring:

| Protection | Threshold | Response |
|------------|-----------|----------|
| Overcurrent | 42A (105% rated) | Immediate shutdown |
| Short circuit | 80A | <1µs shutdown |
| Overtemperature | 145°C | Shutdown with retry |
| Open load | <50mA when on | Warning flag |
| Undervoltage | <6V | Disable outputs |
| Overvoltage | >22V | TVS clamping |

### 8.2 Watchdog

Independent Watchdog (IWDG) configuration:
- Clock: LSI (~32 kHz)
- Prescaler: 32 (1 kHz)
- Reload: 1000 (~1 second timeout)
- Refresh: Every 1ms in control task

```c
hiwdg.Instance = IWDG1;
hiwdg.Init.Prescaler = IWDG_PRESCALER_32;
hiwdg.Init.Reload = 1000;
hiwdg.Init.Window = IWDG_WINDOW_DISABLE;
```

### 8.3 Fault Flags

```c
/* System-wide fault indicators (32-bit bitmask) */
#define FAULT_OVERVOLTAGE       (1 << 0)
#define FAULT_UNDERVOLTAGE      (1 << 1)
#define FAULT_OVERTEMPERATURE   (1 << 2)
#define FAULT_CAN1_ERROR        (1 << 3)
#define FAULT_CAN2_ERROR        (1 << 4)
#define FAULT_FLASH_ERROR       (1 << 5)
#define FAULT_CONFIG_ERROR      (1 << 6)
#define FAULT_WATCHDOG_RESET    (1 << 7)
#define FAULT_LUA_ERROR         (1 << 12)
#define FAULT_LOGIC_ERROR       (1 << 13)
```

---

## 9. Memory Map

### 9.1 STM32H743 Memory Layout

| Region | Start | Size | Usage |
|--------|-------|------|-------|
| Flash | 0x08000000 | 2 MB | Application code |
| ITCM RAM | 0x00000000 | 64 KB | Fast code execution |
| DTCM RAM | 0x20000000 | 128 KB | Fast data |
| AXI SRAM | 0x24000000 | 512 KB | Main heap, stacks |
| SRAM1 | 0x30000000 | 128 KB | DMA buffers |
| Backup SRAM | 0x38800000 | 4 KB | RTC backup data |

### 9.2 External Flash (W25Q512JV)

| Offset | Size | Usage |
|--------|------|-------|
| 0x000000 | 64 KB | Configuration storage |
| 0x010000 | 128 KB | Lua scripts |
| 0x030000 | 512 KB | DBC files |
| 0x0B0000 | ~511 MB | Data logging |

---

## 10. Performance Targets

### 10.1 Timing Requirements

| Metric | Target | Actual |
|--------|--------|--------|
| Control loop jitter | <100 µs | ~50 µs |
| ADC sample to output | <2 ms | ~1.5 ms |
| CAN message latency | <5 ms | ~3 ms |
| Telemetry latency | <10 ms | ~5 ms |
| Logic evaluation | <500 µs | ~200 µs |

### 10.2 Resource Usage

| Resource | Budget | Typical |
|----------|--------|---------|
| CPU Load | <80% | ~60% |
| RAM Usage | <80% | ~65% |
| Flash (code) | <1.5 MB | ~800 KB |
| Stack (Control) | 2 KB | ~1.2 KB |

---

## 11. Emulator Support

The firmware includes an emulator build target for desktop development:

```
firmware/emulator/
├── emu_main.c              # Emulator entry point
├── emu_protocol_server.c   # Socket-based protocol server
├── emu_stubs.c             # HAL stubs for Windows/Linux
├── emu_ui.c                # Console UI
├── emu_flash.c             # File-based flash simulation
└── pmu_emulator.c          # Emulator core
```

Build target: `pmu30_emulator`

---

## 12. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-21 | PMU-30 Team | Initial stub |
| 2.0 | 2025-12-29 | PMU-30 Team | Full architecture documentation |

---

**End of Firmware Architecture Document**
