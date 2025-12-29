# Power Outputs Configuration

Power Outputs are elements that control external devices such as fuel pumps, fans, lights, and motors. The PMU-30 features **30 high-side power outputs** with configurable current limits, PWM control, soft start, and automatic retry on fault.

## Overview

Power outputs provide:
- **Current monitoring** with overcurrent and undercurrent detection
- **Inrush current handling** for motor and pump startup
- **PWM control** for speed/brightness adjustment on 30A outputs
- **Soft start** to limit inrush current on demanding loads
- **Automatic retry** on overcurrent faults

To add a power output, add the **Power Output** element in the Project Tree.

---

## Configuration Options

### Name
The name of the output that will be used as the channel name throughout the project.

**Example**: `o_fuelPump`, `o_radiatorFan`, `o_headlights`

### Pin
Select the output pin(s) to use. Multiple pins can be combined in parallel for higher current capacity:

| Configuration | Max Current | Use Case |
|---------------|-------------|----------|
| **Single** | Up to 40A | Standard loads |
| **Double** | Up to 80A | High-current loads |
| **Triple** | Up to 90A | Very high-current loads |

**Important**: Pins used in parallel must be of the same type. You cannot combine 25A and 15A pins together.

### Output Pin Types

| Pin Type | Continuous Rating | Inrush Rating |
|----------|-------------------|---------------|
| **40A pins** (O1-O10) | 40A continuous | Up to 60A inrush |
| **25A pins** (O11-O20) | 25A continuous | Up to 40A inrush |
| **15A pins** (O21-O25) | 15A continuous | Up to 25A inrush |
| **7A pins** (O26-O30) | 7A continuous | Up to 12A inrush |

---

## Current Protection Settings

### Inrush Current [A]
The maximum current allowed during device startup (Inrush Time period). This value is typically higher than Max Current to accommodate motor/pump startup surge.

- Must be greater than or equal to Max Current
- If exceeded, output status changes to **OVERCURRENT** and turns off
- Maximum value depends on selected output pin type

### Inrush Time [s]
The duration during which current can exceed Max Current (up to Inrush Current limit) during startup.

- Typical range: 0.1s to 5.0s
- After this time, current must drop below Max Current
- Maximum Inrush Time depends on selected Inrush Current and pin rating

### Max Current [A]
Maximum continuous operating current after startup (after Inrush Time expires).

- If exceeded, output turns off with **OVERCURRENT** status
- Should be set based on the device's normal operating current plus safety margin

### Min Current [A]
Minimum expected operating current. Used to detect disconnected or failed loads.

- If current drops below this value, status changes to **UNDERCURRENT**
- Output **remains ON** during undercurrent condition (warning only)
- Set to 0 to disable undercurrent detection

---

## Current Measurement Thresholds

When measuring very low currents, each output has a threshold below which the measured value is clipped to zero:

| Pin Type | Threshold Range | Typical Value |
|----------|-----------------|---------------|
| **40A outputs** | 0 - 2A | ~0.5A |
| **25A outputs** | 0 - 2A | ~0.5A |
| **15A outputs** | 0 - 0.2A | ~0.1A |
| **7A outputs** | 0 - 0.2A | ~0.1A |

**Note**: Despite the measured value being clipped to zero below threshold, the actual current output remains precisely set.

---

## Retry Settings

Configure automatic retry behavior when overcurrent protection triggers:

### Retry Count
Number of attempts to turn the output back on after an overcurrent fault.

- Range: 1 to 10 retries
- After all retries exhausted, output remains OFF until manually reset

### Retry Every [s]
Time interval between retry attempts.

- Range: 0.1s to 60s
- Allows load/wiring to cool down between attempts

### Retry Forever
Enable continuous retry attempts at the specified interval.

- Output will keep attempting to turn on indefinitely
- Useful for critical loads that must remain operational
- **Caution**: Ensure the fault condition will eventually clear

---

## PWM Configuration

PWM (Pulse Width Modulation) control is available on **30A output pins** for variable speed/brightness control.

### Enable PWM
Check the **PWM Configuration** box to enable pulse width modulation.

### Frequency [Hz]
PWM switching frequency. Available options:

| Frequency | Use Case |
|-----------|----------|
| **100 Hz** | Motors, pumps, general loads |
| **125 Hz** | Motors, fans |
| **200 Hz** | LED lighting |
| **500 Hz** | High-frequency applications |
| **1000 Hz** | Smooth LED dimming |

**Note**: Higher frequencies provide smoother control but increase switching losses.

### Soft Start
Enables gradual current ramp-up during output activation. Essential for high-inrush loads.

#### Duration [ms]
Time over which the output ramps from 0% to target duty cycle.

- Range: 10ms to 5000ms
- Typical: 100-500ms for pumps, 50-200ms for fans

#### How Soft Start Works

**Without Soft Start:**
- Output immediately applies full power
- High inrush current spike
- May trigger overcurrent protection on demanding loads

**With Soft Start:**
- Output gradually increases PWM duty cycle
- Current ramps smoothly to operating level
- Reduces mechanical stress and electrical surge

```
Current Profile Comparison:

Soft Start DISABLED          Soft Start ENABLED
     │                            │
 1.3A├─────────────────      1.3A├──────────────────
     │    ┌──────────            │         ╱────────
 1.0A│    │                  1.0A│        ╱
     │    │                      │       ╱
 0.6A│   ╱                   0.6A│      ╱
     │  ╱                        │     ╱
 0.3A│ ╱                     0.3A│    ╱
     │╱                          │   ╱
 0.0A├────────────────       0.0A├──╱───────────────
     └─── Time                   └─── Time

     Instant step-up              Gradual ramp-up
```

### Duty Cycle
The percentage of time the power output is ON during each PWM cycle.

| Duty Cycle | Behavior |
|------------|----------|
| **0%** | Output always OFF |
| **50%** | Output ON half the time (half power) |
| **100%** | Output always ON (full power) |

#### DC Control Mode

The duty cycle can be controlled in three ways:

| Mode | Description |
|------|-------------|
| **Default** | Fixed duty cycle value (0-100%) |
| **Channel** | Duty cycle controlled by another channel value |
| **Formula** | Duty cycle calculated from a formula/expression |

**Channel Control Example:**
Link duty cycle to a temperature channel for automatic fan speed control based on coolant temperature.

#### PWM Current Waveform

```
PWM ENABLED (70% Duty Cycle)     PWM DISABLED (100% DC)
        │                              │
    1.2A├───┐   ┌───┐   ┌───      1.2A├─────────────────
        │   │   │   │   │             │╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲
    0.9A│   │   │   │   │         0.9A│
        │   │   │   │   │             │
    0.6A│   └───┘   └───┘         0.6A│
        │                             │
    0.3A│                         0.3A│
        │                             │
    0.0A├─────────────────        0.0A├─────────────────
        └─── Time                     └─── Time

    Pulsed current (lower avg)    Continuous current
```

With 70% duty cycle, the fuel pump operates at reduced speed as current is supplied only 70% of each cycle compared to constant supply.

---

## Output Control Channel

### Default Mode
Output is controlled by the built-in On/Off state.

- Check **On/Off** to enable output when conditions are met
- Uncheck for output to remain OFF

### Channel Mode
Output state is controlled by another channel's value.

- When channel value > 0: Output ON
- When channel value = 0: Output OFF
- Allows logic-based output control

### Formula Mode
Output state calculated from a formula or expression.

- Click **\<more\>** to access formula editor
- Combine multiple conditions with logic operators

---

## Example Configurations

### Fuel Pump (High Inrush)

```
Name:           o_fuelPump
Pin:            single, O5 (25A)
Inrush Current: 8.0A
Inrush Time:    1.00s
Max Current:    5.0A
Min Current:    0.0A
Retry Count:    3
Retry Every:    1.00s
PWM:            Disabled
Control:        Default, On/Off checked
```

### Radiator Fan (PWM Controlled)

```
Name:           o_radiatorFan
Pin:            single, O1 (40A)
Inrush Current: 15.0A
Inrush Time:    0.50s
Max Current:    12.0A
Min Current:    0.5A
Retry Count:    3
Retry Every:    2.00s
PWM:            Enabled
  Frequency:    100 Hz
  Soft Start:   Enabled, Duration: 150ms
  Duty Cycle:   Channel controlled (linked to coolant temp)
Control:        Channel: "l_fanControl"
```

### LED Light Bar

```
Name:           o_lightBar
Pin:            single, O15 (25A)
Inrush Current: 10.0A
Inrush Time:    0.20s
Max Current:    8.0A
Min Current:    0.0A
Retry Forever:  Enabled
Retry Every:    5.00s
PWM:            Enabled
  Frequency:    500 Hz
  Soft Start:   Disabled
  Duty Cycle:   Default: 100%
Control:        Default, On/Off checked
```

### High-Current Starter Motor

```
Name:           o_starter
Pin:            triple, O1+O2+O3 (90A combined)
Inrush Current: 90.0A
Inrush Time:    3.00s
Max Current:    60.0A
Min Current:    0.0A
Retry Count:    1
Retry Every:    10.00s
PWM:            Disabled
Control:        Channel: "a_startButton"
```

---

## Output Status Indicators

| Status | Description | LED Color |
|--------|-------------|-----------|
| **OFF** | Output disabled | Dark |
| **ON** | Output active, current normal | Green |
| **PWM** | Output active with PWM | Blue |
| **OVERCURRENT** | Current exceeded limit, output OFF | Red |
| **UNDERCURRENT** | Current below minimum (warning) | Yellow |
| **FAULT** | Hardware fault detected | Red flashing |

---

## Monitoring Power Outputs

Use the **Output Monitor** panel (press **F10**) to view real-time status:

| Column | Description |
|--------|-------------|
| **Pin** | Output pin number |
| **Name** | Channel name |
| **State** | ON/OFF/PWM status |
| **Current** | Measured current in amps |
| **Status** | OK/OVERCURRENT/UNDERCURRENT/FAULT |

---

## Tips and Best Practices

1. **Measure actual inrush current** - Use a clamp meter during first startup to set appropriate Inrush Current limits

2. **Add safety margin** - Set Max Current 10-20% above normal operating current

3. **Use Soft Start for pumps/motors** - Reduces mechanical wear and electrical stress

4. **Set appropriate retry intervals** - Allow time for wiring/load to cool before retry

5. **Enable Min Current detection** - Helps detect broken wires or failed loads

6. **Use PWM for variable loads** - Control fan speed based on temperature for efficiency

7. **Parallel pins for high current** - Combine same-type pins for loads over 40A

8. **Monitor output current** - Check Output Monitor to verify proper operation

---

## Related Documentation

- [Output Monitor](output-monitor.md) - Real-time output monitoring
- [Analog Inputs](analog-inputs.md) - Input configuration for control signals
- [Project Tree](project-tree.md) - Adding and managing channels
