# Data Flow Diagrams

**Version:** 1.0
**Date:** December 2024

---

## 1. System Overview Data Flow

```
                           PMU-30 Data Flow Overview
+-------------------------------------------------------------------------+
|                                                                         |
|  INPUTS                    PROCESSING                    OUTPUTS        |
|  ======                    ==========                    =======        |
|                                                                         |
|  +--------+               +-------------+               +--------+      |
|  | ADC    |-------------->| Channel     |-------------->| PROFET |      |
|  | (0-19) |               | Update      |               | (0-29) |      |
|  +--------+               | (1kHz)      |               +--------+      |
|                           +------+------+                               |
|  +--------+                      |                      +--------+      |
|  | Digital|----------------------+                      | H-Brg  |      |
|  | (0-7)  |                      |                      | (0-3)  |      |
|  +--------+                      v                      +--------+      |
|                           +-------------+                               |
|  +--------+               | Logic       |               +--------+      |
|  | CAN RX |-------------->| Functions   |-------------->| CAN TX |      |
|  | (4 bus)|               | (500Hz)     |               | (4 bus)|      |
|  +--------+               +------+------+               +--------+      |
|                                  |                                      |
|  +--------+                      |                      +--------+      |
|  | System |----------------------+                      | LEDs   |      |
|  | Sensors|                                             | Status |      |
|  +--------+                                             +--------+      |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 2. Unified Channel Data Flow

```
                    Channel Data Flow (1kHz Update)
+------------------------------------------------------------------------+
|                                                                        |
|   HARDWARE LAYER              ABSTRACTION LAYER         OUTPUT LAYER   |
|                                                                        |
|   +----------+                +---------------+                        |
|   | ADC DMA  |----[raw]----->| Input Channel |                        |
|   | Buffer   |                | Processing    |                        |
|   +----------+                |  - Scale      |                        |
|                               |  - Filter     |                        |
|   +----------+                |  - Calibrate  |                        |
|   | GPIO     |----[state]--->|               |                        |
|   | Register |                +-------+-------+                        |
|   +----------+                        |                                |
|                                       v                                |
|   +----------+                +---------------+         +----------+   |
|   | CAN RX   |----[frames]-->| Channel       |-------->| PROFET   |   |
|   | Buffers  |                | Registry      |         | Driver   |   |
|   +----------+                | (1024 ch)     |         +----------+   |
|                               |               |                        |
|   +----------+                |  GetValue()   |         +----------+   |
|   | Temp     |----[data]---->|  SetValue()   |-------->| H-Bridge |   |
|   | Sensors  |                |               |         | Driver   |   |
|   +----------+                +-------+-------+         +----------+   |
|                                       |                                |
|   +----------+                        |                 +----------+   |
|   | IMU      |----[accel]--->        |                 | CAN TX   |   |
|   | Sensor   |                        +---------------->| Queue    |   |
|   +----------+                                          +----------+   |
|                                                                        |
+------------------------------------------------------------------------+
```

---

## 3. Logic Function Execution Pipeline

```
                Logic Function Pipeline (500Hz)
+------------------------------------------------------------------------+
|                                                                        |
|   STAGE 1: INPUT COLLECTION                                            |
|   +----------------------------------------------------------------+  |
|   |                                                                |  |
|   |   Channel 0 ----+                                              |  |
|   |   Channel 1 ----+---> [ Input Buffer ]                         |  |
|   |   Channel 2 ----+        (up to 8 inputs per function)         |  |
|   |      ...                                                       |  |
|   |                                                                |  |
|   +----------------------------------------------------------------+  |
|                                    |                                   |
|                                    v                                   |
|   STAGE 2: FUNCTION EXECUTION                                          |
|   +----------------------------------------------------------------+  |
|   |                                                                |  |
|   |   Function[0] --> Function[1] --> ... --> Function[63]         |  |
|   |        |              |                        |               |  |
|   |        v              v                        v               |  |
|   |   +--------+     +--------+              +--------+            |  |
|   |   | Execute|     | Execute|              | Execute|            |  |
|   |   | (ADD)  |     | (CMP)  |              | (PID)  |            |  |
|   |   +--------+     +--------+              +--------+            |  |
|   |        |              |                        |               |  |
|   +--------+--------------+------------------------+---------------+  |
|            |              |                        |                   |
|            v              v                        v                   |
|   STAGE 3: OUTPUT WRITE                                                |
|   +----------------------------------------------------------------+  |
|   |                                                                |  |
|   |   --> Channel 200    --> Channel 201    --> Channel 100        |  |
|   |   (Virtual Output)   (Virtual Output)   (Physical Output)      |  |
|   |                                                                |  |
|   +----------------------------------------------------------------+  |
|                                                                        |
+------------------------------------------------------------------------+
```

---

## 4. Inter-Function Communication

```
           Function Chaining Through Channels
+------------------------------------------------------------------+
|                                                                  |
|   Function 0          Function 1          Function 2             |
|   (Scale)             (Compare)           (AND)                  |
|                                                                  |
|   Input:              Input:              Input:                 |
|   Ch 0 (ADC)          Ch 200 (scaled)     Ch 201 (compare)       |
|         |                   |             Ch 202 (other)         |
|         v                   v                   |                |
|   +---------+         +---------+               v                |
|   | SCALE   |         | GREATER |         +---------+            |
|   | *0.024  |         | > 850   |         | AND     |            |
|   | -400    |         |         |         |         |            |
|   +---------+         +---------+         +---------+            |
|         |                   |                   |                |
|         v                   v                   v                |
|   Output:             Output:             Output:                |
|   Ch 200              Ch 201              Ch 100 (PROFET)        |
|                                                                  |
|   Data flow: ADC -> Scale -> Compare -> AND -> Output            |
|                                                                  |
+------------------------------------------------------------------+
```

---

## 5. Error Propagation Paths

```
                    Error Detection and Handling
+------------------------------------------------------------------+
|                                                                  |
|   ERROR SOURCES           DETECTION           RESPONSE           |
|                                                                  |
|   +----------+         +-----------+        +-----------+        |
|   | ADC      |-------->| Value     |------->| Use       |        |
|   | Fault    |         | Out of    |        | Default   |        |
|   +----------+         | Range     |        | Value     |        |
|                        +-----------+        +-----------+        |
|                                                                  |
|   +----------+         +-----------+        +-----------+        |
|   | CAN      |-------->| Timeout   |------->| Use Last  |        |
|   | Timeout  |         | Detection |        | Good Val  |        |
|   +----------+         +-----------+        +-----------+        |
|                                                                  |
|   +----------+         +-----------+        +-----------+        |
|   | PROFET   |-------->| Overcurr  |------->| Retry or  |        |
|   | Fault    |         | Detection |        | Shutdown  |        |
|   +----------+         +-----------+        +-----------+        |
|                                                                  |
|   +----------+         +-----------+        +-----------+        |
|   | Division |-------->| Div by    |------->| Return    |        |
|   | by Zero  |         | Zero Chk  |        | MAX/MIN   |        |
|   +----------+         +-----------+        +-----------+        |
|                                                                  |
|   All errors set PMU_CHANNEL_FLAG_FAULT on affected channel      |
|                                                                  |
+------------------------------------------------------------------+
```

---

## 6. State Synchronization

```
              Multi-Task State Synchronization
+------------------------------------------------------------------+
|                                                                  |
|   TASK 1: Main Loop (1kHz)                                       |
|   +----------------------------------------------------------+  |
|   |                                                          |  |
|   |   ADC Sample --> Update Channels --> Check Faults        |  |
|   |                         |                                |  |
|   +-------------------------+--------------------------------+  |
|                             |                                    |
|                             v                                    |
|                    +----------------+                            |
|                    | Channel        |                            |
|                    | Registry       | <-- Mutex Protected        |
|                    | (Shared State) |                            |
|                    +----------------+                            |
|                             ^                                    |
|                             |                                    |
|   +-------------------------+--------------------------------+  |
|   |                         |                                |  |
|   |   Read Channels --> Execute --> Write Channels           |  |
|   |                                                          |  |
|   +----------------------------------------------------------+  |
|   TASK 2: Logic Task (500Hz)                                     |
|                                                                  |
|   +----------------------------------------------------------+  |
|   |                                                          |  |
|   |   Receive CAN --> Parse Signals --> Update Channels      |  |
|   |                                                          |  |
|   +----------------------------------------------------------+  |
|   TASK 3: CAN Task (Event-driven)                                |
|                                                                  |
+------------------------------------------------------------------+
```

---

## 7. CAN Bus Data Flow

```
                    CAN Bus Communication Flow
+------------------------------------------------------------------+
|                                                                  |
|   RECEIVE PATH                                                   |
|   ============                                                   |
|                                                                  |
|   CAN Bus --> CAN Controller --> RX FIFO --> Signal Parser       |
|                                                  |                |
|                                                  v                |
|   +---------------------------------------------------+         |
|   | Signal Extraction:                                |         |
|   |   - Message ID filter                             |         |
|   |   - Start bit, length extraction                  |         |
|   |   - Endian conversion                             |         |
|   |   - Factor/Offset scaling                         |         |
|   +---------------------------------------------------+         |
|                                                  |                |
|                                                  v                |
|                                           Channel Update          |
|                                                                  |
|   TRANSMIT PATH                                                  |
|   =============                                                  |
|                                                                  |
|   Channel Value --> Signal Packer --> TX Queue --> CAN Bus       |
|                          |                                       |
|                          v                                       |
|   +---------------------------------------------------+         |
|   | Signal Packing:                                   |         |
|   |   - Read source channels                          |         |
|   |   - Apply factor/offset                           |         |
|   |   - Pack into message bytes                       |         |
|   |   - Set message ID, DLC                           |         |
|   +---------------------------------------------------+         |
|                                                                  |
+------------------------------------------------------------------+
```

---

## 8. Protection System Flow

```
                Protection System Data Flow
+------------------------------------------------------------------+
|                                                                  |
|   MONITORING                EVALUATION              ACTION       |
|                                                                  |
|   +----------+            +------------+         +----------+    |
|   | Battery  |----------->| Voltage    |-------->| Shutdown |    |
|   | Voltage  |            | Thresholds |         | Outputs  |    |
|   +----------+            +------------+         +----------+    |
|                                                                  |
|   +----------+            +------------+         +----------+    |
|   | Total    |----------->| Current    |-------->| Limit    |    |
|   | Current  |            | Limit      |         | Outputs  |    |
|   +----------+            +------------+         +----------+    |
|                                                                  |
|   +----------+            +------------+         +----------+    |
|   | PROFET   |----------->| Per-channel|-------->| Disable  |    |
|   | Current  |            | Limits     |         | Channel  |    |
|   +----------+            +------------+         +----------+    |
|                                                                  |
|   +----------+            +------------+         +----------+    |
|   | Board    |----------->| Temp       |-------->| Derate   |    |
|   | Temp     |            | Thresholds |         | or Stop  |    |
|   +----------+            +------------+         +----------+    |
|                                                                  |
|   +----------+            +------------+         +----------+    |
|   | IMU      |----------->| Crash      |-------->| Safety   |    |
|   | Accel    |            | Detection  |         | Shutdown |    |
|   +----------+            +------------+         +----------+    |
|                                                                  |
+------------------------------------------------------------------+
```

---

## See Also

- [Component Interactions](component-interactions.md)
- [State Machines](state-machines.md)
- [Unified Channel System](../architecture/unified-channel-system.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024
