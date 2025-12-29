# PID Tuner

**Real-time PID controller tuning with live visualization**

The PID Tuner provides an interactive interface for tuning PID controllers while connected to the PMU-30, similar to the ECUMaster EMU PRO PID tuner.

---

## Overview

![PID Tuner Layout](../images/pid-tuner-layout.png)
*Note: Image placeholder - actual screenshot to be added*

The PID Tuner interface consists of:
- **Toolbar** - Controller selection, step test, recording controls
- **Graph** - Real-time plot of setpoint, process variable, and output
- **Controls** - Kp, Ki, Kd sliders and setpoint adjustment
- **Real-time Values** - Current values display
- **Status Bar** - Connection status and messages

---

## Accessing the PID Tuner

1. Open the Configurator and connect to PMU-30
2. Go to **View → PID Tuner** or use keyboard shortcut
3. Select a configured PID controller from the dropdown

> **Note:** You must have at least one PID channel configured before using the tuner.
> See [Logic Functions Reference](../reference/logic-functions.md#9-pid-controller) for PID configuration.

---

## Interface Elements

### Toolbar

| Control | Description |
|---------|-------------|
| **Controller** dropdown | Select which PID controller to tune |
| **Live Update** checkbox | When checked, parameter changes are sent immediately to device |
| **Step Test** button | Apply step change to setpoint for response analysis |
| **Reset** button | Reset controller (clears integral accumulator) |
| **Record** button | Start/stop data recording |
| **Clear** button | Clear graph history |

### Graph Display

The graph shows up to 60 seconds of history (configurable):

| Trace | Color | Description |
|-------|-------|-------------|
| **Setpoint** | Green | Target value the controller is trying to reach |
| **Process** | Blue | Actual measured value (input channel) |
| **Output** | Orange (dashed) | Controller output (0-1000 typically) |
| **Error** | Red (dotted) | Difference between setpoint and process (optional) |

### Parameter Controls

#### PID Gains
Each parameter has both a slider (for quick adjustment) and a spinbox (for precise values):

| Parameter | Range | Description |
|-----------|-------|-------------|
| **Kp (Proportional)** | 0-100 | Response strength to current error |
| **Ki (Integral)** | 0-100 | Response to accumulated error over time |
| **Kd (Derivative)** | 0-100 | Response to rate of error change |

#### Setpoint Controls

| Control | Description |
|---------|-------------|
| **Target** | Set the target setpoint value |
| **Step Size** | Amount to change setpoint during step test |

### Real-time Values

Live display of current controller state:
- **Setpoint** - Current target value
- **Process** - Current measured value
- **Output** - Current controller output
- **Error** - Current error (setpoint - process)

### Graph Settings

| Setting | Description |
|---------|-------------|
| **History** | How many seconds of data to display (10-300s) |
| **Show Error** | Toggle error trace visibility |

---

## Tuning Procedure

### Basic Tuning Steps

1. **Connect to PMU-30** and ensure the PID controller is configured
2. **Select the controller** from the dropdown
3. **Enable Live Update** checkbox
4. **Clear the graph** to start fresh
5. **Start with Kp only:**
   - Set Ki=0, Kd=0
   - Increase Kp until the process responds to setpoint changes
   - Find the value where response is quick but not oscillating
6. **Add Ki if needed:**
   - Slowly increase Ki to eliminate steady-state error
   - Too much Ki causes oscillation
7. **Add Kd if needed:**
   - Increase Kd to reduce overshoot
   - Too much Kd causes jerky response

### Using Step Test

The Step Test feature helps analyze controller response:

1. Set the **Step Size** (e.g., 10 for a 10-unit step)
2. Click **Step Test** - setpoint will jump up by step size
3. Observe the response:
   - **Rise time** - how quickly process approaches setpoint
   - **Overshoot** - how much it exceeds setpoint
   - **Settling time** - how long until stable
4. Click **End Step** to return to original setpoint
5. Adjust parameters and repeat

### Response Analysis

| Observation | Problem | Solution |
|-------------|---------|----------|
| Slow to respond | Kp too low | Increase Kp |
| Large overshoot | Kp too high, Kd too low | Decrease Kp or increase Kd |
| Oscillation | Ki too high | Decrease Ki |
| Never reaches setpoint | Ki=0 or wrong direction | Add Ki or set `reversed: true` |
| Output jumps erratically | Noisy input | Enable derivative filter in config |
| Output stuck at limit | Integral windup | Ensure `anti_windup: true` in config |

---

## Recording Data

To capture tuning data for later analysis:

1. Click **Record** to start recording
2. Perform your tuning adjustments
3. Click **Stop** when done
4. Data can be exported (feature in development)

Recorded data includes timestamp, setpoint, process, output, and error for each sample.

---

## Tips for Effective Tuning

### General Tips

- **Start conservative** - Begin with low gains and increase gradually
- **Change one parameter at a time** - Makes it easier to understand effects
- **Use Step Test** - Gives consistent, reproducible response data
- **Record your session** - Helpful for comparing different settings
- **Reset between tests** - Clear integral accumulator for fair comparison

### Application-Specific Tips

#### Temperature Control (e.g., cooling fan)
- Use **longer history** (60-120s) - temperature changes slowly
- **Kd is helpful** to anticipate temperature rise
- Set `reversed: true` in config (higher output = cooler)
- Sample time: 500-1000ms

#### Idle Speed Control
- Use **shorter history** (20-30s) - RPM changes quickly
- **Ki is essential** to maintain exact setpoint
- Enable **derivative filter** - engine RPM can be noisy
- Sample time: 50-100ms

#### Boost Control
- **Fast sample time** (20-50ms) needed
- Be careful with Ki - can cause boost spikes
- Test at safe boost levels first
- Monitor wastegate duty cycle limits

---

## Troubleshooting

### Graph Not Updating
- Check connection status (should show "Online")
- Verify telemetry is enabled in device settings
- Ensure the selected controller exists in configuration

### Parameters Not Affecting Output
- Check "Live Update" is enabled
- Verify controller is enabled in configuration
- Check source channel is providing valid data

### Step Test Not Working
- Controller must be connected and online
- Setpoint channel must not override manual setpoint
- Check output limits in configuration

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Space` | Start/Stop step test |
| `R` | Reset controller |
| `C` | Clear graph |
| `L` | Toggle live update |

---

## See Also

- [PID Controller Reference](../reference/logic-functions.md#9-pid-controller) - Complete configuration guide
- [Configuration Reference](../reference/configuration.md#311-pid-channel) - JSON schema
- [Variables Inspector](variables-inspector.md) - Monitor channel values
- [Channel Graph](channel-graph.md) - Alternative visualization
