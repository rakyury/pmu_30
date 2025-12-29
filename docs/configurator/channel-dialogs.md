# Channel Configuration Dialogs

This document describes all channel configuration dialogs available in the PMU-30 Configurator.

## Common Dialog Features

All dialogs share these features:

- **Dark theme** styling
- **Channel name** field (user-friendly name)
- **Channel ID** auto-generation or manual entry
- **OK/Cancel** buttons
- **Validation** with error messages
- **Unit** and **decimals** configuration (where applicable)

## Input Dialogs

### Digital Input Dialog

Configure a digital input channel.

```
+--------------------------------------------------+
| Digital Input Configuration                       |
+--------------------------------------------------+
| Name: [Ignition Switch_____________]             |
| Pin:  [D1 ▼]                                     |
|                                                  |
| Type: [● Switch Active High]                     |
|       [○ Switch Active Low]                      |
|       [○ Frequency]                              |
|       [○ RPM]                                    |
|                                                  |
| Pull: [● None] [○ Pull-up] [○ Pull-down]        |
|                                                  |
| Debounce: [10__] ms                              |
|                                                  |
| (RPM only)                                       |
| Pulses per revolution: [2__]                     |
|                                                  |
|                    [Cancel] [OK]                 |
+--------------------------------------------------+
```

| Field | Description |
|-------|-------------|
| Name | User-friendly channel name |
| Pin | D1-D20 selection |
| Type | Input behavior type |
| Pull | Internal pull resistor |
| Debounce | Software debounce time |
| Pulses/rev | For RPM calculation |

### Analog Input Dialog

Configure an analog input channel.

```
+--------------------------------------------------+
| Analog Input Configuration                        |
+--------------------------------------------------+
| Name: [Fuel Level__________________]             |
| Pin:  [A1 ▼]                                     |
|                                                  |
| Type: [Linear ▼]                                 |
|                                                  |
| --- Linear Scaling ---                           |
| Input Range:                                     |
|   Min Voltage: [0.50] V   Max Voltage: [4.50] V |
| Output Range:                                    |
|   Min Value: [0____]      Max Value: [100__]    |
|                                                  |
| Unit: [%_____]  Decimals: [1 ▼]                  |
|                                                  |
| Pull: [○ None] [● Pull-up] [○ Pull-down]        |
|                                                  |
|                    [Cancel] [OK]                 |
+--------------------------------------------------+
```

**Type Options:**
- Linear - Voltage to value scaling
- Switch Active High - Binary with threshold
- Switch Active Low - Inverted binary
- Calibrated - Lookup table interpolation
- Rotary - Discrete position detection

### CAN Input Dialog

Configure a CAN RX signal extraction.

```
+--------------------------------------------------+
| CAN Input Configuration                          |
+--------------------------------------------------+
| Name: [Engine RPM__________________]             |
|                                                  |
| Message ID: [0x100____] [● Std] [○ Ext]         |
| CAN Bus:    [CAN1 ▼]                             |
|                                                  |
| --- Signal Extraction ---                        |
| Start Bit:  [0___]      Length: [16__] bits     |
| Byte Order: [● Intel (little)] [○ Motorola]     |
| Signed:     [○ Yes] [● No]                      |
|                                                  |
| --- Scaling ---                                  |
| Scale:  [0.25__]   Offset: [0_____]             |
| Unit:   [rpm___]   Decimals: [0 ▼]              |
|                                                  |
|                    [Cancel] [OK]                 |
+--------------------------------------------------+
```

## Output Dialogs

### Power Output Dialog

Configure a power output channel.

```
+--------------------------------------------------+
| Power Output Configuration                        |
+--------------------------------------------------+
| Name: [Headlights__________________]             |
|                                                  |
| Pins: [☑ O1] [☑ O2] [☑ O3] [☐ O4] ...          |
|       (Select multiple for higher current)       |
|                                                  |
| Control Source: [Logic Channel ▼]                |
|   Channel: [Headlight Logic ▼]                   |
|                                                  |
| PWM Frequency: [1000_] Hz                        |
| Soft Start:    [100__] ms                        |
|                                                  |
| --- Protection ---                               |
| Current Limit: [40___] A                         |
| Retry Delay:   [1000_] ms                        |
|                                                  |
|                    [Cancel] [OK]                 |
+--------------------------------------------------+
```

**Control Source Options:**
- Direct (always on)
- Digital Input
- Analog Input (threshold)
- Logic Channel
- CAN Input
- Timer

### H-Bridge Dialog

Configure an H-Bridge motor controller.

```
+--------------------------------------------------+
| H-Bridge Configuration                           |
+--------------------------------------------------+
| Name: [Window Motor________________]             |
|                                                  |
| H-Bridge: [HB1 ▼]                               |
|                                                  |
| Mode: [● Standard]                              |
|       [○ Wiper (auto-park)]                     |
|       [○ PID Control]                           |
|                                                  |
| --- Standard Mode ---                            |
| Control Source: [Digital Input ▼]                |
| Forward Input:  [Window Up ▼]                    |
| Reverse Input:  [Window Down ▼]                  |
| PWM: [255__] (0-255)                            |
|                                                  |
| Polarity: [● Normal] [○ Inverted]               |
|                                                  |
|                    [Cancel] [OK]                 |
+--------------------------------------------------+
```

### CAN Output Dialog

Configure a CAN TX message.

```
+--------------------------------------------------+
| CAN Output Configuration                         |
+--------------------------------------------------+
| Name: [Dashboard Status____________]             |
|                                                  |
| Message ID: [0x200____] [● Std] [○ Ext]         |
| CAN Bus:    [CAN1 ▼]                             |
| Cycle Time: [100__] ms (0 = on-change only)     |
|                                                  |
| --- Signals ---                                  |
| [+] Add Signal                                   |
|                                                  |
| | Name       | Source      | Start | Len | Scl |
| | lights     | Light Logic | 0     | 8   | 1   |
| | wipers     | Wiper State | 8     | 8   | 1   |
| |            |             |       |     |     |
|                                                  |
|                    [Cancel] [OK]                 |
+--------------------------------------------------+
```

## Function Dialogs

### Logic Dialog

Configure a logic function channel.

```
+--------------------------------------------------+
| Logic Function Configuration                     |
+--------------------------------------------------+
| Name: [Headlight Logic_____________]             |
|                                                  |
| Function: [AND ▼]                               |
|                                                  |
| Inputs:                                          |
|   [Ignition ▼______] [NOT ☐]                    |
|   [Light Switch ▼__] [NOT ☐]                    |
|   [+ Add Input]                                  |
|                                                  |
| --- Available Functions ---                      |
| AND, OR, XOR, NOT, NAND, NOR                    |
| GT, LT, GE, LE, EQ, NE (comparisons)            |
| RISING_EDGE, FALLING_EDGE, CHANGED              |
| LATCH, SR_FLIP_FLOP, TOGGLE                     |
|                                                  |
|                    [Cancel] [OK]                 |
+--------------------------------------------------+
```

### Number Dialog

Configure a math/number channel.

```
+--------------------------------------------------+
| Number Channel Configuration                     |
+--------------------------------------------------+
| Name: [Average Temperature_________]             |
|                                                  |
| Operation: [AVERAGE ▼]                          |
|                                                  |
| Inputs:                                          |
|   [Board Temp L ▼___]                           |
|   [Board Temp R ▼___]                           |
|   [+ Add Input]                                  |
|                                                  |
| Unit: [°C____]  Decimals: [1 ▼]                  |
|                                                  |
| --- Available Operations ---                     |
| ADD, SUBTRACT, MULTIPLY, DIVIDE                 |
| MIN, MAX, AVERAGE, ABS                          |
| SCALE (value × scale + offset)                  |
| CLAMP (min/max limits)                          |
|                                                  |
|                    [Cancel] [OK]                 |
+--------------------------------------------------+
```

### Timer Dialog

Configure a timer channel.

```
+--------------------------------------------------+
| Timer Configuration                              |
+--------------------------------------------------+
| Name: [Turn Signal Timer___________]             |
|                                                  |
| Mode: [● Delay ON]                              |
|       [○ Delay OFF]                             |
|       [○ One-Shot]                              |
|       [○ Retriggerable]                         |
|                                                  |
| Trigger: [Turn Signal Switch ▼]                  |
| Delay:   [500__] ms                             |
|                                                  |
| Reset On: [○ None]                              |
|           [● Input Low]                         |
|           [○ Timeout]                           |
|                                                  |
|                    [Cancel] [OK]                 |
+--------------------------------------------------+
```

### Filter Dialog

Configure a signal filter.

```
+--------------------------------------------------+
| Filter Configuration                             |
+--------------------------------------------------+
| Name: [Fuel Level Filter___________]             |
|                                                  |
| Input: [Fuel Level Raw ▼]                        |
|                                                  |
| Type: [● Moving Average]                        |
|       [○ Low Pass]                              |
|       [○ Median]                                |
|       [○ Rate Limiter]                          |
|                                                  |
| --- Moving Average ---                           |
| Samples: [10__]                                  |
|                                                  |
| Unit: [%_____]  Decimals: [1 ▼]                  |
|                                                  |
|                    [Cancel] [OK]                 |
+--------------------------------------------------+
```

### Switch Dialog

Configure a state machine switch.

```
+--------------------------------------------------+
| Switch Configuration                             |
+--------------------------------------------------+
| Name: [Mode Selector_______________]             |
|                                                  |
| Number of States: [3 ▼]                          |
|                                                  |
| Transitions:                                     |
| State 0 → State 1: [Mode Button ▼] Rising Edge  |
| State 1 → State 2: [Mode Button ▼] Rising Edge  |
| State 2 → State 0: [Mode Button ▼] Rising Edge  |
|                                                  |
| Initial State: [0 ▼]                             |
|                                                  |
| Output Values:                                   |
| State 0: [0____]  Label: [Off_____]             |
| State 1: [500__]  Label: [Low_____]             |
| State 2: [1000_]  Label: [High____]             |
|                                                  |
|                    [Cancel] [OK]                 |
+--------------------------------------------------+
```

## Table Dialogs

### 2D Table Dialog

Configure a 2D lookup table.

```
+--------------------------------------------------+
| 2D Table Configuration                           |
+--------------------------------------------------+
| Name: [PWM Curve___________________]             |
|                                                  |
| Input: [Throttle Position ▼]                     |
|                                                  |
| Table Data:                                      |
| +--------+--------+                              |
| | Input  | Output |                              |
| +--------+--------+                              |
| |   0    |   0    |                              |
| |  25    |  150   |                              |
| |  50    |  400   |                              |
| |  75    |  700   |                              |
| | 100    | 1000   |                              |
| +--------+--------+                              |
| [+ Add Row] [- Remove Row]                       |
|                                                  |
| Interpolation: [● Linear] [○ Step]              |
|                                                  |
| Output Unit: [_____]  Decimals: [0 ▼]            |
|                                                  |
|                    [Cancel] [OK]                 |
+--------------------------------------------------+
```

### 3D Table Dialog

Configure a 3D lookup table.

```
+--------------------------------------------------+
| 3D Table Configuration                           |
+--------------------------------------------------+
| Name: [Fuel Map____________________]             |
|                                                  |
| X Input: [RPM ▼_____________]                    |
| Y Input: [MAP ▼_____________]                    |
|                                                  |
| Table Data (RPM × MAP):                          |
|        | 0kPa | 50kPa | 100kPa | 150kPa |       |
| +------+------+-------+--------+--------+       |
| | 1000 |  10  |   15  |   20   |   25   |       |
| | 2000 |  12  |   18  |   25   |   32   |       |
| | 3000 |  14  |   22  |   30   |   40   |       |
| | 4000 |  16  |   26  |   36   |   48   |       |
| +------+------+-------+--------+--------+       |
|                                                  |
| [+ Add Row] [+ Add Column]                       |
|                                                  |
| Interpolation: [● Bilinear] [○ Step]            |
|                                                  |
|                    [Cancel] [OK]                 |
+--------------------------------------------------+
```

## Advanced Dialogs

### PID Controller Dialog

Configure a PID control loop.

```
+--------------------------------------------------+
| PID Controller Configuration                     |
+--------------------------------------------------+
| Name: [Fan Speed Controller________]             |
|                                                  |
| Setpoint Source: [Target Temp ▼]                |
| Feedback Source: [Actual Temp ▼]                |
| Output Target:   [Fan PWM ▼____]                |
|                                                  |
| --- PID Gains ---                                |
| Kp (Proportional): [1.00__]                     |
| Ki (Integral):     [0.10__]                     |
| Kd (Derivative):   [0.05__]                     |
|                                                  |
| --- Limits ---                                   |
| Output Min: [0____]   Output Max: [1000_]       |
| Integral Min: [-500]  Integral Max: [500__]     |
|                                                  |
| Update Rate: [100_] ms                           |
|                                                  |
|                    [Cancel] [OK]                 |
+--------------------------------------------------+
```

### Lua Script Dialog

Configure a Lua script channel.

```
+--------------------------------------------------+
| Lua Script Configuration                         |
+--------------------------------------------------+
| Name: [Custom Logic________________]             |
|                                                  |
| +------------------------------------------------+
| | -- Lua Script Editor                          |
| | function update()                              |
| |     local rpm = get_channel("Engine_RPM")     |
| |     local temp = get_channel("Coolant_Temp")  |
| |                                                |
| |     if rpm > 6000 and temp > 100 then         |
| |         set_output("Warning_Light", 1)        |
| |     else                                       |
| |         set_output("Warning_Light", 0)        |
| |     end                                        |
| | end                                            |
| +------------------------------------------------+
|                                                  |
| [Validate] [Format]                              |
|                                                  |
|                    [Cancel] [OK]                 |
+--------------------------------------------------+
```

### BlinkMarine Keypad Dialog

Configure a CAN keypad.

```
+--------------------------------------------------+
| BlinkMarine Keypad Configuration                 |
+--------------------------------------------------+
| Name: [Dashboard Keypad____________]             |
|                                                  |
| CAN ID: [0x18EF0400]                            |
| CAN Bus: [CAN1 ▼]                               |
|                                                  |
| Buttons:                                         |
| | # | Label       | LED Control        | Color |
| | 1 | Lights      | [Headlight Logic▼] | Blue  |
| | 2 | Hazards     | [Hazard Logic ▼__] | Red   |
| | 3 | Wipers      | [Wiper State ▼___] | Green |
| | 4 | Fan         | [Fan Enable ▼____] | Blue  |
|                                                  |
| LED Brightness: [100_] %                         |
|                                                  |
|                    [Cancel] [OK]                 |
+--------------------------------------------------+
```

## Validation Rules

All dialogs enforce:

| Rule | Description |
|------|-------------|
| Unique names | No duplicate channel names |
| Valid references | Source channels must exist |
| No circular deps | Channels can't reference themselves |
| Range limits | Values within valid ranges |
| Required fields | Name and type are mandatory |
