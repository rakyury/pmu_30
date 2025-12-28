# PMU-30 Telemetry System

## Overview

The PMU-30 telemetry system provides real-time streaming of device state, sensor readings, and operational data from the device to the configurator application. Telemetry is streamed at configurable rates (1-100 Hz) over the USB CDC or socket connection.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│   PMU-30        │     │   Protocol       │     │   Configurator      │
│   Firmware      │────►│   Transport      │────►│   Application       │
│                 │     │   (USB/Socket)   │     │                     │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
        │                                                  │
        │                                                  ▼
        │                                        ┌─────────────────────┐
        │                                        │ TelemetrySubject    │
        │                                        │ (Observer Pattern)  │
        │                                        └─────────────────────┘
        │                                                  │
        │                                    ┌─────────────┼─────────────┐
        ▼                                    ▼             ▼             ▼
┌─────────────────┐                   ┌───────────┐ ┌───────────┐ ┌───────────┐
│ Firmware sends  │                   │ Analog    │ │ Output    │ │ Digital   │
│ TELEMETRY_DATA  │                   │ Monitor   │ │ Monitor   │ │ Monitor   │
│ at subscribed   │                   │ Widget    │ │ Widget    │ │ Widget    │
│ rate (10-100Hz) │                   └───────────┘ └───────────┘ └───────────┘
└─────────────────┘
```

## Protocol Messages

### Subscribe to Telemetry (0x30)

Request telemetry streaming at specified rate.

| Field   | Size    | Description                  |
|---------|---------|------------------------------|
| rate_hz | 2 bytes | Telemetry rate (1-100 Hz)    |

```python
# Example: Subscribe at 10 Hz
device_controller.subscribe_telemetry(rate_hz=10)
```

### Unsubscribe Telemetry (0x31)

Stop telemetry streaming.

```python
device_controller.unsubscribe_telemetry()
```

### Telemetry Data Packet (0x32)

The telemetry packet contains 174 bytes of real-time device state:

| Offset | Size    | Field              | Description                        |
|--------|---------|--------------------|------------------------------------|
| 0      | 4 bytes | timestamp_ms       | Device uptime in milliseconds      |
| 4      | 2 bytes | voltage_mv         | Battery voltage in mV              |
| 6      | 2 bytes | temperature_c      | Board temperature (signed)         |
| 8      | 4 bytes | total_current_ma   | Total current draw in mA           |
| 12     | 40 bytes| adc_values         | 20 × uint16 ADC readings           |
| 52     | 30 bytes| profet_states      | 30 × uint8 channel states          |
| 82     | 60 bytes| profet_duties      | 30 × uint16 PWM duties (0-1000)    |
| 142    | 4 bytes | hbridge_states     | 4 × uint8 H-Bridge states          |
| 146    | 8 bytes | hbridge_positions  | 4 × uint16 H-Bridge positions      |
| 154    | 2 bytes | board_temp_2       | Secondary temperature (signed)     |
| 156    | 2 bytes | output_5v_mv       | 5V rail voltage in mV              |
| 158    | 2 bytes | output_3v3_mv      | 3.3V rail voltage in mV            |
| 160    | 2 bytes | flash_temp         | Flash temperature (signed)         |
| 162    | 4 bytes | system_status      | System status flags                |
| 166    | 4 bytes | fault_flags        | Fault flags bitmask                |
| 170    | 4 bytes | digital_inputs     | Digital inputs bitmask (20 bits)   |

### Extended Telemetry (Virtual Channels)

If additional data follows the base packet, it contains virtual channel values:

| Offset | Size    | Field              | Description                        |
|--------|---------|--------------------|------------------------------------|
| 174    | 2 bytes | virtual_count      | Number of virtual channels         |
| 176+   | 6 bytes | channel data       | Each: id (2B) + value (4B signed)  |

## Channel States

Each PROFET output channel reports one of these states:

| Value | State              | Description                    |
|-------|--------------------|--------------------------------|
| 0     | OFF                | Output is off                  |
| 1     | ON                 | Output is on (100% duty)       |
| 2     | FAULT_OVERCURRENT  | Overcurrent protection tripped |
| 3     | FAULT_OVERHEAT     | Thermal protection active      |
| 4     | FAULT_SHORT        | Short circuit detected         |
| 5     | FAULT_OPEN         | Open load detected             |
| 6     | PWM_ACTIVE         | PWM output active              |
| 7     | DISABLED           | Channel disabled in config     |

## Fault Flags

System-wide fault indicators (32-bit bitmask):

| Bit | Flag               | Description                    |
|-----|--------------------|--------------------------------|
| 0   | OVERVOLTAGE        | Input voltage too high         |
| 1   | UNDERVOLTAGE       | Input voltage too low          |
| 2   | OVERTEMPERATURE    | Board temperature exceeded     |
| 3   | CAN1_ERROR         | CAN bus 1 error                |
| 4   | CAN2_ERROR         | CAN bus 2 error                |
| 5   | FLASH_ERROR        | Flash memory error             |
| 6   | CONFIG_ERROR       | Configuration invalid          |
| 7   | WATCHDOG_RESET     | Watchdog reset occurred        |
| 8   | POWER_FAIL         | Power failure detected         |
| 9   | GROUND_FAULT       | Ground fault detected          |
| 10  | REVERSE_POLARITY   | Reverse polarity detected      |
| 11  | SENSOR_ERROR       | Sensor error                   |
| 12  | LUA_ERROR          | Lua script error               |
| 13  | LOGIC_ERROR        | Logic function error           |
| 16  | CHANNEL_FAULT_1    | Channels 1-8 have fault        |
| 17  | CHANNEL_FAULT_2    | Channels 9-16 have fault       |
| 18  | CHANNEL_FAULT_3    | Channels 17-24 have fault      |
| 19  | CHANNEL_FAULT_4    | Channels 25-30 have fault      |

## Data Classes

### TelemetryPacket

The main data structure for telemetry data:

```python
from communication.telemetry import TelemetryPacket

@dataclass
class TelemetryPacket:
    timestamp_ms: int              # Device uptime
    input_voltage_mv: int          # Battery voltage
    temperature_c: int             # Board temperature
    total_current_ma: int          # Total current
    adc_values: list[int]          # 20 ADC readings
    profet_states: list[ChannelState]  # 30 channel states
    profet_duties: list[int]       # 30 PWM duties
    hbridge_states: list[int]      # 4 H-Bridge states
    hbridge_positions: list[int]   # 4 H-Bridge positions
    fault_flags: FaultFlags        # System faults
    digital_inputs: list[int]      # 20 digital input states
    virtual_channels: dict[int, int]  # Virtual channel values
```

#### Useful Properties

```python
packet.input_voltage      # float: Voltage in volts
packet.has_faults         # bool: Any fault active
packet.active_channels    # list: Indices of ON/PWM channels
packet.faulted_channels   # list: Indices of faulted channels
packet.total_current_a    # float: Current in amps
packet.total_power_w      # float: Power in watts
```

### HBridgeTelemetry

Extended telemetry for H-Bridge motor control:

```python
@dataclass
class HBridgeTelemetry:
    bridge_id: int
    mode: HBridgeMode        # COAST, FORWARD, REVERSE, BRAKE, etc.
    state: HBridgeState      # IDLE, RUNNING, STALLED, FAULT, etc.
    direction: int           # 0=coast, 1=forward, 2=reverse, 3=brake
    pwm: int                 # 0-255 duty cycle
    current_ma: int          # Motor current
    position: int            # Position feedback
    omega: float             # Angular velocity (rad/s)
    theta: float             # Angular position (rad)
    temperature_c: float     # Motor/driver temperature
```

## Observer Pattern

The telemetry system uses the Observer pattern for efficient distribution to multiple widgets.

### TelemetrySubject

Central hub that distributes telemetry to subscribers:

```python
from communication.telemetry_observer import (
    TelemetrySubject, TelemetryField, get_telemetry_subject
)

# Get global instance
subject = get_telemetry_subject()

# Subscribe to specific fields
def on_voltage_update(updates):
    voltage = updates.get(TelemetryField.INPUT_VOLTAGE)
    print(f"Voltage: {voltage}V")

subject.subscribe(on_voltage_update, {TelemetryField.INPUT_VOLTAGE})
```

### TelemetryField Enum

Available fields for subscription:

| Field             | Description                    |
|-------------------|--------------------------------|
| INPUT_VOLTAGE     | Battery voltage (V)            |
| TEMPERATURE       | Primary board temperature (°C) |
| BOARD_TEMP_2      | Secondary temperature (°C)     |
| TOTAL_CURRENT     | Total current draw (A)         |
| UPTIME            | Device uptime (ms)             |
| SYSTEM_STATUS     | System status flags            |
| FAULT_FLAGS       | Fault bitmask                  |
| OUTPUT_5V         | 5V rail voltage (mV)           |
| OUTPUT_3V3        | 3.3V rail voltage (mV)         |
| PROFET_STATES     | Channel states array           |
| PROFET_CURRENTS   | Channel currents array         |
| PROFET_DUTIES     | PWM duty cycles array          |
| ADC_VALUES        | Raw ADC readings array         |
| DIGITAL_INPUTS    | Digital input states           |
| CAN_RX_VALUES     | CAN received values            |
| VIRTUAL_CHANNELS  | Virtual channel values         |
| ALL               | All fields (for widgets that need everything) |

### Creating a Telemetry Observer Widget

```python
from communication.telemetry_observer import TelemetryObserver, TelemetryField

class MyMonitorWidget(QWidget, TelemetryObserver):
    def __init__(self, parent=None):
        super().__init__(parent)
        # ... widget setup ...

    def get_subscribed_fields(self) -> set:
        """Return fields this widget needs."""
        return {
            TelemetryField.INPUT_VOLTAGE,
            TelemetryField.TEMPERATURE,
            TelemetryField.PROFET_STATES
        }

    def on_telemetry_update(self, updates: dict):
        """Handle telemetry updates."""
        if TelemetryField.INPUT_VOLTAGE in updates:
            self.voltage_label.setText(f"{updates[TelemetryField.INPUT_VOLTAGE]:.2f}V")

        if TelemetryField.TEMPERATURE in updates:
            self.temp_label.setText(f"{updates[TelemetryField.TEMPERATURE]}°C")
```

## Usage in Application

### DeviceController Integration

```python
from controllers.device_controller import DeviceController

controller = DeviceController()

# Connect to telemetry signal
controller.telemetry_received.connect(on_telemetry)

def on_telemetry(packet: TelemetryPacket):
    """Handle raw telemetry packet."""
    print(f"Voltage: {packet.input_voltage}V")
    print(f"Active channels: {packet.active_channels}")

# Connect to device
controller.connect({"type": "Emulator", "host": "localhost", "port": 5555})

# Start telemetry streaming
controller.subscribe_telemetry(rate_hz=10)
```

### Using TelemetryMixin

For widgets that need telemetry access:

```python
from ui.mixins.telemetry_mixin import TelemetryMixin

class MyWidget(QWidget, TelemetryMixin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_telemetry()  # From mixin

    def on_telemetry(self, packet):
        """Override to handle telemetry."""
        self.update_display(packet)
```

## Performance Considerations

1. **Rate Selection**: Choose appropriate telemetry rate for your use case:
   - 10 Hz: General monitoring, dashboards
   - 50 Hz: Real-time graphs, data logging
   - 100 Hz: High-speed diagnostics

2. **Selective Subscription**: Subscribe only to needed fields to reduce processing:
   ```python
   # Instead of ALL, subscribe to specific fields
   subject.subscribe(callback, {TelemetryField.INPUT_VOLTAGE})
   ```

3. **Throttling**: For slow UI updates, consider throttling:
   ```python
   import time
   last_update = 0

   def on_telemetry(updates):
       global last_update
       now = time.time()
       if now - last_update < 0.1:  # 100ms throttle
           return
       last_update = now
       # Update UI
   ```

## See Also

- [Protocol Specification](protocol_specification.md) - Full protocol documentation
- [Device Controller](../configurator/src/controllers/device_controller.py) - Controller implementation
- [Telemetry Module](../configurator/src/communication/telemetry.py) - Data structures
