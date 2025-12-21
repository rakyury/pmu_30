# Reference PDM Analysis

**Owner:** R2 m-sport
**Document Version:** 1.0
**Date:** 2025-12-21
**Confidentiality:** Proprietary - Internal Use Only

---

**© 2025 R2 m-sport. All rights reserved.**

---

Analysis of leading PDM systems to inform PMU-30 design decisions.

## Reference Products

### 1. ECUMaster PMU24 DL (Data Logger)

#### Hardware Specifications
- **Outputs**: 24 channels
- **Current Rating**: Up to 25A per channel (varies by channel group)
- **Input Voltage**: 9-16V nominal
- **Microcontroller**: High-performance 32-bit ARM
- **Connectivity**:
  - 2x CAN bus
  - WiFi module
  - USB
- **Inputs**:
  - 16x analog/digital configurable inputs
  - Internal accelerometer
  - GPS receiver
- **Data Logging**: Internal memory for high-speed logging
- **Temperature Monitoring**: Board and output stage monitoring

#### Software Features
- **Virtual Channels**: Mathematical channels derived from inputs
- **Logic Functions**: Configurable logic with timers, delays
- **PWM Outputs**: Configurable frequency and duty cycle
- **Soft Start**: Configurable ramp-up times
- **Protection**:
  - Overcurrent with adjustable limits
  - Overtemperature
  - Short circuit detection
  - Low voltage cutoff
- **CAN Support**:
  - Custom CAN messages
  - Popular ECU protocols
  - CAN keypads
- **PC Software**: PMU Manager - Windows-based configuration tool

#### Key Features
- Drag-and-drop logic builder
- Real-time monitoring
- Advanced math functions
- Lua scripting support
- Data analysis tools
- Cloud connectivity

---

### 2. MaxxECU PDM

#### Hardware Specifications
- **Outputs**: 16 channels (standard model)
- **Current Rating**: Up to 30A per channel
- **Input Voltage**: 8-18V
- **Microcontroller**: ARM Cortex-M series
- **Connectivity**:
  - 2x CAN bus
  - USB
- **Inputs**: Multiple analog/digital inputs
- **Integration**: Tight integration with MaxxECU engine management

#### Software Features
- **Virtual Outputs**: Logic-based output control
- **Math Channels**: Custom calculations
- **PWM Control**: Full PWM capability
- **Protection Systems**:
  - Current limiting
  - Thermal protection
  - Diagnostics
- **CAN Functions**:
  - CAN-based inputs
  - Broadcast output states
  - Keypad support
- **PC Software**: MaxxECU tuning suite integration

#### Key Features
- Seamless ECU integration
- Table-based control
- Launch control integration
- Traction control outputs
- Shift light control

---

### 3. MoTec PDM32

#### Hardware Specifications
- **Outputs**: 32 channels
- **Current Rating**: 0-30A per channel (configurable)
- **Input Voltage**: 9-16V nominal, 6-18V operating
- **Microcontroller**: High-performance processor
- **Connectivity**:
  - 2x CAN bus
  - Ethernet
  - USB
- **Inputs**:
  - 32x general purpose inputs (analog/digital/frequency)
  - Internal sensors
- **Display**: Optional integrated display
- **Expansion**: Modular expansion capability

#### Software Features
- **Channels System**: Comprehensive channel mathematics
- **Logic System**:
  - Complex boolean logic
  - State machines
  - PID controllers
- **PWM**: Advanced PWM with synchronization
- **Protection**:
  - Programmable current limits
  - Temperature monitoring
  - Voltage monitoring
  - Diagnostic trouble codes (DTCs)
- **CAN**:
  - Full CAN configuration
  - Multiple protocols
  - Device integration
- **PC Software**: MoTeC i2 Pro - professional data analysis

#### Key Features
- Professional motorsport grade
- Advanced telemetry
- Pit lane speed limiter
- Engine mapping integration
- Comprehensive logging
- Custom channel math

---

## Feature Comparison Matrix

| Feature | ECUMaster PMU24 DL | Link PDM Razor | AIM PDM | MoTec PDM32 | RaceCapture | **PMU-30** |
|---------|-------------------|----------------|---------|-------------|-------------|------------|
| **Hardware** |
| Output Channels | 24 | 16 | 8-16 | 32 | 4-8 | **30** |
| Max Current/Channel | 25A | 40A | 30A | 30A | 10A | **40A (160A inrush)** |
| H-Bridge Outputs | No | No | No | No | No | **4x Dual (30A each)** |
| Input Channels | 16 | 8 | Varies | 32 | 8+ | **20 ADC (10-bit, protected)** |
| Input Protection | Yes | Yes | Yes | Yes | Basic | **Overvoltage protected, pullup/down** |
| CAN Interfaces | 2 (CAN) | 1 | 1-2 | 2 | 1 | **2x CAN FD + 2x CAN 2.0** |
| LIN Bus | No | No | No | No | No | **Yes (1x)** |
| WiFi | Yes | No | Optional | No | Yes | **Yes (AP mode)** |
| Bluetooth | No | No | No | No | Yes | **Yes** |
| USB | Yes | Yes | Yes | Yes | Yes | **Yes (USB-C)** |
| Accelerometer | 3-axis | No | 3-axis | Optional | 3-axis | **Yes (3-axis + 3-axis gyro)** |
| Gyroscope | No | No | No | No | No | **Yes (3-axis)** |
| GPS | Yes | No | Optional | Optional | Yes | **Optional** |
| Data Logging | Internal | Via ECU | Via AIM | Internal | SD Card | **512MB internal, 500Hz** |
| RTC | Yes | Yes | Yes | Yes | Yes | **Yes** |
| Sensor Power Out | No | No | Yes | Yes | Yes | **5V, 500mA monitored** |
| Operating Voltage | 9-16V | 8-18V | 9-16V | 9-16V | 9-16V | **6-22V (ISO 7637)** |
| Temp Range | -40 to +85°C | -40 to +85°C | -40 to +85°C | -40 to +85°C | -40 to +85°C | **-40 to +125°C (AEC-Q100 Grade 1)** |
| **Output Features** |
| PWM Control | Yes | Yes | Yes | Yes | No | **Yes** |
| Wiper Output | No | Yes (park/brake) | No | No | No | **Yes (park/brake)** |
| Blinker Function | No | Yes | No | No | No | **Yes (built-in logic)** |
| Soft Start | Yes | Yes | Yes | Yes | No | **Yes** |
| H-Bridge Control | No | No | No | No | No | **Yes (4x dual)** |
| Current Monitoring | Per channel | Per channel | Per channel | Per channel | No | **Per channel** |
| Temperature Monitoring | Groups | Yes | Per channel | Per channel | Board | **Per channel** |
| **Protection** |
| Overcurrent | Yes | Yes | Yes | Yes | Basic | **Yes** |
| Overtemperature | Yes | Yes | Yes | Yes | Yes | **Yes (board + channels)** |
| Short Circuit | Yes | Yes | Yes | Yes | Basic | **Yes** |
| Overvoltage | Yes | Yes | Yes | Yes | Basic | **Yes (6-22V range)** |
| Reverse Polarity | Yes | Yes | Yes | Yes | Basic | **Yes (internal)** |
| Open Load Detection | Yes | Yes | Yes | Yes | No | **Yes** |
| **Logic System** |
| Virtual Channels | Yes | Yes | Yes | Yes | Yes | **Yes (100 functions)** |
| Virtual Switches | Yes | Yes | Yes | Yes | Yes | **Yes** |
| Logic Operations | AND/OR/NOT | AND/OR/NOT | Full Boolean | Full Boolean | Full Boolean | **isTrue, isFalse, =, !=, <, <=, >, >=, AND, OR, XOR** |
| Special Logic | Timers | Timers | State machines | State machines | Timers | **Flash, Pulse, Toggle, Set/Reset Latch** |
| Number of Functions | ~50 | ~30 | ~50 | Unlimited | ~50 | **100** |
| Number of Operations | ~100 | ~50 | ~200 | Unlimited | ~100 | **250** |
| Update Frequency | 100Hz | 100Hz | 200Hz | 1000Hz | 50Hz | **500Hz** |
| Look-up Tables | Yes | Yes | Yes | Yes | Yes | **Yes** |
| Math Functions | Advanced | Basic | Advanced | Advanced | Advanced | **Advanced** |
| PID Controllers | Limited | No | Limited | Yes | Basic | **Yes** |
| Scripting | Lua | No | No | No | Lua (limited) | **Lua 5.4 (full support)** |
| **CAN Features** |
| CAN Keypads | Yes | Yes | Yes | Yes | No | **Yes (Blinkmarine)** |
| Custom Messages | Yes | Yes | Yes | Yes | Yes | **Yes** |
| ECU Integration | Multi-brand | Link ECU | AIM | MoTec | Generic | **Generic** |
| CAN FD | No | No | No | Limited | No | **Yes (2x)** |
| CAN 2.0 | 2x | 1x | 1-2x | 2x | 1x | **Yes (2x)** |
| CAN Data Broadcast | Yes | Yes | Yes | Yes | Yes | **Yes (all PMU data)** |
| DBC/CANX Support | Limited | No | Limited | Yes | Yes | **Yes (import/export)** |
| **Configuration** |
| PC Software | PMU Manager | Link Suite | AIM Race Studio | i2 Pro | RaceCapture | **Python+Qt (cross-platform)** |
| Platform | Windows | Windows | Windows | Windows | All | **Windows/Linux/macOS** |
| Web Interface | View-only | No | No | No | Yes | **Full monitoring** |
| Mobile App | Limited | No | Yes | Optional | Yes | **Via web interface** |
| OTA Updates | No | No | No | No | Yes | **Yes** |
| Open Source | No | No | No | No | Yes | **Firmware: No, Configurator: Potential** |
| **Diagnostics** |
| LED Indicators | System | System | Per channel | Per channel | System | **30x bicolor (per channel)** |
| Fault Codes | Yes | Yes | Yes | Yes | Yes | **Yes** |
| Real-time Monitoring | Yes | Yes | Yes | Yes | Yes | **Yes (WiFi/USB)** |
| Data Export | Yes | Yes | Yes | Yes | CSV/JSON | **Yes** |
| **Price Tier** | ~$1200 | ~$800 | ~$1500 | ~$2500+ | ~$600 | **TBD** |

---

### 4. ECUMaster Dual H-Bridge

#### Hardware Specifications
- **Outputs**: 2x Dual H-Bridge
- **Current Rating**: 30A per bridge (60A total per dual unit)
- **Input Voltage**: 9-16V nominal
- **PWM Frequency**: Up to 20kHz
- **Applications**: Motors, actuators, variable speed fans

#### Software Features
- **Bidirectional Control**: Forward/reverse/brake
- **Current Limiting**: Software-configurable per bridge
- **Brake Mode**: Active braking (short both sides)
- **Diagnostic**: Current and temperature monitoring

#### Key Features
- Integrated current sensing
- Thermal protection
- CAN integration with PMU
- Compact form factor

---

### 5. AIM PDM (SmartyCam PDM)

#### Hardware Specifications
- **Outputs**: 8-16 channels (model dependent)
- **Current Rating**: Up to 30A per channel
- **Input Voltage**: 9-16V
- **Integration**: Tight integration with AIM data systems
- **Connectivity**: CAN bus, RS232

#### Software Features
- **Race Dash Integration**: Seamless with AIM MXL/MXG/MXS
- **Data Logging**: Integrated with AIM Race Studio
- **Math Channels**: Advanced calculations
- **Predictive Lap Timing**: Based on power usage

#### Key Features
- Video integration (SmartyCam)
- Professional motorsport focus
- Extensive sensor support
- Advanced telemetry

---

### 6. Link ECU PDM Razor

#### Hardware Specifications
- **Outputs**: 16 channels
- **Current Rating**: Up to 40A per channel
- **Input Voltage**: 8-18V
- **Inputs**: 8x analog/digital inputs
- **Connectivity**: CAN bus

#### Software Features
- **Link ECU Integration**: Direct integration with Link ECUs
- **Wiper Control**: Dedicated wiper output with park/brake
- **Blinker Logic**: Integrated turn signal logic
- **Launch Control**: Integration with ECU launch/traction

#### Key Features
- Compact design
- Plug-and-play with Link ECUs
- Cost-effective
- Reliable performance

---

### 7. RaceCapture from Autosport Labs

#### Hardware Specifications
- **Type**: Data logger with integrated outputs
- **Outputs**: 4-8 channels (limited vs dedicated PDM)
- **Inputs**: Multiple analog/digital/GPS/IMU
- **Data Logging**: SD card based
- **Connectivity**: WiFi, Bluetooth, CAN

#### Software Features
- **Open Source**: Firmware and software are open source
- **Telemetry**: Real-time wireless telemetry
- **Track Detection**: GPS-based automatic track detection
- **Predictive Timing**: Predictive lap times
- **Mobile Apps**: iOS/Android apps

#### Key Features
- Open source ecosystem
- Strong community support
- Excellent data visualization
- Track mapping
- WiFi/cellular telemetry
- Cost-effective

---

## Key Insights for PMU-30 Design

### What to Adopt

1. **Higher Current Rating**: 40A continuous per channel exceeds all references
2. **CAN FD Support**: Modern protocol, future-proof
3. **Per-Channel Temperature**: MoTec level monitoring
4. **Cross-Platform Software**: Better than Windows-only competitors
5. **Modern Connectivity**: WiFi AP + Bluetooth + USB-C
6. **OTA Updates**: Unique feature in this class
7. **Comprehensive LED Feedback**: Per-channel + system status

### What to Improve

1. **Configuration Complexity**: Simplify UI/UX vs MoTec's complexity
2. **Learning Curve**: Better documentation and examples
3. **Integration**: Make generic protocol support easier than brand-specific

### Competitive Advantages

1. **40A outputs** - highest in class for compact PDM
2. **CAN FD** - future-proof communication
3. **Cross-platform configurator** - Mac/Linux support
4. **OTA updates** - field upgrades without physical access
5. **Integrated web interface** - no PC needed for monitoring
6. **Modern USB-C** - universal connector

### Feature Priorities

#### Must Have (Match Industry Standard)
- Virtual channels and switches
- Boolean logic operations
- Look-up tables
- PWM with soft-start
- Comprehensive protection
- CAN keypad support
- Data logging

#### Should Have (Competitive Parity)
- PID controllers
- Advanced math functions
- Real-time monitoring
- Diagnostic codes

#### Nice to Have (Differentiators)
- OTA updates
- Web-based monitoring
- Cross-platform software
- Bluetooth connectivity

---

## Technical Implementation Recommendations

### Hardware
- Use **STM32H743** or **H753** (dual-core H747 if needed)
- **PROFET 2 BTS7008-2EPA** (40A) or similar for outputs
- **W25Q512JV** or similar for 512MB flash
- **ESP32-C3** for WiFi/BT (separate MCU)
- **LIS3DH** or **LSM6DS3** for accelerometer
- **MCP2518FD** for CAN FD transceivers

### Firmware Architecture
- **RTOS**: FreeRTOS for task management
- **HAL**: STM32 CubeMX/HAL for peripherals
- **File System**: FatFS for log storage
- **Network**: LwIP for WiFi web server
- **CAN**: Custom CANopen-like protocol

### Software Stack
- **Language**: C (firmware), Python 3.10+ (configurator)
- **GUI Framework**: PyQt6 or PySide6
- **Communication**: Serial over USB, WiFi HTTP/WebSocket
- **Data Format**: JSON for configuration, binary for logs

---

## References

- ECUMaster PMU24 DL: https://www.ecumaster.com/products/pmu-16/
- MaxxECU PDM: https://www.maxxecu.com/
- MoTec PDM32: https://www.motec.com.au/
- PROFET 2 Family: Infineon Technologies
- STM32H7 Series: STMicroelectronics

---

*Document Version: 1.0*
*Last Updated: 2025-12-21*
