# PMU-30 Technical Specification (Hardware Design)

**Document Version:** 1.2
**Date:** 2025-12-29
**Status:** Implementation Phase
**Owner:** R2 m-sport
**Confidentiality:** Proprietary - Internal Use Only

---

**© 2025 R2 m-sport. All rights reserved.**

This document contains proprietary information belonging to R2 m-sport. No part of this document may be reproduced, distributed, or transmitted without prior written permission.

---

## 1. General Requirements

### 1.1 Purpose
Design and development of a 30-channel intelligent power distribution module for motorsport and high-performance automotive applications.

### 1.2 Operating Environment
- **Temperature Range**: -40°C to +85°C (industrial grade)
- **Vibration**: Per ISO 16750-3 (automotive vibration)
- **Shock**: Per ISO 16750-3 (automotive shock)
- **EMC**: ISO 7637-2, ISO 11452-2 (automotive EMC)
- **IP Rating**: IP65 (with proper connector sealing)
- **Altitude**: Up to 3000m

### 1.3 Electrical Requirements
- **Input Voltage**: 12V nominal, 6-22V operating range
- **Surge Protection**: ISO 7637-2 transient immunity
- **Reverse Polarity**: Internal protection (all voltage range)
- **Operating Current**: Up to 1200A total (30 channels × 40A) + 240A (H-bridges)
- **Standby Current**: <100mA @ 12V
- **Temperature Rating**: AEC-Q100 Grade 1 (-40°C to +125°C)

---

## 2. Power Stage Design

### 2.1 Output Channels (30x)

#### 2.1.1 Power Switch Requirements
- **Type**: Infineon PROFET 2 series or equivalent
- **Recommended Part**: BTS7008-2EPA or BTS7012-2EPA
- **Continuous Current**: 40A minimum per channel
- **Inrush Current**: 160A for 1ms minimum
- **On-Resistance**: <5mΩ typical
- **Diagnostic Features**:
  - Current sense output
  - Temperature sense output
  - Open load detection
  - Short circuit detection
  - Overvoltage protection

#### 2.1.2 Output Protection
- **Overcurrent**: Hardware + software limiting
  - Adjustable threshold: 0.5A to 45A
  - Response time: <10µs
- **Overtemperature**: Per-channel monitoring
  - Warning threshold: 125°C
  - Shutdown threshold: 150°C
- **Short Circuit**: Immediate shutdown (<1µs)
- **Open Load Detection**: Detection at <1A load

#### 2.1.3 PWM Capability
- **Frequency Range**: 10Hz to 30kHz
- **Resolution**: 12-bit minimum (0.025%)
- **Soft-Start**: Configurable 0-5000ms ramp
- **Synchronization**: Phase-locked outputs available

#### 2.1.4 Output Connectors
- **Type**: AMP Superseal 1.5mm or DTM series
- **Pinout**: Power + Sense return per channel
- **Wire Gauge Support**: 12-18 AWG (0.8-4mm²)

### 2.2 H-Bridge Outputs (4x Dual)

#### 2.2.1 H-Bridge Requirements
- **Type**: Dual H-Bridge motor driver
- **Recommended IC**: BTN8982TA (Infineon) or VNH5019 (STMicroelectronics)
- **Continuous Current**: 30A per bridge
- **Peak Current**: 60A for 100ms
- **Operating Voltage**: 6-22V
- **PWM Frequency**: 10Hz - 20kHz
- **Control Modes**:
  - Forward (CW)
  - Reverse (CCW)
  - Brake (short both sides)
  - Coast (hi-Z)

#### 2.2.2 H-Bridge Protection
- **Overcurrent**: Hardware current sense + software limiting
- **Overtemperature**: Thermal shutdown @ 150°C
- **Short Circuit**: Immediate shutdown
- **Undervoltage Lockout**: Prevent operation below 5V

#### 2.2.3 Applications
- Wiper motors (with park/brake function)
- Cooling fans (variable speed, bidirectional)
- Seat motors, window motors
- Throttle actuators
- Wastegate actuators

#### 2.2.4 Wiper-Specific Features
- **Park Position Detection**: Dedicated input for wiper park sensor
- **Brake Function**: Active braking when commanded to stop
- **Auto-park**: Return to park position on shutdown
- **Interval Control**: Configurable wiper delay/interval timing

### 2.3 Sensor Power Output

#### 2.3.1 5V Sensor Supply
- **Output Voltage**: 5.0V ±2%
- **Current Capacity**: 500mA continuous
- **Protection**: Short-circuit protected, current limiting
- **Monitoring**: Real-time current and voltage monitoring
- **Fault Detection**: Overcurrent, short to ground/battery
- **Applications**:
  - MAP sensors
  - TPS sensors
  - Temperature sensors
  - Pressure transducers
  - Hall-effect sensors

### 2.4 Power Supply Architecture

#### 2.4.1 Main Power Input
- **Positive Terminal**: Radlock 200A connector
  - **Type**: TE Connectivity Radlock (or equivalent)
  - **Rating**: 200A continuous
  - **Features**: Tool-less connection, vibration resistant
- **Ground Terminal**: M8 stud terminal (150A rated)
- **Fuse**: External 200A ANL fuse recommended
- **Filtering**:
  - TVS diode array (SMAJ series)
  - LC filter for noise suppression
  - Bulk capacitance: 1000µF minimum

#### 2.4.2 Internal Power Rails
- **12V Rail**: Direct from battery (filtered)
- **5V Rail**: 5A minimum, buck converter
  - For MCU, sensors, logic
  - Ripple: <50mV
- **3.3V Rail**: 3A minimum, LDO or buck
  - For MCU core, CAN transceivers
  - Ripple: <30mV
- **Isolation**: Optoisolated USB and CAN

---

## 3. Microcontroller System

### 3.1 Main MCU

#### 3.1.1 Processor Selection
- **Family**: STMicroelectronics STM32H7 series
- **Recommended**: STM32H743VIT6 or STM32H753VIT6
- **Core**: ARM Cortex-M7 @ 480MHz
- **Flash**: 2MB internal
- **RAM**: 1MB (512KB SRAM + 512KB DTCM/ITCM)
- **Package**: LQFP-100 or BGA

#### 3.1.2 Required Peripherals
- **Timers**:
  - 2x advanced (TIM1, TIM8) for PWM
  - 4x general purpose for timing
- **ADC**: 3x 16-bit ADC, 36 channels total
- **SPI**: 3x (for memory, WiFi module, expansion)
- **I2C**: 2x (for sensors, RTC)
- **UART**: 2x (for debug, Bluetooth)
- **USB**: 1x USB 2.0 HS with PHY
- **CAN-FD**: 2x FDCAN peripherals
- **RTC**: Integrated with backup domain

### 3.2 WiFi/Bluetooth Module

#### 3.2.1 Module Selection
- **Recommended**: ESP32-C3-MINI-1 or ESP32-C6
- **Interface**: SPI or UART to main MCU
- **WiFi**: 802.11 b/g/n, AP mode required
- **Bluetooth**: BLE 5.0
- **Power**: <200mA active, <5µA deep sleep

#### 3.2.2 Antenna
- **Type**: PCB antenna or U.FL connector
- **Frequency**: 2.4GHz dual-band
- **Gain**: >2dBi

---

## 4. Input/Output System

### 4.1 Digital Input Channels (20x)

PMU-30 features 20 dedicated digital input channels optimized for switch, button, and frequency inputs.

#### 4.1.1 Digital Input Specifications
- **Type**: Dedicated digital inputs
- **Voltage Range**: 0-5V nominal
- **Resolution**: 10-bit ADC (oversampling to 12-bit effective)
- **Sample Rate**: 500Hz per channel (logic update frequency)
- **Input Impedance**: >100kΩ
- **Protection**:
  - Overvoltage protection to 40V
  - Reverse voltage protection to -18V
  - ESD protection (IEC 61000-4-2, Level 4)
  - TVS diode clamp + series resistor
  - Resettable fuse (optional)

#### 4.1.2 Digital Input Types and Modes

Each digital input can be configured as one of the following types:

##### 1. Switch - Active Low
- **Description**: Digital switch input, active when grounded
- **Logic**: 0 when voltage < threshold, 1 when voltage > threshold
- **Pullup/Pulldown**: Configurable internal pull-up resistor
- **Debounce**: Configurable time delay (e.g., 0.01s)
- **Threshold Voltages**:
  - 0 if voltage > [V]: Configurable (e.g., 3.5V)
  - 1 if voltage < [V]: Configurable (e.g., 1.5V)
- **Applications**: Ground-switched buttons, switches

##### 2. Switch - Active High
- **Description**: Digital switch input, active when powered
- **Logic**: 1 when voltage > threshold, 0 when voltage < threshold
- **Pullup/Pulldown**: Configurable internal pull-down resistor
- **Debounce**: Configurable time delay
- **Threshold Voltages**: Configurable upper/lower limits
- **Applications**: +12V switched inputs, positive logic switches

##### 3. Rotary Switch
- **Description**: Multi-position rotary switch input
- **Detection**: Voltage-based position detection
- **Positions**: Up to 12 positions
- **Voltage Ranges**: User-defined voltage ranges per position
- **Debounce**: Position change filtering
- **Applications**: Multi-position selector switches, mode selectors

##### 4. Frequency Input
- **Description**: Frequency measurement input
- **Range**: 0-10kHz
- **Resolution**: 1Hz
- **Timeout**: Signal loss detection (configurable)
- **Applications**:
  - Speed sensors
  - RPM sensors (via divider)
  - Pulse-width encoders

#### 4.1.3 Digital Input Configuration Parameters

| Parameter | Description | Range |
|-----------|-------------|-------|
| **Name** | User-defined input name | Up to 32 characters |
| **Pin** | Physical pin assignment | 1-20 |
| **Type** | Input type selection | switch-low, switch-high, rotary, frequency |
| **Pull-up/Pull-down** | Internal resistor | Pull-up 10kΩ, Pull-down 10kΩ, Floating |
| **Threshold High** | Upper voltage threshold | 0-5V, 0.1V steps |
| **Threshold Low** | Lower voltage threshold | 0-5V, 0.1V steps |
| **Debounce Time** | Switch debounce delay | 0.001-1.0 seconds |

#### 4.1.4 Digital Input Example

##### Ignition Switch (Active Low)
```
Type: Switch - Active Low
Pull-up: 10kΩ
Threshold: 2.5V
Debounce: 50ms
```

---

### 4.2 Analog Input Channels (20x)

PMU-30 features 20 dedicated analog input channels optimized for sensor measurements.

#### 4.2.1 Analog Input Specifications
- **Type**: Dedicated analog inputs
- **Voltage Range**: 0-5V nominal
- **Resolution**: 12-bit ADC (4096 steps)
- **Sample Rate**: 1kHz per channel
- **Input Impedance**: >100kΩ
- **Protection**: Same as digital inputs (40V overvoltage, -18V reverse)

#### 4.2.2 Analog Input Types

##### 1. Linear Analog Sensor
- **Description**: Direct voltage-to-value mapping with linear scaling
- **Input Range**: 0-5V
- **Scaling**: User-defined slope and offset
  - Output = (Voltage × Multiplier) + Offset
- **Unit**: User-configurable (V, bar, psi, °C, %, etc.)
- **Decimal Places**: 0-3 decimal places
- **Filtering**: Moving average, configurable samples
- **Applications**:
  - Throttle position sensors (TPS)
  - Linear potentiometers
  - 0-5V pressure sensors
  - Linear temperature sensors

##### 2. Calibrated Analog Sensor
- **Description**: Multi-point calibration table for non-linear sensors
- **Calibration**: Up to 20 calibration points (voltage → value)
- **Interpolation**: Linear interpolation between points
- **Unit**: User-configurable
- **Decimal Places**: 0-3 decimal places
- **Extrapolation**: Clamp to min/max or linear extrapolation
- **Applications**:
  - Non-linear temperature sensors (NTC/PTC)
  - Non-linear pressure sensors
  - Fuel level sensors
  - Custom sensor curves

#### 4.2.3 Analog Input Configuration Parameters

| Parameter | Description | Range |
|-----------|-------------|-------|
| **Name** | User-defined input name | Up to 32 characters |
| **Pin** | Physical pin assignment | 1-20 |
| **Type** | Input type selection | linear, calibrated |
| **Pull-up/Pull-down** | Internal resistor | 10kΩ up/down, 100kΩ up/down, Floating |
| **Unit** | Measurement unit | Text string (V, bar, psi, °C, °F, %, etc.) |
| **Decimal Places** | Display precision | 0-3 |
| **Multiplier** | Linear scaling factor | -1000.0 to +1000.0 |
| **Offset** | Linear offset value | -1000.0 to +1000.0 |
| **Filter Samples** | Moving average samples | 1-20 |
| **Calibration Table** | Voltage-value pairs | Up to 20 points |

#### 4.2.4 Analog Input Examples

##### Example 1: Oil Pressure Sensor (Linear)
```
Type: Linear Analog Sensor
Input Range: 0.5V - 4.5V
Output Range: 0 - 10 bar
Multiplier: 2.5 (10 bar / 4V)
Offset: -1.25 (to account for 0.5V offset)
Unit: bar
Decimal Places: 1
```

##### Example 2: Coolant Temperature (Calibrated)
```
Type: Calibrated Analog Sensor
Calibration Table:
  0.5V → -40°C
  1.0V → 0°C
  2.0V → 40°C
  3.0V → 80°C
  4.0V → 120°C
Unit: °C
Decimal Places: 0
```

#### 4.2.5 Signal Conditioning (Analog Inputs)
- **Filtering**: RC filter, 1kHz cutoff (hardware)
- **Digital Filtering**: Moving average filter (software, configurable)
- **Protection**: TVS + series resistor + resettable fuse
- **Calibration**: Per-channel offset and gain (factory + user)
- **Sampling**: 1kHz base rate, 12-bit effective resolution

### 4.3 DAC Outputs (10x)

#### 4.3.1 Output Specifications
- **Type**: Voltage output DAC
- **Voltage Range**: 0-5V
- **Resolution**: 12-bit
- **Update Rate**: 10kHz minimum
- **Output Current**: 10mA per channel
- **Protection**: Short-circuit protected

#### 4.3.2 Applications
- Gauge outputs
- External device control
- Analog signal generation
- Voltage reference outputs

### 4.4 Digital I/O
- **GPIO Reserve**: 10x additional GPIO for expansion
- **Voltage Level**: 3.3V logic, 5V tolerant
- **Drive Capability**: 25mA per pin

---

## 5. Communication Interfaces

### 5.1 CAN FD (2x)

#### 5.1.1 Transceiver
- **Type**: TI TCAN1044 or similar CAN FD transceiver
- **Speed**: Up to 5Mbps (CAN FD)
- **Isolation**: Optional isolation (ADuM1201 or Si8651)
- **Termination**: 120Ω switchable per channel
- **Protection**:
  - ±58V fault protection
  - Thermal shutdown
  - TXD timeout

#### 5.1.2 Connector
- **Type**: 2x DTM 4-pin or D-sub 9-pin
- **Pinout**: CAN_H, CAN_L, GND, +12V (optional)

#### 5.1.3 CAN Message Object Configuration

Each CAN message that the PMU-30 transmits or receives must be configured as a Message Object. The configurator provides a comprehensive interface for defining CAN messages.

##### Message Object Parameters

| Parameter | Description | Range/Options |
|-----------|-------------|---------------|
| **Name** | User-defined message identifier | Up to 32 characters (e.g., "m_mob8") |
| **CANbus** | Target CAN bus selection | CAN1, CAN2, CAN3, CAN4 |
| **Base ID (hex)** | CAN message identifier | 0x000-0x7FF (Standard), 0x00000000-0x1FFFFFFF (Extended) |
| **ID Type** | Identifier format | Standard (11-bit) / Extended (29-bit) |
| **Message Type** | Message category | Normal, RTR (Remote Transmission Request), Error frame |
| **Size** | Number of CAN frames | 1-8 frames (for CAN FD: up to 64 bytes) |
| **Timeout [s]** | Reception timeout | 0.001-60.0 seconds |
| **Direction** | Message direction | Transmit (TX) / Receive (RX) / Both |
| **Transmission Rate [Hz]** | Periodic transmission frequency | 0 (on-demand) to 1000 Hz |
| **Data Length Code (DLC)** | Number of data bytes | 0-8 (CAN 2.0), 0-64 (CAN FD) |

##### Data Configuration

Each message object includes data field configuration:

- **Data Bytes**: 8 bytes for CAN 2.0 (0x0 to 0x7), up to 64 bytes for CAN FD
- **Default Values**: Hexadecimal values for each byte (e.g., 0xFF, 0x00, 0xAA)
- **Live Capture**: Enable real-time data capture from CAN bus for receive messages
- **Signal Mapping**: Map individual signals within the message (via DBC integration)

##### Test Data Interface

The configurator provides test data functionality for development and debugging:

- **Manual Entry**: Enter test data in hexadecimal format for each byte
- **Live Capture**: Capture actual CAN bus data in real-time
- **Playback**: Replay captured messages for testing
- **Frequency Control**: Set transmission frequency for test messages

##### Example Message Configurations

**Example 1: Periodic Status Broadcast (TX)**
```
Name: PMU_Status
CANbus: CAN1
Base ID: 0x600
Type: Standard (11-bit)
Message Type: Normal
Size: 1 frame
DLC: 8 bytes
Transmission Rate: 100 Hz
Data: 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00
```

**Example 2: ECU Data Reception (RX)**
```
Name: Engine_Data
CANbus: CAN2
Base ID: 0x0CFFF048
Type: Extended (29-bit)
Message Type: Normal
Size: 1 frame
Timeout: 0.1 s
DLC: 8 bytes
Live Capture: Enabled
```

**Example 3: Event-Triggered Command (TX)**
```
Name: Output_Command
CANbus: CAN1
Base ID: 0x701
Type: Standard
Message Type: Normal
Size: 1 frame
Transmission Rate: 0 Hz (on-demand)
DLC: 4 bytes
```

##### Message Filtering and Acceptance

- **Hardware Filtering**: STM32H7 CAN peripheral supports hardware message filtering
- **Filter Banks**: Up to 28 filter banks per CAN interface
- **Filter Modes**:
  - ID List mode (exact match)
  - ID Mask mode (range match)
- **FIFO Assignment**: Assign messages to FIFO0 or FIFO1 for priority handling

##### CAN FD Specific Features

When using CAN FD interfaces (CAN1, CAN2):

- **Bit Rate Switching (BRS)**: Enable faster data phase (up to 5 Mbps)
- **Flexible Data Rate**: Support for 12, 16, 20, 24, 32, 48, 64 byte payloads
- **Error State Indicator (ESI)**: Monitor transmitter error state
- **CRC**: Extended CRC for enhanced error detection

### 5.2 USB-C

#### 5.2.1 Interface
- **Standard**: USB 2.0 High-Speed
- **PHY**: USB3300 or integrated
- **Speed**: 480Mbps
- **Power**: USB-C PD sink (optional 5V/3A)
- **Protection**: ESD protection, overcurrent

#### 5.2.2 Functions
- Device configuration
- Firmware updates
- Real-time data streaming
- Diagnostic interface

### 5.3 WiFi

#### 5.3.1 Mode
- **Primary**: Access Point (AP) mode
- **SSID**: PMU30-XXXXXX (MAC-based)
- **Security**: WPA2-PSK
- **Channel**: Auto-select (1-11)
- **Range**: 50m line-of-sight

#### 5.3.2 Services
- HTTP web server (port 80)
- WebSocket (real-time data)
- mDNS (pmu30.local)
- OTA update server

### 5.4 Bluetooth

#### 5.4.1 Mode
- **Type**: Bluetooth Low Energy (BLE)
- **Profile**: Custom GATT services
- **Range**: 10m typical
- **Pairing**: PIN or NFC (optional)

#### 5.4.2 Services
- Device status broadcast
- Configuration interface
- Firmware update (alternative to WiFi)

---

## 5.5 GPS/GNSS Module

### 5.5.1 Module Selection
- **Recommended**: u-blox MAX-M10S or NEO-M9N
- **Constellation**: GPS, GLONASS, Galileo, BeiDou (concurrent)
- **Position Accuracy**: 1.5m CEP (open sky)
- **Velocity Accuracy**: 0.05 m/s
- **Update Rate**: Configurable 1-25 Hz
- **Time to First Fix**: <1s hot start, <26s cold start
- **Interface**: UART (115200 baud default)
- **Protocol**: NMEA 0183, UBX binary

### 5.5.2 Antenna
- **Type**: External active antenna via U.FL connector
- **Gain**: 15-30 dB LNA
- **Voltage**: 3.3V bias (provided by module)
- **Placement**: Keep-out zone 15mm radius on PCB

### 5.5.3 Applications
- High-precision vehicle speed measurement
- Position logging for track analysis
- Lap timing (geofence-based)
- Time synchronization for data logging
- Distance and heading calculation
- Acceleration/deceleration analysis

### 5.5.4 Data Available
| Parameter | Update Rate | Resolution | Notes |
|-----------|-------------|------------|-------|
| Latitude/Longitude | 1-25 Hz | 0.0000001° | ~1cm resolution |
| Altitude | 1-25 Hz | 0.1m | MSL or WGS84 |
| Speed | 1-25 Hz | 0.01 m/s | Ground speed |
| Heading | 1-25 Hz | 0.01° | Course over ground |
| UTC Time | 1 Hz | 1ms | GPS time sync |
| Satellites | 1 Hz | Count | Visible/used |
| HDOP/PDOP | 1 Hz | 0.1 | Position accuracy |

---

## 5.6 LIN Bus

### 5.6.1 Interface
- **Standard**: LIN 2.2A
- **Speed**: Up to 20kbps
- **Mode**: Master or Slave (configurable)
- **Applications**:
  - Dashboard integration
  - Climate control
  - Window/mirror control
  - Diagnostic communication

### 5.6.2 Transceiver
- **Type**: TJA1021 or similar
- **Protection**: Short circuit, overvoltage
- **Wake-up**: LIN wake-up capable

---

## 5.7 Lua Scripting Engine

### 5.7.1 Overview
PMU-30 includes an embedded Lua 5.4 scripting engine for advanced custom logic that cannot be achieved with built-in logic operations. This feature is inspired by RaceCapture's successful Lua implementation.

### 5.7.2 Lua Engine Specifications
- **Version**: Lua 5.4 (lightweight embedded version)
- **Memory**: 256KB dedicated RAM for scripts
- **Flash Storage**: Up to 128KB for script storage
- **Execution**: Sandboxed environment for safety
- **Update Rate**: Configurable (10Hz - 500Hz)
- **Script Slots**: Up to 10 independent scripts

### 5.7.3 Available Lua APIs

#### System Functions
```lua
-- Get system uptime in milliseconds
getUptime()

-- Get battery voltage
getBatteryVoltage()

-- Get board temperature
getBoardTemp()

-- Print debug message
print(message)
```

#### Output Control
```lua
-- Set output channel state
setOutput(channel, state)  -- channel: 1-30, state: 0/1

-- Set output PWM duty cycle
setOutputPWM(channel, duty)  -- duty: 0-100%

-- Set output current limit
setOutputCurrentLimit(channel, amps)

-- H-Bridge control
setHBridge(bridge, mode, duty)  -- bridge: 1-4, mode: 'fwd'/'rev'/'brake'/'coast'
```

#### Input Reading
```lua
-- Read analog input (0-5V)
getAnalogInput(channel)  -- returns voltage

-- Read digital input
getDigitalInput(channel)  -- returns true/false

-- Read frequency input
getFrequencyInput(channel)  -- returns Hz
```

#### Sensor Data
```lua
-- Get accelerometer data
getAccelX(), getAccelY(), getAccelZ()  -- returns g-force

-- Get gyroscope data
getGyroX(), getGyroY(), getGyroZ()  -- returns degrees/sec

-- Get channel current
getOutputCurrent(channel)  -- returns amps

-- Get channel temperature
getOutputTemp(channel)  -- returns °C
```

#### CAN Functions
```lua
-- Send CAN message
sendCAN(bus, id, data, dlc)  -- bus: 1-4, id: CAN ID, data: table, dlc: 1-64

-- Receive CAN message (in onCANMessage callback)
function onCANMessage(bus, id, data, dlc)
    -- Process received message
end

-- Read CAN signal from DBC
getCANSignal("SignalName")  -- returns signal value

-- Write CAN signal to DBC
setCANSignal("SignalName", value)
```

#### Timers and Delays
```lua
-- Create timer
setTimer(id, interval_ms, callback)

-- Cancel timer
cancelTimer(id)

-- Get milliseconds since script start
millis()
```

#### Math and Logic
```lua
-- Map value from one range to another
map(value, fromLow, fromHigh, toLow, toHigh)

-- Constrain value
constrain(value, min, max)

-- Moving average filter
movingAvg(channel, value, samples)
```

### 5.7.4 Script Lifecycle

#### Initialization
```lua
function onInit()
    -- Called once when script starts
    print("Script initialized")
end
```

#### Main Loop
```lua
function onTick()
    -- Called at configured rate (10-500Hz)
    -- Main script logic goes here
end
```

#### Event Callbacks
```lua
function onCANMessage(bus, id, data, dlc)
    -- Called when CAN message received
end

function onInputChange(channel, value)
    -- Called when input state changes
end

function onFault(channel, faultType)
    -- Called when fault detected
end
```

### 5.7.5 Example Scripts

#### Example 1: Custom Launch Control
```lua
-- Launch control with RPM-based boost control
local launchActive = false
local targetRPM = 4000

function onTick()
    local rpm = getCANSignal("Engine_RPM")
    local throttle = getAnalogInput(1)  -- TPS
    local clutchPressed = getDigitalInput(2)

    if clutchPressed and throttle > 90 then
        launchActive = true
    end

    if launchActive and rpm > targetRPM then
        -- Cut ignition outputs 1-4 (ignition coils)
        for i = 1, 4 do
            setOutput(i, 0)
        end
    else
        for i = 1, 4 do
            setOutput(i, 1)
        end
    end

    if not clutchPressed then
        launchActive = false
    end
end
```

#### Example 2: Progressive Nitrous Control
```lua
-- Progressive nitrous system with safety interlocks
function onTick()
    local rpm = getCANSignal("Engine_RPM")
    local tps = getAnalogInput(1)
    local nitrousButton = getDigitalInput(5)
    local coolantTemp = getCANSignal("Coolant_Temp")

    -- Safety checks
    local safeToArm = (rpm > 3000 and rpm < 7500
                       and coolantTemp < 95
                       and tps > 80)

    if nitrousButton and safeToArm then
        -- Progressive solenoid control based on RPM
        local nitrousDuty = map(rpm, 3000, 7500, 30, 100)
        setOutputPWM(10, nitrousDuty)  -- Nitrous solenoid
        setOutput(11, 1)  -- Fuel enrichment solenoid
    else
        setOutput(10, 0)
        setOutput(11, 0)
    end
end
```

#### Example 3: Intelligent Cooling Fan Control
```lua
-- Multi-stage fan control with predictive logic
local fanSpeed = 0
local tempHistory = {}
local MAX_HISTORY = 10

function onTick()
    local coolantTemp = getCANSignal("Coolant_Temp")
    local vehicleSpeed = getCANSignal("Vehicle_Speed")
    local engineLoad = getCANSignal("Engine_Load")

    -- Track temperature trend
    table.insert(tempHistory, coolantTemp)
    if #tempHistory > MAX_HISTORY then
        table.remove(tempHistory, 1)
    end

    local tempRising = (tempHistory[#tempHistory] > tempHistory[1])

    -- Fan control logic
    if coolantTemp > 95 or (tempRising and coolantTemp > 90) then
        fanSpeed = 100
    elseif coolantTemp > 85 and vehicleSpeed < 30 then
        fanSpeed = 70
    elseif coolantTemp > 80 then
        fanSpeed = 40
    elseif coolantTemp < 75 then
        fanSpeed = 0
    end

    -- Apply fan speed
    setOutputPWM(15, fanSpeed)  -- Fan relay on channel 15
end
```

### 5.7.6 Script Management
- **Upload**: Via USB, WiFi, or configurator software
- **Storage**: Scripts stored in external flash
- **Editor**: Built-in editor in configurator with syntax highlighting
- **Debugging**: Serial console output, breakpoints (via configurator)
- **Validation**: Syntax check before upload
- **Runtime Protection**: Watchdog timer, memory limits, execution time limits

### 5.7.7 Safety and Limitations
- **Sandboxed**: Scripts cannot access system-critical functions
- **Execution Time**: Max 10ms per tick (enforced)
- **Memory Limits**: 256KB RAM limit
- **No File I/O**: Scripts cannot write to filesystem (security)
- **Protected Functions**: Cannot override safety limits (current, temp)

---

## 5.8 CAN Database (DBC/CANX) Support

### 5.8.1 Overview
PMU-30 supports industry-standard CAN database formats for seamless integration with existing vehicle systems and data acquisition equipment.

### 5.8.2 Supported Formats
- **DBC**: Vector CANdb++ database format
- **KCD**: Kayak CAN definition (XML-based)
- **SYM**: PEAK PCAN symbol file format
- **Future**: CANX (extended format)

### 5.8.3 DBC Import Capabilities

#### Automatic Signal Mapping
- Import complete CAN database files
- Automatic parsing of:
  - Message definitions (ID, name, DLC)
  - Signal definitions (name, start bit, length, byte order)
  - Value tables (enumerations)
  - Scaling and offset (factor, offset)
  - Min/max values
  - Units
  - Multiplex signals

#### Signal Access
```c
// In firmware
float rpm = can_get_signal_value("Engine_RPM");
float coolant_temp = can_get_signal_value("Coolant_Temp");
can_set_signal_value("PMU_Output_Status", 0x12345678);
```

```lua
-- In Lua scripts
local rpm = getCANSignal("Engine_RPM")
local speed = getCANSignal("Vehicle_Speed")
setCANSignal("PMU_Status", 1)
```

#### CAN Bus Input Configuration

The configurator provides a comprehensive interface for mapping CAN signals to internal virtual channels. Each CAN input can extract specific signals from CAN messages and make them available to the logic engine, Lua scripts, and output mappings.

##### Channel Configuration

| Parameter | Description | Options/Range |
|-----------|-------------|---------------|
| **Create new channel** | Create a new virtual channel for this signal | Radio button |
| **Override existing** | Map signal to an existing channel | Radio button (recommended) |
| **Override channel** | Target channel name | User-defined (e.g., "ecu.rpm", "sensor.oil_pressure") |

##### Message Object Selection

| Parameter | Description | Options/Range |
|-----------|-------------|---------------|
| **Message object** | CAN message object to extract from | Dropdown list of configured messages |
| **Message ID** | CAN message identifier | Display only (from message object) |

##### Signal Extraction Parameters

| Parameter | Description | Options/Range |
|-----------|-------------|---------------|
| **Type** | Data type of the signal | unsigned, signed, float, double |
| **Data format** | Bit width of the signal | 1bit, 8bit, 16bit, 32bit, 64bit |
| **Endian** | Byte order | little endian, big endian (Motorola) |
| **Byte offset** | Starting byte position in message | 0-63 (0-7 for CAN 2.0) |
| **Extract bitfield** | Enable bit-level extraction | Checkbox |
| **Bit count** | Number of bits to extract | 1-64 |
| **Bit position** | Starting bit position within byte | 0-7 |

##### Scaling and Conversion

| Parameter | Description | Range |
|-----------|-------------|-------|
| **Multiplier** | Multiply extracted value | -1000000.0 to +1000000.0 |
| **Divider** | Divide extracted value | 0.001 to 1000000.0 |
| **Offset** | Add offset to result | -1000000.0 to +1000000.0 |
| **Decimal places** | Display precision | 0-6 |

**Formula:** `Result = ((RawValue × Multiplier) / Divider) + Offset`

##### Fault Handling

| Parameter | Description | Options |
|-----------|-------------|---------|
| **If message times out** | Behavior when message not received | - Use the previous value (hold last)<br>- Set value (specify fallback) |
| **Set value** | Fallback value on timeout | User-defined numeric value |

##### Test Data Interface

The configurator includes a test data section for validation:

| Parameter | Description |
|-----------|-------------|
| **Length** | Message length (DLC) | Matches message object |
| **Data (hex)** | Raw CAN data bytes | 8 bytes (CAN 2.0) or up to 64 bytes (CAN FD) |
| **Live Capture** | Capture real-time CAN data | Checkbox - enables live monitoring |
| **Result** | Calculated signal value | Display field showing decoded result |

##### Example Configurations

**Example 1: Engine RPM (16-bit unsigned, little endian)**
```
Override channel: ecu.rpm
Message object: m_emublack (ID: 0x600)
Type: unsigned
Data format: 16bit
Endian: little endian
Byte offset: 0
Bit count: 16
Bit position: 0
Multiplier: 1
Divider: 1
Offset: 0
Timeout: use previous value

Test data: 03 00 01 01 00 01 00 00
Result: 3 rpm
```

**Example 2: Coolant Temperature (8-bit signed with offset)**
```
Override channel: ecu.coolant_temp
Message object: m_engine_data (ID: 0x0CFFF048)
Type: signed
Data format: 8bit
Endian: little endian
Byte offset: 2
Multiplier: 1
Divider: 1
Offset: -40
Decimal places: 0
Timeout: set value: -40

Formula: Temperature = RawValue - 40
Range: -40°C to +215°C
```

**Example 3: Throttle Position (10-bit bitfield)**
```
Override channel: ecu.tps
Message object: m_sensors (ID: 0x123)
Type: unsigned
Data format: 16bit
Endian: little endian
Byte offset: 1
Extract bitfield: ☑
Bit count: 10
Bit position: 0
Multiplier: 0.1
Divider: 1
Offset: 0
Decimal places: 1
Timeout: use previous value

Formula: TPS% = (RawValue × 0.1)
Range: 0.0% to 102.3%
```

**Example 4: Oil Pressure (big endian, scaled)**
```
Override channel: sensor.oil_pressure
Message object: m_oil_data (ID: 0x456)
Type: unsigned
Data format: 16bit
Endian: big endian
Byte offset: 0
Multiplier: 1
Divider: 100
Offset: 0
Decimal places: 2
Timeout: set value: 0

Formula: Pressure = RawValue / 100
Range: 0.00 to 655.35 bar
```

##### Signal Mapping Best Practices

1. **Channel Naming**: Use hierarchical naming (e.g., "ecu.rpm", "sensor.oil_pressure")
2. **Override Existing**: Prefer overriding existing channels for consistency
3. **Timeout Handling**: Use "previous value" for critical signals, "set value" for non-critical
4. **Bit Extraction**: Use bitfield extraction for signals not byte-aligned
5. **Scaling**: Apply multiplier/divider to match engineering units
6. **Testing**: Always verify with test data before deployment

##### Virtual Channel Usage

Once mapped, CAN signals become virtual channels accessible throughout the system:

- **Logic Engine**: Use in conditional logic and virtual functions
- **Lua Scripts**: Access via `getCANSignal("channel_name")`
- **Output Mapping**: Map to output channel duty cycles or current limits
- **Data Logging**: Automatically logged at 500 Hz
- **Web Interface**: Real-time display and monitoring

### 5.8.4 DBC Export Capabilities

#### PMU Data Broadcasting
Automatically generate DBC file for PMU signals:
- All 30 output channel states
- Current consumption per channel
- Temperature per channel
- Input states (20 channels)
- System voltage, temperature
- Accelerometer/gyro data
- Fault codes

#### Example Generated DBC Entry
```dbc
BO_ 1536 PMU_Outputs_1_8: 8 PMU30
 SG_ Output_1_Current : 0|16@1+ (0.01,0) [0|40] "A" ECU
 SG_ Output_2_Current : 16|16@1+ (0.01,0) [0|40] "A" ECU
 SG_ Output_3_Current : 32|16@1+ (0.01,0) [0|40] "A" ECU
 SG_ Output_4_Current : 48|16@1+ (0.01,0) [0|40] "A" ECU

BO_ 1537 PMU_Status: 8 PMU30
 SG_ Battery_Voltage : 0|16@1+ (0.01,0) [0|30] "V" ECU
 SG_ Board_Temp : 16|8@1+ (1,-40) [-40|125] "C" ECU
 SG_ System_State : 24|8@1+ (1,0) [0|255] "" ECU
```

### 5.8.5 Integration Workflows

#### Workflow 1: ECU Integration
1. Import ECU's DBC file
2. Map CAN signals to PMU functions
3. Configure virtual channels based on ECU data
4. Export PMU DBC for logging software

#### Workflow 2: Data Logging
1. Import combined DBC (ECU + dash + sensors)
2. Configure PMU to decode relevant signals
3. Add PMU signals to unified DBC
4. Use in AIM, MoTeC i2, or other analysis software

#### Workflow 3: Testing and Simulation
1. Import DBC file
2. Use CAN bus simulation tools
3. Test PMU logic with simulated signals
4. Validate before vehicle integration

### 5.8.6 Configurator DBC Tools

#### DBC Editor Features
- Visual signal browser
- Signal-to-channel mapping interface
- Drag-and-drop signal assignment
- Conflict detection (duplicate IDs)
- Message scheduling configuration
- Live CAN bus monitoring with decoded signals

#### Import Wizard
1. Select DBC file
2. Preview messages and signals
3. Select signals to use
4. Auto-map to PMU functions
5. Resolve conflicts
6. Generate configuration

#### Export Wizard
1. Select PMU signals to broadcast
2. Configure CAN IDs (auto or manual)
3. Set transmission rates
4. Generate DBC file
5. Export for external tools

### 5.8.7 Technical Implementation

#### DBC Parser
- **Library**: Custom lightweight parser (C)
- **Memory**: Parse on-demand, not all in RAM
- **Storage**: Compressed DBC stored in flash
- **Runtime**: Fast signal lookup (hash table)

#### Signal Decoding
- **Performance**: Hardware-accelerated (DMA)
- **Precision**: 32-bit float conversion
- **Endianness**: Support both little/big endian
- **Error Handling**: Out-of-range clamping, stale data timeout

### 5.8.8 Limitations
- **Max Signals**: 500 signals per DBC file
- **Max Messages**: 200 messages per bus
- **Update Rate**: Configurable (1Hz - 1kHz per message)
- **File Size**: Max 512KB DBC file

---

## 6. Sensors and Monitoring

### 6.1 IMU (Inertial Measurement Unit)

The PMU-30 includes an integrated 6-axis IMU combining 3-axis accelerometer and 3-axis gyroscope for comprehensive motion sensing.

#### 6.1.1 IMU Selection
- **Type**: 6-axis MEMS IMU (accelerometer + gyroscope)
- **Recommended Part**: LSM6DSO32X or ICM-42688-P
- **Interface**: I2C (up to 1MHz) or SPI (up to 10MHz)
- **Package**: LGA-14 (2.5 × 3.0 × 0.83 mm)

#### 6.1.2 Accelerometer Specifications
| Parameter | Value |
|-----------|-------|
| **Axes** | 3 (X, Y, Z) |
| **Range** | ±4g, ±8g, ±16g, ±32g (selectable) |
| **Resolution** | 16-bit |
| **Sample Rate** | Up to 6.6 kHz |
| **Noise Density** | 70 µg/√Hz |
| **Zero-g Offset** | ±20 mg |

#### 6.1.3 Gyroscope Specifications
| Parameter | Value |
|-----------|-------|
| **Axes** | 3 (X, Y, Z) |
| **Range** | ±125, ±250, ±500, ±1000, ±2000 °/s (selectable) |
| **Resolution** | 16-bit |
| **Sample Rate** | Up to 6.6 kHz |
| **Noise Density** | 4 mdps/√Hz |
| **Zero-rate Offset** | ±1 °/s |

#### 6.1.4 IMU Applications
- **G-force data logging**: Record lateral, longitudinal, and vertical acceleration
- **Impact detection**: Trigger alerts and data capture on crash/collision
- **Roll/pitch/yaw**: Calculate vehicle orientation angles
- **Wheel spin detection**: Use gyro data to detect and react to wheelspin
- **Launch control**: G-force based traction control during acceleration
- **Data analysis**: Correlate vehicle dynamics with output states
- **Lap analysis**: Combined with GPS for comprehensive track telemetry

#### 6.1.5 Lua API for IMU
```lua
-- Get accelerometer data (in g-force)
local ax, ay, az = getAccelX(), getAccelY(), getAccelZ()

-- Get gyroscope data (in degrees/second)
local gx, gy, gz = getGyroX(), getGyroY(), getGyroZ()

-- Example: Crash detection
if math.abs(ax) > 3.0 or math.abs(ay) > 3.0 then
    setOutput(30, 1)  -- Activate hazard relay
    logEvent("IMPACT", ax, ay, az)
end
```

### 6.2 Temperature Sensors

#### 6.2.1 Board Temperature
- **Type**: Digital sensor
- **Recommended**: TMP102, LM75, or internal ADC + thermistor
- **Range**: -40°C to +125°C
- **Accuracy**: ±2°C
- **Location**: Near power stage

#### 6.2.2 Per-Channel Temperature
- **Source**: PROFET 2 integrated sensor
- **Method**: Analog voltage output (Kilis pin)
- **Processing**: ADC conversion via multiplexer
- **Update Rate**: 10Hz per channel minimum

### 6.3 Voltage and Current Monitoring

#### 6.3.1 Input Voltage
- **Measurement**: Resistor divider to ADC
- **Range**: 0-20V
- **Resolution**: 0.05V
- **Accuracy**: ±1%

#### 6.3.2 Per-Channel Current
- **Source**: PROFET 2 current sense (IS pin)
- **Ratio**: Kilis ratio (typically 10000:1 or 22700:1)
- **Range**: 0-50A
- **Resolution**: 0.1A
- **Accuracy**: ±5%

---

## 7. Memory and Storage

### 7.1 Data Logging Memory

#### 7.1.1 Flash Memory
- **Type**: Serial NOR Flash (QSPI)
- **Recommended**: Winbond W25Q512JV or Micron MT25Q series
- **Capacity**: 512MB (64MB × 8-bit or 512Mb)
- **Interface**: Quad-SPI
- **Speed**: 133MHz clock, up to 532Mbps
- **Endurance**: 100k erase cycles minimum

#### 7.1.2 File System
- **Type**: FatFS or LittleFS
- **Wear Leveling**: Implemented
- **Format**: Binary log files + index
- **Access**: Via USB/WiFi for download

### 7.2 Configuration Storage

#### 7.2.1 EEPROM/Flash
- **Type**: Internal MCU flash or external EEPROM
- **Capacity**: 256KB minimum for config
- **Format**: Structured binary or JSON
- **Backup**: CRC32 checksums, dual-bank storage

### 7.3 RTC Backup

#### 7.3.1 Battery
- **Type**: CR2032 coin cell or supercap
- **Capacity**: 5-year retention minimum
- **Circuit**: Diode OR with main power

---

## 8. LED Indicators

### 8.1 Per-Channel LEDs (30x)

#### 8.1.1 LED Specification
- **Type**: SMD LED (0805 or 0603)
- **Color**: RGB or dual-color (Red/Green)
- **Driver**: Shift register or PWM multiplexing
- **Brightness**: Software controlled

#### 8.1.2 Status Indication
- **Off**: Channel disabled
- **Green**: Channel active, normal
- **Red**: Channel fault (overcurrent/temp)
- **Amber**: Channel warning
- **Blinking**: PWM active

### 8.2 System Status LEDs

#### 8.2.1 Power LED
- **Color**: Green
- **State**: Solid when powered

#### 8.2.2 Status LED
- **Color**: RGB or tri-color
- **States**:
  - Green: System OK
  - Red: System fault
  - Blue: WiFi/BT active
  - Blinking patterns for boot/update

#### 8.2.3 Communication LEDs
- **CAN1/CAN2**: Yellow (activity)
- **USB**: Blue (connected)
- **WiFi**: Blue (clients connected)

---

## 9. PCB Design Requirements

### 9.1 Board Specifications

#### 9.1.1 Dimensions
- **PCB Size**: 150mm × 120mm
- **Board Thickness**: 2.4mm
- **Enclosure Size**: 156mm × 126mm × 40mm
- **Layers**: 8-layer
- **Material**: FR-4, High-Tg (Tg ≥ 170°C)
- **Copper Weight**:
  - Outer layers (L1, L8): 3oz (105µm)
  - Power planes (L4, L5): 2oz (70µm)
  - Signal layers (L3, L6): 1oz (35µm)
  - Ground planes (L2, L7): 2oz (70µm)

#### 9.1.2 Layer Stack-up (8-layer)
| Layer | Function | Copper | Notes |
|-------|----------|--------|-------|
| L1 | Signal + Power | 105µm | Components, high-current |
| L2 | GND Plane | 70µm | Solid ground reference |
| L3 | Signal | 35µm | USB, QSPI (high-speed) |
| L4 | Power (+12V) | 70µm | Main power distribution |
| L5 | Power (+5V/3.3V) | 70µm | Logic power planes |
| L6 | Signal | 35µm | CAN, I2C, SPI |
| L7 | GND Plane | 70µm | Signal return path |
| L8 | Signal + Power | 105µm | Bottom components |

### 9.2 Thermal Management

#### 9.2.1 Cooling
- **Method**: Forced air or natural convection
- **Heatsinking**:
  - PROFET devices: Thermal vias to ground plane
  - PCB as heatsink: Large copper pours
- **Thermal Interface**: Thermal pads to enclosure (optional)

#### 9.2.2 Thermal Design Goals
- **Junction Temp**: <125°C at full load (40A/channel)
- **Board Temp**: <85°C ambient + self-heating
- **Derating**: 50% at 85°C ambient (20A per channel)

### 9.3 Component Placement

#### 9.3.1 Zones
- **Power Zone**: PROFET devices, input filtering
- **MCU Zone**: STM32, support components
- **Communication**: CAN, USB, WiFi module
- **I/O**: ADC inputs, DAC outputs
- **Memory**: Flash memory, close to MCU

#### 9.3.2 Clearances
- **High-current traces**: 3mm minimum from signals
- **High-voltage**: 5mm minimum clearance
- **CAN differential**: Keep routed together, 100Ω impedance

### 9.4 Connector Placement

#### 9.4.1 Edge Connectors
- **Power Input**: Main edge (large connector)
- **USB-C**: Accessible edge for cable
- **CAN**: Grouped together
- **Outputs**: Grouped by function/rating

#### 9.4.2 Mounting
- **Holes**: M4 or M5 mounting holes
- **Spacing**: 100mm × 100mm grid
- **Grounding**: Star ground to chassis via mounting

---

## 10. Protection and Safety

### 10.1 Input Protection

#### 10.1.1 Overvoltage
- **TVS Diode**: SMAJ18A or equivalent (18V clamp)
- **Fuse**: Recommended external 150A+
- **Reverse Polarity**: P-channel MOSFET or diode bridge

#### 10.1.2 Transient Protection
- **Load Dump**: ISO 7637-2 pulse 5a (up to 150V, 400ms)
- **Suppression**: MOV + TVS cascade

### 10.2 Output Protection

#### 10.2.1 Per PROFET Device
- Integrated overcurrent shutdown
- Thermal shutdown
- Short-circuit protection
- Open-load detection

#### 10.2.2 System Level
- Global current monitoring
- Power limiting (total current budget)
- Emergency shutdown (all channels off)

### 10.3 ESD Protection

#### 10.3.1 Requirements
- **Standard**: IEC 61000-4-2
- **Level**: ±8kV contact, ±15kV air
- **Protection**: TVS diode arrays on all I/O

### 10.4 Conformal Coating
- **Type**: Acrylic or polyurethane
- **Coverage**: Full board except connectors
- **Purpose**: Moisture, vibration, contamination protection

---

## 11. Manufacturing and Testing

### 11.1 Assembly Requirements

#### 11.1.1 SMT Process
- **Solder Paste**: Lead-free (SAC305)
- **Reflow Profile**: Standard 6-zone profile
- **Inspection**: AOI + X-ray for critical components

#### 11.1.2 Through-Hole
- **Connectors**: Wave solder or selective solder
- **Final Inspection**: Manual + functional test

### 11.2 Testing Points

#### 11.2.1 Test Pads
- All power rails
- Critical signals (CAN, USB, SPI)
- MCU programming (SWD)

#### 11.2.2 Functional Test
- Power-on self-test (POST)
- Channel activation test
- Communication test (CAN, USB, WiFi)
- Protection test (overcurrent simulation)

### 11.3 Programming

#### 11.3.1 Bootloader
- **Interface**: USB or UART
- **Protection**: Write-protected sectors
- **Update**: Field-upgradeable

#### 11.3.2 Production Programming
- **Method**: SWD via Tag-Connect or header
- **Firmware**: Factory default firmware
- **Configuration**: Blank (user configurable)

---

## 12. Compliance and Certification

### 12.1 Target Standards
- **Automotive**: ISO 16750 (environmental)
- **EMC**: ISO 7637-2, ISO 11452-2
- **Safety**: ISO 26262 (functional safety) - ASIL-B target

### 12.2 Documentation Requirements
- Schematic diagrams
- BOM with part numbers
- PCB fabrication files (Gerber)
- Assembly drawings
- Test procedures
- Compliance test reports

---

## 13. Design Verification Checklist

### 13.1 Electrical Validation
- [ ] Power supply ripple <50mV on all rails
- [ ] All channels deliver 40A continuous
- [ ] Inrush current 160A for 1ms verified
- [ ] Protection thresholds calibrated
- [ ] Temperature sensing accuracy ±2°C
- [ ] Current sensing accuracy ±5%

### 13.2 Functional Validation
- [ ] All 30 outputs independently controllable
- [ ] PWM frequency 10Hz-30kHz verified
- [ ] Soft-start functionality confirmed
- [ ] CAN FD communication at 5Mbps
- [ ] WiFi AP mode stable
- [ ] USB enumeration successful
- [ ] Data logging write speed >1MB/s

### 13.3 Environmental Testing
- [ ] Temperature cycling -40°C to +85°C
- [ ] Vibration per ISO 16750-3
- [ ] Shock per ISO 16750-3
- [ ] EMC emissions pass
- [ ] EMC immunity pass
- [ ] IP65 rating verified

---

## 14. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-21 | PMU-30 Team | Initial specification |
| 1.1 | 2025-12-29 | PMU-30 Team | Updated to Implementation Phase, verified against firmware |
| 1.2 | 2025-12-29 | PMU-30 Team | Updated PCB specs (150×120mm, 8-layer), added GPS/GNSS module (5.5), LIN bus (5.6), Superseal connectors |

---

**End of Technical Specification**
