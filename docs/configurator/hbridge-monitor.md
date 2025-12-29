# H-Bridge Monitor

The H-Bridge Monitor displays real-time status and provides manual control for all 4 H-Bridge motor controller channels.

## Table Layout

| Bridge | Name | Mode | Dir | PWM | Current | Speed | Position | Temp | Status |
|--------|------|------|-----|-----|---------|-------|----------|------|--------|
| HB1 | Window Motor | Forward | → | 75% | 2.5A | 50% | - | 45°C | RUN |
| HB2 | Wiper Motor | Wiper | ↔ | 100% | 3.2A | - | 85% | 52°C | RUN |
| HB3 | Seat Adjust | Idle | - | 0% | 0.0A | - | - | 35°C | IDLE |
| HB4 | Mirror | Reverse | ← | 50% | 0.8A | 25% | - | 38°C | RUN |

## Column Definitions

| Column | Width | Description |
|--------|-------|-------------|
| **Bridge** | 60px | H-Bridge identifier (HB1-HB4) |
| **Name** | 120px | User-assigned motor name |
| **Mode** | 80px | Operating mode |
| **Dir** | 40px | Direction indicator |
| **PWM** | 50px | Duty cycle (0-100%) |
| **Current** | 70px | Motor current draw |
| **Speed** | 60px | Relative speed (if available) |
| **Position** | 70px | Position feedback (wiper/encoder) |
| **Temp** | 50px | Driver temperature |
| **Status** | 60px | Current state |

## Operating Modes

| Mode | Description | Direction |
|------|-------------|-----------|
| **Coast** | Motor free-running | - |
| **Forward** | Positive direction | → |
| **Reverse** | Negative direction | ← |
| **Brake** | Active braking | X |
| **Wiper** | Automatic wiper pattern | ↔ |
| **PID** | Closed-loop control | Auto |

## Status Values

| Status | Description | Row Color |
|--------|-------------|-----------|
| **IDLE** | Motor stopped | Black (#000000) |
| **RUN** | Motor running | Green (#325032) or Blue (#282864) |
| **STALL** | Motor stalled | Orange (#643C00) |
| **FAULT** | General fault | Red (#503028) |
| **OC** | Overcurrent | Red (#503028) |
| **OT** | Overtemperature | Red (#503028) |

## Direction Indicators

| Symbol | Meaning |
|--------|---------|
| → | Forward direction |
| ← | Reverse direction |
| ↔ | Oscillating (wiper) |
| X | Braking |
| - | Idle/Coast |

## Control Panel

Located below the table, provides manual motor control:

```
+--------------------------------------------------+
|  [FWD]   [STOP]   [REV]   [BRAKE]   [All Stop]  |
|                                                  |
|  PWM: [====|=========] 75%     [0] [255]        |
+--------------------------------------------------+
```

### Control Buttons

| Button | Color | Action |
|--------|-------|--------|
| **FWD** | Light Green (#90EE90) | Run selected motor forward |
| **STOP** | Yellow (#FFD700) | Stop motor (coast) |
| **REV** | Light Blue (#87CEEB) | Run selected motor reverse |
| **BRAKE** | Salmon (#FFA07A) | Active brake |
| **All Stop** | Red (#FF6666) | Emergency stop all motors |

### PWM Slider

- **Range**: 0-255 (maps to 0-100% duty)
- **Default**: 128 (50%)
- **Live update**: Changes take effect immediately when motor running

## Row Colors

| Condition | Background |
|-----------|------------|
| Idle/Stopped | #000000 (Black) |
| Forward | #325032 (Dark Green) |
| Reverse | #282864 (Dark Blue) |
| Brake | #808000 (Dark Yellow) |
| Stalled | #643C00 (Dark Orange) |
| Fault | #503028 (Dark Red) |
| Disabled | #3C3C3C (Gray) |

## H-Bridge Specifications

| Parameter | Value |
|-----------|-------|
| Channels | 4 independent H-Bridges |
| Max Current | 20A continuous per channel |
| Peak Current | 40A for 10 seconds |
| PWM Frequency | Configurable 1-25 kHz |
| Voltage | Follows battery (8-18V) |

## Wiper Mode

Special mode for windshield wiper motors:

```
Configuration:
  mode: "wiper"
  park_position: 5%      (home position)
  sweep_angle: 90%       (max travel)
  speeds: [slow, fast]   (intermittent, continuous)

Operation:
  1. Motor sweeps from park to max position
  2. Returns to park position
  3. Waits for next sweep command
  4. Auto-park when stopped
```

### Wiper Position Display

| Value | Meaning |
|-------|---------|
| 0% | Parked position |
| 50% | Mid-sweep |
| 100% | Full sweep |
| PARK | Parking in progress |

## PID Mode

Closed-loop position or speed control:

```
Configuration:
  mode: "pid"
  setpoint_source: "channel_id"
  feedback_source: "encoder_channel"
  Kp: 1.0
  Ki: 0.1
  Kd: 0.05
```

## Current Monitoring

Current display format:

| Range | Format |
|-------|--------|
| < 1A | "0.XX A" |
| 1-10A | "X.X A" |
| 10-20A | "XX A" |
| > 20A (fault) | "OC!" |

## Temperature Monitoring

| Range | Display | Color |
|-------|---------|-------|
| < 60°C | Normal | White |
| 60-80°C | Warning | Orange |
| > 80°C | Critical | Red |
| > 100°C | Shutdown | Red + OT status |

## Manual Control Workflow

1. **Select H-Bridge** - Click row in table
2. **Set PWM level** - Adjust slider (0-255)
3. **Choose direction** - Click FWD or REV
4. **Stop** - Click STOP (coast) or BRAKE (active)

### Safety Notes

- **All Stop** button immediately halts all motors
- Motors auto-stop on disconnect
- Overcurrent triggers automatic shutdown
- Control panel only active when connected to device

## Wiring Diagram

```
        PMU-30 H-Bridge
         ____________
        |            |
Motor --|OUT_A  OUT_B|-- Motor
        |            |
        |   SENSE    |-- Current sense (internal)
        |____________|
              |
          GND / Battery
```

## Update Behavior

- **Refresh rate**: 100ms (10 Hz)
- **Data source**: H-Bridge telemetry
- **Offline**: Control panel disabled, last values shown

## Double-Click Action

Double-clicking a row opens the H-Bridge Configuration dialog.

## Command Protocol

Commands are sent via the device protocol:

```
Signal: hbridge_command(bridge_id, command, pwm)

Commands:
  0 = Coast (stop)
  1 = Forward
  2 = Reverse
  3 = Brake
```
