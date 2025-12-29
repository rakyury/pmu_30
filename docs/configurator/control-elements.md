# Control Elements: PID, Timers, and Tables

This document covers the advanced control elements available in the PMU-30 Configurator: PID controllers for closed-loop control, Timers for time-based operations, and Tables for lookup/interpolation functions.

---

## PID Controller

The PID controller is a **Proportional-Integral-Derivative** controller whose purpose is to maintain a measured value (Process Value) at a desired level called the **Set Point**. It operates in a closed feedback loop, continuously calculating the error between the set point and measured value, then adjusting its output to minimize this error.

### How PID Control Works

```
                    ┌─────────────────────────────────────────────┐
                    │              PID Controller                  │
                    │                                              │
Set Point ──┬──────►│  ┌───────────┐                              │
            │       │  │Proportional├──► P Term ──┐               │
            │ Error │  │  (Kp × e)  │              │               │
            ├──────►│  └───────────┘              │               │
            │       │                             │    ┌───────┐  │
            │       │  ┌───────────┐              ├───►│  SUM  ├──┼──► Output
            │       │  │ Integral  ├──► I Term ──┤    └───────┘  │
            │       │  │(Ki × ∫e dt)│              │        ▲     │
            │       │  └───────────┘              │        │     │
            │       │                             │   Feed Forward
            │       │  ┌───────────┐              │   Custom Term │
            │       │  │Derivative ├──► D Term ──┘               │
            │       │  │(Kd × de/dt)│                             │
Process ────┴──────►│  └───────────┘                              │
Value               │                                              │
                    └─────────────────────────────────────────────┘
```

**Output Formula:**
```
Output = Feed Forward + Custom Term + (P Term) + (I Term) + (D Term)

Where:
  P Term = Kp × error
  I Term = Ki × ∫error dt  (clamped to integral limits)
  D Term = Kd × d(error)/dt
  error  = Set Point - Process Value
```

### Configuration Options

#### Basic Settings

| Parameter | Description |
|-----------|-------------|
| **Name** | PID controller name (used as channel prefix) |
| **Set point channel** | Channel defining the desired target value |
| **Process value channel** | Channel providing the measured/actual value |
| **Activation channel** | Channel that enables/disables the controller |

#### Gain Parameters

| Parameter | Description |
|-----------|-------------|
| **Proportional gain (Kp)** | Determines response magnitude to current error. Higher values = faster response but may cause oscillation |
| **Integral gain (Ki)** | Determines response to accumulated error over time. Eliminates steady-state error but may cause overshoot |
| **Derivative gain (Kd)** | Determines response to rate of change. Reduces overshoot and oscillation but sensitive to noise |

#### Limits and Output

| Parameter | Description |
|-----------|-------------|
| **Feed forward** | Constant value added to output (open-loop contribution) |
| **Integral limit min** | Minimum value for integral term (prevents windup) |
| **Integral limit max** | Maximum value for integral term (prevents windup) |
| **Custom term** | Channel value added to output (independent of PID calculation) |
| **Time step** | Update interval for PID calculations |
| **Output min** | Minimum allowed output value (duty cycle floor) |
| **Output max** | Maximum allowed output value (duty cycle ceiling) |
| **Control direction** | Normal (increase setpoint → increase output) or Inverted |

### Activation Behavior

When the **Activation channel** is set to `false`:
- Controller output = Feed Forward + Custom Term value
- Proportional, Integral, and Derivative terms are set to **zero**
- Integral accumulator is reset (prevents windup during inactive periods)

When the **Activation channel** is set to `true`:
- Full PID calculation is performed
- All terms contribute to output

### Output Channels

Each PID controller creates the following sub-channels:

| Channel | Description |
|---------|-------------|
| `{name}.output` | Final controller output value |
| `{name}.proportionalTerm` | Current P term contribution |
| `{name}.integralTerm` | Current I term contribution |
| `{name}.derivativeTerm` | Current D term contribution |
| `{name}.error` | Current error (setpoint - process value) |

### Control Direction

| Mode | Behavior | Use Case |
|------|----------|----------|
| **Normal** | Increasing setpoint → Increasing output | Heating, acceleration, pressure increase |
| **Inverted** | Increasing setpoint → Decreasing output | Cooling, braking, pressure reduction |

### Integral Windup Prevention

The integral limits prevent **integral windup**, a condition where the integral term accumulates to very large values during sustained errors (e.g., when the system is saturated). This can cause:
- Large overshoot when the error finally decreases
- Slow response due to "unwinding" the accumulated integral

**Best Practice:** Set integral limits to reasonable values based on your expected output range.

### Example Configuration: Boost Controller

```
Name:                   pid_boost
Set point channel:      c_targetBoost
Process value channel:  a_manifoldPressure
Activation channel:     c_boostEnabled

Feed forward:           30.0
Proportional gain:      5.0
Integral gain:          0.5
Derivative gain:        0.1

Integral limit min:     -20.0
Integral limit max:     50.0
Custom term:            (none)
Time step:              20 ms

Output min:             0.0
Output max:             100.0
Control direction:      Normal
```

**Explanation:**
- Target boost pressure is defined by `c_targetBoost`
- Actual boost is measured by `a_manifoldPressure`
- Feed forward of 30% provides baseline wastegate duty
- PID gains adjust for error compensation
- Output drives wastegate solenoid (0-100% duty cycle)

### Example Configuration: Idle Speed Controller

```
Name:                   pid_idle
Set point channel:      c_targetRPM
Process value channel:  d_engineRPM
Activation channel:     c_idleActive

Feed forward:           25.0
Proportional gain:      0.02
Integral gain:          0.005
Derivative gain:        0.001

Integral limit min:     -10.0
Integral limit max:     30.0
Time step:              50 ms

Output min:             5.0
Output max:             60.0
Control direction:      Normal
```

### Tuning Guidelines

#### Start with P Only
1. Set I and D gains to 0
2. Increase P until system oscillates
3. Reduce P to ~60% of oscillation value

#### Add Integral
1. Start with small I gain
2. Increase until steady-state error is eliminated
3. Reduce if overshoot is excessive

#### Add Derivative (if needed)
1. Start with small D gain
2. Increase to reduce overshoot
3. Reduce if system becomes noisy or twitchy

#### Common Issues

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| Oscillation | P too high | Reduce Kp |
| Slow response | P too low | Increase Kp |
| Overshoot | I too high, D too low | Reduce Ki, increase Kd |
| Steady-state error | I too low or missing | Increase Ki |
| Noise amplification | D too high | Reduce Kd, add filtering |

---

## Timers - Counting Time

Timers are used for counting time, useful for implementing delays, timeouts, and timed sequences.

### Timer Modes

| Mode | Description |
|------|-------------|
| **Count up** | Counts from zero to the set limit value |
| **Count down** | Counts from the set limit value to zero |

### Configuration Options

| Parameter | Description |
|-----------|-------------|
| **Channel name** | Timer name (used as channel prefix) |
| **Start channel** | Channel that triggers timer start |
| **Start edge** | Edge type to start timer: Rising or Falling |
| **Stop channel** | Channel that stops the timer |
| **Stop edge** | Edge type to stop timer: Rising or Falling |
| **Mode** | Count up or Count down |
| **Limit [hours]** | Hours component of time limit |
| **Limit [minutes]** | Minutes component of time limit |
| **Limit [seconds]** | Seconds component of time limit |

### Timer Behavior

```
Start/Stop Logic:

  Start Channel ─────┐
                     │    ┌─────────────┐
  Start Edge ────────┼───►│             │
                     │    │    Timer    ├───► .value
  Stop Channel ──────┼───►│   Engine    ├───► .elapsed
                     │    │             ├───► .running
  Stop Edge ─────────┘    └─────────────┘
```

**Start Behavior:**
- Timer starts when the defined edge (Rising/Falling) appears on the Start channel
- If timer is already running, the start edge is **ignored**
- Start edge only triggers after timer is stopped or has finished counting

**Stop Behavior:**
- Timer stops when the defined edge appears on the Stop channel
- After stopping, the next start edge will reset the timer to its initial value

**Same Channel Start/Stop:**
Starting and stopping can use the **same channel and edge**. The timer will alternate between starting and stopping on each edge.

### Output Channels

Each timer creates three sub-channels:

| Channel | Description |
|---------|-------------|
| `{name}.value` | Current time value in seconds (resolution: 0.01s) |
| `{name}.elapsed` | `1` when time has elapsed, `0` otherwise (resets on next start) |
| `{name}.running` | `1` when timer is actively counting, `0` when stopped |

### Example Configuration: Engine Run Timer

```
Channel name:    r_timer1
Start channel:   c_csb_switch1
Start edge:      Rising
Stop channel:    c_csb_switch1
Stop edge:       Rising
Mode:            Count up
Limit [hours]:   0 h
Limit [minutes]: 5 min
Limit [seconds]: 0 s
```

**Behavior:**
- Starts counting when `c_csb_switch1` goes high
- Counts up from 0 to 5 minutes
- `r_timer1.elapsed` becomes 1 when 5 minutes pass
- Same channel/edge for start and stop allows toggle behavior

### Example Configuration: Fuel Pump Prime Timer

```
Channel name:    t_fuelPrime
Start channel:   d_ignitionOn
Start edge:      Rising
Stop channel:    d_engineRunning
Stop edge:       Rising
Mode:            Count down
Limit [hours]:   0 h
Limit [minutes]: 0 min
Limit [seconds]: 5 s
```

**Behavior:**
- Starts 5-second countdown when ignition turns on
- Counts down from 5 to 0
- Stops early if engine starts running
- Use `t_fuelPrime.running` to control fuel pump relay

### Example Configuration: Turbo Timer

```
Channel name:    t_turboTimer
Start channel:   d_ignitionOff
Start edge:      Rising
Stop channel:    (same as start)
Stop edge:       Rising
Mode:            Count down
Limit [hours]:   0 h
Limit [minutes]: 2 min
Limit [seconds]: 0 s
```

---

## Tables - 2D and 3D Lookup

Tables provide lookup and interpolation functionality, essential for mapping sensor values to outputs, calibration curves, and complex control strategies.

### Table Types

| Type | Axes | Size Range | Use Case |
|------|------|------------|----------|
| **2D Table** | X axis only | 2×1 to 21×1 | Simple sensor calibration, single-variable lookup |
| **3D Table** | X and Y axes | 2×2 to 21×21 | Fuel/ignition maps, complex calibrations |

### Creating a Table

#### Step 1: Define Axis Channels

| Parameter | Description |
|-----------|-------------|
| **Name** | Table name (becomes the output channel) |
| **Quantity/Unit** | Unit type for output values |
| **Decimal places** | Display precision for values |
| **Axis X: channel** | Input channel for X axis lookup |
| **Axis Y: channel** | Input channel for Y axis (leave blank for 2D table) |

#### Step 2: Define Axis Range

For each axis, configure:

| Parameter | Description |
|-----------|-------------|
| **min** | Minimum axis value |
| **max** | Maximum axis value |
| **step** | Increment between axis points |
| **columns/rows** | Automatically calculated from min/max/step |

**Example:**
```
X Axis:
  Channel: adu.a1.voltage
  min: 0.000
  max: 5.000
  step: 1.000
  columns: 6

Y Axis:
  Channel: adu.a2.voltage
  min: 0.000
  max: 5.000
  step: 1.000
  rows: 6
```

#### Step 3: Fill Table Values

After clicking **Create**, the table grid appears:
- **Column headers** = X axis values
- **Row headers** = Y axis values (3D tables only)
- **Cells** = Output values for each axis intersection

The table uses **color coding** to visualize values:
- **Green** = Lower values
- **Yellow** = Mid-range values
- **Red** = Higher values

### Table Editing

#### Cell Selection
- **Click** - Select single cell
- **Shift + Click** - Select range of cells
- **Ctrl + Arrow** - Copy value to adjacent cell

#### Context Menu Commands

Right-click on the table to access editing commands:

| Command | Shortcut | Description |
|---------|----------|-------------|
| **Interpolate horizontally** | Ctrl+H | Linear interpolate selected row cells |
| **Interpolate vertically** | Ctrl+L | Linear interpolate selected column cells |
| **Interpolate diagonally** | Ctrl+D | Linear interpolate diagonal selection |
| **Equalize selection** | E | Set all selected cells to same value |
| **Transpose** | - | Swap rows and columns |
| **Copy cells** | Ctrl+C | Copy selected cells |
| **Paste cells** | Ctrl+V | Paste copied cells |

#### Row/Column Operations

| Command | Shortcut | Description |
|---------|----------|-------------|
| **Insert row above** | Alt+Ctrl+Up | Add row above selected cell |
| **Insert row below** | Alt+Ctrl+Down | Add row below selected cell |
| **Insert column before** | Alt+Ctrl+Left | Add column to left of selected cell |
| **Insert column after** | Alt+Ctrl+Right | Add column to right of selected cell |
| **Delete row** | Alt+Shift+Back | Remove row containing selected cell |
| **Delete column** | Alt+Back | Remove column containing selected cell |

#### Axis Bin Wizards

| Wizard | Description |
|--------|-------------|
| **X Axis bins wizard** | Define new column count and regenerate X axis values with interpolation |
| **Y Axis bins wizard** | Define new row count and regenerate Y axis values with interpolation |

### Interpolation

Tables use **bilinear interpolation** for values between axis points:

```
For 2D tables (single axis):
  output = interpolate(x, x1, x2, y1, y2)

For 3D tables (two axes):
  output = bilinear_interpolate(x, y, corners[4])

Where:
  - x, y = current input values
  - corners = nearest 4 table values
```

This means smooth transitions between defined points rather than step changes.

### Example: Coolant Temperature Sensor Calibration (2D)

```
Name: t_coolantTemp
Axis X: a_coolantSensor (voltage)

X Axis:     0.5V    1.0V    1.5V    2.0V    2.5V    3.0V    3.5V    4.0V    4.5V
Output:     120°C   100°C   85°C    70°C    50°C    30°C    10°C    -10°C   -30°C
```

**Use:** Converts raw NTC sensor voltage to temperature in degrees Celsius.

### Example: Boost Target Map (3D)

```
Name: t_boostTarget
Axis X: d_engineRPM
Axis Y: a_throttlePosition

             1000   2000   3000   4000   5000   6000   7000
    100%     0.8    1.0    1.2    1.4    1.5    1.5    1.4
     80%     0.6    0.8    1.0    1.2    1.3    1.3    1.2
     60%     0.4    0.6    0.8    1.0    1.1    1.1    1.0
     40%     0.2    0.4    0.5    0.6    0.7    0.7    0.6
     20%     0.0    0.1    0.2    0.3    0.3    0.3    0.3
      0%     0.0    0.0    0.0    0.0    0.0    0.0    0.0

Output: Target boost pressure in bar
```

**Use:** Defines target boost pressure based on RPM and throttle position.

### Example: PWM Fan Control (2D)

```
Name: t_fanDuty
Axis X: t_coolantTemp (from calibration table above)

Temp:       60°C    70°C    80°C    90°C    100°C   110°C
Duty:       0%      20%     40%     60%     80%     100%
```

**Use:** Controls radiator fan speed based on coolant temperature.

### Tips for Table Design

1. **Start simple** - Begin with fewer axis points, add resolution where needed

2. **Use meaningful ranges** - Set axis min/max to cover actual operating range

3. **Consider resolution** - More points = smoother control but more tuning effort

4. **Use interpolation tools** - After setting corner values, use Ctrl+H/L/D to fill intermediate cells

5. **Test boundary conditions** - Verify behavior at axis limits

6. **Chain tables** - Output of one table can be input to another (e.g., sensor calibration → control lookup)

---

## Switches - Virtual Switches and Counters

Switches convert **momentary/non-latching inputs** (like push buttons from analog or CAN sources) into **latching switches** that maintain state. They also function as counters that can cycle through a defined range of states.

### How Switches Work

```
                    ┌─────────────────────────────────────────┐
                    │           Virtual Switch                 │
                    │                                          │
Input channel up ──►│  ┌─────────┐    ┌─────────────────────┐ │
  (Trigger edge up) │  │ Counter │    │  State: 0,1,2...N   │ │
                    │  │         ├───►│                     ├─┼──► Output
Input channel down─►│  │ Up/Down │    │  First ↔ Last      │ │    (current state)
(Trigger edge down) │  └─────────┘    └─────────────────────┘ │
                    │                                          │
                    └─────────────────────────────────────────┘
```

**Key Behavior:**
- Each trigger edge increments or decrements the counter
- Counter wraps around at boundaries (Last → First, First → Last)
- State persists until next trigger (latching behavior)

### Configuration Options

| Parameter | Description |
|-----------|-------------|
| **Name** | Switch/counter name (output channel) |
| **Input channel up** | Channel that triggers increment |
| **Trigger edge up** | Edge type for increment: Rising or Falling |
| **Input channel down** | Channel that triggers decrement |
| **Trigger edge down** | Edge type for decrement: Rising or Falling |
| **First state** | Minimum counter value |
| **Last state** | Maximum counter value |
| **Default state** | Initial value on startup |

### Counter Behavior

#### Counting Up
- Each appearance of **Trigger edge up** on **Input channel up** increases value by 1
- When value equals **Last state** and another up-trigger occurs, value wraps to **First state**

#### Counting Down
- Each appearance of **Trigger edge down** on **Input channel down** decreases value by 1
- When value equals **First state** and another down-trigger occurs, value wraps to **Last state**

```
Example: First state = 0, Last state = 3

UP sequence:   0 → 1 → 2 → 3 → 0 → 1 → 2 → 3 → 0 ...
DOWN sequence: 0 → 3 → 2 → 1 → 0 → 3 → 2 → 1 → 0 ...
```

### Use Cases

#### 1. Momentary to Latching Conversion

Convert a momentary push button into an on/off toggle:

```
Name:               s_headlights
Input channel up:   d_headlightButton
Trigger edge up:    Rising
Input channel down: d_headlightButton
Trigger edge down:  Rising
First state:        0
Last state:         1
Default state:      0

Behavior:
  Press 1: OFF (0) → ON (1)
  Press 2: ON (1) → OFF (0)
  Press 3: OFF (0) → ON (1)
  ...
```

#### 2. Multi-Position Selector

Create a 4-position mode selector from a single button:

```
Name:               s_driveMode
Input channel up:   d_modeButton
Trigger edge up:    Rising
Input channel down: (none or different button)
Trigger edge down:  -
First state:        0
Last state:         3
Default state:      0

States:
  0 = Eco Mode
  1 = Normal Mode
  2 = Sport Mode
  3 = Track Mode

Behavior:
  Press cycles: Eco → Normal → Sport → Track → Eco → ...
```

#### 3. Up/Down Counter

Two-button brightness control:

```
Name:               s_brightness
Input channel up:   d_brightnessUp
Trigger edge up:    Rising
Input channel down: d_brightnessDown
Trigger edge down:  Rising
First state:        0
Last state:         10
Default state:      5

Behavior:
  Up button: 5 → 6 → 7 → 8 → 9 → 10 → 0 → 1 ...
  Down button: 5 → 4 → 3 → 2 → 1 → 0 → 10 → 9 ...
```

#### 4. Rotary Encoder Simulation

Use with CAN button inputs for multi-state control:

```
Name:               s_menuSelection
Input channel up:   can_encoderCW
Trigger edge up:    Rising
Input channel down: can_encoderCCW
Trigger edge down:  Rising
First state:        0
Last state:         7
Default state:      0

Output: Menu item index (0-7)
```

### Combining with Logic Elements

Switches are often combined with logic elements to drive outputs:

```
Virtual Switch → Logic Compare → Output Enable

Example:
  s_headlights (0 or 1) → Compare (s_headlights == 1) → out_headlights.enable
```

### Tips

1. **Same input for up/down** - Using the same channel for both creates a simple toggle
2. **Different edges** - Use Rising for up and Falling for down to trigger on both transitions
3. **Wide range for counters** - Set First=0, Last=100 for percentage-style controls
4. **Binary for on/off** - Use First=0, Last=1 for simple latching switches
5. **Default state** - Set to safe value (e.g., lights off, mode=normal)

---

## Related Documentation

- [Logic Elements](logic-elements.md) - Boolean logic and conditions
- [Analog Inputs](analog-inputs.md) - Input signal configuration
- [Digital Inputs](digital-inputs.md) - Digital signal configuration
- [Power Outputs](power-outputs.md) - Output control
