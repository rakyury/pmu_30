# Digital Inputs Configuration

Digital Inputs are used for transforming digital signals such as signals from crankshaft position sensors, wheel speed sensors, or ethanol sensors (FlexFuel). These inputs can also be used as inputs for buttons connected to ground. The PMU-30 features **20 digital input channels** with configurable pull-up resistors, adjustable thresholds, and frequency/RPM measurement capabilities.

## Overview

Digital inputs provide:
- **Frequency measurement** for speed sensors and tachometers
- **RPM decoding** from crankshaft/camshaft position sensors
- **Switch input** for buttons and toggle switches
- **Specialized sensor support** for FlexFuel, PULS oil sensors, and AIM beacons
- **Configurable pull-up resistors** (4.7kΩ internal)
- **Adjustable voltage thresholds** for various sensor types

To add a digital input, add the **Digital Input** element in the Project Tree.

---

## Configuration Options

### Name
The name of the digital input that will be used as the channel name throughout the project.

**Example**: `d_engineRPM`, `d_absFrontRSpeed`, `d_startButton`

### Input Pin
Select the digital input pin (D1-D20). Some input types have specific pin requirements:

| Pin | Special Function |
|-----|------------------|
| **D1** | Engine RPM (crankshaft/camshaft sensor) - **Required for RPM type** |
| **D2** | FlexFuel sensor, AIM Beacon |
| **D4** | PULS oil level/temperature sensor |
| **D3-D20** | General purpose (Switch, Frequency) |

---

## Input Types

### Switch - Active Low
The digital input functions as a switch (button) activated by a **low state** (connected to ground).

```
Configuration:
  type: "switch_active_low"

Behavior:
  - Input HIGH (open/floating) → Output = 0
  - Input LOW (connected to GND) → Output = 1

Typical Use:
  - Buttons connecting signal to ground
  - Ground-switched toggle switches
```

**Wiring Example:**
```
        PMU-30
         ___
Button -|D8 |
  |     |   |
GND ----|GND|
        |___|

Configuration:
  Enable pull-up: Checked (4.7kΩ)
  Threshold: 2.5V
  Debounce: 50ms
```

### Switch - Active High
The digital input functions as a switch (button) activated by a **high state** (connected to power).

```
Configuration:
  type: "switch_active_high"

Behavior:
  - Input LOW (open/floating) → Output = 0
  - Input HIGH (connected to +V) → Output = 1

Typical Use:
  - Switches connecting signal to power
  - Hall effect proximity sensors
```

### Frequency
The digital input measures the signal frequency in Hz.

```
Configuration:
  type: "frequency"
  multiplier: 10
  divider: 32
  timeout: 1000ms

Formula:
  output_value = (measured_frequency × multiplier) / divider

Typical Use:
  - Wheel speed sensors (ABS sensors)
  - Turbocharger speed sensors
  - Flow meters
```

**Example - ABS Wheel Speed Sensor:**
```
Name:           d_absFrontRSpeed
Type:           Frequency
Input pin:      D4
Enable pullup:  Unchecked
Threshold:      2.39V
Trigger edge:   Rising
Multiplier:     10
Divider:        32
Timeout:        1000 ms

Calculation:
  If sensor outputs 160 Hz:
  Speed value = (160 × 10) / 32 = 50 (km/h or user units)
```

### RPM
The digital input decodes the signal from a crankshaft/camshaft position sensor to measure engine speed.

**Important**: Only the **D1** input can be used to measure engine speed.

```
Configuration:
  type: "rpm"
  number_of_teeth: 58  (for 60-2 wheel)
  multiplier: 1
  divider: 1

Formula:
  RPM = (frequency × 60 × multiplier) / (teeth × divider)

Supported Trigger Wheels:
  - 60-2 (58 teeth) - Most common
  - 36-1 (35 teeth)
  - 12+1 (13 teeth)
  - Custom tooth counts
```

**Example - Engine RPM from 60-2 Wheel:**
```
Name:           d_engineRPM
Type:           RPM
Input pin:      D1
Enable pullup:  Unchecked
Threshold:      0.8V
Trigger edge:   Rising
Number of teeth: 58
Multiplier:     1
Divider:        1
```

### Flex Fuel
Digital input for reading ethanol content and fuel temperature from a FlexFuel sensor.

**Important**: Only the **D2** input is compatible with FlexFuel sensors.

```
Configuration:
  type: "flexfuel"

Output Channels:
  - adu.ff.ethanolContent    (0-100%)
  - adu.ff.fuelTemperature   (°C)
  - adu.ff.sensorStatus      (0=OK, 1=Error)

Supported Sensors:
  - Continental FlexFuel sensors
  - GM FlexFuel sensors
  - Aftermarket compatible sensors
```

**Wiring:**
```
        PMU-30
         ___
Signal -|D2 |
        |   |
+12V ---|+12|
        |   |
GND ----|GND|
        |___|
```

### Beacon
Digital input for decoding signals from an AIM beacon (lap timing transponder).

**Important**: The **D2** input is compatible with AIM beacons.

```
Configuration:
  type: "beacon"

Behavior:
  - Detects beacon signal crossing
  - Outputs pulse when beacon detected
  - Used for lap timing applications
```

### PULS Oil Sensor
Digital input for reading data from PULS-type oil level and temperature sensors.

**Important**: PULS sensors can only be connected to the **D4** input.

```
Configuration:
  type: "puls_oil"
  Enable pull-up: Checked
  Threshold: 2.5V

Output Channels:
  - adu.puls.level         (mm)
  - adu.puls.temperature   (°C)
  - adu.puls.status        (0=OK, 1=Error)
```

**Compatible Sensor Example:**
```
Hella PULS Sensor: 6PR 010 497-05
Range: 18-118.8 mm

Wiring:
  Pin 1: +12V
  Pin 2: Ground
  Pin 3: Signal → D4

Configuration:
  Enable pull-up: Checked
  Threshold: 2.5V

Note: Configure measuring range in
      "PULS oil temperature" > "level sensor" window
```

---

## Signal Conditioning

### Enable Pull-up
Activates an internal **4.7kΩ pull-up resistor** for the input.

| Setting | Use Case |
|---------|----------|
| **Enabled** | Open-collector sensors, buttons to ground, PULS sensors |
| **Disabled** | Push-pull sensors, voltage output sensors |

### Threshold
The reference voltage which determines the input state change from 0 to 1 (and vice versa).

| Sensor Type | Typical Threshold |
|-------------|-------------------|
| **Inductive sensors** | 0.5V - 1.0V |
| **Hall effect sensors** | 2.5V |
| **Optical sensors** | 2.5V |
| **PULS sensors** | 2.5V |
| **Buttons (with pull-up)** | 2.5V |

### Trigger Edge
The signal edge used when transforming a signal.

| Edge | Description |
|------|-------------|
| **Rising** | Trigger on low-to-high transition |
| **Falling** | Trigger on high-to-low transition |

### Debounce Time
For **Switch** type inputs, this parameter determines the time needed to stabilize switch contacts and prevent false triggers from contact bounce.

| Application | Typical Value |
|-------------|---------------|
| **Push buttons** | 20-50 ms |
| **Toggle switches** | 10-30 ms |
| **Rotary switches** | 30-50 ms |

---

## Frequency/RPM Scaling

### Number of Teeth
For **RPM** signals, this is the physical number of teeth on the trigger wheel used by the crankshaft/camshaft position sensor.

| Trigger Wheel | Teeth Setting |
|---------------|---------------|
| **60-2** | 58 |
| **36-1** | 35 |
| **12+1** | 13 |
| **4-cylinder cam** | 4 |

### Multiplier
The value by which input frequency or engine speed will be multiplied. Used for calibrating values such as turbocharger speed or vehicle speed.

### Divider
The value by which input frequency or engine speed will be divided. Used in combination with multiplier for precise scaling.

```
Output Value Formula:
  value = (raw_frequency × multiplier) / divider

Example - Wheel Speed from ABS Ring:
  ABS ring: 48 teeth
  Wheel circumference: 2.0 m
  Desired output: km/h

  At 100 km/h:
    Wheel RPM = (100000 m/h) / (2.0 m × 60 min) = 833.3 RPM
    Frequency = 833.3 × 48 / 60 = 666.7 Hz

  To get km/h from Hz:
    multiplier = 10, divider = 32
    (666.7 × 10) / 32 ≈ 208 → needs adjustment

  Better: multiplier = 3, divider = 10
    (666.7 × 3) / 10 = 200 → scale factor 0.5 → 100 km/h
```

### Timeout
For **Frequency** type inputs, this parameter sets the time after which the frequency reading is considered zero if no pulses are received.

| Application | Typical Value |
|-------------|---------------|
| **Wheel speed** | 500-1000 ms |
| **Engine RPM** | 500 ms |
| **Flow meters** | 2000 ms |

---

## Example Configurations

### Engine Speed (RPM) from 60-2 Trigger Wheel

```
Name:           d_engineRPM
Type:           RPM
Input pin:      D1
Enable pullup:  Unchecked
Threshold:      0.8 V
Trigger edge:   Rising
Number of teeth: 58
Multiplier:     1
Divider:        1
```

**Description**: Engine speed read-out from inductive camshaft sensor with 60-2 toothed wheel. The sensor must be connected to Digital Input 1.

---

### Wheel Speed from ABS Sensor

```
Name:           d_absFrontRSpeed
Type:           Frequency
Input pin:      D4
Enable pullup:  Unchecked
Threshold:      2.39 V
Trigger edge:   Rising
Multiplier:     10
Divider:        32
Timeout:        1000 ms
```

**Description**: Wheel speed read-out from ABS sensor connected to Digital Input 4. The `d_absFrontRSpeed` variable value equals the input frequency multiplied by 10 and divided by 32 (multiplier/divider).

---

### Button Connected to Ground

```
Name:           d_startButton
Type:           Switch - active low
Input pin:      D8
Enable pullup:  Checked
Threshold:      2.5 V
Debounce:       50 ms
```

**Description**: Status read-out of button connected to Digital Input 8. The button connects the signal to ground. The `d_startButton` variable assumes value 0 when button is not pressed and 1 when pressed.

---

### FlexFuel Sensor

```
Name:           d_flexFuel
Type:           Flex Fuel
Input pin:      D2
Enable pullup:  Unchecked
Threshold:      2.5 V
```

**Output Channels**:
- `adu.ff.ethanolContent` - Ethanol percentage (0-100%)
- `adu.ff.fuelTemperature` - Fuel temperature (°C)
- `adu.ff.sensorStatus` - Sensor status (0=OK)

---

### PULS Oil Level Sensor

```
Name:           d_oilLevel
Type:           PULS oil sensor
Input pin:      D4
Enable pullup:  Checked
Threshold:      2.5 V
```

**Compatible Sensor**: Hella 6PR 010 497-05 (Range: 18-118.8 mm)

**Output Channels**:
- `adu.puls.level` - Oil level (mm)
- `adu.puls.temperature` - Oil temperature (°C)
- `adu.puls.status` - Sensor status (0=OK)

---

### Turbocharger Speed

```
Name:           d_turboSpeed
Type:           Frequency
Input pin:      D3
Enable pullup:  Unchecked
Threshold:      2.5 V
Trigger edge:   Rising
Multiplier:     60
Divider:        1
Timeout:        500 ms
```

**Description**: Turbocharger speed from variable reluctance sensor. Output in RPM (frequency × 60).

---

## Input Specifications

| Parameter | Value |
|-----------|-------|
| **Number of inputs** | 20 (D1-D20) |
| **Input voltage range** | 0-5V (tolerant to 12V with protection) |
| **Pull-up resistor** | 4.7kΩ to 5V |
| **Maximum frequency** | 20 kHz |
| **Minimum pulse width** | 25 µs |
| **Input impedance** | >100kΩ (pull-up disabled) |
| **Threshold accuracy** | ±50 mV |

---

## Wiring Diagrams

### Inductive Sensor (VRS)
```
        PMU-30
         ___
Signal -|D1 |
        |   |
GND ----|GND|
        |___|

Configuration:
  Pull-up: Disabled
  Threshold: 0.5-1.0V
  Edge: Rising
```

### Hall Effect Sensor
```
        PMU-30
         ___
Signal -|D3 |
        |   |
+5V ----|+5V|
        |   |
GND ----|GND|
        |___|

Configuration:
  Pull-up: Disabled (sensor has push-pull output)
  Threshold: 2.5V
  Edge: Rising or Falling
```

### Open-Collector Sensor
```
        PMU-30
         ___
Signal -|D5 |--- Internal 4.7kΩ pull-up to 5V
        |   |
GND ----|GND|
        |___|

Configuration:
  Pull-up: Enabled
  Threshold: 2.5V
```

### Button to Ground
```
        PMU-30
         ___
Button -|D8 |--- Internal 4.7kΩ pull-up to 5V
  |     |   |
GND ----|GND|
        |___|

Configuration:
  Pull-up: Enabled
  Threshold: 2.5V
  Debounce: 50ms
```

---

## Monitoring Digital Inputs

Use the **Digital Monitor** panel (press **F12**) to view real-time status:

| Column | Description |
|--------|-------------|
| **Pin** | Digital input number (D1-D20) |
| **Name** | Channel name |
| **State** | Current logic state (0/1) |
| **Value** | Processed value (Hz, RPM, %) |
| **Raw** | Raw input state |

---

## Tips and Best Practices

1. **Use correct threshold** - Set threshold based on sensor type (0.8V for inductive, 2.5V for Hall/optical)

2. **Enable pull-up for buttons** - Always use internal pull-up for ground-switched buttons

3. **Set appropriate debounce** - Use 30-50ms debounce for mechanical switches to prevent false triggers

4. **Verify tooth count** - Ensure number of teeth matches actual trigger wheel (60-2 = 58, not 60)

5. **Use timeout for speed signals** - Set timeout to detect zero speed (stationary vehicle)

6. **Check pin restrictions** - RPM must use D1, FlexFuel/Beacon use D2, PULS uses D4

7. **Shield sensor cables** - Use shielded cables for inductive sensors near ignition systems

8. **Calculate multiplier/divider** - Pre-calculate scaling factors for desired output units

---

## Related Documentation

- [Digital Monitor](digital-monitor.md) - Real-time digital input monitoring
- [Analog Inputs](analog-inputs.md) - Analog input configuration
- [Project Tree](project-tree.md) - Adding and managing channels
