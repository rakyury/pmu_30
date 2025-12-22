# State Machine Documentation

**Version:** 1.0
**Date:** December 2024

---

## 1. Channel Lifecycle State Machine

```
                    Channel State Machine
+------------------------------------------------------------------+
|                                                                  |
|                    +-------------+                               |
|                    | UNREGISTERED|                               |
|                    +------+------+                               |
|                           |                                      |
|                    Register()                                    |
|                           |                                      |
|                           v                                      |
|                    +-------------+                               |
|          +-------->|  DISABLED   |<--------+                     |
|          |         +------+------+         |                     |
|          |                |                |                     |
|          |         SetEnabled(true)   SetEnabled(false)          |
|          |                |                |                     |
|          |                v                |                     |
|          |         +-------------+         |                     |
|   Unregister()     |   ENABLED   |---------+                     |
|          |         +------+------+                               |
|          |                |                                      |
|          |           Fault detected                              |
|          |                |                                      |
|          |                v                                      |
|          |         +-------------+                               |
|          +---------|   FAULT     |                               |
|                    +------+------+                               |
|                           |                                      |
|                    ClearFault()                                  |
|                           |                                      |
|                           v                                      |
|                    +-------------+                               |
|                    |   ENABLED   |                               |
|                    +-------------+                               |
|                                                                  |
+------------------------------------------------------------------+
```

### State Descriptions

| State | Description | Flags |
|-------|-------------|-------|
| UNREGISTERED | Channel not in registry | N/A |
| DISABLED | Registered but not active | ENABLED = 0 |
| ENABLED | Active, updating normally | ENABLED = 1 |
| FAULT | Error condition detected | FAULT = 1 |

---

## 2. Connection States (CAN/Communication)

```
                    Connection State Machine
+------------------------------------------------------------------+
|                                                                  |
|                    +-------------+                               |
|                    | DISCONNECTED|                               |
|                    +------+------+                               |
|                           |                                      |
|                    Connect()                                     |
|                           |                                      |
|                           v                                      |
|                    +-------------+                               |
|                    | CONNECTING  |------+                        |
|                    +------+------+      |                        |
|                           |          Timeout                     |
|                    Connected          |                          |
|                           |             |                        |
|                           v             v                        |
|                    +-------------+   +-------------+             |
|           +------->|  CONNECTED  |   |   ERROR     |             |
|           |        +------+------+   +------+------+             |
|           |               |                 |                    |
|      Reconnect       Lost connection    Retry                    |
|           |               |                 |                    |
|           |               v                 |                    |
|           |        +-------------+          |                    |
|           +--------| RECONNECTING|<---------+                    |
|                    +-------------+                               |
|                                                                  |
+------------------------------------------------------------------+
```

### CAN Bus States

```c
typedef enum {
    CAN_STATE_DISCONNECTED = 0,
    CAN_STATE_CONNECTING,
    CAN_STATE_CONNECTED,
    CAN_STATE_ERROR_PASSIVE,
    CAN_STATE_ERROR_ACTIVE,
    CAN_STATE_BUS_OFF,
    CAN_STATE_RECOVERING
} PMU_CAN_State_t;
```

---

## 3. Logic Function Execution States

```
                Function Execution State Machine
+------------------------------------------------------------------+
|                                                                  |
|   Per-cycle states (500Hz):                                      |
|                                                                  |
|   +----------+     +----------+     +----------+     +----------+|
|   | IDLE     |---->| READING  |---->| EXECUTING|---->| WRITING  ||
|   +----------+     +----------+     +----------+     +----------+|
|        ^                                                  |      |
|        |                                                  |      |
|        +--------------------------------------------------+      |
|                                                                  |
|   Function lifecycle:                                            |
|                                                                  |
|                    +-------------+                               |
|                    | UNREGISTERED|                               |
|                    +------+------+                               |
|                           |                                      |
|                    Register()                                    |
|                           |                                      |
|                           v                                      |
|                    +-------------+                               |
|                    |  REGISTERED |                               |
|                    |  (Disabled) |                               |
|                    +------+------+                               |
|                           |                                      |
|                    Enable()                                      |
|                           |                                      |
|                           v                                      |
|                    +-------------+                               |
|                    |   ACTIVE    |                               |
|                    | (Executing) |                               |
|                    +-------------+                               |
|                                                                  |
+------------------------------------------------------------------+
```

---

## 4. PROFET Output States

```
                    PROFET Output State Machine
+------------------------------------------------------------------+
|                                                                  |
|                    +-------------+                               |
|                    |     OFF     |<-----------+                  |
|                    +------+------+            |                  |
|                           |                   |                  |
|                    SetOutput(ON)        Fault/Overtemp           |
|                           |                   |                  |
|                           v                   |                  |
|                    +-------------+            |                  |
|                    | SOFT_START  |            |                  |
|                    +------+------+            |                  |
|                           |                   |                  |
|                    Ramp complete              |                  |
|                           |                   |                  |
|                           v                   |                  |
|                    +-------------+     +-------------+           |
|                    |     ON      |---->|   FAULT     |           |
|                    +------+------+     +------+------+           |
|                           |                   |                  |
|                    SetOutput(OFF)       ClearFault()             |
|                    or PWM duty              (if cleared)         |
|                           |                   |                  |
|                           v                   v                  |
|                    +-------------+     +-------------+           |
|                    |     OFF     |     | RETRY_WAIT  |           |
|                    |  (or PWM)   |     +------+------+           |
|                    +-------------+            |                  |
|                                          Retry timer             |
|                                               |                  |
|                                               v                  |
|                                        +-------------+           |
|                                        | SOFT_START  |           |
|                                        +-------------+           |
|                                                                  |
+------------------------------------------------------------------+
```

### PROFET State Implementation

```c
typedef enum {
    PROFET_STATE_OFF = 0,
    PROFET_STATE_SOFT_START,
    PROFET_STATE_ON,
    PROFET_STATE_FAULT,
    PROFET_STATE_RETRY_WAIT,
    PROFET_STATE_DISABLED
} PMU_PROFET_State_t;

typedef struct {
    PMU_PROFET_State_t state;
    uint16_t target_duty;
    uint16_t current_duty;
    uint32_t soft_start_start_ms;
    uint16_t soft_start_duration_ms;
    uint8_t retry_count;
    uint32_t retry_timer_ms;
    uint8_t fault_code;
} PMU_PROFET_Channel_t;
```

---

## 5. H-Bridge States

```
                    H-Bridge State Machine
+------------------------------------------------------------------+
|                                                                  |
|                    +-------------+                               |
|                    |   COAST     |<---------+                    |
|                    +------+------+          |                    |
|                           |                 |                    |
|         +-----------------+--------+        |                    |
|         |                          |        |                    |
|    Forward()                   Reverse()    |                    |
|         |                          |        |                    |
|         v                          v        |                    |
|   +-------------+           +-------------+ |                    |
|   |   FORWARD   |           |   REVERSE   | |                    |
|   +------+------+           +------+------+ |                    |
|          |                         |        |                    |
|          |   Brake()   Brake()     |        |                    |
|          |      |         |        |        |                    |
|          +------+---------+--------+        |                    |
|                 |                           |                    |
|                 v                           |                    |
|          +-------------+                    |                    |
|          |    BRAKE    |--------------------+                    |
|          +------+------+     Coast()                             |
|                 |                                                |
|              Fault                                               |
|                 |                                                |
|                 v                                                |
|          +-------------+                                         |
|          |    FAULT    |                                         |
|          +-------------+                                         |
|                                                                  |
+------------------------------------------------------------------+
```

### H-Bridge State Transitions

| Current State | Event | Next State | Action |
|---------------|-------|------------|--------|
| COAST | Forward(duty) | FORWARD | Set PWM, enable |
| COAST | Reverse(duty) | REVERSE | Set PWM, enable |
| FORWARD | Brake() | BRAKE | Both low-side ON |
| FORWARD | Coast() | COAST | All OFF |
| REVERSE | Brake() | BRAKE | Both low-side ON |
| REVERSE | Coast() | COAST | All OFF |
| ANY | Overcurrent | FAULT | Disable, log |
| FAULT | Clear + Coast | COAST | Reset fault |

---

## 6. Error Recovery State Flows

```
                    Error Recovery State Machine
+------------------------------------------------------------------+
|                                                                  |
|   +----------+                                                   |
|   | NORMAL   |                                                   |
|   +----+-----+                                                   |
|        |                                                         |
|   Error detected                                                 |
|        |                                                         |
|        v                                                         |
|   +----------+                                                   |
|   | ERROR    |----+                                              |
|   | DETECTED |    |                                              |
|   +----+-----+    |                                              |
|        |          |                                              |
|   Evaluate    Non-recoverable                                    |
|        |          |                                              |
|        v          v                                              |
|   +----------+  +----------+                                     |
|   | RETRY    |  | SHUTDOWN |                                     |
|   +----+-----+  +----------+                                     |
|        |                                                         |
|   +----+----+                                                    |
|   |         |                                                    |
| Success   Fail (max retries)                                     |
|   |         |                                                    |
|   v         v                                                    |
|   +----------+  +----------+                                     |
|   | NORMAL   |  | DEGRADED |                                     |
|   +----------+  +----+-----+                                     |
|                      |                                           |
|                 Manual reset                                     |
|                      |                                           |
|                      v                                           |
|                 +----------+                                     |
|                 | NORMAL   |                                     |
|                 +----------+                                     |
|                                                                  |
+------------------------------------------------------------------+
```

### Error Classification

| Error Type | Recoverable | Action |
|------------|-------------|--------|
| Overcurrent | Yes | Auto-retry after delay |
| Overvoltage | Yes | Wait for voltage drop |
| Undervoltage | Yes | Wait for voltage rise |
| Overtemperature | Yes | Wait for cooldown |
| Short circuit | Maybe | Retry with limit |
| Open load | Yes | Log warning |
| CAN timeout | Yes | Use default value |
| Crash detected | No | Safety shutdown |

---

## 7. Resource Cleanup Sequences

```
                    Shutdown Sequence
+------------------------------------------------------------------+
|                                                                  |
|   1. Application Layer                                           |
|      +--------------------------------------------------+       |
|      | Stop logging | Stop telemetry | Save state       |       |
|      +--------------------------------------------------+       |
|                              |                                   |
|                              v                                   |
|   2. Services Layer                                              |
|      +--------------------------------------------------+       |
|      | Disable logic | Set outputs safe | Stop timers   |       |
|      +--------------------------------------------------+       |
|                              |                                   |
|                              v                                   |
|   3. Abstraction Layer                                           |
|      +--------------------------------------------------+       |
|      | Unregister channels | Stop CAN | Flush buffers   |       |
|      +--------------------------------------------------+       |
|                              |                                   |
|                              v                                   |
|   4. Driver Layer                                                |
|      +--------------------------------------------------+       |
|      | Stop ADC DMA | Stop PWM | Reset peripherals      |       |
|      +--------------------------------------------------+       |
|                              |                                   |
|                              v                                   |
|   5. Hardware Layer                                              |
|      +--------------------------------------------------+       |
|      | All outputs OFF | Enter low-power | Wait for POR  |       |
|      +--------------------------------------------------+       |
|                                                                  |
+------------------------------------------------------------------+
```

### Safe State Definition

```c
void PMU_EnterSafeState(void) {
    // 1. Disable all PROFET outputs
    for (int i = 0; i < 30; i++) {
        PMU_PROFET_SetDuty(i, 0);
        PMU_PROFET_Disable(i);
    }

    // 2. Set H-bridges to coast
    for (int i = 0; i < 4; i++) {
        PMU_HBridge_Coast(i);
    }

    // 3. Disable logic execution
    PMU_LogicFunctions_DisableAll();

    // 4. Send CAN error message
    PMU_CAN_SendErrorFrame(ERROR_SAFE_STATE);

    // 5. Set status LEDs
    PMU_LED_SetAll(LED_RED);

    // 6. Log event
    PMU_Log_Event(EVENT_SAFE_STATE_ENTERED);
}
```

---

## See Also

- [Data Flow Diagrams](data-flow-diagrams.md)
- [Component Interactions](component-interactions.md)
- [Protection Circuits](../architecture/unified-channel-system.md#10-error-handling)

---

**Document Version:** 1.0
**Last Updated:** December 2024
