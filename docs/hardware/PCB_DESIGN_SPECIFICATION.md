# PMU-30 PCB Design Specification

| Field | Value |
|-------|-------|
| **Document Title** | PCB Design Specification for PMU-30 Power Management Unit |
| **Version** | 1.2 |
| **Date** | 2025-12-29 |
| **Project** | PMU-30 (30-Channel Power Management Unit) |
| **Company** | R2 m-sport |

---

## 1. Executive Summary

This document provides comprehensive specifications for the PCB design and manufacturing of the PMU-30, a professional-grade 30-channel Power Management Unit for motorsport and high-performance automotive applications.

### 1.1 Key Specifications Summary

| Parameter | Value |
|-----------|-------|
| Power Output Channels | 30x PROFET 2 (40A continuous each) |
| H-Bridge Outputs | 4x Dual (30A continuous each) |
| Analog Inputs | 20x dedicated (0-5V, 12-bit ADC) |
| Digital Inputs | 20x dedicated (switch, frequency) |
| Total Current Capacity | 1,200A maximum |
| Total Power Capacity | 14.4 kW @ 12V |
| Input Voltage Range | 6-22V DC |
| Operating Temperature | -40C to +125C |
| Protection Class | IP67 |
| Microcontroller | STM32H743VIT6 (480 MHz Cortex-M7) |
| Power Terminal | Radlock 200A (positive) |

---

## 2. Mechanical Specifications

### 2.1 Enclosure Dimensions

| Dimension | Value | Tolerance |
|-----------|-------|-----------|
| **Length** | 156.0 mm | +/-0.5 mm |
| **Width** | 126.0 mm | +/-0.5 mm |
| **Height** | 40.0 mm | +/-0.3 mm |
| **Corner Radius** | 6.0 mm | +/-0.2 mm |

### 2.2 PCB Dimensions

| Parameter | Value | Notes |
|-----------|-------|-------|
| **PCB Length** | 150.0 mm | 3mm clearance each side |
| **PCB Width** | 120.0 mm | 3mm clearance each side |
| **PCB Thickness** | 2.4 mm | Heavy copper requirement |
| **Max Component Height (Top)** | 12.0 mm | For connectors |
| **Max Component Height (Bottom)** | 8.0 mm | Thermal interface |

### 2.3 Mounting Holes

| Hole | X Position | Y Position | Diameter | Type |
|------|------------|------------|----------|------|
| M1 | 6.0 mm | 6.0 mm | 3.2 mm (M3) | Plated, isolated |
| M2 | 144.0 mm | 6.0 mm | 3.2 mm (M3) | Plated, isolated |
| M3 | 6.0 mm | 114.0 mm | 3.2 mm (M3) | Plated, isolated |
| M4 | 144.0 mm | 114.0 mm | 3.2 mm (M3) | Plated, isolated |

### 2.4 Enclosure Specifications

| Parameter | Specification |
|-----------|---------------|
| **Material** | Aluminum alloy 6061-T6 or 6082-T6 |
| **Manufacturing** | CNC machined from solid billet |
| **Surface Finish** | Hard anodized (Type III), 25-50 um |
| **Color** | Black (RAL 9005) or Natural aluminum |
| **Sealing** | IP67 rated with silicone gasket |
| **Heat Sink Fins** | Integrated, min 8 fins, 3mm depth |
| **Thermal Conductivity** | >150 W/m-K |

### 2.5 Gasket and Sealing

| Component | Specification |
|-----------|---------------|
| **Gasket Material** | Silicone rubber (VMQ), Shore A 50+/-5 |
| **Gasket Cross-section** | 2.0 mm diameter O-ring |
| **Compression** | 20-30% nominal |
| **Temperature Range** | -60C to +200C |
| **Connector Sealing** | Deutsch standard seals |

---

## 3. Electrical Specifications

### 3.1 Power Input Requirements

| Parameter | Min | Typical | Max | Unit |
|-----------|-----|---------|-----|------|
| Operating Voltage | 6.0 | 12.0/14.4 | 22.0 | V DC |
| Cranking Voltage (100ms) | 4.5 | - | - | V DC |
| Load Dump (ISO 7637-2) | - | - | 36.0 | V DC |
| Reverse Polarity | -16 | - | - | V DC |
| Input Current (no load) | - | 150 | 250 | mA |
| Input Current (max load) | - | - | 1,200 | A |

### 3.2 Power Output Channels (PROFET 2)

**All 30 Output Channels (Channels 1-30)**

| Parameter | Min | Typical | Max | Unit |
|-----------|-----|---------|-----|------|
| Continuous Current | - | - | 40 | A |
| Inrush Current (1ms) | - | - | 160 | A |
| On-Resistance | - | 3.5 | 5.0 | mohm |
| PWM Frequency | 10 | 500 | 30,000 | Hz |
| PWM Resolution | - | 12 | - | bits |
| Soft-start Time | 0 | - | 5,000 | ms |
| Total System Capacity | - | - | 1,200 | A |

**Note:** All 30 outputs use identical 40A-rated BTS7012-2EPA high-side switches.

### 3.3 H-Bridge Outputs

| Parameter | Min | Typical | Max | Unit |
|-----------|-----|---------|-----|------|
| Continuous Current | - | - | 30 | A |
| Peak Current (100ms) | - | - | 60 | A |
| On-Resistance | - | 26 | 35 | mohm |
| PWM Frequency | 10 | 1,000 | 20,000 | Hz |
| Dead-time | 1 | 2 | - | us |

### 3.4 Analog Inputs (20x)

| Parameter | Min | Typical | Max | Unit |
|-----------|-----|---------|-----|------|
| Channels | - | 20 | - | - |
| Input Voltage Range | 0 | - | 5.0 | V |
| Absolute Max Voltage | -2.0 | - | 36.0 | V |
| ADC Resolution | - | 12 | - | bits |
| Input Impedance | 100 | - | - | kohm |
| Sample Rate | - | 1,000 | - | Hz/ch |

**Function:** Sensor inputs (temperature, pressure, position, level, etc.)

### 3.5 Digital Inputs (20x)

| Parameter | Min | Typical | Max | Unit |
|-----------|-----|---------|-----|------|
| Channels | - | 20 | - | - |
| Input Voltage Range | 0 | - | 5.0 | V |
| Absolute Max Voltage | -2.0 | - | 36.0 | V |
| Logic Threshold | - | 2.5 | - | V |
| Input Impedance | 100 | - | - | kohm |
| Sample Rate | - | 500 | - | Hz/ch |
| Debounce | 1 | - | 1000 | ms |

**Function:** Switch inputs, frequency inputs, rotary switches

### 3.6 CAN Bus Interfaces

**CAN FD Interfaces (Bus 1, 2)**

| Parameter | Specification |
|-----------|---------------|
| **Standard** | ISO 11898-1:2015 CAN FD |
| **Arbitration Rate** | 125 kbps to 1 Mbps |
| **Data Rate (BRS)** | Up to 5 Mbps |
| **Payload** | 8, 12, 16, 20, 24, 32, 48, 64 bytes |
| **Transceiver** | TJA1463 (CAN FD with SIC) |
| **Termination** | 120Ω switchable (software controlled) |
| **ESD Protection** | +/-15 kV HBM, +/-8 kV IEC 61000-4-2 |
| **Bus Fault Tolerance** | -58V to +58V |
| **Common Mode Range** | -12V to +12V |
| **Loop Delay** | <150 ns |

**CAN 2.0B Interfaces (Bus 3, 4)**

| Parameter | Specification |
|-----------|---------------|
| **Standard** | ISO 11898-1:2003 CAN 2.0B |
| **Baud Rate** | 125, 250, 500, 1000 kbps |
| **Payload** | 0-8 bytes |
| **Transceiver** | TJA1051T/3 or MCP2562FD |
| **Termination** | 120Ω switchable (software controlled) |
| **ESD Protection** | +/-8 kV HBM |
| **Bus Fault Tolerance** | -27V to +40V |

**CAN Bus Common Features**

| Feature | Specification |
|---------|---------------|
| **Message Filters** | 28 filter banks per interface |
| **TX Mailboxes** | 3 per interface |
| **RX FIFOs** | 2 per interface (64 messages each) |
| **Error Handling** | Automatic retransmission, bus-off recovery |
| **Wake-up** | CAN wake-up from low-power mode |
| **BlinkMarine Support** | PKP-2200/2400/2600-SI keypads on any bus |

---

## 4. PCB Stack-up and Materials

### 4.1 Layer Stack-up (8-Layer)

| Layer | Function | Copper Weight | Thickness |
|-------|----------|---------------|-----------|
| L1 | Power/Signal | 3 oz (105um) | 105 um |
| Prepreg | 1080x2 | - | 200 um |
| L2 | Ground Plane | 2 oz (70um) | 70 um |
| Core | FR4 | - | 200 um |
| L3 | Signal | 1 oz (35um) | 35 um |
| Prepreg | 2116 | - | 120 um |
| L4 | Power Plane (12V) | 2 oz (70um) | 70 um |
| Core | FR4 | - | 400 um |
| L5 | Power Plane (5V/3.3V) | 2 oz (70um) | 70 um |
| Prepreg | 2116 | - | 120 um |
| L6 | Signal | 1 oz (35um) | 35 um |
| Core | FR4 | - | 200 um |
| L7 | Ground Plane | 2 oz (70um) | 70 um |
| Prepreg | 1080x2 | - | 200 um |
| L8 | Power/Signal | 3 oz (105um) | 105 um |
| **TOTAL** | | | **~2.4 mm** |

### 4.2 PCB Material Specifications

| Parameter | Specification |
|-----------|---------------|
| **Base Material** | FR4, High-Tg (Tg >= 170C) |
| **Recommended** | Isola FR408HR, Panasonic Megtron 6 |
| **Dk** | 3.6 - 4.0 @ 1 GHz |
| **Df** | < 0.010 @ 1 GHz |
| **CTI** | >= 400V |
| **Flammability** | UL94 V-0 |
| **Thermal Conductivity** | >= 0.4 W/m-K |

### 4.3 Via Specifications

| Via Type | Drill | Finished | Copper | Current |
|----------|-------|----------|--------|---------|
| Standard Signal | 0.3 mm | 0.25 mm | 25 um | 1A |
| Power Via | 0.5 mm | 0.45 mm | 25 um | 3A |
| Thermal Via | 0.4 mm | 0.35 mm | Filled | 2A |
| High-Current | 0.8 mm | 0.7 mm | 50 um | 5A |

### 4.4 Surface Finish

| Option | Specification |
|--------|---------------|
| **Primary** | ENIG (Ni: 3-6 um, Au: 0.05-0.1 um) |
| **Solder Mask** | LPI, Green or Black, Tg >= 150C |
| **Silkscreen** | White, epoxy-based |

---

## 5. Component Selection

### 5.1 Microcontroller

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | STM32H743VIT6 or STM32H753VIT6 |
| **Package** | LQFP100 (14x14mm, 0.5mm pitch) |
| **Core** | ARM Cortex-M7 @ 480 MHz |
| **Flash** | 2 MB |
| **RAM** | 1 MB |
| **Operating Temp** | -40C to +125C (Grade 1) |

### 5.2 Power Output Drivers (PROFET 2)

| Parameter | Specification |
|-----------|---------------|
| **High-Current (20x)** | Infineon BTS7008-2EPA (2-ch, 40A) |
| **Standard (10x)** | Infineon BTS7006-2EPA (2-ch, 25A) |
| **Package** | PG-TSDSO-14 (exposed pad) |
| **Quantity** | 10x BTS7008 + 5x BTS7006 |

**Alternatives:** BTS50015-1TAD, BTS50085-1TAD

### 5.3 H-Bridge Drivers

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | Infineon BTN8982TA |
| **Package** | PG-TO263-7 (D2PAK-7) |
| **Continuous Current** | 30A |
| **Peak Current** | 55A |
| **Quantity** | 8x (4 dual H-bridges) |

**Alternatives:** VNH5019A-E, BTS7960B

### 5.4 CAN Transceivers

| Interface | Part Number | Package |
|-----------|-------------|---------|
| CAN FD 1,2 | TJA1463 | HVSON8 |
| CAN 2.0 3,4 | TJA1051T/3 | SO8 |

**Alternatives:** MCP2562FD, TCAN1042V

### 5.5 Power Supply ICs

| Function | Part Number | Specification |
|----------|-------------|---------------|
| 5V Buck | LM5146RGYR | 6-42V in, 5V/5A out |
| 3.3V LDO | TPS62912RPHR | 5V in, 3.3V/1A out |
| Sensor 5V | TPS7A4001 | 5.0V/500mA, +/-1% |

### 5.6 WiFi/Bluetooth Module

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | ESP32-C3-MINI-1-N4 |
| **WiFi** | 802.11 b/g/n (2.4 GHz) |
| **Bluetooth** | BLE 5.0 |
| **Certification** | FCC, CE, IC |

### 5.7 External Flash Memory

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | W25Q512JVEIQ |
| **Capacity** | 512 Mbit (64 MB) |
| **Interface** | Quad SPI, 133 MHz |

### 5.8 IMU (Accelerometer/Gyroscope)

6-axis MEMS IMU for motion sensing and vehicle dynamics analysis.

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | LSM6DSO32X (recommended) |
| **Manufacturer** | STMicroelectronics |
| **Package** | LGA-14 (2.5 × 3.0 mm) |
| **Accelerometer** | ±4/8/16/32g selectable |
| **Gyroscope** | ±125 to ±2000 °/s selectable |
| **Resolution** | 16-bit |
| **Sample Rate** | Up to 6.6 kHz |
| **Interface** | SPI (10MHz) / I2C (1MHz) |

**Applications:**
- G-force data logging (lateral, longitudinal, vertical)
- Crash/impact detection
- Roll/pitch/yaw calculation
- Traction control inputs

### 5.9 GPS/GNSS Module

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | u-blox MAX-M10S or NEO-M9N |
| **Constellation** | GPS, GLONASS, Galileo, BeiDou |
| **Position Accuracy** | 1.5m CEP |
| **Update Rate** | Up to 25 Hz |
| **Time to First Fix** | <1s hot, <26s cold |
| **Interface** | UART (115200 baud) |
| **Antenna** | External active antenna via U.FL |
| **Protocol** | NMEA 0183, UBX binary |
| **Power** | 3.3V, 25mA typical |
| **Operating Temp** | -40°C to +85°C |

**Applications:**
- High-precision speed measurement
- Position logging for track analysis
- Time synchronization for data logging
- Lap timing (when used with geofencing)
- Distance and heading calculation

### 5.10 Protection Components

**TVS Diodes (Power Input)**

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | SMDJ26CA x4 (parallel) |
| **Standoff Voltage** | 26V |
| **Peak Power** | 12,000W total |

**Reverse Polarity Protection**

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | AUIRF3805S-7P |
| **Vds** | 55V |
| **Rds(on)** | 3.3 mohm |
| **Id** | 210A |

---

## 6. Thermal Management

### 6.1 Power Dissipation Budget

| Component | Qty | Power Each | Total |
|-----------|-----|------------|-------|
| PROFET 2 (40A, 4mohm) | 20 | 6.4W | 128W |
| PROFET 2 (25A, 6mohm) | 10 | 3.75W | 37.5W |
| H-Bridge (30A, 26mohm) | 8 | 23.4W | 187.2W |
| Other | - | - | 4W |
| **TOTAL MAX** | | | **~357W** |

**Note:** Typical dissipation: 50-100W

### 6.2 Thermal Interface

| Interface | Material | Conductivity | Thickness |
|-----------|----------|--------------|-----------|
| PCB to Enclosure | Thermal pad (Bergquist GP5000S35) | 5.0 W/m-K | 1.0 mm |

### 6.3 Thermal Via Design (Per PROFET)

- Grid: 5x5 thermal vias
- Via diameter: 0.4mm
- Pitch: 1.0mm
- Type: Plugged and plated
- Bottom copper: 50mm2 minimum

### 6.4 Enclosure Heat Sink

- Fin height: 8mm
- Fin spacing: 4mm
- Fin thickness: 2mm
- Number of fins: 10-12
- Surface area: > 400 cm2
- Thermal resistance: < 0.3 C/W (forced air), < 0.8 C/W (natural)

---

## 7. EMC/EMI Design Guidelines

### 7.1 Applicable Standards

| Standard | Description | Level |
|----------|-------------|-------|
| ISO 11452-2 | Radiated immunity | 100 V/m |
| ISO 11452-4 | BCI immunity | 100 mA |
| CISPR 25 | Radiated emissions | Class 5 |
| ISO 7637-2 | Conducted transients | Level IV |
| IEC 61000-4-2 | ESD | +/-15 kV air |

### 7.2 Grounding Strategy

- **Star ground** at input connector
- **Separate grounds:** Power GND, Signal GND, Analog GND
- **Ground planes:** L2 and L7 (solid, max 10% voids)
- **Via stitching:** Every 20mm

### 7.3 Routing Rules

| Signal Type | Max Length | Rules |
|-------------|------------|-------|
| CAN bus | 100mm | Differential, 120 ohm |
| SPI | 50mm | Reference to ground |
| Clock | 30mm | Guard traces |
| ADC inputs | 30mm | Away from switching |

---

## 8. Component Placement

### 8.1 Placement Zones

```
+----------------------------------------------------------+
|  ZONE A: POWER OUTPUTS (PROFET 2 drivers)                |
|  - Aligned for heat sinking                               |
|  - 20x high-current + 10x standard                        |
+----------------------------------------------------------+
|                                                          |
|  ZONE B: H-BRIDGES    |    ZONE C: CONTROL               |
|  - 4x dual BTN89      |    - MCU, Flash, IMU             |
|                       |    - WiFi/BT, RTC, LEDs          |
+-----------------------+----------------------------------+
|                                                          |
|  ZONE D: POWER SUPPLY |    ZONE E: ANALOG                |
|  - Buck, LDOs         |    - Input conditioning          |
|  - Input protection   |    - ADC references              |
+-----------------------+----------------------------------+
|  ZONE F: CONNECTORS                                      |
|  - Deutsch DTM series                                    |
|  - Power input stud/terminal                             |
+----------------------------------------------------------+
```

### 8.2 Keep-Out Zones

| Area | Radius | Reason |
|------|--------|--------|
| Buck inductor | 10mm | EMI |
| WiFi antenna | 15mm | RF |
| Crystal | 5mm | Noise |
| Mounting holes | 3mm | Mechanical |
| Enclosure seal | 2mm | Gasket |

---

## 9. Routing Guidelines

### 9.1 Trace Width (IPC-2221, 20C rise)

| Current | Internal 1oz | External 2oz | External 3oz |
|---------|--------------|--------------|--------------|
| 1A | 0.5mm | 0.3mm | 0.2mm |
| 5A | 2.5mm | 1.5mm | 1.0mm |
| 10A | 5.0mm | 3.0mm | 2.0mm |
| 20A | 10.0mm | 6.0mm | 4.0mm |
| 40A | 20.0mm | 12.0mm | 8.0mm |

### 9.2 Design Rules

| Parameter | Minimum | Recommended |
|-----------|---------|-------------|
| Trace/Space (signal) | 0.1/0.1mm | 0.15/0.15mm |
| Trace/Space (power) | 0.2/0.2mm | 0.3/0.3mm |
| Via-to-via | 0.3mm | 0.5mm |
| Via-to-trace | 0.2mm | 0.3mm |
| Copper-to-edge | 0.3mm | 0.5mm |

### 9.3 Differential Pairs (CAN)

| Parameter | Value |
|-----------|-------|
| Trace width | 0.2mm |
| Trace spacing | 0.2mm |
| Impedance | 120 ohm +/-10% |
| Max length mismatch | 2mm |

---

## 10. Connector Specifications

### 10.1 Connector Selection: TE Superseal 1.0 Series

The PMU-30 uses TE Connectivity Superseal 1.0 series connectors for robust automotive-grade connections with IP67 sealing.

| Connector | Part Number | Positions | Current | Application |
|-----------|-------------|-----------|---------|-------------|
| Main A | 1-1564514-1 | 34 | 13A/pin | Outputs 1-30, H-Bridge |
| Main B | 1-1564512-1 | 26 | 13A/pin | Analog Inputs, CAN, LIN, Aux |
| Main C | 1-1564512-1 | 26 | 13A/pin | Digital Inputs |
| Power (+) | Radlock 200A | 1 | 200A | Main battery positive |
| Ground (-) | M8 stud | 1 | 150A | Chassis ground |

**Main Connector A (34-pin) - Outputs:**

| Pin | Function | Pin | Function |
|-----|----------|-----|----------|
| 1-10 | Outputs 1-10 | 18-27 | Outputs 11-20 |
| 11-15 | Outputs 21-25 | 28-32 | Outputs 26-30 |
| 16-17 | H-Bridge 1 (A/B) | 33-34 | H-Bridge 2 (A/B) |

**Main Connector B (26-pin) - Analog Inputs/Comms:**

| Pin | Function | Pin | Function |
|-----|----------|-----|----------|
| 1-10 | Analog Inputs 1-10 | 14-20 | Analog Inputs 11-17 |
| 11-13 | Analog Inputs 18-20 | 21 | 5V Sensor Supply |
| 22 | Sensor Ground | 23 | CAN1 H |
| 24 | CAN1 L | 25 | CAN2 H |
| 26 | CAN2 L | - | - |

**Main Connector C (26-pin) - Digital Inputs:**

| Pin | Function | Pin | Function |
|-----|----------|-----|----------|
| 1-10 | Digital Inputs 1-10 | 14-20 | Digital Inputs 11-17 |
| 11-13 | Digital Inputs 18-20 | 21 | LIN |
| 22 | USB D+ | 23 | USB D- |
| 24 | USB GND | 25-26 | Reserved |

**Power Terminal (Positive):**

| Parameter | Specification |
|-----------|---------------|
| Type | Radlock 200A (TE Connectivity) |
| Rating | 200A continuous |
| Features | Tool-less, vibration resistant |
| Wire | 2/0 AWG (70mm²) recommended |
| Fuse | 200A ANL external |

**Ground Terminal:**

| Parameter | Specification |
|-----------|---------------|
| Thread | M8 x 1.25 |
| Material | Brass, nickel plated |
| Torque | 8-10 Nm |
| Current Rating | 150A continuous |
| Wire | 4 AWG (25mm²) ring terminal |

### 10.2 Wire Gauge Recommendations

| Current | Minimum AWG | Recommended |
|---------|-------------|-------------|
| 5A | 20 AWG | 18 AWG |
| 10A | 16 AWG | 14 AWG |
| 20A | 12 AWG | 10 AWG |
| 40A | 8 AWG | 6 AWG |

---

## 11. Protection Circuits

### 11.1 Input Protection

| Component | Value | Function |
|-----------|-------|----------|
| F1 (external) | 150A fuse | Overcurrent |
| L1 | 10uH, 150A | Filter |
| D1 | SMDJ26CA x4 | TVS, 12kW |
| Q1 | AUIRF3805S | Reverse polarity |
| C1 | 1000uF/35V | Bulk capacitor |

### 11.2 Analog Input Protection

| Component | Value | Function |
|-----------|-------|----------|
| R1 | 10kohm | Current limit |
| D1 | 5.1V TVS | Overvoltage |
| R2 + C1 | 1kohm + 100nF | RC filter (1.6kHz) |

### 11.3 CAN Bus Protection

| Component | Value | Function |
|-----------|-------|----------|
| CMC | 100uH | Common mode filter |
| TVS | PESD1CAN | ESD protection |

---

## 12. Testing Requirements

### 12.1 Design Verification Tests

| Test | Standard | Requirement |
|------|----------|-------------|
| Operating Voltage | ISO 16750-2 | 6-22V |
| Overvoltage | ISO 16750-2 | 24V, 1hr |
| Reverse Polarity | ISO 16750-2 | -16V, 1min |
| Load Dump | ISO 7637-2 | 36V, 400ms |

### 12.2 Environmental Tests

| Test | Standard | Conditions |
|------|----------|------------|
| High Temperature | ISO 16750-4 | +125C, 1000 hrs |
| Low Temperature | ISO 16750-4 | -40C, 96 hrs |
| Thermal Shock | ISO 16750-4 | -40C to +125C, 100 cycles |
| Humidity | ISO 16750-4 | 85C/85% RH, 1000 hrs |
| Vibration | ISO 16750-3 | Random, 32 hrs |
| IP67 Ingress | IEC 60529 | Dust + 1m water |

### 12.3 EMC Tests

| Test | Standard | Level |
|------|----------|-------|
| Radiated Immunity | ISO 11452-2 | 100 V/m |
| Radiated Emissions | CISPR 25 | Class 5 |
| ESD | ISO 10605 | +/-25kV air |
| Transients | ISO 7637-2 | Level IV |

---

## 13. Manufacturing Requirements

### 13.1 PCB Fabrication

| Parameter | Specification |
|-----------|---------------|
| **Certification** | IATF 16949 (automotive) |
| **PCB Class** | IPC-6012 Class 3 |
| **Electrical Test** | 100% netlist test |

### 13.2 Assembly Requirements

| Parameter | Specification |
|-----------|---------------|
| **Certification** | IATF 16949, IPC-A-610 Class 3 |
| **Solder Paste** | SAC305 (lead-free), Type 4 |
| **AOI Inspection** | 100% of boards |
| **X-Ray Inspection** | BGA, QFN packages |

### 13.3 Quality Standards

| Standard | Description |
|----------|-------------|
| IATF 16949 | Automotive quality |
| AEC-Q100 | IC qualification (Grade 1) |
| AEC-Q200 | Passive qualification |

### 13.4 Reliability Targets

| Parameter | Target |
|-----------|--------|
| MTBF | > 50,000 hours @ 85C |
| Design Life | 15 years / 300,000 km |

---

## 14. Deliverables

### 14.1 Design Deliverables

| Item | Format |
|------|--------|
| Schematic | PDF + Native (Altium/KiCad) |
| PCB Layout | Gerber RS-274X |
| Drill Files | Excellon |
| Pick and Place | CSV |
| Assembly Drawing | PDF |
| 3D Model | STEP |
| BOM | Excel |

### 14.2 Manufacturing Deliverables

| Item | Quantity |
|------|----------|
| Prototype PCBs | 10 |
| Assembled Prototypes | 5 |
| Test Fixtures | 1 |

---

## 15. Reference Designs

| Product | Manufacturer | Channels |
|---------|--------------|----------|
| PMU-16/24 | ECUMaster | 16/24 |
| PDM-30 | MoTeC | 30 |
| C127 | Link ECU | 27 |
| PDM-15 | Haltech | 15 |

**Application Notes:**
- Infineon AN_201701_PL12_017: BTS7xxx Design Guide
- Infineon AN_2018-08: BTN89xx Motor Control
- ST AN4661: Getting started with STM32H7

---

## Appendix A: Component Cross-Reference

| Function | Primary | Alternative 1 | Alternative 2 |
|----------|---------|---------------|---------------|
| MCU | STM32H743VIT6 | STM32H753VIT6 | STM32H745ZIT6 |
| PROFET 40A (x30) | BTS7012-2EPA | VNQ7050AJ | VNQ7040AJ |
| H-Bridge | BTN8982TA | VNH5019A-E | BTS7960B |
| CAN FD | TJA1463 | MCP2562FD | TCAN1042V |
| CAN 2.0B | TJA1051T/3 | MCP2561 | SN65HVD230 |
| Buck 5V | LM5146 | LMR36015 | TPS54560 |
| Flash | W25Q512JVEIQ | IS25LP512MG | MX25L51245G |
| IMU | LSM6DSO32X | ICM-42688-P | BMI088 |
| GPS/GNSS | MAX-M10S | NEO-M9N | SAM-M10Q |
| WiFi/BT | ESP32-C3-MINI-1 | ESP32-C6 | ESP32-S3 |

---

## Appendix B: Thermal Calculations

```
PROFET Power (single @ 40A): P = 40^2 x 0.0035 = 5.6W
Total PROFET (30 x 40A): 30 x 5.6W = 168W
H-Bridge (8 x 30A): 8 x 11.7W = 93.6W
Total Max: ~262W

Required Rth (85C ambient, 125C max):
Rth = (125-85)/262 = 0.15 C/W
```

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-21 | Initial release |
| 1.1 | 2025-12-29 | Updated PCB dimensions (150mm × 120mm), 8-layer stack-up, added GPS/GNSS module, LIN transceiver, expanded CAN FD specifications |
| 1.2 | 2025-12-29 | Updated all 30 outputs to 40A, added 20 analog + 20 digital input architecture, Radlock 200A power terminal, Main C connector for digital inputs, enhanced IMU specs |

---

**END OF DOCUMENT**

*R2 m-sport - Proprietary Information*

---

## Appendix C: Detailed Routing Guide

### C.1 Power Routing Strategy

**Track Width Calculator (105μm/3oz outer copper, 20°C rise):**

| Current | Track Width |
|---------|------------|
| 10A | 2.0mm |
| 15A | 3.0mm |
| 20A | 4.0mm |
| 30A | 8.0mm |
| 40A | 12.0mm |

**Track Width Calculator (70μm/2oz inner planes, 20°C rise):**

| Current | Track Width |
|---------|------------|
| 5A | 1.5mm |
| 10A | 3.0mm |
| 20A | 6.0mm |

**Power Routing Rules:**
1. Use polygon pours for main power distribution
2. Multiple vias to inner +12V plane (minimum 10× 0.8mm vias per 10A)
3. Thermal relief for power connections
4. Keep power traces on outer layers where possible

### C.2 PROFET Power Distribution

Each PROFET BTS7012-2EPA handles 2 channels at 40A each.

**PROFET Routing Rules:**
1. VBB pin: 5mm track minimum, star connection from main bus
2. GND pins: Multiple vias directly to GND plane
3. Output pins: 3mm tracks to output connectors
4. IS (current sense): Keep short, away from power traces
5. DEN/DSEL: 0.2mm tracks, can route on B.Cu

### C.3 MCU Signal Routing (STM32H743)

**Critical Signals:**
- USB: 90Ω differential, length matched ±0.5mm
- CAN FD: 120Ω differential, 0.3mm tracks
- QSPI Flash: Length matched, max 30mm
- Crystal: Keep traces short (<5mm), ground guard

### C.4 CAN Bus Routing

**Routing Rules:**
1. CANH/CANL as differential pair, 120Ω impedance
2. Keep CAN traces away from power switching
3. ESD protection at connector: PESD2CAN
4. Stub length to transceiver: <25mm

### C.5 Copper Pours (8-Layer Design)

1. **L1 (Top)**: +12V pour around power section, signal routing
2. **L2**: Solid GND plane (max 10% voids for vias)
3. **L3**: Signal routing, minimal pour (QSPI, USB area)
4. **L4**: +12V plane (main power distribution)
5. **L5**: Split plane (5V and 3.3V regions)
6. **L6**: Signal routing, minimal pour (CAN, I2C area)
7. **L7**: Solid GND plane (return path)
8. **L8 (Bottom)**: GND pour in MCU area, +12V pour in power area

### C.6 Routing Checklist

#### Phase 1: Power (L1, L4, L8)
- [ ] Main +12V input polygon (L1)
- [ ] PROFET VBB connections (star topology)
- [ ] H-Bridge VS connections
- [ ] GND via stitching (L2, L7)

#### Phase 2: Critical Signals (L3, L6)
- [ ] USB differential pair (90Ω)
- [ ] CAN FD pairs (120Ω, 4 buses)
- [ ] QSPI to Flash (length matched)

#### Phase 3: Control & Analog
- [ ] PROFET DEN/DSEL signals
- [ ] Analog inputs with filtering
- [ ] Analog ground island

#### Phase 4: Cleanup
- [ ] Copper pour fill (all layers)
- [ ] Via stitching (GND every 5mm)
- [ ] DRC clean

