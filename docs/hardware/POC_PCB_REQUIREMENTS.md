# PMU-30 POC (Proof of Concept) PCB Requirements

| Field | Value |
|-------|-------|
| **Document Title** | PMU-30 POC Minimal PCB Requirements |
| **Version** | 1.0 |
| **Date** | 2025-12-29 |
| **Project** | PMU-30 POC (10-Channel Power Management Unit) |
| **Company** | R2 m-sport |

---

## 1. Overview

Minimal Proof of Concept board for PMU-30 development and testing. Scaled-down version with core functionality for validation before full production.

### 1.1 POC vs Full PMU-30 Comparison

| Feature | POC | Full PMU-30 |
|---------|-----|-------------|
| Power Outputs | 10x 30A | 30x 40A |
| H-Bridge Outputs | 2x | 4x |
| Analog Inputs | 5x | 20x |
| Digital Inputs | 5x | 20x |
| CAN Bus | 2x CAN 2.0B | 2x CAN FD + 2x CAN 2.0B |
| GPS/GNSS | No | Yes |
| Total Current | 300A | 1200A |

---

## 2. Core Requirements

### 2.1 Power Output Channels (10x)

| Parameter | Specification |
|-----------|---------------|
| **Channels** | 10 |
| **Current per Channel** | 30A continuous |
| **Peak Current** | 120A for 1ms (inrush) |
| **IC** | BTS7008-2EPA or BTS7006-2EPA |
| **ICs Required** | 5 (2 channels per IC) |
| **PWM Frequency** | 10Hz - 30kHz |
| **PWM Resolution** | 12-bit |
| **Protection** | Over-temp, overcurrent, short circuit |
| **Current Sense** | Analog output per channel |

### 2.2 H-Bridge Outputs (2x)

| Parameter | Specification |
|-----------|---------------|
| **Bridges** | 2 |
| **Current per Bridge** | 30A continuous |
| **Peak Current** | 55A |
| **IC** | BTN8982TA |
| **ICs Required** | 4 (2 half-bridges per motor) |
| **PWM Frequency** | 10Hz - 20kHz |
| **Modes** | Forward, Reverse, Brake, Coast |

### 2.3 Analog Inputs (5x)

| Parameter | Specification |
|-----------|---------------|
| **Channels** | 5 |
| **Voltage Range** | 0-5V |
| **Resolution** | 12-bit ADC |
| **Sample Rate** | 1kHz per channel |
| **Protection** | 36V overvoltage, -2V reverse |
| **Pull Options** | 10k up/down, 100k up/down, none |

### 2.4 Digital Inputs (5x)

| Parameter | Specification |
|-----------|---------------|
| **Channels** | 5 |
| **Voltage Range** | 0-5V |
| **Logic Threshold** | 2.5V configurable |
| **Sample Rate** | 500Hz |
| **Debounce** | 1-1000ms configurable |
| **Protection** | 36V overvoltage, -2V reverse |
| **Modes** | Switch high/low, frequency, rotary |

---

## 3. Microcontroller

### 3.1 Main MCU

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | STM32H743VIT6 |
| **Core** | ARM Cortex-M7 @ 480MHz |
| **Internal Flash** | 2MB |
| **RAM** | 1MB |
| **Package** | LQFP-100 |

### 3.2 External Flash

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | W25Q512JVEIQ |
| **Capacity** | 512 Mbit (64MB) |
| **Interface** | Quad SPI |
| **Speed** | 133MHz |

---

## 4. Communication Interfaces

### 4.1 CAN Bus (2x CAN 2.0B)

| Parameter | Specification |
|-----------|---------------|
| **Buses** | 2 (CAN1, CAN2) |
| **Standard** | CAN 2.0B (NO CAN FD) |
| **Baud Rate** | 125, 250, 500, 1000 kbps |
| **Transceiver** | TJA1051T/3 or MCP2562 |
| **Termination** | 120Ω switchable per bus |
| **Protection** | +/-40V bus fault tolerance |

### 4.2 LIN Bus (1x) - REQUIRED

| Parameter | Specification |
|-----------|---------------|
| **Buses** | 1 |
| **Standard** | LIN 2.2 / SAE J2602 |
| **Baud Rate** | 9600 - 20000 bps |
| **Transceiver** | TJA1021 or similar |
| **Mode** | Master + Slave |

### 4.3 USB-C

| Parameter | Specification |
|-----------|---------------|
| **Standard** | USB 2.0 High-Speed |
| **Speed** | 480 Mbps |
| **Connector** | USB-C receptacle |
| **Protection** | ESD, overcurrent |
| **Functions** | Configuration, firmware update, data |

### 4.4 WiFi/Bluetooth

| Parameter | Specification |
|-----------|---------------|
| **Module** | ESP32-C3-MINI-1 or ESP32-C6 |
| **WiFi** | 802.11 b/g/n, AP mode |
| **Bluetooth** | BLE 5.0 |
| **Interface** | SPI or UART to main MCU |
| **Antenna** | PCB antenna or U.FL |

---

## 5. Sensors - REQUIRED

### 5.1 IMU (Accelerometer/Gyroscope)

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | LSM6DSO32X |
| **Type** | 6-axis MEMS IMU |
| **Accelerometer** | ±4/8/16/32g selectable |
| **Gyroscope** | ±125 to ±2000 °/s |
| **Resolution** | 16-bit |
| **Sample Rate** | Up to 6.6kHz |
| **Interface** | SPI or I2C |

---

## 6. Power Supply

### 6.1 Input Power

| Parameter | Specification |
|-----------|---------------|
| **Nominal Voltage** | 12V |
| **Operating Range** | 6-22V DC |
| **Max Current** | 300A (10 channels × 30A) |
| **Connector** | M6 or M8 stud terminals |

### 6.2 DC-DC Converters

| Rail | Specification |
|------|---------------|
| **5V Rail** | 3A minimum, buck converter |
| **3.3V Rail** | 2A minimum, LDO or buck |
| **Sensor 5V** | 500mA, protected output |

### 6.3 Reverse Polarity Protection - REQUIRED

| Parameter | Specification |
|-----------|---------------|
| **Type** | P-channel MOSFET or ideal diode |
| **IC** | AUIRF3805S-7P or similar |
| **Voltage** | -16V minimum |
| **Current** | Full load current |

---

## 7. Protection (Same as Full Module)

### 7.1 Input Protection

| Component | Specification |
|-----------|---------------|
| **TVS Diodes** | SMDJ26CA (parallel for capacity) |
| **Reverse Polarity** | P-FET based |
| **Inrush Limiting** | Soft-start circuit |

### 7.2 Output Protection

| Protection | Method |
|------------|--------|
| **Overcurrent** | PROFET built-in + software |
| **Short Circuit** | Hardware shutdown <1µs |
| **Overtemperature** | Per-channel monitoring |
| **Open Load** | Detection at <1A |

### 7.3 Input Protection (Analog/Digital)

| Component | Value |
|-----------|-------|
| **TVS Diode** | PESD5V0S1BL (5.1V) |
| **Series Resistor** | 10kΩ |
| **Filter Capacitor** | 100nF |

---

## 8. LED Indicators - REQUIRED

| LED | Color | Function |
|-----|-------|----------|
| **Power** | Green | Power on indicator |
| **Status** | Blue | MCU heartbeat |
| **Error** | Red | Fault indicator |
| **CAN1** | Yellow | CAN1 activity |
| **CAN2** | Yellow | CAN2 activity |
| **WiFi** | Blue | WiFi connected |
| **Output 1-10** | Green/Red | Output status (optional) |

---

## 9. Connectors

### 9.1 Suggested Connector Layout

| Connector | Type | Pins | Function |
|-----------|------|------|----------|
| Main A | Superseal 1.0 | 18-pin | Outputs 1-10, H-Bridge |
| Main B | Superseal 1.0 | 14-pin | Inputs, CAN, LIN |
| Power + | M6/M8 stud | 1 | Battery positive |
| Power - | M6/M8 stud | 1 | Ground |
| USB | USB-C | - | Configuration |

### 9.2 Main A Pinout (18-pin)

| Pin | Function | Pin | Function |
|-----|----------|-----|----------|
| 1-5 | Outputs 1-5 | 10-14 | Outputs 6-10 |
| 6-7 | H-Bridge 1 (A/B) | 15-16 | H-Bridge 2 (A/B) |
| 8-9 | Ground | 17-18 | Sense return |

### 9.3 Main B Pinout (14-pin)

| Pin | Function | Pin | Function |
|-----|----------|-----|----------|
| 1-5 | Analog Inputs 1-5 | 8-12 | Digital Inputs 1-5 |
| 6 | CAN1 H | 13 | CAN2 H |
| 7 | CAN1 L | 14 | CAN2 L |
| - | - | - | LIN on Main A or separate |

---

## 10. PCB Specifications

### 10.1 Dimensions (Target)

| Parameter | Value |
|-----------|-------|
| **Length** | 100mm |
| **Width** | 80mm |
| **Layers** | 4-6 |
| **Thickness** | 1.6-2.0mm |

### 10.2 Layer Stack (4-layer)

| Layer | Function |
|-------|----------|
| L1 | Signal + Power |
| L2 | Ground plane |
| L3 | Power plane |
| L4 | Signal + Power |

### 10.3 Copper Weight

| Layer | Weight |
|-------|--------|
| **Outer layers** | 2oz (70µm) |
| **Inner layers** | 1oz (35µm) |
| **Power traces** | 3oz if needed |

---

## 11. BOM Summary

| Category | Components | Qty |
|----------|------------|-----|
| MCU | STM32H743VIT6 | 1 |
| PROFET | BTS7008-2EPA | 5 |
| H-Bridge | BTN8982TA | 4 |
| CAN Transceiver | TJA1051T/3 | 2 |
| LIN Transceiver | TJA1021 | 1 |
| WiFi/BT | ESP32-C3-MINI-1 | 1 |
| Flash | W25Q512JVEIQ | 1 |
| IMU | LSM6DSO32X | 1 |
| USB-C | USB4110-GF-A | 1 |
| Power MOSFETs | Various | ~10 |
| LEDs | Various | 10-20 |
| Connectors | Superseal | 2-3 |

---

## 12. NOT Included in POC

- GPS/GNSS module
- CAN FD support (CAN 2.0B only)
- Extended I/O (only 5+5 inputs)
- Full 30-channel outputs
- Radlock 200A connector (use smaller studs)

---

## 13. Development Priority

### Phase 1: Core Functionality
1. Power outputs (10x 30A)
2. MCU + Flash
3. USB-C interface
4. Basic power supply

### Phase 2: Communication
1. CAN1 + CAN2
2. LIN bus
3. WiFi/Bluetooth

### Phase 3: I/O + Sensors
1. Analog inputs (5x)
2. Digital inputs (5x)
3. H-Bridge outputs (2x)
4. IMU

### Phase 4: Protection + Polish
1. All protection circuits
2. LED indicators
3. Final testing

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-29 | Initial POC requirements |

---

**END OF DOCUMENT**

*R2 m-sport - Proprietary Information*
