# Analog Inputs Configuration

The PMU-30 device is equipped with **20 analog inputs** (A1-A20) for measuring voltage from sensors or as inputs for buttons and switches.

## Overview

Analog inputs are used for:
- **Measuring voltage** from sensors (e.g., oil pressure, MAP, throttle position)
- **Button/switch inputs** with configurable thresholds
- **Temperature sensors** with non-linear characteristics (NTC/PTC)
- **Rotary switch** position detection

To add an analog input, add the **Analog Input** element in the Project Tree.

---

## Configuration Options

### Name
The name of the analog input that will be used as the channel name throughout the project. This name is used to reference the input in logic functions, tables, and outputs.

**Example**: `a_oilPressure`, `a_fuelLevel`, `a_startButton`

### Pin
The physical analog input pin (A1-A20) to which this configuration applies.

### Type
The function that the analog input will perform:

| Type | Description |
|------|-------------|
| **Switch - active low** | Input functions as a button activated by connecting to ground |
| **Switch - active high** | Input functions as a button activated by connecting to power |
| **Rotary switch** | Discrete position detection based on voltage levels |
| **Linear analog sensor** | Linear voltage-to-value conversion for sensors |
| **Calibrated analog sensor** | Non-linear conversion using lookup table (for NTC/PTC sensors) |

### Pullup/Pulldown
Activates internal resistors for proper signal conditioning:

| Option | Resistor | Use Case |
|--------|----------|----------|
| **Default: 10K pullup** | 10kΩ to +5V | Buttons/switches connected to ground |
| **Default: 1M pulldown** | 1MΩ to GND | Analog sensors, voltage measurement |

- **Pull-up (10K)**: Use when the button connects the input to ground (active low)
- **Pull-down (1M)**: Use for analog sensors or voltage measurement to prevent floating inputs

### Quantity/Unit
For Linear and Calibrated analog sensor types, defines the physical quantity and unit:

| Quantity | Units |
|----------|-------|
| Voltage | V, mV |
| Pressure | kPa, bar, psi |
| Temperature | °C, °F, K |
| Percentage | % |
| Custom | User-defined |

### Decimal Places
Defines the number of decimal places for the measured value (0-3). Applies to Linear and Calibrated input types.

---

## Switch Configuration

### Switch - Active Low

For buttons connected between the analog input and ground:

| Parameter | Description |
|-----------|-------------|
| **0 if voltage > [V]** | Voltage threshold to detect OFF state (button released) |
| **for [s]** | Debounce time - voltage must be above threshold for this duration |
| **1 if voltage < [V]** | Voltage threshold to detect ON state (button pressed) |
| **for [s]** | Debounce time - voltage must be below threshold for this duration |

**Behavior**:
- When button is **released**: Pull-up resistor pulls input to ~5V → Output = 0
- When button is **pressed**: Input connected to ground → Output = 1

### Switch - Active High

For buttons connected between the analog input and power:

**Behavior**:
- When button is **released**: Pull-down keeps input near 0V → Output = 0
- When button is **pressed**: Input connected to power → Output = 1

### Example: Button to Ground

```
Configuration for a button connected to ground on analog input A1:

Name:           a_sampleButton
Pin:            A1
Type:           switch - active low
Pullup/Pulldown: default: 10K pullup
0 if voltage >: 3.5V    for: 0.01s
1 if voltage <: 1.5V    for: 0.01s
```

The `a_sampleButton` value will be:
- **0** when the button is not pressed (voltage > 3.5V)
- **1** when the button is pressed (voltage < 1.5V)

---

## Linear Analog Sensor Configuration

For sensors with a linear voltage-to-value relationship:

| Parameter | Description |
|-----------|-------------|
| **Min value** | Minimum output value |
| **for voltage [V]** | Voltage corresponding to minimum value |
| **Max value** | Maximum output value |
| **for voltage [V]** | Voltage corresponding to maximum value |

**Formula**:
```
output = min_value + (voltage - min_voltage) × (max_value - min_value) / (max_voltage - min_voltage)
```

### Example: MAP Sensor (10-115 kPa)

```
Configuration for a pressure sensor (MAP) on analog input A2:

Name:           a_mapSensor115kPA
Pin:            A2
Type:           linear analog sensor
Pullup/Pulldown: default: 1M pulldown
Quantity/Unit:  Pressure / kPa
Decimal places: 1
Min value:      10.0    for voltage: 0.50V
Max value:      115.0   for voltage: 4.50V
```

The `a_mapSensor115kPa` value will range from **10.0 kPa to 115.0 kPa**.

### Example: Voltage Measurement (0-5V)

```
Configuration for measuring 0-5V on analog input A3:

Name:           a_voltmeter
Pin:            A3
Type:           linear analog sensor
Pullup/Pulldown: default: 1M pulldown
Quantity/Unit:  Voltage / V
Decimal places: 2
Min value:      0.00    for voltage: 0.00V
Max value:      5.00    for voltage: 5.00V
```

The `a_voltmeter` value will range from **0.00V to 5.00V**.

---

## Calibrated Analog Sensor Configuration

For sensors with non-linear characteristics (e.g., NTC/PTC temperature sensors):

### Using the Wizard

The easiest way to calibrate non-linear temperature sensors is to use the **Wizard**:

1. Press the **Wizard** button in the configuration dialog
2. Select a **Predefined sensor** from the list, or
3. Enter three temperature/resistance value pairs manually
4. Specify the **Rx value** (pull-up resistor value used in the circuit)

The wizard automatically generates a 2D calibration map.

### Manual Calibration Table

For custom sensors, enter voltage-to-value pairs directly in the calibration table:

| Voltage [V] | Value |
|-------------|-------|
| 0.00 | 250.0 |
| 0.11 | 157.0 |
| 0.22 | 124.2 |
| 0.33 | 106.7 |
| ... | ... |
| 5.00 | -50.0 |

**Table Operations**:
- Right-click on the table to access **Modify bins** options
- Values are linearly interpolated between defined points

### Example: NTC Temperature Sensor

```
Configuration for an NTC temperature sensor on analog input A3:

Name:           a_coolantTemp
Pin:            A3
Type:           calibrated analog sensor
Pullup/Pulldown: default: 1M pulldown
Quantity/Unit:  Temperature / °C
Decimal places: 1

Calibration Table:
| Voltage | Temperature |
|---------|-------------|
| 0.00V   | 250.0°C     |
| 0.50V   | 120.0°C     |
| 1.00V   | 90.0°C      |
| 1.50V   | 70.0°C      |
| 2.00V   | 50.0°C      |
| 2.50V   | 30.0°C      |
| 3.00V   | 10.0°C      |
| 3.50V   | -10.0°C     |
| 4.00V   | -30.0°C     |
| 4.50V   | -50.0°C     |
```

---

## Rotary Switch Configuration

For multi-position rotary switches with resistor ladder:

| Parameter | Description |
|-----------|-------------|
| **Min value** | First position number (typically 0 or 1) |
| **Max value** | Last position number |

The input assumes a discrete value based on the voltage level, corresponding to the rotary switch position.

### Example: 12-Position Rotary Switch

```
Name:           a_modeSelector
Pin:            A5
Type:           rotary switch
Min value:      1
Max value:      12
```

---

## Monitoring Analog Inputs

The values of analog inputs can be viewed in the **Analog Monitor** panel (press **F11**):

| Column | Description |
|--------|-------------|
| **Pin** | Analog pin identifier (A1-A20) |
| **Name** | User-assigned channel name |
| **Value** | Scaled/processed value with unit |
| **Vltg** | Raw ADC voltage (0-5V) |
| **Pu/pd** | Pull-up/Pull-down configuration |

---

## Wiring Guidelines

### Button/Switch (Active Low)

```
        PMU-30
         ___
Button -|A1 |--- Internal 10K pull-up to +5V
        |   |
GND ----|GND|
        |___|

Configuration: 10K pullup, switch - active low
```

### Linear Sensor (0-5V Output)

```
        PMU-30
         ___
+5V ----|5V |--- Sensor power
Signal -|A1 |--- Sensor output
GND ----|GND|--- Sensor ground
        |___|

Configuration: 1M pulldown, linear analog sensor
```

### NTC Temperature Sensor

```
        PMU-30
         ___
+5V ----|5V |--- External pull-up resistor (e.g., 2.2kΩ)
        |   |         |
NTC ----|A1 |---------+
        |   |
GND ----|GND|--- NTC to ground
        |___|

Configuration: calibrated analog sensor with temperature curve
```

### Resistive Sender (Fuel Level)

```
        PMU-30
         ___
Sender -|A1 |--- Pull-up enabled
        |   |
GND ----|GND|
        |___|

Configuration: 10K pullup, linear or calibrated
```

---

## Common Sensor Configurations

| Sensor Type | Input Type | Range | Typical Voltage |
|-------------|------------|-------|-----------------|
| MAP Sensor (1 bar) | Linear | 0-105 kPa | 0.5-4.5V |
| MAP Sensor (3 bar) | Linear | 0-300 kPa | 0.5-4.5V |
| TPS (Throttle) | Linear | 0-100% | 0.5-4.5V |
| Oil Pressure | Linear | 0-10 bar | 0.5-4.5V |
| Coolant Temp (NTC) | Calibrated | -40 to 150°C | Variable |
| Intake Air Temp | Calibrated | -40 to 100°C | Variable |
| Fuel Level | Linear/Calibrated | 0-100% | Variable |
| Lambda/O2 | Linear | 0.7-1.3 λ | 0-1V |
| EGT (Thermocouple) | Calibrated | 0-1100°C | 0-5V (with amplifier) |
| Brake Pressure | Linear | 0-200 bar | 0.5-4.5V |
| Steering Angle | Linear | -720 to +720° | 0.5-4.5V |

---

## Tips and Best Practices

1. **Use meaningful names** - Include the sensor type in the name (e.g., `a_oilPressure`, `a_coolantTemp`)

2. **Set appropriate debounce times** - For buttons, 10-50ms (0.01-0.05s) is typical

3. **Verify pull-up/pull-down settings** - Wrong setting can cause floating inputs or incorrect readings

4. **Use 1M pulldown for voltage signals** - This provides minimal loading on the signal

5. **Calibrate temperature sensors** - Use the Wizard for common NTC sensors or create custom tables

6. **Check voltage thresholds** - Ensure switch thresholds have adequate hysteresis (at least 0.5V gap)

7. **Monitor raw voltage** - Use the Analog Monitor to verify sensor wiring before scaling

---

## Related Documentation

- [Analog Monitor](analog-monitor.md) - Real-time analog input monitoring
- [Digital Inputs](digital-inputs.md) - Digital input configuration
- [Project Tree](project-tree.md) - Adding and managing channels
