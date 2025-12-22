# PMU-30 PCB Design Specification

| Field | Value |
|-------|-------|
| **Document Title** | PCB Design Specification for PMU-30 Power Management Unit |
| **Version** | 1.0 |
| **Date** | December 2024 |
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
| Total Current Capacity | 1,200A maximum |
| Total Power Capacity | 14.4 kW @ 12V |
| Input Voltage Range | 6-22V DC |
| Operating Temperature | -40C to +125C |
| Protection Class | IP67 |
| Microcontroller | STM32H743VIT6 (480 MHz Cortex-M7) |

---

## 2. Mechanical Specifications

### 2.1 Enclosure Dimensions (Based on ECUMaster PMU +15% height)

| Dimension | Value | Tolerance |
|-----------|-------|-----------|
| **Length** | 131.0 mm | +/-0.5 mm |
| **Width** | 129.0 mm | +/-0.5 mm |
| **Height** | 37.4 mm | +/-0.3 mm |
| **Corner Radius** | 6.0 mm | +/-0.2 mm |

### 2.2 PCB Dimensions

| Parameter | Value | Notes |
|-----------|-------|-------|
| **PCB Length** | 125.0 mm | 3mm clearance each side |
| **PCB Width** | 123.0 mm | 3mm clearance each side |
| **PCB Thickness** | 2.4 mm | Heavy copper requirement |
| **Max Component Height (Top)** | 12.0 mm | For connectors |
| **Max Component Height (Bottom)** | 8.0 mm | Thermal interface |

### 2.3 Mounting Holes

| Hole | X Position | Y Position | Diameter | Type |
|------|------------|------------|----------|------|
| M1 | 6.0 mm | 6.0 mm | 3.2 mm (M3) | Plated, isolated |
| M2 | 119.0 mm | 6.0 mm | 3.2 mm (M3) | Plated, isolated |
| M3 | 6.0 mm | 117.0 mm | 3.2 mm (M3) | Plated, isolated |
| M4 | 119.0 mm | 117.0 mm | 3.2 mm (M3) | Plated, isolated |

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

**High-Current Outputs (Channels 1-20)**

| Parameter | Min | Typical | Max | Unit |
|-----------|-----|---------|-----|------|
| Continuous Current | - | - | 40 | A |
| Inrush Current (1ms) | - | - | 160 | A |
| On-Resistance | - | 4.0 | 5.5 | mohm |
| PWM Frequency | 10 | 500 | 30,000 | Hz |
| PWM Resolution | - | 12 | - | bits |
| Soft-start Time | 0 | - | 5,000 | ms |

**Standard Outputs (Channels 21-30)**

| Parameter | Min | Typical | Max | Unit |
|-----------|-----|---------|-----|------|
| Continuous Current | - | - | 25 | A |
| Inrush Current (1ms) | - | - | 100 | A |
| On-Resistance | - | 6.0 | 8.0 | mohm |

### 3.3 H-Bridge Outputs

| Parameter | Min | Typical | Max | Unit |
|-----------|-----|---------|-----|------|
| Continuous Current | - | - | 30 | A |
| Peak Current (100ms) | - | - | 60 | A |
| On-Resistance | - | 26 | 35 | mohm |
| PWM Frequency | 10 | 1,000 | 20,000 | Hz |
| Dead-time | 1 | 2 | - | us |

### 3.4 Analog/Digital Inputs

| Parameter | Min | Typical | Max | Unit |
|-----------|-----|---------|-----|------|
| Input Voltage Range | 0 | - | 5.0 | V |
| Absolute Max Voltage | -2.0 | - | 36.0 | V |
| ADC Resolution | - | 12 | - | bits |
| Input Impedance | 100 | - | - | kohm |
| Sample Rate | - | 500 | 1,000 | Hz/ch |

### 3.5 CAN Bus Interfaces

| Parameter | Specification |
|-----------|---------------|
| **CAN FD (Bus 1, 2)** | ISO 11898-1:2015, up to 5 Mbps |
| **CAN 2.0 (Bus 3, 4)** | ISO 11898-1:2003, up to 1 Mbps |
| **Termination** | 120 ohm switchable (software) |
| **ESD Protection** | +/-15 kV HBM |
| **Bus Fault Tolerance** | -27V to +40V |

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

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | BMI088 or LSM6DSO32 |
| **Accelerometer** | +/-24g |
| **Gyroscope** | +/-2000 dps |
| **Interface** | SPI |

### 5.9 Protection Components

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

### 10.1 Connector Selection: Deutsch DTM Series

| Connector | Positions | Current | Application |
|-----------|-----------|---------|-------------|
| DTM06-12SA | 12 | 7.5A/pin | Outputs 1-12 |
| DTM06-12SA | 12 | 7.5A/pin | Outputs 13-24 |
| DTM06-8SA | 8 | 7.5A/pin | Outputs 25-30 |
| DTM06-12SA | 12 | 7.5A/pin | H-Bridge outputs |
| DTM06-12SA | 12 | 7.5A/pin | Inputs 1-12 |
| DTM06-8SA | 8 | 7.5A/pin | Inputs 13-20 |
| DTM06-6SA | 6 | 7.5A/pin | CAN + Aux |
| DTM04-4P | 4 | 13A/pin | Main power |

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
| PROFET 40A | BTS7008-2EPA | BTS50015-1TAD | VNQ7050AJ |
| PROFET 25A | BTS7006-2EPA | BTS50010-1TAD | VNQ7040AJ |
| H-Bridge | BTN8982TA | VNH5019A-E | BTS7960B |
| CAN FD | TJA1463 | MCP2562FD | TCAN1042V |
| Buck 5V | LM5146 | LMR36015 | TPS54560 |
| Flash | W25Q512JVEIQ | IS25LP512MG | MX25L51245G |
| IMU | BMI088 | LSM6DSO32 | ICM-42688-P |

---

## Appendix B: Thermal Calculations

```
PROFET Power (single @ 40A): P = 40^2 x 0.004 = 6.4W
Total PROFET (20 x 40A): 20 x 6.4W = 128W
PROFET (10 x 25A): 10 x 3.75W = 37.5W
H-Bridge (8 x 30A): 8 x 11.7W = 93.6W
Total Max: ~265W

Required Rth (85C ambient, 125C max):
Rth = (125-85)/265 = 0.15 C/W
```

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | December 2024 | Initial release |

---

**END OF DOCUMENT**

*R2 m-sport - Proprietary Information*
