# Component Interaction Model

**Version:** 1.0
**Date:** December 2024

---

## 1. System Components Overview

```
+------------------------------------------------------------------+
|                     PMU-30 Component Architecture                 |
+------------------------------------------------------------------+
|                                                                   |
|   +-------------------+       +-------------------+               |
|   |  Channel Manager  |<----->|  Logic Engine     |               |
|   +-------------------+       +-------------------+               |
|          ^    ^                      ^    ^                       |
|          |    |                      |    |                       |
|          v    v                      v    v                       |
|   +----------+ +----------+   +----------+ +----------+           |
|   | ADC      | | CAN      |   | PROFET   | | H-Bridge |           |
|   | Driver   | | Driver   |   | Driver   | | Driver   |           |
|   +----------+ +----------+   +----------+ +----------+           |
|          ^          ^               ^           ^                 |
|          |          |               |           |                 |
|          v          v               v           v                 |
|   +----------------------------------------------------------+   |
|   |                    HAL / Hardware Layer                   |   |
|   +----------------------------------------------------------+   |
|                                                                   |
+------------------------------------------------------------------+
```

---

## 2. Channel Manager Interactions

### 2.1 ADC Driver Interface

```c
// ADC Driver -> Channel Manager
void ADC_ConvCpltCallback(ADC_HandleTypeDef* hadc) {
    // DMA transfer complete
    for (int i = 0; i < ADC_CHANNEL_COUNT; i++) {
        PMU_Channel_SetValue(i, adc_buffer[i]);
    }
}

// Interaction flow:
// 1. ADC samples at 1kHz via DMA
// 2. DMA complete interrupt fires
// 3. Callback updates channel values
// 4. Channel flags updated if out of range
```

### 2.2 PROFET Driver Interface

```c
// Channel Manager -> PROFET Driver
void PMU_Channel_ApplyOutputs(void) {
    for (int i = 0; i < 30; i++) {
        int32_t value = PMU_Channel_GetValue(PROFET_CHANNEL_BASE + i);
        PMU_PROFET_SetDuty(i, value);
    }
}

// PROFET Driver -> Channel Manager (diagnostics)
void PMU_PROFET_UpdateDiagnostics(void) {
    for (int i = 0; i < 30; i++) {
        uint16_t current = PMU_PROFET_GetCurrent(i);
        PMU_Channel_SetValue(PROFET_CURRENT_BASE + i, current);

        if (PMU_PROFET_IsFault(i)) {
            PMU_Channel_SetFault(PROFET_CHANNEL_BASE + i, true);
        }
    }
}
```

### 2.3 CAN Driver Interface

```c
// CAN Driver -> Channel Manager (RX)
void HAL_CAN_RxFifo0MsgPendingCallback(CAN_HandleTypeDef* hcan) {
    CAN_RxHeaderTypeDef header;
    uint8_t data[8];
    HAL_CAN_GetRxMessage(hcan, CAN_RX_FIFO0, &header, data);

    // Find matching signal mapping
    PMU_CAN_Signal_t* signal = PMU_CAN_FindSignal(header.StdId);
    if (signal) {
        int32_t value = PMU_CAN_ExtractSignal(data, signal);
        PMU_Channel_SetValue(signal->channel_id, value);
    }
}

// Channel Manager -> CAN Driver (TX)
void PMU_CAN_TransmitMessages(void) {
    for (int i = 0; i < tx_message_count; i++) {
        PMU_CAN_TxMsg_t* msg = &tx_messages[i];
        if (is_time_to_send(msg)) {
            uint8_t data[8] = {0};
            // Pack signals from channels
            for (int j = 0; j < msg->signal_count; j++) {
                int32_t value = PMU_Channel_GetValue(msg->signals[j].channel);
                PMU_CAN_PackSignal(data, &msg->signals[j], value);
            }
            PMU_CAN_Send(msg->bus, msg->id, data, msg->dlc);
        }
    }
}
```

---

## 3. Logic Function Dispatcher Interactions

### 3.1 Function Registration

```c
// Application -> Logic Dispatcher
HAL_StatusTypeDef PMU_LogicFunctions_Register(PMU_LogicFunction_t* func) {
    // Validate
    if (!validate_function(func)) return HAL_ERROR;

    // Store in registry
    memcpy(&function_registry[func->function_id], func, sizeof(PMU_LogicFunction_t));

    // Initialize state
    init_function_state(func->function_id);

    return HAL_OK;
}
```

### 3.2 Execution Loop

```c
// Logic Dispatcher main execution
void PMU_LogicFunctions_Update(void) {
    uint32_t start_time = HAL_GetTick();

    for (int i = 0; i < PMU_MAX_LOGIC_FUNCTIONS; i++) {
        PMU_LogicFunction_t* func = &function_registry[i];

        if (!func->enabled) continue;

        // Read inputs
        int32_t inputs[8];
        for (int j = 0; j < func->input_count; j++) {
            inputs[j] = PMU_Channel_GetValue(func->input_channels[j]);
        }

        // Execute function
        int32_t result = execute_function(func, inputs);

        // Write output
        PMU_Channel_SetValue(func->output_channel, result);
    }

    // Performance monitoring
    uint32_t elapsed = HAL_GetTick() - start_time;
    if (elapsed > 2) {
        // Log warning - execution took too long
    }
}
```

### 3.3 Function Type Dispatcher

```c
static int32_t execute_function(PMU_LogicFunction_t* func, int32_t* inputs) {
    switch (func->type) {
        // Math
        case PMU_FUNC_ADD:
            return inputs[0] + inputs[1];
        case PMU_FUNC_SUBTRACT:
            return inputs[0] - inputs[1];
        case PMU_FUNC_MULTIPLY:
            return (inputs[0] * inputs[1]) / 1000;
        case PMU_FUNC_DIVIDE:
            return (inputs[1] != 0) ? (inputs[0] * 1000) / inputs[1] : INT32_MAX;

        // Comparison
        case PMU_FUNC_GREATER:
            return (inputs[0] > inputs[1]) ? 1 : 0;
        case PMU_FUNC_LESS:
            return (inputs[0] < inputs[1]) ? 1 : 0;

        // Stateful
        case PMU_FUNC_PID:
            return execute_pid(func, inputs[0]);
        case PMU_FUNC_HYSTERESIS:
            return execute_hysteresis(func, inputs[0]);
        case PMU_FUNC_MOVING_AVG:
            return execute_moving_avg(func, inputs[0]);

        default:
            return 0;
    }
}
```

---

## 4. Configuration Management Flow

```
                Configuration Load/Save Flow
+------------------------------------------------------------------+
|                                                                  |
|   USER                 CONFIGURATOR            PMU FIRMWARE      |
|                                                                  |
|   [Open File] -----> [Parse JSON] -------> [Validate Schema]     |
|                            |                       |             |
|                            v                       v             |
|                      [Build Config]          [Check Limits]      |
|                            |                       |             |
|                            v                       v             |
|   [Edit UI] <------- [Display] <--------- [Return Status]        |
|       |                                                          |
|       v                                                          |
|   [Save] ----------> [Serialize JSON] ----> [Write Flash]        |
|                            |                       |             |
|                            v                       v             |
|                      [Upload Protocol]       [Apply Config]      |
|                            |                       |             |
|                            v                       v             |
|   [Confirm] <------- [ACK Response] <------ [Return Status]      |
|                                                                  |
+------------------------------------------------------------------+
```

### 4.1 Configuration Protocol

```c
// Configuration upload protocol
typedef struct {
    uint8_t command;        // CMD_CONFIG_UPLOAD
    uint16_t total_size;    // Total config size
    uint16_t chunk_index;   // Current chunk (0-N)
    uint16_t chunk_size;    // Size of this chunk
    uint8_t data[256];      // Chunk data
    uint16_t crc;           // CRC16
} PMU_ConfigPacket_t;

// Upload sequence:
// 1. Host sends CMD_CONFIG_START
// 2. PMU acknowledges, prepares buffer
// 3. Host sends chunks with CMD_CONFIG_DATA
// 4. PMU acknowledges each chunk
// 5. Host sends CMD_CONFIG_END
// 6. PMU validates, applies, saves to flash
// 7. PMU sends final ACK/NACK
```

---

## 5. Event Handling and Callbacks

### 5.1 Event Types

```c
typedef enum {
    PMU_EVENT_CHANNEL_UPDATED,
    PMU_EVENT_CHANNEL_FAULT,
    PMU_EVENT_OUTPUT_OVERCURRENT,
    PMU_EVENT_CAN_TIMEOUT,
    PMU_EVENT_SYSTEM_OVERVOLTAGE,
    PMU_EVENT_SYSTEM_UNDERVOLTAGE,
    PMU_EVENT_TEMPERATURE_WARNING,
    PMU_EVENT_CONFIG_CHANGED,
} PMU_EventType_t;

typedef struct {
    PMU_EventType_t type;
    uint16_t source_id;     // Channel or function ID
    int32_t value;          // Associated value
    uint32_t timestamp;     // Event time
} PMU_Event_t;
```

### 5.2 Event Dispatch

```c
// Event queue
static PMU_Event_t event_queue[64];
static volatile uint8_t event_head = 0;
static volatile uint8_t event_tail = 0;

void PMU_Event_Post(PMU_EventType_t type, uint16_t source, int32_t value) {
    event_queue[event_head].type = type;
    event_queue[event_head].source_id = source;
    event_queue[event_head].value = value;
    event_queue[event_head].timestamp = HAL_GetTick();
    event_head = (event_head + 1) % 64;
}

void PMU_Event_Process(void) {
    while (event_tail != event_head) {
        PMU_Event_t* event = &event_queue[event_tail];

        switch (event->type) {
            case PMU_EVENT_OUTPUT_OVERCURRENT:
                handle_overcurrent(event->source_id);
                break;
            case PMU_EVENT_CAN_TIMEOUT:
                handle_can_timeout(event->source_id);
                break;
            // ... other handlers
        }

        event_tail = (event_tail + 1) % 64;
    }
}
```

---

## 6. Dependency Relationships

```
                    Module Dependencies
+------------------------------------------------------------------+
|                                                                  |
|   Level 4 (Application)                                          |
|   +----------------------------------------------------------+  |
|   | Configuration | Telemetry | Logging | Web Interface      |  |
|   +----------------------------------------------------------+  |
|                               |                                  |
|                               v                                  |
|   Level 3 (Services)                                             |
|   +----------------------------------------------------------+  |
|   | Logic Functions | Protection | Diagnostics | Scheduler   |  |
|   +----------------------------------------------------------+  |
|                               |                                  |
|                               v                                  |
|   Level 2 (Abstraction)                                          |
|   +----------------------------------------------------------+  |
|   | Channel Manager | CAN Manager | Timer Manager            |  |
|   +----------------------------------------------------------+  |
|                               |                                  |
|                               v                                  |
|   Level 1 (Drivers)                                              |
|   +----------------------------------------------------------+  |
|   | ADC | SPI | CAN | UART | GPIO | PWM | DMA               |  |
|   +----------------------------------------------------------+  |
|                               |                                  |
|                               v                                  |
|   Level 0 (HAL/Hardware)                                         |
|   +----------------------------------------------------------+  |
|   | STM32H7 HAL | Peripheral Registers | Interrupts          |  |
|   +----------------------------------------------------------+  |
|                                                                  |
+------------------------------------------------------------------+
```

---

## 7. Initialization Sequence

```c
// System initialization order
void System_Init(void) {
    // Level 0: Hardware
    HAL_Init();
    SystemClock_Config();

    // Level 1: Drivers
    MX_GPIO_Init();
    MX_DMA_Init();
    MX_ADC1_Init();
    MX_CAN_Init();
    MX_SPI_Init();
    MX_TIM_Init();

    // Level 2: Abstraction
    PMU_Channel_Init();           // Must be first in L2
    PMU_CAN_Manager_Init();
    PMU_Timer_Init();

    // Level 3: Services
    PMU_Protection_Init();        // Before outputs enabled
    PMU_LogicFunctions_Init();
    PMU_Diagnostics_Init();

    // Level 4: Application
    PMU_Config_Load();            // Load from flash
    PMU_Config_Apply();           // Apply configuration
    PMU_Telemetry_Init();
    PMU_Logging_Init();

    // Start operation
    PMU_ADC_Start();
    PMU_CAN_Start();
    PMU_Scheduler_Start();
}
```

---

## See Also

- [Data Flow Diagrams](data-flow-diagrams.md)
- [State Machines](state-machines.md)
- [Channel API Reference](../api/channel-api.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024
