# Power Output Pin Merging

This document explains how to merge multiple PROFET output pins into a single logical output for higher current capacity.

## Overview

Each PMU-30 PROFET output channel is rated for **40A continuous** current. When a load requires more than 40A, multiple pins can be merged (paralleled) into a single logical output.

| Configuration | Total Current Capacity |
|---------------|------------------------|
| 1 pin | 40A |
| 2 pins merged | 80A |
| 3 pins merged | 120A |

## How Merging Works

### Electrical Behavior

When pins are merged:

```
                    ┌─────────────┐
                    │   LOAD      │
                    │  (e.g. 90A) │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
      ┌────┴────┐    ┌────┴────┐    ┌────┴────┐
      │ PROFET  │    │ PROFET  │    │ PROFET  │
      │   O1    │    │   O2    │    │   O3    │
      │  ~30A   │    │  ~30A   │    │  ~30A   │
      └────┬────┘    └────┬────┘    └────┬────┘
           │               │               │
           └───────────────┴───────────────┘
                           │
                      Battery +
```

**Key Points:**
- Current distributes approximately equally across all merged pins
- Each pin sees ~1/N of the total load current (where N = number of pins)
- All pins switch ON/OFF simultaneously
- PWM duty cycle is identical across all pins

### Control Signal Synchronization

All merged pins receive the same control signals:

| Signal | Behavior |
|--------|----------|
| ON/OFF State | Applied to all pins simultaneously |
| PWM Duty Cycle | Identical value on all pins (0-100%) |
| PWM Frequency | Same frequency, synchronized edges |
| Soft Start | Same ramp-up timing |

```
PWM Signal (50% duty):

O1: ████████________████████________████████
O2: ████████________████████________████████  (synchronized)
O3: ████████________████████________████████
    └──────┘        └──────┘        └──────┘
     50% ON          50% ON          50% ON
```

## Configuration

### Configurator Dialog

In the Output Configuration dialog:

```
+----------------------------------------------------------+
| Power Output Configuration                                |
+----------------------------------------------------------+
| Name: [High Current Load___________]                      |
|                                                           |
| Pins (select 1-3 for higher current):                    |
|   Pin 1: [O5 ▼]    (Primary - required)                  |
|   Pin 2: [O6 ▼]    (Optional)                            |
|   Pin 3: [O7 ▼]    (Optional)                            |
|                                                           |
| Control Source: [Logic Channel ▼]                        |
|   Channel: [Engine Running ▼]                            |
|                                                           |
| PWM Frequency: [1000_] Hz                                |
| Soft Start:    [500__] ms                                |
|                                                           |
+----------------------------------------------------------+
```

### Pin Selection Rules

| Rule | Description |
|------|-------------|
| Pin 1 required | At least one pin must be selected |
| No duplicates | Same pin cannot be selected twice |
| No conflicts | Pin cannot be used by another output |
| Max 3 pins | Maximum of 3 pins per logical output |

### JSON Configuration Format

```json
{
  "id": "out_main_power",
  "channel_type": "power_output",
  "channel_name": "Main Power Bus",
  "output_pins": [4, 5, 6],
  "source_channel": "l_engine_running",
  "pwm_enabled": true,
  "pwm_frequency_hz": 1000,
  "duty_fixed": 100.0,
  "soft_start_ms": 500,
  "current_limit_a": 100.0,
  "inrush_current_a": 200.0,
  "inrush_time_ms": 200
}
```

**Field Descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| `output_pins` | Array | List of pin indices (0-29 = O1-O30) |
| `source_channel` | String | Control function channel ID |
| `pwm_enabled` | Boolean | Enable PWM modulation |
| `pwm_frequency_hz` | Integer | PWM frequency (100-25000 Hz) |
| `duty_fixed` | Float | Fixed duty cycle (0-100%) |
| `soft_start_ms` | Integer | Ramp-up time in milliseconds |
| `current_limit_a` | Float | Total current limit for all pins |
| `inrush_current_a` | Float | Allowed inrush current |
| `inrush_time_ms` | Integer | Inrush time window |

## Display in Output Monitor

### Merged Output Display

The Output Monitor shows merged outputs with combined information:

```
| Pin     | Name            | Status | Curr   | Peak   |
|---------|-----------------|--------|--------|--------|
| O5,O6,O7| Main Power Bus  | ON     | 87.5A  | 92.3A  |
| O8      | Fuel Pump       | ON     | 8.2A   | 12.1A  |
| O9      | -               | -      | -      | -      |
```

**Display Features:**

| Feature | Behavior |
|---------|----------|
| Pin column | Shows all merged pins: "O5,O6,O7" |
| Current | Sum of all merged pin currents |
| Peak | Maximum sum since last reset |
| Secondary pins | Hidden from table (O6, O7 rows not shown) |

### Current Aggregation

Current is summed from all merged pins:

```
Individual Pin Readings:
  O5: 28.5A
  O6: 29.2A
  O7: 29.8A
  ─────────
  Total: 87.5A (displayed)
```

## Protection Mechanisms

### Per-Pin Protection

Each PROFET channel maintains independent protection:

| Protection | Per-Pin Limit | Action |
|------------|---------------|--------|
| Overcurrent | 42A (105% of 40A) | OC state, retry |
| Short Circuit | 80A | Immediate shutdown |
| Overtemperature | 145°C | OT state, cooldown |
| Open Load | < 50mA when ON | OL warning |

**Important:** If one pin faults, only that pin shuts down. Other merged pins continue operating (degraded mode).

### Aggregate Protection

The configurator-defined `current_limit_a` is informational only. Hardware protection operates per-pin:

```
Configuration: current_limit_a = 100A (3 pins merged)
Reality: Each pin limited to 40A by hardware
         = 120A maximum theoretical capacity
         = 100A soft limit for this output
```

### Fault Scenarios

**Single Pin Fault:**
```
Normal Operation:
  O5: 30A ✓    O6: 30A ✓    O7: 30A ✓    Total: 90A

O6 Overcurrent Fault:
  O5: 30A ✓    O6: FAULT    O7: 30A ✓    Total: 60A (degraded)
```

**Cascade Protection:**
If remaining pins are overloaded after one faults, they will also trip independently.

## Wiring Requirements

### Wire Sizing

Each pin path must handle its share of current:

| Merged Pins | Current per Wire | Minimum Wire Gauge |
|-------------|------------------|-------------------|
| 2 pins (80A) | 40A each | 8 AWG (8mm²) |
| 3 pins (120A) | 40A each | 8 AWG (8mm²) |

### Connection Points

All merged pin wires must join at the load:

```
Correct Wiring:
                    ┌──────────┐
  O5 ────────────┬──┤          │
  O6 ────────────┤  │   LOAD   │
  O7 ────────────┴──┤          │
                    └──────────┘

Incorrect (resistance imbalance):
  O5 ─────┬───────────┐
  O6 ─────┤           │   LOAD
  O7 ─────┴───────────┘
       ↑
   Connection here causes O5 to carry more current
```

### Fusing

**Option 1: Single Fuse (Preferred)**
```
  O5 ───┬───[ FUSE 100A ]───── LOAD
  O6 ───┤
  O7 ───┘
```

**Option 2: Individual Fuses**
```
  O5 ───[ FUSE 40A ]───┬───── LOAD
  O6 ───[ FUSE 40A ]───┤
  O7 ───[ FUSE 40A ]───┘
```

## Use Cases

### High-Power Lighting

```json
{
  "channel_name": "Main Headlights",
  "output_pins": [0, 1],
  "source_channel": "l_headlight_switch",
  "pwm_enabled": true,
  "pwm_frequency_hz": 200,
  "duty_channel": "n_headlight_dimmer"
}
```
- 2 pins merged for 55W HID ballasts
- PWM dimming for high/low beam

### Electric Cooling Fan

```json
{
  "channel_name": "Radiator Fan",
  "output_pins": [10, 11, 12],
  "source_channel": "l_fan_enable",
  "pwm_enabled": true,
  "pwm_frequency_hz": 25000,
  "duty_channel": "pid_fan_speed"
}
```
- 3 pins for 100A brushless fan
- 25kHz PWM for silent operation
- PID speed control

### Fuel Pump Relay

```json
{
  "channel_name": "Fuel Pump",
  "output_pins": [20, 21],
  "soft_start_ms": 0,
  "current_limit_a": 60.0,
  "inrush_current_a": 120.0,
  "inrush_time_ms": 500
}
```
- 2 pins for high-flow fuel pump
- No soft start (immediate prime)
- High inrush for motor startup

## Best Practices

### Pin Selection

| Recommendation | Reason |
|----------------|--------|
| Use adjacent pins | Easier wiring, shorter traces |
| Avoid mixing banks | O1-O15 and O16-O30 on different sides |
| Reserve spares | Don't use O30 as secondary if possible |

### Current Derating

For reliability, derate the total capacity:

| Merged Pins | Theoretical | Recommended |
|-------------|-------------|-------------|
| 2 pins | 80A | 70A (87%) |
| 3 pins | 120A | 100A (83%) |

### Thermal Considerations

- Merged pins share thermal zones on the PCB
- Heavy loads may require forced airflow
- Monitor board temperatures (`pmu.board_temp_l`, `pmu.board_temp_r`)

## Troubleshooting

### Uneven Current Distribution

**Symptom:** One pin carries significantly more current than others.

**Causes:**
1. Wire resistance imbalance
2. Connection resistance at terminals
3. Different wire lengths

**Solution:** Ensure all wires are same gauge and length, check terminal crimps.

### Repeated Single-Pin Faults

**Symptom:** Same pin always faults first under load.

**Causes:**
1. Higher resistance path to that pin
2. Poor thermal contact
3. Damaged PROFET chip

**Solution:** Swap primary/secondary pin assignments to isolate cause.

### PWM Noise

**Symptom:** Audible noise from merged output load.

**Causes:**
1. PWM frequency in audible range
2. Slight timing skew between pins

**Solution:** Use frequency above 20kHz for silent operation, or below 100Hz if motor can handle it.
