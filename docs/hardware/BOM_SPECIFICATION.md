# PMU-30 Bill of Materials (BOM) Specification

**Document Version:** 1.0
**Date:** 2025-12-29
**Status:** Implementation Phase
**Owner:** R2 m-sport

---

## 1. Document Overview

This document provides the complete Bill of Materials for the PMU-30 Power Management Unit, including primary components, alternatives, and sourcing information.

---

## 2. Summary

| Category | Component Count | Estimated Cost |
|----------|-----------------|----------------|
| Microcontroller & Memory | 3 | - |
| Power Switches (PROFET) | 15 | - |
| H-Bridge Drivers | 4 | - |
| Power Supply ICs | 4 | - |
| Communication ICs | 8 | - |
| Sensors & Modules | 3 | - |
| Connectors | 6 | - |
| Passives | ~500 | - |
| **Total Unique Parts** | ~545 | - |

### 2.1 I/O Summary

| I/O Type | Count | Notes |
|----------|-------|-------|
| Power Outputs | 30 | 40A continuous each |
| H-Bridge Outputs | 4 | 30A continuous each |
| Analog Inputs | 20 | 0-5V, 12-bit ADC |
| Digital Inputs | 20 | Switch, frequency modes |
| CAN Bus | 4 | 2x CAN FD, 2x CAN 2.0 |
| LIN Bus | 1 | - |
| USB | 1 | USB-C |

---

## 3. Microcontroller & Processing

### 3.1 Main MCU

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | STM32H743VIT6 |
| **Manufacturer** | STMicroelectronics |
| **Package** | LQFP100 (14x14mm, 0.5mm pitch) |
| **Core** | ARM Cortex-M7 @ 480 MHz |
| **Flash** | 2 MB |
| **RAM** | 1 MB |
| **ADC** | 3x 16-bit, 3.6 MSPS |
| **CAN** | 2x CAN FD (FDCAN) |
| **Qty** | 1 |

**Alternatives:**
| Part Number | Notes |
|-------------|-------|
| STM32H753VIT6 | With crypto engine |
| STM32H745ZIT6 | Dual-core variant |

### 3.2 WiFi/Bluetooth Module

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | ESP32-C3-MINI-1-N4 |
| **Manufacturer** | Espressif |
| **WiFi** | 802.11 b/g/n (2.4 GHz) |
| **Bluetooth** | BLE 5.0 |
| **Flash** | 4 MB |
| **Certification** | FCC, CE, IC |
| **Qty** | 1 |

**Alternatives:**
| Part Number | Notes |
|-------------|-------|
| ESP32-C6-MINI-1 | WiFi 6 + Thread/Zigbee |
| ESP32-S3-MINI-1 | Dual-core, AI acceleration |

### 3.3 External Flash

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | W25Q512JVEIQ |
| **Manufacturer** | Winbond |
| **Capacity** | 512 Mbit (64 MB) |
| **Interface** | Quad SPI, 133 MHz |
| **Package** | WSON-8 (8x6mm) |
| **Qty** | 1 |

**Alternatives:**
| Part Number | Notes |
|-------------|-------|
| IS25LP512MG | ISSI equivalent |
| MX25L51245G | Macronix equivalent |

---

## 4. Power Output Stages

### 4.1 High-Side Switches (PROFET)

#### 4.1.1 40A Power Outputs (Outputs 1-30)

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | BTS7012-2EPA |
| **Manufacturer** | Infineon |
| **Package** | PG-TSDSO-24 |
| **Channels** | 2 per IC |
| **Current per Channel** | 40A continuous |
| **Peak Current** | 160A for 1ms (inrush) |
| **Rds(on)** | 3.5 mΩ typical |
| **Current Sense** | Analog output (kILIS = 14500) |
| **Protection** | Over-temp, overcurrent, short circuit |
| **Qty** | 15 (for 30 channels) |

**Note:** All 30 output channels rated for 40A continuous (1200A total capacity)

**Alternatives:**
| Part Number | Current | Notes |
|-------------|---------|-------|
| VNQ7050AJ | 50A | ST Micro, higher headroom |
| VNQ7040AJ | 40A | ST Micro alternative |
| BTS7008-2EPA | 40A peak | Lower duty cycle applications |

### 4.2 H-Bridge Motor Drivers

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | BTN8982TA |
| **Manufacturer** | Infineon |
| **Package** | PG-TO263-7 (D2PAK-7) |
| **Continuous Current** | 30A |
| **Peak Current** | 55A |
| **Rds(on)** | 13 mΩ |
| **PWM Frequency** | Up to 25 kHz |
| **Protection** | Over-temp, overcurrent |
| **Qty** | 8 (4 full bridges) |

**Alternatives:**
| Part Number | Current | Notes |
|-------------|---------|-------|
| VNH5019A-E | 30A | ST Micro |
| BTS7960B | 43A | Half-bridge |

---

## 5. Power Supply

### 5.1 DC-DC Converters

| Function | Part Number | Manufacturer | Specification | Qty |
|----------|-------------|--------------|---------------|-----|
| 5V Main | LM5146RGYR | Texas Instruments | 6-42V in, 5V/5A out | 1 |
| 3.3V Logic | TPS62912RPHR | Texas Instruments | 5V in, 3.3V/1A out | 1 |
| 3.3V Analog | TPS7A2033PDQNR | Texas Instruments | 5V in, 3.3V/300mA, low noise | 1 |

**Alternatives:**
| Function | Part Number | Notes |
|----------|-------------|-------|
| 5V Main | LMR36015 | Higher efficiency |
| 5V Main | TPS54560 | Wide VIN |

### 5.2 Reverse Polarity Protection

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | AUIRF3805S-7P |
| **Manufacturer** | Infineon |
| **Package** | D2PAK-7 |
| **Vds** | 55V |
| **Rds(on)** | 3.3 mΩ |
| **Id** | 210A |
| **Qty** | 1 |

### 5.3 TVS Diodes (Power Input)

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | SMDJ26CA |
| **Manufacturer** | Littelfuse |
| **Standoff Voltage** | 26V |
| **Clamping Voltage** | 42.1V @ 53A |
| **Peak Power** | 3,000W |
| **Qty** | 4 (parallel) |

---

## 6. Communication Interfaces

### 6.1 CAN Transceivers

| Interface | Part Number | Manufacturer | Package | Qty |
|-----------|-------------|--------------|---------|-----|
| CAN FD 1 | TJA1463ATK/0Z | NXP | HVSON8 | 1 |
| CAN FD 2 | TJA1463ATK/0Z | NXP | HVSON8 | 1 |
| CAN 2.0B 3 | TJA1051T/3 | NXP | SO8 | 1 |
| CAN 2.0B 4 | TJA1051T/3 | NXP | SO8 | 1 |

**CAN FD Specifications (TJA1463):**
- Arbitration rate: 125 kbps to 1 Mbps
- Data rate: Up to 5 Mbps
- ESD protection: +/-15 kV HBM
- Bus fault: -58V to +58V

**CAN 2.0B Specifications (TJA1051T/3):**
- Baud rate: 125 kbps to 1 Mbps
- ESD protection: +/-8 kV HBM
- Bus fault: -27V to +40V

**Alternatives:**
| Part Number | Type | Notes |
|-------------|------|-------|
| MCP2562FD | CAN FD | Microchip |
| TCAN1042V | CAN FD | TI |
| SN65HVD230 | CAN 2.0 | TI |

### 6.2 LIN Transceiver

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | TJA1021T/20 |
| **Manufacturer** | NXP |
| **Package** | SO8 |
| **Standard** | LIN 2.2A |
| **Baud Rate** | Up to 20 kbps |
| **Mode** | Master/Slave selectable |
| **Protection** | Short circuit, overvoltage |
| **Wake-up** | LIN bus wake-up capable |
| **Qty** | 1 |

**Alternatives:**
| Part Number | Notes |
|-------------|-------|
| TJA1020 | Previous generation |
| TLIN2021-Q1 | TI, automotive grade |
| MCP2003B | Microchip |

### 6.3 USB Interface

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | USBLC6-2SC6 |
| **Manufacturer** | STMicroelectronics |
| **Function** | USB 2.0 ESD protection |
| **Package** | SOT-23-6 |
| **Qty** | 1 |

### 6.4 CAN Bus ESD Protection

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | PESD1CAN |
| **Manufacturer** | Nexperia |
| **Function** | CAN bus TVS |
| **ESD Protection** | +/-30 kV |
| **Qty** | 4 (one per bus) |

---

## 7. Sensors & Modules

### 7.1 IMU (Inertial Measurement Unit)

6-axis MEMS IMU for motion sensing, crash detection, and vehicle dynamics analysis.

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | LSM6DSO32X |
| **Manufacturer** | STMicroelectronics |
| **Package** | LGA-14 (2.5x3.0mm) |
| **Accelerometer** | ±4/8/16/32g selectable, 16-bit |
| **Gyroscope** | ±125/250/500/1000/2000 °/s, 16-bit |
| **Sample Rate** | Up to 6.6 kHz |
| **Interface** | I2C (1MHz) / SPI (10MHz) |
| **Qty** | 1 |

**Applications:**
- G-force data logging (lateral, longitudinal, vertical)
- Crash/impact detection and alert
- Roll/pitch/yaw calculation
- Wheel spin detection for traction control
- Combined with GPS for lap analysis

**Alternatives:**
| Part Number | Notes |
|-------------|-------|
| ICM-42688-P | TDK InvenSense, high performance |
| BMI088 | Bosch Sensortec, ±24g accel |
| LSM6DS3TR-C | Lower cost option |

### 7.2 GPS/GNSS Module

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | MAX-M10S |
| **Manufacturer** | u-blox |
| **Package** | LCC-24 (9.7x10.1mm) |
| **Constellation** | GPS, GLONASS, Galileo, BeiDou |
| **Position Accuracy** | 1.5m CEP |
| **Update Rate** | Up to 25 Hz |
| **Time to First Fix** | <1s hot, <26s cold |
| **Interface** | UART (115200 baud) |
| **Protocol** | NMEA 0183, UBX binary |
| **Power** | 3.3V, 25mA typical |
| **Qty** | 1 |

**Alternatives:**
| Part Number | Notes |
|-------------|-------|
| NEO-M9N | Higher performance |
| SAM-M10Q | With integrated antenna |

### 7.3 GPS Antenna

| Parameter | Specification |
|-----------|---------------|
| **Type** | Active patch antenna |
| **Connector** | U.FL |
| **Gain** | 15-30 dB LNA |
| **Voltage** | 3.3V (from module) |
| **Cable Length** | 100-300mm typical |
| **Qty** | 1 |

---

## 8. Analog Front-End

### 8.1 ADC (External)

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | ADS8688A |
| **Manufacturer** | Texas Instruments |
| **Channels** | 8 (multiplexed) |
| **Resolution** | 16-bit |
| **Sample Rate** | 500 kSPS |
| **Interface** | SPI |
| **Qty** | 3 (for 20 analog inputs + current sense) |

### 8.2 Analog Input Protection

| Component | Part Number | Value | Qty |
|-----------|-------------|-------|-----|
| Series Resistor | - | 10 kΩ 0402 | 20 |
| TVS Diode | PESD5V0S1BL | 5.1V | 20 |
| Filter Capacitor | - | 100 nF 0402 | 20 |

---

## 9. Connectors

### 9.1 Main Connector A (34-pin) - Outputs

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | 1-1564514-1 |
| **Manufacturer** | TE Connectivity |
| **Series** | Superseal 1.0 |
| **Positions** | 34 |
| **Current Rating** | 13A per contact |
| **Sealing** | IP67 |
| **Qty** | 1 |

**Function:** Power outputs 1-30, H-Bridge outputs

### 9.2 Main Connector B (26-pin) - Analog Inputs

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | 1-1564512-1 |
| **Manufacturer** | TE Connectivity |
| **Series** | Superseal 1.0 |
| **Positions** | 26 |
| **Current Rating** | 13A per contact |
| **Sealing** | IP67 |
| **Qty** | 1 |

**Function:** 20x Analog inputs, CAN bus, 5V sensor supply

### 9.3 Main Connector C (26-pin) - Digital Inputs

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | 1-1564512-1 |
| **Manufacturer** | TE Connectivity |
| **Series** | Superseal 1.0 |
| **Positions** | 26 |
| **Current Rating** | 13A per contact |
| **Sealing** | IP67 |
| **Qty** | 1 |

**Function:** 20x Digital inputs, LIN bus, USB

### 9.4 Power Terminal (Positive)

| Parameter | Specification |
|-----------|---------------|
| **Type** | Radlock 200A |
| **Manufacturer** | TE Connectivity |
| **Rating** | 200A continuous |
| **Features** | Tool-less connection, vibration resistant |
| **Qty** | 1 |

**Note:** 200A ANL fuse required, 2/0 AWG (70mm²) wire recommended

### 9.5 Ground Terminal

| Parameter | Specification |
|-----------|---------------|
| **Type** | M8 stud terminal |
| **Material** | Brass, nickel plated |
| **Thread** | M8 x 1.25 |
| **Current Rating** | 150A continuous |
| **Mounting** | Through-hole, isolated |
| **Qty** | 1 |

**Note:** Ring terminal 4 AWG (25mm²), 8-10 Nm torque

### 9.6 USB Connector

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | USB4110-GF-A |
| **Type** | USB-C receptacle |
| **Sealing** | IP67 with cap |
| **Qty** | 1 |

---

## 10. Passive Components

### 10.1 Power Input Filtering

| Component | Value | Package | Qty |
|-----------|-------|---------|-----|
| Input Inductor | 10 µH, 150A | Custom | 1 |
| Bulk Capacitor | 1000 µF 25V | Electrolytic | 4 |
| Ceramic Capacitor | 100 µF 25V | 1210 | 10 |
| Ceramic Capacitor | 10 µF 25V | 0805 | 20 |

### 10.2 Decoupling Capacitors

| Component | Value | Package | Qty |
|-----------|-------|---------|-----|
| MCU VDD | 100 nF | 0402 | 12 |
| MCU VDD | 4.7 µF | 0603 | 4 |
| PROFET VDD | 100 nF | 0603 | 30 |
| H-Bridge VDD | 100 nF | 0603 | 8 |
| H-Bridge Bootstrap | 100 nF | 0603 | 8 |

### 10.3 Crystal Oscillator

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | ABM8G-25.000MHZ |
| **Frequency** | 25 MHz |
| **Load Capacitance** | 12 pF |
| **Tolerance** | +/-20 ppm |
| **Package** | 3.2x2.5mm |
| **Qty** | 1 |

### 10.4 RTC Crystal

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | ABS07-32.768KHZ-7-T |
| **Frequency** | 32.768 kHz |
| **Load Capacitance** | 7 pF |
| **Package** | 3.2x1.5mm |
| **Qty** | 1 |

---

## 11. Recommended Suppliers

| Manufacturer | Distributor | Notes |
|--------------|-------------|-------|
| Infineon | DigiKey, Mouser, Arrow | PROFET, H-Bridge, MOSFETs |
| STMicroelectronics | DigiKey, Mouser | MCU, LDOs |
| NXP | DigiKey, Mouser | CAN/LIN transceivers |
| Texas Instruments | DigiKey, Mouser, TI Direct | Power management, ADCs |
| u-blox | DigiKey, Mouser | GPS modules |
| TE Connectivity | DigiKey, Mouser | Connectors |
| Espressif | DigiKey, Mouser | WiFi/BT modules |
| Winbond | DigiKey, Mouser | Flash memory |
| Bosch | DigiKey, Mouser | IMU sensors |

---

## 12. Quality Requirements

### 12.1 Component Grades

| Category | Requirement |
|----------|-------------|
| Active Components | AEC-Q100 Grade 1 (-40°C to +125°C) |
| Passive Components | AEC-Q200 |
| Connectors | IP67, automotive rated |

### 12.2 Lead-Free Compliance

All components must be:
- RoHS compliant
- Lead-free (Pb-free)
- Compatible with SAC305 reflow soldering

---

## 13. Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-29 | Initial release with GPS/GNSS, LIN support |
| 1.1 | 2025-12-29 | Updated to 30x40A outputs (BTS7012-2EPA), added 20 analog + 20 digital inputs, Radlock 200A power terminal, 3 main connectors (A/B/C), enhanced IMU specs (LSM6DSO32X) |

---

## See Also

- [PCB Design Specification](PCB_DESIGN_SPECIFICATION.md) - Detailed PCB requirements
- [PCB Routing Guide](pcb_routing_guide.md) - Layout guidelines
- [Technical Specification](technical_specification.md) - Full hardware specification

---

**END OF DOCUMENT**

*R2 m-sport - Proprietary Information*
