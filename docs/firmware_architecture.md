# PMU-30 Firmware Architecture

**Document Version:** 4.0
**Date:** 2026-01-01
**Target Platform:** STM32H743/H753
**Owner:** R2 m-sport
**Confidentiality:** Proprietary - Internal Use Only

---

**Note:** This is part of the official PMU-30 documentation. See [docs/README.md](README.md) for the single source of truth.

---

**Copyright 2026 R2 m-sport. All rights reserved.**

---

## Table of Contents

1. [Overview](#1-overview)
2. [System Architecture](#2-system-architecture)
3. [Hardware Abstraction Layer (HAL)](#3-hardware-abstraction-layer-hal)
4. [Boot Sequence](#4-boot-sequence)
5. [FreeRTOS Configuration](#5-freertos-configuration)
6. [Task Architecture](#6-task-architecture)
7. [Main Control Loop](#7-main-control-loop)
8. [Channel Abstraction System](#8-channel-abstraction-system)
9. [Driver Modules](#9-driver-modules)
10. [Protection System](#10-protection-system)
11. [Communication Stack](#11-communication-stack)
12. [Error Handling](#12-error-handling)
13. [Memory Management](#13-memory-management)
14. [Configuration System](#14-configuration-system)
15. [Performance Characteristics](#15-performance-characteristics)
16. [Emulator Architecture](#16-emulator-architecture)
17. [Appendix](#17-appendix)

---

## 1. Overview

### 1.1 Purpose

This document provides comprehensive firmware architecture documentation for the PMU-30 Power Distribution Module, covering all aspects from hardware abstraction to high-level application logic.

### 1.2 Development Environment

| Component | Specification |
|-----------|---------------|
| **IDE** | VSCode with PlatformIO |
| **Framework** | STM32 HAL/LL + FreeRTOS v10.5.1 |
| **Language** | C (C11 standard) |
| **Compiler** | ARM GCC 12.x |
| **Build System** | PlatformIO (CMake-based) |
| **Debugger** | ST-Link V3 or J-Link |
| **Flash Tool** | STM32CubeProgrammer |

### 1.3 Design Principles

- **Deterministic real-time operation** - 1kHz control loop with guaranteed timing
- **Safety-critical design** - Multi-layer protection with hardware watchdog
- **Modularity** - Clean separation between HAL, drivers, and application
- **Extensibility** - Lua scripting for custom logic
- **Reliability** - Fault tolerance with auto-recovery

### 1.4 Key Specifications

| Feature | Specification |
|---------|---------------|
| Control Loop | 1000 Hz (1ms period) |
| Logic Engine | 500 Hz (2ms period) |
| Total Channels | 1024 (physical + virtual) |
| Max Logic Functions | 100 (10 operations each) |
| Lua Scripts | Up to 16 concurrent |
| Watchdog Timeout | 1 second |
| Telemetry Rate | 1-1000 Hz configurable |

---

## 2. System Architecture

### 2.1 Layered Architecture Diagram

```
+=========================================================================+
|                          APPLICATION LAYER                               |
+-------------------------------------------------------------------------+
|  +-----------+ +-----------+ +-----------+ +-----------+ +-----------+  |
|  |  Logic    | |    Lua    | |  Config   | | Logging   | |    UI     |  |
|  |  Engine   | |  Scripts  | |  Manager  | |  System   | |  Handler  |  |
|  | (500 Hz)  | | (500 Hz)  | |           | | (500 Hz)  | | (20 Hz)   |  |
|  +-----------+ +-----------+ +-----------+ +-----------+ +-----------+  |
+=========================================================================+
|                     CHANNEL ABSTRACTION LAYER                            |
+-------------------------------------------------------------------------+
|  +-------------------------------------------------------------------+  |
|  |                      PMU Channel Manager                           |  |
|  |  - 1024 channel slots (physical + virtual)                        |  |
|  |  - Name-based and ID-based lookup                                 |  |
|  |  - Value caching with 1kHz update                                 |  |
|  |  - Type conversion and scaling                                    |  |
|  +-------------------------------------------------------------------+  |
+=========================================================================+
|                          DRIVER LAYER                                    |
+-------------------------------------------------------------------------+
|  +----------+ +----------+ +----------+ +----------+ +----------+       |
|  | PROFET   | | H-Bridge | |   ADC    | |   CAN    | | Protocol |       |
|  | Driver   | |  Driver  | |  Driver  | |  Driver  | | Handler  |       |
|  | (30 ch)  | | (4 dual) | | (20 ch)  | | (4 bus)  | | (WiFi)   |       |
|  +----------+ +----------+ +----------+ +----------+ +----------+       |
|  +----------+ +----------+ +----------+ +----------+ +----------+       |
|  |   LIN    | |   SPI    | | External | |   Lua    | |  CAN     |       |
|  |  Driver  | |  Flash   | |   RTC    | |    VM    | | Stream   |       |
|  +----------+ +----------+ +----------+ +----------+ +----------+       |
+=========================================================================+
|                       ESP32 BRIDGE LAYER                                 |
+-------------------------------------------------------------------------+
|  +-------------------------------------------------------------------+  |
|  |                    ESP32-C3 Communication Bridge                   |  |
|  |  - UART3 @ 115200 baud with 512-byte ring buffer                  |  |
|  |  - AT command protocol (send/receive with timeout)                |  |
|  |  - Async callbacks for notifications (WiFi, BLE events)           |  |
|  |  - Hardware reset via GPIO (PD0=EN, PD1=IO0)                      |  |
|  +-------------------------------------------------------------------+  |
|  +------------------------+ +------------------------+                   |
|  |      WiFi Driver       | |    Bluetooth Driver    |                   |
|  |  - AP+STA mode         | |  - BLE GATT server     |                   |
|  |  - AT+CWSAP/CWJAP      | |  - AT+BLEINIT/BLEADV   |                   |
|  |  - TCP server          | |  - Characteristic TX   |                   |
|  +------------------------+ +------------------------+                   |
+=========================================================================+
|                       PROTECTION LAYER                                   |
+-------------------------------------------------------------------------+
|  +-------------------------------------------------------------------+  |
|  |                     Protection Manager                             |  |
|  |  - Overcurrent detection (per-channel and total)                  |  |
|  |  - Overtemperature monitoring (3 sensors + MCU die)               |  |
|  |  - Short circuit protection (<1us response)                       |  |
|  |  - Voltage monitoring (6-22V range)                               |  |
|  |  - Reverse polarity protection                                    |  |
|  |  - Load shedding under fault conditions                           |  |
|  +-------------------------------------------------------------------+  |
+=========================================================================+
|                    HARDWARE ABSTRACTION LAYER                            |
+-------------------------------------------------------------------------+
|  +----------+ +----------+ +----------+ +----------+ +----------+       |
|  | STM32H7  | |  Timer   | |   SPI    | |   UART   | |   GPIO   |       |
|  |   HAL    | |   PWM    | |  Flash   | |  Debug   | |   Pins   |       |
|  +----------+ +----------+ +----------+ +----------+ +----------+       |
|  +----------+ +----------+ +----------+ +----------+ +----------+       |
|  |   ADC    | |  FDCAN   | |   I2C    | |   DMA    | |   MPU    |       |
|  |  (3 mod) | | (4 bus)  | | (IMU)    | | (async)  | | (cache)  |       |
|  +----------+ +----------+ +----------+ +----------+ +----------+       |
+=========================================================================+
|                         HARDWARE LAYER                                   |
+-------------------------------------------------------------------------+
|  STM32H743VIT6 (480 MHz Cortex-M7) | W25Q512JV (64MB Flash)            |
|  BTS7012-2EPA (15x dual PROFET)    | BTN8982TA (8x half-bridge)        |
|  TJA1463 (CAN FD)                  | ESP32-C3-MINI-1 (WiFi/BT)         |
+=========================================================================+
```

### 2.2 Source File Organization

```
firmware/
├── include/                         # Header files (35 files)
│   ├── main.h                       # System configuration, defines
│   ├── pmu_types.h                  # Common type definitions
│   ├── pmu_config.h                 # Configuration structures (679 lines)
│   ├── pmu_channel.h                # Channel abstraction API
│   ├── pmu_profet.h                 # PROFET driver API
│   ├── pmu_hbridge.h                # H-Bridge driver API
│   ├── pmu_adc.h                    # ADC driver API
│   ├── pmu_can.h                    # CAN driver API
│   ├── pmu_protocol.h               # Communication protocol API
│   ├── pmu_protection.h             # Protection system API
│   ├── pmu_logic.h                  # Logic engine API
│   ├── pmu_logic_functions.h        # Logic function implementations
│   ├── pmu_lua.h                    # Lua scripting API
│   ├── pmu_can_stream.h             # Standard CAN stream API
│   ├── pmu_bootloader.h             # Bootloader interface
│   ├── pmu_flash.h                  # External flash API
│   ├── pmu_pid.h                    # PID controller API
│   ├── pmu_esp32.h                  # ESP32-C3 bridge API (220 lines)
│   ├── pmu_wifi.h                   # WiFi driver API
│   ├── pmu_bluetooth.h              # Bluetooth/BLE driver API
│   └── ...
│
├── src/                             # Source files (32 files)
│   ├── main.c (564 lines)           # Entry point, RTOS tasks
│   ├── pmu_protocol.c (1271 lines)  # Protocol handler
│   ├── pmu_config_json.c (4372 lines) # JSON configuration
│   ├── pmu_can.c (1192 lines)       # CAN bus driver
│   ├── pmu_profet.c (890 lines)     # PROFET outputs
│   ├── pmu_adc.c (790 lines)        # ADC inputs
│   ├── pmu_channel.c (889 lines)    # Channel abstraction
│   ├── pmu_hbridge.c (~24KB)        # H-Bridge control
│   ├── pmu_protection.c (19KB)      # Protection systems
│   ├── pmu_logic.c (16KB)           # Logic engine
│   ├── pmu_logic_functions.c        # Logic implementations
│   ├── pmu_lua.c (18KB)             # Lua VM integration
│   ├── pmu_lua_api.c (1102 lines)   # Lua hardware API
│   ├── pmu_logging.c (22KB)         # Data logging
│   ├── pmu_can_stream.c (930 lines) # CAN stream broadcast
│   ├── pmu_bootloader.c (955 lines) # Bootloader interface
│   ├── pmu_pid.c                    # PID controllers
│   ├── pmu_esp32.c (450 lines)      # ESP32 bridge (AT commands)
│   ├── pmu_wifi.c                   # WiFi via ESP32 AT commands
│   ├── pmu_bluetooth.c              # Bluetooth via ESP32 AT commands
│   └── ...
│
├── lib/FreeRTOS/                    # FreeRTOS v10.5.1 kernel
│   ├── FreeRTOSConfig.h             # RTOS configuration
│   ├── tasks.c                      # Task management
│   ├── queue.c                      # Queue management
│   ├── semphr.c                     # Semaphores
│   └── ...
│
├── emulator/                        # Hardware emulator
│   ├── emu_main.c (1023 lines)      # Emulator entry point
│   ├── pmu_emulator.c (2643 lines)  # Emulator core
│   ├── emu_protocol_server.c        # Socket-based server
│   ├── emu_stubs.c                  # HAL stubs
│   └── ...
│
└── platformio.ini                   # Build configuration
```

---

## 3. Hardware Abstraction Layer (HAL)

### 3.1 MCU Overview

| Parameter | Value |
|-----------|-------|
| **Part Number** | STM32H743VIT6 / STM32H753VIT6 |
| **Core** | ARM Cortex-M7 @ 480 MHz |
| **Flash** | 2 MB internal |
| **RAM** | 1 MB total (multiple regions) |
| **FPU** | Single and double precision |
| **Cache** | 16 KB I-Cache, 16 KB D-Cache |
| **Package** | LQFP100 |

### 3.2 Clock Tree Configuration

```
                          +-------------------+
                          |   HSE (25 MHz)    |
                          |   Crystal Osc     |
                          +---------+---------+
                                    |
                          +---------v---------+
                          |       PLL1        |
                          |  M=5, N=192, P=2  |
                          |  VCO = 960 MHz    |
                          +---------+---------+
                                    |
                          +---------v---------+
                          |  SYSCLK (480 MHz) |
                          +---------+---------+
                                    |
          +-------------------------+-------------------------+
          |                         |                         |
+---------v---------+     +---------v---------+     +---------v---------+
|   AHB (240 MHz)   |     |   APB1 (120 MHz)  |     |   APB2 (120 MHz)  |
|   /2 prescaler    |     |   /2 prescaler    |     |   /2 prescaler    |
+-------------------+     +-------------------+     +-------------------+
          |                         |                         |
    +-----+-----+             +-----+-----+             +-----+-----+
    |           |             |           |             |           |
  Flash       SRAM         UART1-5     SPI2-3       ADC1-3      TIM1
  (4 WS)                   I2C1-3      TIM2-7       FDCAN       TIM8
                           TIM12-14                 USART6      SPI1
```

**Clock Configuration Code (SystemClock_Config):**
```c
/* PLL Configuration */
RCC_OscInitStruct.PLL.PLLM = 5;       /* 25 MHz / 5 = 5 MHz */
RCC_OscInitStruct.PLL.PLLN = 192;     /* 5 MHz * 192 = 960 MHz VCO */
RCC_OscInitStruct.PLL.PLLP = 2;       /* 960 MHz / 2 = 480 MHz SYSCLK */
RCC_OscInitStruct.PLL.PLLQ = 4;       /* 960 MHz / 4 = 240 MHz (USB, etc) */
RCC_OscInitStruct.PLL.PLLR = 2;       /* 960 MHz / 2 = 480 MHz */

/* Bus Prescalers */
RCC_ClkInitStruct.AHBCLKDivider = RCC_HCLK_DIV2;    /* 240 MHz */
RCC_ClkInitStruct.APB1CLKDivider = RCC_APB1_DIV2;   /* 120 MHz */
RCC_ClkInitStruct.APB2CLKDivider = RCC_APB2_DIV2;   /* 120 MHz */
```

### 3.3 Memory Protection Unit (MPU)

The MPU is configured to optimize cache behavior for critical memory regions:

```c
static void MPU_Config(void)
{
    MPU_Region_InitTypeDef MPU_InitStruct;

    HAL_MPU_Disable();

    /* Region 0: AXI SRAM (0x24000000, 512 KB) */
    MPU_InitStruct.Enable = MPU_REGION_ENABLE;
    MPU_InitStruct.BaseAddress = 0x24000000;
    MPU_InitStruct.Size = MPU_REGION_SIZE_512KB;
    MPU_InitStruct.AccessPermission = MPU_REGION_FULL_ACCESS;
    MPU_InitStruct.IsBufferable = MPU_ACCESS_NOT_BUFFERABLE;
    MPU_InitStruct.IsCacheable = MPU_ACCESS_CACHEABLE;
    MPU_InitStruct.IsShareable = MPU_ACCESS_NOT_SHAREABLE;
    MPU_InitStruct.Number = MPU_REGION_NUMBER0;
    MPU_InitStruct.TypeExtField = MPU_TEX_LEVEL0;
    MPU_InitStruct.SubRegionDisable = 0x00;
    MPU_InitStruct.DisableExec = MPU_INSTRUCTION_ACCESS_ENABLE;

    HAL_MPU_ConfigRegion(&MPU_InitStruct);
    HAL_MPU_Enable(MPU_PRIVILEGED_DEFAULT);
}
```

### 3.4 Cache Configuration

```c
static void CPU_CACHE_Enable(void)
{
    /* Enable I-Cache (16 KB) */
    SCB_EnableICache();

    /* Enable D-Cache (16 KB) */
    SCB_EnableDCache();
}
```

**Cache Considerations:**
- D-Cache must be cleaned/invalidated for DMA operations
- Critical real-time data placed in non-cacheable regions (DTCM)
- `SCB_CleanDCache_by_Addr()` used before DMA TX
- `SCB_InvalidateDCache_by_Addr()` used after DMA RX

### 3.5 Peripheral Mapping

| Peripheral | Function | Configuration |
|------------|----------|---------------|
| **ADC1** | Analog inputs 1-8 | 12-bit, 1 MSPS |
| **ADC2** | Analog inputs 9-16 | 12-bit, 1 MSPS |
| **ADC3** | Analog inputs 17-20 + internal | 12-bit, 1 MSPS |
| **TIM1** | PROFET PWM (channels 1-8) | 20 kHz, center-aligned |
| **TIM2** | PROFET PWM (channels 9-16) | 20 kHz, center-aligned |
| **TIM3** | PROFET PWM (channels 17-24) | 20 kHz, center-aligned |
| **TIM4** | PROFET PWM (channels 25-30) | 20 kHz, center-aligned |
| **TIM8** | H-Bridge PWM (4 channels) | 20 kHz, center-aligned |
| **FDCAN1** | CAN bus 1 (CAN FD) | 1 Mbps / 5 Mbps |
| **FDCAN2** | CAN bus 2 (CAN FD) | 1 Mbps / 5 Mbps |
| **CAN3** | CAN bus 3 (CAN 2.0) | 1 Mbps |
| **CAN4** | CAN bus 4 (CAN 2.0) | 1 Mbps |
| **USART1** | USB Debug / Console | 115200 baud |
| **USART2** | LIN bus (via TJA1020) | 19200 baud |
| **USART3** | ESP32-C3 WiFi/BT module | 115200 baud (AT commands) |
| **SPI1** | External flash (W25Q512JV) | 50 MHz |
| **I2C1** | IMU (LSM6DSO32X) | 400 kHz |
| **IWDG1** | Independent Watchdog | 1 second timeout |

### 3.6 GPIO Pin Allocation

| Port | Pins | Function |
|------|------|----------|
| **GPIOA** | PA0-PA7 | ADC inputs 1-8 |
| **GPIOB** | PB0-PB7 | Digital inputs 1-8 |
| **GPIOC** | PC0-PC5 | ADC inputs 9-14 |
| **GPIOD** | PD0-PD1 | ESP32 control (PD0=EN, PD1=IO0) |
| **GPIOD** | PD2-PD7 | PROFET control (DEN, IN, IS) |
| **GPIOE** | PE0-PE15 | PROFET PWM outputs |
| **GPIOF** | PF0-PF7 | H-Bridge control |
| **GPIOG** | PG0-PG7 | CAN transceivers, LEDs |
| **GPIOH** | PH0-PH1 | HSE crystal |

### 3.7 Interrupt Priority Configuration

FreeRTOS requires specific interrupt priority configuration:

| Priority | Interrupts | Description |
|----------|------------|-------------|
| 0-3 | Reserved | Higher than FreeRTOS (cannot use RTOS API) |
| 4 | FDCAN1_IT0, FDCAN2_IT0 | CAN RX/TX (edge cases) |
| 5 | SysTick, PendSV | FreeRTOS kernel (configKERNEL_INTERRUPT_PRIORITY) |
| 6 | ADC_IRQ, DMA_IRQ | Data acquisition |
| 7-15 | USART, TIM | Lower priority peripherals |

```c
/* FreeRTOS interrupt priorities */
#define configLIBRARY_LOWEST_INTERRUPT_PRIORITY      15
#define configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY  5
```

### 3.8 DMA Configuration

| DMA Stream | Peripheral | Direction | Purpose |
|------------|------------|-----------|---------|
| DMA1_Stream0 | ADC1 | P->M | Analog input sampling |
| DMA1_Stream1 | ADC2 | P->M | Analog input sampling |
| DMA1_Stream2 | ADC3 | P->M | Analog input sampling |
| DMA1_Stream3 | SPI1_TX | M->P | Flash write |
| DMA1_Stream4 | SPI1_RX | P->M | Flash read |
| DMA2_Stream0 | USART1_TX | M->P | WiFi TX |
| DMA2_Stream1 | USART1_RX | P->M | WiFi RX (circular) |

---

## 4. Boot Sequence

### 4.1 Power-On Sequence Diagram

```
+===========================================================================+
|                            POWER ON RESET                                  |
+===========================================================================+
                                    |
                                    v
+===========================================================================+
|                         BOOTLOADER (128 KB)                                |
|  @ 0x08000000                                                              |
|  - Checks for firmware update request                                      |
|  - Validates application CRC                                               |
|  - Jumps to application if valid                                           |
+===========================================================================+
                                    |
                                    v
+===========================================================================+
|                    APPLICATION START (main.c)                              |
|  @ 0x08020000                                                              |
+===========================================================================+
          |
          v
    +-----------+
    | MPU_Config|  Configure Memory Protection Unit
    +-----------+
          |
          v
+-------------------+
| CPU_CACHE_Enable  |  Enable I-Cache and D-Cache
+-------------------+
          |
          v
    +-----------+
    | HAL_Init  |  Reset peripherals, init Flash interface, SysTick
    +-----------+
          |
          v
+---------------------+
| SystemClock_Config  |  Configure PLL to 480 MHz
+---------------------+
          |
          v
    +------------+
    | GPIO_Init  |  Enable all GPIO port clocks
    +------------+
          |
          v
    +------------+
    | IWDG_Init  |  Start Independent Watchdog (~1 sec timeout)
    +------------+
          |
          v
+===========================================================================+
|                      PMU SUBSYSTEM INITIALIZATION                          |
+===========================================================================+
          |
          v
+------------------+
| PMU_Flash_Init   |  External SPI flash (W25Q512JV - 64MB)
+------------------+
          |
          v
+------------------+
| PMU_Config_Init  |  Load configuration from flash (or defaults)
+------------------+
          |
          v
+------------------+     +------------------+
| PMU_PROFET_Init  | --> | PMU_HBridge_Init |  Initialize power outputs
+------------------+     +------------------+
          |
          v
+------------------+     +------------------+
| PMU_CAN_Init     | --> | PMU_ADC_Init     |  Initialize comm + inputs
+------------------+     +------------------+
          |
          v
+----------------------+
| PMU_Protection_Init  |  Start voltage/temp monitoring
+----------------------+
          |
          v
+------------------+
| PMU_Channel_Init |  Initialize universal channel abstraction
+------------------+
          |
          v
+--------------------------+     +----------------+
| PMU_LogicFunctions_Init  | --> | PMU_Logic_Init |  Logic engine
+--------------------------+     +----------------+
          |
          v
+-------------------+     +--------------+
| PMU_Logging_Init  | --> | PMU_UI_Init  |  Data logging + UI
+-------------------+     +--------------+
          |
          v
+---------------+     +---------------+
| PMU_Lua_Init  | --> | PMU_JSON_Init |  Scripting + JSON parser
+---------------+     +---------------+
          |
          v
+------------------------------------+
| PMU_Protocol_Init(PMU_TRANSPORT_WIFI) |  Communication protocol
+------------------------------------+
          |
          v
+---------------------+
| PMU_CanStream_Init  |  Standard CAN stream (disabled by default)
+---------------------+
          |
          v
+===========================================================================+
|                    BOOTLOADER HANDSHAKE                                    |
|  Clear boot attempt counter (prevents rollback)                            |
+===========================================================================+
          |
          v
+===========================================================================+
|                    FREERTOS TASK CREATION                                  |
|  Create 5 tasks:                                                           |
|  - vControlTask (1 kHz, highest priority)                                  |
|  - vProtectionTask (1 kHz, high priority)                                  |
|  - vCANTask (100 Hz, medium priority)                                      |
|  - vLoggingTask (500 Hz, low priority)                                     |
|  - vUITask (20 Hz, lowest priority)                                        |
+===========================================================================+
          |
          v
+===========================================================================+
|                    vTaskStartScheduler()                                   |
|  FreeRTOS takes control - application runs in tasks                        |
+===========================================================================+
```

### 4.2 Initialization Order Dependencies

The initialization order is critical. Dependencies are:

```
PMU_Flash_Init()
    └── PMU_Config_Init()
            ├── PMU_PROFET_Init()     (loads output configs)
            ├── PMU_HBridge_Init()    (loads H-bridge configs)
            ├── PMU_CAN_Init()        (loads CAN configs)
            └── PMU_ADC_Init()        (loads input configs)
                    │
PMU_Protection_Init() ←─────────────┘ (uses ADC for temp sensors)
    │
    └── PMU_Channel_Init()            (registers physical channels)
            │
            ├── PMU_LogicFunctions_Init()  (depends on channels)
            │       └── PMU_Logic_Init()    (depends on functions)
            │
            ├── PMU_Logging_Init()     (logs channel values)
            │
            └── PMU_Lua_Init()         (accesses channels via API)
                    │
                    └── PMU_Protocol_Init()  (queries all modules)
                            └── PMU_CanStream_Init() (depends on channels)
```

### 4.3 Initialization Code (from main.c)

```c
int main(void)
{
    /* 1. MCU initialization (order critical!) */
    MPU_Config();
    CPU_CACHE_Enable();
    HAL_Init();
    SystemClock_Config();  /* 480 MHz */
    GPIO_Init();
    IWDG_Init();           /* ~1 second watchdog */

    /* 2. Storage initialization */
    PMU_Flash_Init();

    /* 3. PMU subsystems initialization (order matters!) */
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

    /* 4. Standard CAN Stream (disabled by default) */
    {
        PMU_CanStreamConfig_t stream_config = {
            .enabled = false,
            .can_bus = 1,
            .base_id = 0x600,
            .is_extended = false,
            .include_extended = true
        };
        PMU_CanStream_Init(&stream_config);
    }

    /* 5. Clear bootloader boot counter (successful boot) */
    PMU_Boot_SharedData_t* boot_data = PMU_Bootloader_GetSharedData();
    if (boot_data != NULL) {
        boot_data->app_boot_count = 0;
    }

    /* 6. Create FreeRTOS tasks */
    xTaskCreate(vControlTask, "Control", 512, NULL,
                configMAX_PRIORITIES - 1, &xControlTaskHandle);
    xTaskCreate(vProtectionTask, "Protection", 384, NULL,
                configMAX_PRIORITIES - 2, &xProtectionTaskHandle);
    xTaskCreate(vCANTask, "CAN", 512, NULL,
                configMAX_PRIORITIES - 3, &xCANTaskHandle);
    xTaskCreate(vLoggingTask, "Logging", 512, NULL,
                tskIDLE_PRIORITY + 1, &xLoggingTaskHandle);
    xTaskCreate(vUITask, "UI", 256, NULL,
                tskIDLE_PRIORITY + 2, &xUITaskHandle);

    /* 7. Start scheduler (never returns) */
    vTaskStartScheduler();

    /* Should never reach here */
    while (1) {
        Error_Handler();
    }
}
```

### 4.4 Boot Complete Signal

After all initialization completes, the device sends a `BOOT_COMPLETE` (0x72) message to inform connected hosts that:
- Device has finished booting
- Configuration has been loaded from flash
- All subsystems are operational
- Telemetry subscription is available

---

## 5. FreeRTOS Configuration

### 5.1 RTOS Version and Settings

| Parameter | Value |
|-----------|-------|
| **FreeRTOS Version** | 10.5.1 |
| **Tick Rate** | 1000 Hz (1 ms) |
| **Max Priorities** | 7 |
| **Heap Size** | 64 KB |
| **Stack Overflow Detection** | Enabled |
| **Preemption** | Enabled |

### 5.2 FreeRTOSConfig.h Key Settings

```c
#define configUSE_PREEMPTION                    1
#define configUSE_IDLE_HOOK                     0
#define configUSE_TICK_HOOK                     0
#define configCPU_CLOCK_HZ                      (480000000UL)
#define configTICK_RATE_HZ                      (1000)
#define configMAX_PRIORITIES                    (7)
#define configMINIMAL_STACK_SIZE                (128)
#define configTOTAL_HEAP_SIZE                   (64 * 1024)
#define configMAX_TASK_NAME_LEN                 (16)
#define configUSE_16_BIT_TICKS                  0
#define configIDLE_SHOULD_YIELD                 1
#define configUSE_MUTEXES                       1
#define configUSE_RECURSIVE_MUTEXES             1
#define configUSE_COUNTING_SEMAPHORES           1
#define configQUEUE_REGISTRY_SIZE               8
#define configUSE_QUEUE_SETS                    1
#define configCHECK_FOR_STACK_OVERFLOW          2
#define configUSE_TRACE_FACILITY                1
#define configUSE_STATS_FORMATTING_FUNCTIONS    1

/* Cortex-M7 specific */
#define configPRIO_BITS                         4
#define configLIBRARY_LOWEST_INTERRUPT_PRIORITY 15
#define configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY 5
#define configKERNEL_INTERRUPT_PRIORITY         (configLIBRARY_LOWEST_INTERRUPT_PRIORITY << (8 - configPRIO_BITS))
#define configMAX_SYSCALL_INTERRUPT_PRIORITY    (configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY << (8 - configPRIO_BITS))
```

### 5.3 Heap Implementation

FreeRTOS heap_4.c is used for dynamic memory allocation:
- Supports `pvPortMalloc()` and `vPortFree()`
- Memory fragmentation handling
- Thread-safe allocation

---

## 6. Task Architecture

### 6.1 Task Overview

| Task | Priority | Stack (words) | Period | Rate | Function |
|------|----------|---------------|--------|------|----------|
| **Control** | MAX-1 | 512 | 1 ms | 1000 Hz | Main control loop |
| **Protection** | MAX-2 | 384 | 1 ms | 1000 Hz | Fault detection |
| **CAN** | MAX-3 | 512 | 10 ms | ~100 Hz | CAN communication |
| **Logging** | IDLE+1 | 512 | 2 ms | 500 Hz | Data logging |
| **UI** | IDLE+2 | 256 | 50 ms | 20 Hz | Status LEDs |

### 6.2 Task Priority Levels

```c
#define TASK_CONTROL_PRIORITY       (configMAX_PRIORITIES - 1)  /* 6 - Highest */
#define TASK_PROTECTION_PRIORITY    (configMAX_PRIORITIES - 2)  /* 5 */
#define TASK_CAN_PRIORITY           (configMAX_PRIORITIES - 3)  /* 4 */
#define TASK_LOGGING_PRIORITY       (tskIDLE_PRIORITY + 1)      /* 1 */
#define TASK_UI_PRIORITY            (tskIDLE_PRIORITY + 2)      /* 2 */
```

### 6.3 Task Timing Diagram

```
Time (ms)  0    1    2    3    4    5    6    7    8    9   10   ...
           |    |    |    |    |    |    |    |    |    |    |
Control    ████ ████ ████ ████ ████ ████ ████ ████ ████ ████ ████
           (runs every 1ms, preempts all others)

Protection  ▓▓   ▓▓   ▓▓   ▓▓   ▓▓   ▓▓   ▓▓   ▓▓   ▓▓   ▓▓   ▓▓
           (runs every 1ms, after Control)

Logging         ░░        ░░        ░░        ░░        ░░
               (runs every 2ms)

CAN                                                          ▒▒▒▒
                                                      (every 10ms)

UI                                                               (every 50ms)

████ = Control task (highest priority)
▓▓   = Protection task (high priority)
░░   = Logging task (low priority)
▒▒   = CAN task (medium priority)
```

### 6.4 Task Stack Sizes

| Task | Stack (words) | Stack (bytes) | Usage Estimate |
|------|---------------|---------------|----------------|
| Control | 512 | 2048 | ~1200 bytes (60%) |
| Protection | 384 | 1536 | ~900 bytes (60%) |
| CAN | 512 | 2048 | ~1100 bytes (55%) |
| Logging | 512 | 2048 | ~1000 bytes (50%) |
| UI | 256 | 1024 | ~600 bytes (60%) |

---

## 7. Main Control Loop

### 7.1 Control Task Implementation

The Control Task is the heart of the system, running at 1 kHz with deterministic timing:

```c
static void vControlTask(void *pvParameters)
{
    TickType_t xLastWakeTime;
    const TickType_t xFrequency = pdMS_TO_TICKS(1);  /* 1 ms = 1 kHz */
    uint8_t logic_counter = 0;

    (void)pvParameters;

    /* Initialize with current time for accurate timing */
    xLastWakeTime = xTaskGetTickCount();

    for (;;)
    {
        /* CRITICAL: Use vTaskDelayUntil for deterministic timing */
        vTaskDelayUntil(&xLastWakeTime, xFrequency);

        /* ============================================
         * Phase 1: INPUT ACQUISITION (every 1ms)
         * ============================================ */

        /* Read all 20 analog inputs via DMA */
        PMU_ADC_Update();

        /* Sync physical channels to channel registry */
        PMU_Channel_Update();

        /* ============================================
         * Phase 2: LOGIC PROCESSING (every 2ms = 500 Hz)
         * ============================================ */

        if (++logic_counter >= 2) {
            logic_counter = 0;

            /* Execute logic state machines */
            PMU_Logic_Execute();

            /* Update all logic functions (numbers, tables, etc.) */
            PMU_LogicFunctions_Update();

            /* Run Lua scripts */
            PMU_Lua_Update();
        }

        /* ============================================
         * Phase 3: OUTPUT UPDATE (every 1ms)
         * ============================================ */

        /* Update 30 PROFET outputs (PWM, states) */
        PMU_PROFET_Update();

        /* Update 4 H-bridge outputs */
        PMU_HBridge_Update();

        /* ============================================
         * Phase 4: COMMUNICATION (every 1ms)
         * ============================================ */

        /* Process protocol commands and telemetry streaming */
        PMU_Protocol_Update();

        /* ============================================
         * Phase 5: WATCHDOG (every 1ms)
         * ============================================ */

#ifndef UNIT_TEST
        /* Refresh watchdog - prevents system reset */
        HAL_IWDG_Refresh(&hiwdg);
#endif
    }
}
```

### 7.2 Control Loop Timing Budget

| Phase | Max Time | Typical Time | Function |
|-------|----------|--------------|----------|
| ADC Update | 100 us | 50 us | Read 20 analog inputs |
| Channel Update | 50 us | 30 us | Sync physical channels |
| Logic (500 Hz) | 200 us | 100 us | Logic engine + Lua |
| PROFET Update | 100 us | 60 us | Update 30 outputs |
| H-Bridge Update | 50 us | 30 us | Update 4 H-bridges |
| Protocol Update | 200 us | 100 us | Commands + telemetry |
| Watchdog | 5 us | 3 us | IWDG refresh |
| **Total (1 kHz)** | **705 us** | **373 us** | 63% headroom |
| **Total (500 Hz)** | **905 us** | **473 us** | 53% headroom |

### 7.3 Data Flow Diagram

```
                     ┌──────────────────────┐
                     │   PHYSICAL INPUTS    │
                     │  20 Analog + 20 DI   │
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │   PMU_ADC_Update()   │
                     │   Read via DMA       │
                     │   @ 1000 Hz          │
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │ PMU_Channel_Update() │
                     │ Sync to registry     │
                     │ @ 1000 Hz            │
                     └──────────┬───────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         │                      │                      │
         ▼                      ▼                      ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  CAN RX Virtual  │ │   Logic Engine   │ │    Lua Scripts   │
│    Channels      │ │    @ 500 Hz      │ │    @ 500 Hz      │
└────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
                              ▼
                    ┌──────────────────────┐
                    │   OUTPUT RESOLUTION  │
                    │  (priority logic)    │
                    └──────────┬───────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ PROFET Outputs   │ │  H-Bridge Outs   │ │   CAN TX         │
│ (30 channels)    │ │  (4 dual)        │ │   Broadcast      │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

### 7.4 Protection Task

```c
static void vProtectionTask(void *pvParameters)
{
    TickType_t xLastWakeTime;
    const TickType_t xFrequency = pdMS_TO_TICKS(1);  /* 1ms */

    (void)pvParameters;
    xLastWakeTime = xTaskGetTickCount();

    for (;;)
    {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);

        /* Monitor and respond to:
         * - Overvoltage (>22V)
         * - Undervoltage (<6V)
         * - Overtemperature (>125C critical)
         * - Total overcurrent (>1200A)
         * - Individual channel faults
         */
        PMU_Protection_Update();
    }
}
```

### 7.5 Other Tasks

```c
/* CAN Task - Event-driven with 10ms minimum period */
static void vCANTask(void *pvParameters)
{
    (void)pvParameters;
    for (;;) {
        PMU_CAN_Update();           /* Process CAN RX/TX */
        PMU_CanStream_Process();    /* Broadcast status (20 Hz + 62.5 Hz) */
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

/* Logging Task - 500 Hz data capture */
static void vLoggingTask(void *pvParameters)
{
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = pdMS_TO_TICKS(2);  /* 2ms = 500 Hz */

    (void)pvParameters;
    for (;;) {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
        PMU_Logging_Update();       /* Write to external flash */
    }
}

/* UI Task - 20 Hz LED updates */
static void vUITask(void *pvParameters)
{
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = pdMS_TO_TICKS(50);  /* 50ms = 20 Hz */

    (void)pvParameters;
    for (;;) {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
        PMU_UI_Update();            /* Status LEDs, buzzer, buttons */
    }
}
```

---

## 8. Channel Abstraction System

### 8.1 Channel ID Ranges

| Range | Type | Description | Examples |
|-------|------|-------------|----------|
| 0-99 | Physical Inputs | Analog and digital inputs | `A1`, `D5` |
| 100-199 | Physical Outputs | Power outputs, H-bridges | `OUT1`, `HB2` |
| 200-999 | Virtual Channels | Logic, tables, CAN, Lua | `FuelPump`, `RPM` |
| 1000-1023 | System Channels | Battery, temperature, status | `pmu.battery` |

### 8.2 System Channel IDs

```c
/* ECUMaster-compatible system channels (pmuX.*) */
#define PMU_CHANNEL_SYSTEM_BATTERY_V        1000  /* pmuX.battery (mV) */
#define PMU_CHANNEL_SYSTEM_TOTAL_I          1001  /* pmuX.totalCurrent (mA) */
#define PMU_CHANNEL_SYSTEM_MCU_TEMP         1002  /* pmuX.mcuTemperature (C) */
#define PMU_CHANNEL_SYSTEM_BOARD_TEMP_L     1003  /* pmuX.boardTemperatureL (C) */
#define PMU_CHANNEL_SYSTEM_BOARD_TEMP_R     1004  /* pmuX.boardTemperatureR (C) */
#define PMU_CHANNEL_SYSTEM_BOARD_TEMP_MAX   1005  /* pmuX.boardTemperatureMax (C) */
#define PMU_CHANNEL_SYSTEM_UPTIME           1006  /* pmuX.uptime (seconds) */
#define PMU_CHANNEL_SYSTEM_STATUS           1007  /* pmuX.status (bitmask) */
#define PMU_CHANNEL_SYSTEM_USER_ERROR       1008  /* pmuX.userError (code) */
#define PMU_CHANNEL_SYSTEM_5V_OUTPUT        1009  /* pmuX.5VOutput (mV) */
#define PMU_CHANNEL_SYSTEM_3V3_OUTPUT       1010  /* pmuX.3V3Output (mV) */
#define PMU_CHANNEL_SYSTEM_IS_TURNING_OFF   1011  /* pmuX.isTurningOff (bool) */
#define PMU_CHANNEL_CONST_ZERO              1012  /* zero - Constant 0 */
#define PMU_CHANNEL_CONST_ONE               1013  /* one - Constant 1 */
```

### 8.3 Output Sub-Channels

Each power output has associated sub-channels:

```c
/* Base + output_index (0-29) */
#define PMU_CHANNEL_OUTPUT_STATUS_BASE      1100  /* oY.status (0-7) */
#define PMU_CHANNEL_OUTPUT_CURRENT_BASE     1130  /* oY.current (mA) */
#define PMU_CHANNEL_OUTPUT_VOLTAGE_BASE     1160  /* oY.voltage (mV) */
#define PMU_CHANNEL_OUTPUT_ACTIVE_BASE      1190  /* oY.active (bool) */
#define PMU_CHANNEL_OUTPUT_DUTY_BASE        1250  /* oY.dutyCycle (0-1000) */

/* Example: Output 5 current = 1130 + 5 = 1135 */
```

### 8.4 Channel Types

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

### 8.5 Channel API

```c
/* Core API */
HAL_StatusTypeDef PMU_Channel_Init(void);
HAL_StatusTypeDef PMU_Channel_Register(const PMU_Channel_t* channel);
HAL_StatusTypeDef PMU_Channel_Unregister(uint16_t channel_id);

/* Value access */
int32_t PMU_Channel_GetValue(uint16_t channel_id);
HAL_StatusTypeDef PMU_Channel_SetValue(uint16_t channel_id, int32_t value);
HAL_StatusTypeDef PMU_Channel_UpdateValue(uint16_t channel_id, int32_t value);

/* Lookup */
const PMU_Channel_t* PMU_Channel_GetInfo(uint16_t channel_id);
const PMU_Channel_t* PMU_Channel_GetByName(const char* name);
uint16_t PMU_Channel_GetIndexByID(const char* name);

/* Management */
void PMU_Channel_Update(void);  /* Called at 1 kHz */
HAL_StatusTypeDef PMU_Channel_SetEnabled(uint16_t channel_id, bool enabled);
uint16_t PMU_Channel_GenerateID(void);
```

---

## 9. Driver Modules

### 9.1 PROFET Driver (pmu_profet.c)

Controls 30 high-side power outputs using BTS7012-2EPA (15 dual-channel ICs).

**Specifications:**
| Parameter | Value |
|-----------|-------|
| Channels | 30 (15 x 2) |
| Current per channel | 40A continuous, 160A inrush |
| PWM frequency | Up to 20 kHz |
| Current sense | kILIS ratio 4700:1 |
| Protection | Overcurrent, overtemp, short circuit |

**Output States:**
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

### 9.2 H-Bridge Driver (pmu_hbridge.c)

Controls 4 dual H-bridge motor drivers using BTN8982TA.

**Specifications:**
| Parameter | Value |
|-----------|-------|
| Bridges | 4 (8 half-bridges) |
| Current per bridge | 30A continuous |
| PWM frequency | 1-20 kHz |
| Features | PID position control, stall detection, park position |

**Operating Modes:**
```c
typedef enum {
    PMU_HBRIDGE_MODE_COAST = 0,     /* Hi-Z (coast) */
    PMU_HBRIDGE_MODE_FORWARD,       /* Forward direction */
    PMU_HBRIDGE_MODE_REVERSE,       /* Reverse direction */
    PMU_HBRIDGE_MODE_BRAKE          /* Active brake */
} PMU_HBridge_Mode_t;
```

### 9.3 ADC Driver (pmu_adc.c)

Manages 20 analog inputs using 3 ADC modules with DMA.

**Specifications:**
| Parameter | Value |
|-----------|-------|
| Channels | 20 external + internal sensors |
| Resolution | 12-bit (0-4095) |
| Sampling | 1 MSPS per ADC |
| Reference | 3.3V |
| Input range | 0-5V (with voltage divider) |

**Input Subtypes:**
```c
typedef enum {
    PMU_AI_SUBTYPE_SWITCH_ACTIVE_LOW = 0,
    PMU_AI_SUBTYPE_SWITCH_ACTIVE_HIGH,
    PMU_AI_SUBTYPE_ROTARY_SWITCH,
    PMU_AI_SUBTYPE_LINEAR,
    PMU_AI_SUBTYPE_CALIBRATED
} PMU_AnalogInputSubtype_t;
```

### 9.4 CAN Driver (pmu_can.c)

Manages 4 CAN bus interfaces (2 CAN FD + 2 CAN 2.0).

**Specifications:**
| Parameter | Value |
|-----------|-------|
| CAN FD buses | 2 (FDCAN1, FDCAN2) |
| CAN 2.0 buses | 2 (CAN3, CAN4) |
| Bitrate | Up to 1 Mbps arbitration, 5 Mbps data |
| Transceivers | TJA1463 (CAN FD) |

---

## 10. Protection System

### 10.1 Protection Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                    PROTECTION SYSTEM                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌───────────────────┐  ┌───────────────────┐  ┌─────────────┐  │
│  │  VOLTAGE MONITOR  │  │   TEMP MONITOR    │  │   CURRENT   │  │
│  │  6-22V range      │  │   3 sensors +MCU  │  │   MONITOR   │  │
│  └─────────┬─────────┘  └─────────┬─────────┘  └──────┬──────┘  │
│            │                      │                   │          │
│            v                      v                   v          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    FAULT DETECTION                        │   │
│  │  - Undervoltage (<6V)      - Overtemp (>100C warning)    │   │
│  │  - Overvoltage (>22V)      - Overtemp (>125C critical)   │   │
│  │  - Reverse polarity        - Total overcurrent (>1200A)   │   │
│  └───────────────────────────────┬──────────────────────────┘   │
│                                  │                               │
│                                  v                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   FAULT RESPONSE                          │   │
│  │  - Load shedding (priority-based, see 10.5)               │   │
│  │  - Channel disable                                        │   │
│  │  - System shutdown (critical)                             │   │
│  │  - Auto-recovery (after cooldown)                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 Protection Thresholds

```c
/* Voltage thresholds (mV) */
#define PMU_VOLTAGE_MIN             6000    /* Absolute minimum: 6V */
#define PMU_VOLTAGE_WARN_LOW        10500   /* Warning: 10.5V */
#define PMU_VOLTAGE_NOMINAL         12000   /* Nominal: 12V */
#define PMU_VOLTAGE_WARN_HIGH       15000   /* Warning: 15V */
#define PMU_VOLTAGE_MAX             22000   /* Absolute maximum: 22V */

/* Temperature thresholds (C) */
#define PMU_TEMP_NORMAL             85      /* Normal operation */
#define PMU_TEMP_WARNING            100     /* Warning threshold */
#define PMU_TEMP_CRITICAL           125     /* Critical - shutdown */

/* Power limits */
#define PMU_TOTAL_CURRENT_MAX_MA    1200000 /* 1200A total (30ch x 40A) */
#define PMU_TOTAL_POWER_MAX_W       14400   /* 14.4kW @ 12V */

/* Fault detection */
#define PMU_FAULT_THRESHOLD         3       /* Consecutive faults before action */
#define PMU_FAULT_RECOVERY_DELAY_MS 1000    /* Delay before auto-recovery */
```

### 10.3 Protection Fault Flags

```c
typedef enum {
    PMU_PROT_FAULT_NONE = 0x0000,

    /* Voltage faults */
    PMU_PROT_FAULT_UNDERVOLTAGE     = 0x0001,
    PMU_PROT_FAULT_OVERVOLTAGE      = 0x0002,
    PMU_PROT_FAULT_REVERSE_POLARITY = 0x0004,

    /* Temperature faults */
    PMU_PROT_FAULT_OVERTEMP_WARNING  = 0x0010,
    PMU_PROT_FAULT_OVERTEMP_CRITICAL = 0x0020,

    /* Power faults */
    PMU_PROT_FAULT_OVERCURRENT_TOTAL = 0x0100,
    PMU_PROT_FAULT_POWER_LIMIT       = 0x0200,

    /* System faults */
    PMU_PROT_FAULT_WATCHDOG    = 0x1000,
    PMU_PROT_FAULT_BROWNOUT    = 0x2000,
    PMU_PROT_FAULT_FLASH_ERROR = 0x4000
} PMU_Protection_Fault_t;
```

### 10.4 Independent Watchdog (IWDG)

```c
static void IWDG_Init(void)
{
#ifndef UNIT_TEST
    /* IWDG Configuration:
     * - Clock: LSI (~32 kHz)
     * - Prescaler: 32 (1 kHz counter)
     * - Reload: 1000 (~1 second timeout)
     */
    hiwdg.Instance = IWDG1;
    hiwdg.Init.Prescaler = IWDG_PRESCALER_32;
    hiwdg.Init.Reload = 1000;
    hiwdg.Init.Window = IWDG_WINDOW_DISABLE;

    HAL_IWDG_Init(&hiwdg);
#endif
}
```

**Watchdog Behavior:**
- Starts automatically after initialization
- Must be refreshed every <1 second (done at 1 kHz in Control Task)
- System reset if not refreshed (software hang protection)
- Disabled during unit testing (`UNIT_TEST` flag)

### 10.5 Load Shedding Priority System

Load shedding is a critical protection mechanism that intelligently disables outputs during fault conditions (overcurrent, overtemperature) to reduce system load.

**Priority Configuration:**

Each power output has a `shed_priority` field (0-10):

```c
typedef struct {
    /* ... other fields ... */
    uint8_t shed_priority;  /* 0=critical (never shed), 1-10=shed order */
} PMU_OutputConfig_t;
```

| Priority | Behavior | Example Use Case |
|----------|----------|------------------|
| **0** | Never shed (critical) | ECU power, fuel pump, ignition |
| **1-3** | Shed last (important) | Headlights, brake lights |
| **4-6** | Shed middle (normal) | Interior lights, accessories |
| **7-10** | Shed first (low priority) | Heated seats, auxiliary loads |

**Load Shedding Algorithm:**

```c
uint8_t PMU_Protection_ActivateLoadShedding(uint32_t target_reduction_mA)
{
    /* 1. Sort active outputs by shed_priority (highest first) */
    /* 2. Starting from highest priority number, disable outputs */
    /* 3. Track current reduction until target_reduction_mA reached */
    /* 4. Return number of outputs shed */

    for (each output sorted by priority descending) {
        if (output.shed_priority == 0) continue;  /* Never shed critical */
        disable_output(output);
        shed_output_list[shed_count++] = output_index;
        current_reduction += output.current_mA;
        if (current_reduction >= target_reduction_mA) break;
    }
    return shed_count;
}
```

**Load Shedding API:**

```c
/* Activate load shedding with target current reduction */
uint8_t PMU_Protection_ActivateLoadShedding(uint32_t target_reduction_mA);

/* Deactivate load shedding and re-enable shed outputs */
uint8_t PMU_Protection_DeactivateLoadShedding(void);

/* Query load shedding status */
uint8_t PMU_Protection_IsLoadSheddingActive(void);
uint8_t PMU_Protection_GetShedOutputCount(void);
```

**Automatic Triggers:**
- Total current exceeds 1200A → Shed to reduce by 20%
- Temperature exceeds 100°C → Shed high-priority outputs progressively
- Battery voltage drops below 10.5V → Shed non-critical outputs

---

## 11. Communication Stack

### 11.1 Protocol Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    COMMUNICATION STACK                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  APPLICATION LAYER                       │    │
│  │  - Configuration upload/download                         │    │
│  │  - Telemetry streaming                                   │    │
│  │  - Real-time control commands                            │    │
│  │  - Firmware update                                       │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             │                                    │
│  ┌──────────────────────────v──────────────────────────────┐    │
│  │                   PROTOCOL LAYER                         │    │
│  │  - Binary framing (0xAA start, CRC16)                    │    │
│  │  - Request/Response pattern                              │    │
│  │  - Command dispatch                                      │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             │                                    │
│  ┌──────────────────────────v──────────────────────────────┐    │
│  │                  TRANSPORT LAYER                         │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐               │    │
│  │  │  WiFi    │  │  UART    │  │   CAN    │               │    │
│  │  │(ESP32-C3)│  │(115200)  │  │ (1Mbps)  │               │    │
│  │  └──────────┘  └──────────┘  └──────────┘               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 11.2 ESP32-C3 Bridge Layer

The ESP32-C3 module provides WiFi and Bluetooth connectivity via AT commands over UART3.

**Bridge Architecture:**

```
┌─────────────────────────────────────────────────────────────────┐
│                      STM32H743 (Main MCU)                        │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    PMU_ESP32 Bridge                          │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │ │
│  │  │ Ring Buffer  │  │ AT Command   │  │ Async Callback   │  │ │
│  │  │ (512 bytes)  │  │ Parser       │  │ System           │  │ │
│  │  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │ │
│  │         │                 │                   │             │ │
│  └─────────┼─────────────────┼───────────────────┼─────────────┘ │
│            │                 │                   │               │
│     ┌──────▼─────────────────▼───────────────────▼────────┐     │
│     │                    UART3 @ 115200                    │     │
│     └──────────────────────────┬──────────────────────────┘     │
│                                │                                 │
└────────────────────────────────┼─────────────────────────────────┘
                                 │
                       ┌─────────▼─────────┐
                       │   ESP32-C3-MINI-1  │
                       │   WiFi + BLE       │
                       └───────────────────┘
```

**ESP32 Bridge API:**

```c
/* Initialization and control */
HAL_StatusTypeDef PMU_ESP32_Init(void);
HAL_StatusTypeDef PMU_ESP32_Reset(void);
HAL_StatusTypeDef PMU_ESP32_DeInit(void);
bool PMU_ESP32_IsReady(void);

/* AT Command interface */
HAL_StatusTypeDef PMU_ESP32_SendCommand(
    const char* cmd,
    char* response,
    uint16_t response_size,
    uint32_t timeout_ms
);

/* Async notification callbacks */
typedef void (*PMU_ESP32_Callback_t)(const char* notification, void* user_data);
void PMU_ESP32_SetCallback(PMU_ESP32_Callback_t callback, void* user_data);
```

**Ring Buffer Implementation:**

```c
/* 512-byte circular buffer for async UART RX */
typedef struct {
    uint8_t buffer[512];
    volatile uint16_t head;  /* Write position */
    volatile uint16_t tail;  /* Read position */
} RingBuffer_t;

/* Called from UART IRQ - adds bytes to buffer */
void PMU_ESP32_UART_IRQHandler(uint8_t byte);

/* Called from main loop - processes responses */
void PMU_ESP32_Process(void);
```

### 11.3 WiFi Implementation (AT Commands)

WiFi connectivity is implemented via ESP32 AT commands:

| Function | AT Command | Description |
|----------|------------|-------------|
| `PMU_WiFi_Init()` | `AT+CWMODE=3` | Set AP+STA mode |
| `PMU_WiFi_StartAP()` | `AT+CWSAP="PMU30_XXXX","password",1,3` | Start soft AP |
| `PMU_WiFi_Connect()` | `AT+CWJAP="ssid","password"` | Connect to router |
| `PMU_WiFi_Disconnect()` | `AT+CWQAP` | Disconnect from router |
| `PMU_WiFi_StartServer()` | `AT+CIPSERVER=1,8080` | Start TCP server |
| `PMU_WiFi_GetStatus()` | `AT+CWSTATE?` | Query connection state |
| `PMU_WiFi_GetIP()` | `AT+CIPSTA?` | Get IP address |

**WiFi Operating Modes:**

```c
typedef enum {
    PMU_WIFI_MODE_OFF = 0,    /* WiFi disabled */
    PMU_WIFI_MODE_STA,        /* Station mode (connect to router) */
    PMU_WIFI_MODE_AP,         /* Access Point mode (create network) */
    PMU_WIFI_MODE_AP_STA      /* Both AP and STA simultaneously */
} PMU_WiFi_Mode_t;
```

**WiFi Async Notifications:**

```c
/* Callback for WiFi events */
static void WiFi_AsyncCallback(const char* notification, void* user_data)
{
    if (strstr(notification, "WIFI GOT IP")) {
        wifi_state.connected = true;
        WiFi_ParseIP(notification);  /* Extract IP address */
    }
    else if (strstr(notification, "WIFI DISCONNECT")) {
        wifi_state.connected = false;
    }
    else if (strstr(notification, "+STA_CONNECTED")) {
        wifi_state.client_count++;  /* Client connected to AP */
    }
}
```

### 11.4 Bluetooth Implementation (AT Commands)

Bluetooth Low Energy (BLE) is implemented via ESP32 AT commands:

| Function | AT Command | Description |
|----------|------------|-------------|
| `PMU_Bluetooth_Init()` | `AT+BLEINIT=2` | Init as BLE server |
| `PMU_Bluetooth_SetName()` | `AT+BLENAME="PMU30-XXXX"` | Set device name |
| `PMU_Bluetooth_StartAdvertising()` | `AT+BLEADVSTART` | Start advertising |
| `PMU_Bluetooth_StopAdvertising()` | `AT+BLEADVSTOP` | Stop advertising |
| `PMU_Bluetooth_SendData()` | `AT+BLEGATTSNTFY=0,1,1,len` | Notify characteristic |
| `PMU_Bluetooth_GetConnections()` | `AT+BLECONN?` | List connections |

**BLE GATT Server Setup:**

```c
HAL_StatusTypeDef BT_CreateGATTServer(void)
{
    /* 1. Create GATT service */
    PMU_ESP32_SendCommand("AT+BLEGATTSSRVCRE", resp, sizeof(resp), 1000);

    /* 2. Start GATT service */
    PMU_ESP32_SendCommand("AT+BLEGATTSSRVSTART", resp, sizeof(resp), 1000);

    /* 3. Set advertising data */
    PMU_ESP32_SendCommand("AT+BLEADVDATA=\"0201060908504D553330\"",
                          resp, sizeof(resp), 1000);

    return HAL_OK;
}
```

**BLE Service UUIDs:**

| Service | UUID | Description |
|---------|------|-------------|
| PMU Service | `0x1820` | Primary PMU service |
| Telemetry Char | `0x2A6E` | Telemetry data (notify) |
| Command Char | `0x2A6F` | Command input (write) |
| Status Char | `0x2A6D` | Device status (read) |

**BLE Async Notifications:**

```c
static void BT_AsyncCallback(const char* notification, void* user_data)
{
    if (strstr(notification, "+BLECONN:")) {
        bt_state.connected = true;
        bt_state.connection_count++;
    }
    else if (strstr(notification, "+BLEDISCONN:")) {
        bt_state.connected = false;
    }
    else if (strstr(notification, "+WRITE:")) {
        /* Data received on write characteristic */
        BT_ParseWriteData(notification);
    }
}
```

### 11.5 Packet Format

```
┌────────┬─────────┬────────┬─────────────────┬────────┐
│ Start  │ Command │ Length │     Payload     │  CRC   │
│ (1B)   │  (1B)   │ (2B)   │   (0-256 B)     │ (2B)   │
│  0xAA  │  0x00-  │  LE    │                 │ CRC16  │
│        │  0xFF   │        │                 │        │
└────────┴─────────┴────────┴─────────────────┴────────┘
```

### 11.6 Command Categories

```c
typedef enum {
    /* Basic (0x00-0x1F) */
    PMU_CMD_PING                = 0x01,
    PMU_CMD_GET_VERSION         = 0x02,
    PMU_CMD_GET_SERIAL          = 0x03,
    PMU_CMD_RESET               = 0x04,
    PMU_CMD_BOOTLOADER          = 0x05,

    /* Telemetry (0x20-0x3F) */
    PMU_CMD_START_STREAM        = 0x20,
    PMU_CMD_STOP_STREAM         = 0x21,
    PMU_CMD_GET_OUTPUTS         = 0x22,
    PMU_CMD_GET_INPUTS          = 0x23,
    PMU_CMD_GET_CAN             = 0x24,
    PMU_CMD_GET_TEMPS           = 0x25,
    PMU_CMD_GET_VOLTAGES        = 0x26,
    PMU_CMD_GET_FAULTS          = 0x27,

    /* Control (0x40-0x5F) */
    PMU_CMD_SET_OUTPUT          = 0x40,
    PMU_CMD_SET_PWM             = 0x41,
    PMU_CMD_SET_HBRIDGE         = 0x42,
    PMU_CMD_CLEAR_FAULTS        = 0x43,
    PMU_CMD_SET_VIRTUAL         = 0x44,

    /* Configuration (0x60-0x7F) */
    PMU_CMD_LOAD_CONFIG         = 0x60,
    PMU_CMD_SAVE_CONFIG         = 0x61,
    PMU_CMD_GET_CONFIG          = 0x62,
    PMU_CMD_UPLOAD_CONFIG       = 0x63,
    PMU_CMD_DOWNLOAD_CONFIG     = 0x64,
    PMU_CMD_VALIDATE_CONFIG     = 0x65,
    PMU_CMD_SET_CHANNEL_CONFIG  = 0x66,  /* Atomic channel update */
    PMU_CMD_CHANNEL_CONFIG_ACK  = 0x67,

    /* Logging (0x80-0x9F) */
    PMU_CMD_START_LOGGING       = 0x80,
    PMU_CMD_STOP_LOGGING        = 0x81,
    PMU_CMD_GET_LOG_INFO        = 0x82,
    PMU_CMD_DOWNLOAD_LOG        = 0x83,
    PMU_CMD_ERASE_LOGS          = 0x84,

    /* Diagnostics (0xA0-0xAF) */
    PMU_CMD_GET_STATS           = 0xA0,
    PMU_CMD_GET_UPTIME          = 0xA1,
    PMU_CMD_GET_CAN_STATS       = 0xA2,
    PMU_CMD_SELF_TEST           = 0xA3,

    /* Lua Scripting (0xB0-0xBF) */
    PMU_CMD_LUA_EXECUTE         = 0xB0,
    PMU_CMD_LUA_LOAD_SCRIPT     = 0xB1,
    PMU_CMD_LUA_UNLOAD_SCRIPT   = 0xB2,
    PMU_CMD_LUA_RUN_SCRIPT      = 0xB3,
    PMU_CMD_LUA_STOP_SCRIPT     = 0xB4,
    PMU_CMD_LUA_GET_SCRIPTS     = 0xB5,
    PMU_CMD_LUA_GET_STATUS      = 0xB6,
    PMU_CMD_LUA_GET_OUTPUT      = 0xB7,
    PMU_CMD_LUA_SET_ENABLED     = 0xB8,

    /* Firmware Update (0xC0-0xDF) */
    PMU_CMD_FW_UPDATE_START     = 0xC0,
    PMU_CMD_FW_UPDATE_DATA      = 0xC1,
    PMU_CMD_FW_UPDATE_FINISH    = 0xC2,
    PMU_CMD_FW_UPDATE_ABORT     = 0xC3,

    /* Responses (0xE0-0xFF) */
    PMU_CMD_ACK                 = 0xE0,
    PMU_CMD_NACK                = 0xE1,
    PMU_CMD_ERROR               = 0xE2,
    PMU_CMD_DATA                = 0xE3
} PMU_CMD_Type_t;
```

### 11.7 Telemetry Configuration

```c
typedef struct {
    bool outputs_enabled;       /* Stream output states */
    bool inputs_enabled;        /* Stream input values */
    bool can_enabled;           /* Stream CAN data */
    bool temps_enabled;         /* Stream temperatures */
    bool voltages_enabled;      /* Stream voltages */
    bool faults_enabled;        /* Stream faults */
    uint16_t rate_hz;           /* Stream rate (1-1000 Hz) */
} PMU_TelemetryConfig_t;
```

### 11.8 Standard CAN Stream

Broadcasts PMU status on CAN bus (ECUMaster compatible):

```c
typedef struct {
    bool enabled;               /* Disabled by default */
    uint8_t can_bus;            /* CAN bus (1-4) */
    uint32_t base_id;           /* Base CAN ID (0x600) */
    bool is_extended;           /* Use 29-bit IDs */
    bool include_extended;      /* Include PMU-30 extended frames */
} PMU_CanStreamConfig_t;
```

**Frame Rates:**
- Status frames: 20 Hz
- Extended data: 62.5 Hz

---

## 12. Error Handling

### 12.1 Error Handling Patterns

**Pattern 1: HAL Status Returns**
```c
HAL_StatusTypeDef status = PMU_Protection_Init();
if (status != HAL_OK) {
    Error_Handler();  /* Global error handler */
}
```

**Pattern 2: Validation Macros**
```c
#define PROFET_VALIDATE_CHANNEL(ch) \
    do { if (!IS_VALID_CHANNEL(ch)) return HAL_ERROR; } while(0)

#define PROFET_VALIDATE_CHANNEL_PTR(ch) \
    do { if (!IS_VALID_CHANNEL(ch)) return NULL; } while(0)
```

**Pattern 3: Fault Accumulation**
```c
/* Require N consecutive faults before triggering */
if (voltage_low_detected) {
    undervoltage_count++;
    if (undervoltage_count >= PMU_FAULT_THRESHOLD) {
        fault_flags |= PMU_PROT_FAULT_UNDERVOLTAGE;
        trigger_protection_response();
    }
} else {
    undervoltage_count = 0;  /* Reset on good reading */
}
```

### 12.2 Global Error Handler

```c
void Error_Handler(void)
{
    /* Disable interrupts to prevent further damage */
    __disable_irq();

    /* Optionally: Blink error LED pattern */
    while (1)
    {
        /* System halted - requires power cycle */
    }
}
```

### 12.3 Fault Recovery

```c
/* Auto-recovery after fault clears */
if (recovery_timer >= PMU_FAULT_RECOVERY_DELAY_MS) {
    if (!fault_condition_present) {
        clear_fault_flag();
        re_enable_affected_outputs();
        recovery_timer = 0;
    }
}
```

### 12.4 Fault Logging

Faults are logged to external flash for diagnostics:
- Timestamp (milliseconds since boot)
- Fault type
- Affected channels
- System state snapshot

---

## 13. Memory Management

### 13.1 Memory Map

| Region | Start | Size | Usage |
|--------|-------|------|-------|
| **Flash (Internal)** | 0x08000000 | 2 MB | Application code |
| **ITCM RAM** | 0x00000000 | 64 KB | Fast code (ISRs) |
| **DTCM RAM** | 0x20000000 | 128 KB | Fast data (stacks) |
| **AXI SRAM** | 0x24000000 | 512 KB | Main heap, FreeRTOS |
| **SRAM1** | 0x30000000 | 128 KB | DMA buffers |
| **SRAM2** | 0x30020000 | 128 KB | CAN buffers |
| **SRAM3** | 0x30040000 | 32 KB | Lua VM heap |
| **Backup SRAM** | 0x38800000 | 4 KB | RTC backup data |

### 13.2 Flash Layout

**Internal Flash (2 MB):**
| Offset | Size | Usage |
|--------|------|-------|
| 0x00000 | 128 KB | Bootloader |
| 0x20000 | 1.5 MB | Application |
| 0x1E0000 | 64 KB | Configuration |
| 0x1F0000 | 64 KB | Backup Configuration |

**External Flash (64 MB W25Q512JV):**
| Offset | Size | Usage |
|--------|------|-------|
| 0x000000 | 64 KB | Configuration mirror |
| 0x010000 | 128 KB | Lua scripts |
| 0x030000 | 512 KB | DBC files |
| 0x0B0000 | ~511 MB | Data logging |

### 13.3 Stack Allocation

| Component | Size | Location |
|-----------|------|----------|
| Main stack (MSP) | 1 KB | DTCM |
| Control task | 2 KB | AXI SRAM |
| Protection task | 1.5 KB | AXI SRAM |
| CAN task | 2 KB | AXI SRAM |
| Logging task | 2 KB | AXI SRAM |
| UI task | 1 KB | AXI SRAM |
| ISR stack | 512 B | DTCM |

---

## 14. Configuration System

### 14.1 Binary Configuration Format

Configuration is stored in binary format (`.pmu30` files):

```
┌────────────────────────────────┐
│  File Header (32 bytes)        │
│  - Magic: 0x43464733 ("CFG3")  │
│  - Version: 2                   │
│  - Device type: 0x0030         │
│  - CRC-32 checksum             │
│  - Channel count               │
├────────────────────────────────┤
│  Channel 0                     │
│  ├─ Header (14 bytes)          │
│  ├─ Name (0-31 bytes)          │
│  └─ Config (type-specific)     │
├────────────────────────────────┤
│  Channel 1...N                 │
└────────────────────────────────┘
```

**Key features:**
- No JSON parsing - binary format only
- CRC-32 verified
- Identical format for firmware and configurator
- Shared library for serialization/deserialization

### 14.2 Channel Executor Integration

The shared library `channel_executor` handles virtual channel execution:

```c
#include "channel_executor.h"
#include "channel_config.h"

// Initialize executor with HAL callbacks
PMU_ChannelExec_Init();

// Load channels from binary config
PMU_ChannelExec_LoadConfig(binary_data, size);

// Execute at 500Hz in control loop
PMU_ChannelExec_Update();
```

### 14.3 Configuration API

```c
// Channel executor API
HAL_StatusTypeDef PMU_ChannelExec_Init(void);
HAL_StatusTypeDef PMU_ChannelExec_AddChannel(uint16_t id, uint8_t type, const void* config);
void PMU_ChannelExec_Update(void);
int PMU_ChannelExec_LoadConfig(const uint8_t* data, uint16_t size);

// Legacy config API (for system settings)
void PMU_Config_Init(void);
void PMU_Config_LoadDefaults(void);
void PMU_Config_Save(void);
void PMU_Config_Load(void);
```

For detailed binary format specification, see [Configuration Reference](reference/configuration.md).

---

## 15. Performance Characteristics

### 15.1 Timing Specifications

| Metric | Target | Measured |
|--------|--------|----------|
| Control loop period | 1 ms | 1.00 ms ±50 us |
| Control loop jitter | <100 us | ~50 us |
| ADC sample to output | <2 ms | ~1.5 ms |
| CAN message latency | <5 ms | ~3 ms |
| Telemetry latency | <10 ms | ~5 ms |
| Logic evaluation | <500 us | ~200 us |
| Lua script cycle | <1 ms | ~500 us |

### 15.2 Resource Usage

| Resource | Budget | Typical |
|----------|--------|---------|
| CPU Load | <80% | ~60% |
| RAM Usage | <80% | ~65% |
| Flash (code) | <1.5 MB | ~800 KB |
| External Flash | 64 MB | Variable |

### 15.3 Power Consumption

| State | Consumption |
|-------|-------------|
| Idle (no outputs) | ~50 mA @ 12V |
| Active (telemetry) | ~100 mA @ 12V |
| Full load (30 outputs) | ~200 mA @ 12V (logic only) |

### 15.4 Status LED Indication

The RGB status LED provides visual feedback for system state.

**Implementation:** `pmu_led.c` / `pmu_led.h`

| State | Color | LED Behavior | Description |
|-------|-------|--------------|-------------|
| Startup | Yellow | Fast blink | System initializing |
| Startup OK | Green | 1 blink | Initialized successfully |
| Startup error | Red | Fast blink | Critical error |
| Config loaded | Green | 2 blinks | Configuration loaded |
| Config error | Red | Fast blink | Error loading config |
| Normal | Off | Off | System running |
| Warning | Yellow | Slow blink | Non-critical issue |
| Fault | Red | Fast blink | System fault |
| Comm active | Blue | Heartbeat | WiFi/BT/CAN activity |

**Timing specifications:**
- Single blink: 200ms on
- Fast blink: 100ms on, 100ms off (continuous)
- Slow blink: 500ms on, 500ms off
- Between blinks: 300ms pause
- Heartbeat: 100ms pulse, 100ms gap, 100ms pulse, 600ms pause

**API:**
```c
PMU_LED_Init();                      // Initialize LED module
PMU_LED_Update();                    // Call at 20-50Hz from UI task
PMU_LED_SignalStartupOK();           // 1 green blink
PMU_LED_SignalConfigLoaded();        // 2 green blinks
PMU_LED_SignalConfigError();         // Fast red blink
PMU_LED_TriggerCommActivity();       // Brief blue flash
```

**Hardware:** RGB LED on PC6 (R), PC7 (G), PC8 (B) - see `board_config.h`

---

## 16. Emulator Architecture

### 16.1 Overview

The emulator allows desktop development without hardware:

```
firmware/emulator/
├── emu_main.c              # Emulator entry point
├── pmu_emulator.c          # Emulator core (2643 lines)
├── emu_protocol_server.c   # Socket-based protocol server
├── emu_stubs.c             # HAL stubs for Windows/Linux
├── emu_ui.c                # Console UI
├── emu_flash.c             # File-based flash simulation
├── emu_webui.c             # Web-based UI (optional)
└── emu_state.json          # Persistent state
```

### 16.2 Build Target

```bash
# Build emulator
pio run -e pmu30_emulator

# Run emulator
.pio/build/pmu30_emulator/program.exe
```

### 16.3 Emulator Features

- Full protocol compatibility (socket on port 9876)
- Simulated channel values
- JSON configuration loading
- State persistence (`emu_state.json`)
- Real-time telemetry streaming

### 16.4 Emulator Limitations

The emulator stubs out hardware-specific functionality:

| Component | Emulator Behavior | Real Hardware |
|-----------|-------------------|---------------|
| **ESP32 WiFi/BT** | Stubbed (always "ready") | AT commands via UART3 |
| **UART (ESP32)** | No actual communication | 115200 baud ring buffer |
| **ADC Channels** | Set via protocol/file | DMA-based sampling |
| **PWM Outputs** | State tracked, no waveform | Timer-based generation |
| **PROFET Sensing** | Simulated current | Real IS pin ADC |
| **CAN TX** | Logged to console | Hardware transmission |
| **LIN Bus** | Fully stubbed | UART-based protocol |
| **Flash Storage** | File-based (`emu_flash.bin`) | SPI flash chip |

**Fully Functional in Emulator:**
- All channel types (logic, number, timer, filter, table)
- Configuration parsing and validation
- Telemetry streaming
- Protection logic and load shedding algorithm
- Protocol handler with CRC16

**For detailed emulator documentation, see [Emulator Guide](testing/emulator-guide.md).**

### 16.5 Emulator-Specific Protocol Commands

| Command | Code | Description |
|---------|------|-------------|
| `EMU_INJECT_FAULT` | `0x80` | Inject fault on output |
| `EMU_CLEAR_FAULT` | `0x81` | Clear fault |
| `EMU_SET_VOLTAGE` | `0x82` | Set battery voltage |
| `EMU_SET_TEMPERATURE` | `0x83` | Set temperature |
| `EMU_SET_DIGITAL_INPUT` | `0x84` | Set digital input |
| `EMU_SET_ANALOG_INPUT` | `0x86` | Set analog voltage |
| `EMU_INJECT_CAN` | `0x88` | Inject CAN message |

---

## 17. Appendix

### 17.1 Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-21 | PMU-30 Team | Initial stub |
| 2.0 | 2025-12-29 | PMU-30 Team | Full architecture |
| 3.0 | 2025-12-29 | PMU-30 Team | Deep HAL/RTOS detail |
| 3.1 | 2025-12-30 | PMU-30 Team | ESP32 bridge layer, WiFi/BT AT commands, load shedding priority |
| 3.2 | 2025-12-30 | PMU-30 Team | Emulator limitations documentation, ESP32/WiFi/BT stubs |

### 17.2 Related Documents

- [Channels Reference](reference/channels.md) - Channel system details
- [Configuration Reference](reference/configuration.md) - JSON schema
- [Protocol Reference](reference/protocol.md) - Communication protocol
- [Logic Functions Reference](reference/logic-functions.md) - Logic engine
- [Hardware Specification](hardware/technical_specification.md) - Electrical specs
- [Emulator Guide](testing/emulator-guide.md) - Emulator usage and limitations

### 17.3 Glossary

| Term | Definition |
|------|------------|
| **Channel** | Abstract data point (input, output, or virtual) |
| **PROFET** | Infineon high-side switch IC (BTS7012-2EPA) |
| **HAL** | Hardware Abstraction Layer (ST-provided) |
| **RTOS** | Real-Time Operating System (FreeRTOS) |
| **IWDG** | Independent Watchdog (hardware watchdog) |
| **MPU** | Memory Protection Unit |
| **DMA** | Direct Memory Access |
| **FDCAN** | Flexible Data-rate CAN |

---

**End of Firmware Architecture Document**

---

**Copyright 2025 R2 m-sport. All rights reserved.**
