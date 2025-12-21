# PMU-30 Bill of Materials (BOM)

**Document Version:** 1.0
**Date:** 2025-12-21
**PCB Revision:** A (Prototype)
**Owner:** R2 m-sport
**Confidentiality:** Proprietary - Internal Use Only

---

**© 2025 R2 m-sport. All rights reserved.**

---

---

## BOM Summary

| Category | Quantity | Estimated Cost (USD) |
|----------|----------|---------------------|
| Power Stage | 45 | $450 |
| Microcontroller & Memory | 15 | $85 |
| Communication | 12 | $45 |
| Sensors | 8 | $25 |
| Power Supply | 25 | $35 |
| Passives (R, C, L) | ~500 | $50 |
| Connectors | 15 | $75 |
| LEDs & Indicators | 35 | $15 |
| Protection | 30 | $30 |
| PCB | 1 | $150 |
| **Total** | **~686** | **~$960** |

---

## 1. Power Stage Components

### 1.1 High-Side Smart Switches (30x)

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| U10-U39 | BTS7008-2EPA | Infineon | PROFET 2 Smart High-Side Switch, 40A, TO263-7 | 30 | $12.00 | $360.00 |

**Alternatives:**
- BTS7012-2EPA (50A version)
- BTS7006-2EPA (30A version, lower cost)

**Key Features:**
- Integrated current sensing (Kilis = 22700:1)
- Temperature sensing
- Diagnostic outputs
- Short circuit protection
- Open load detection

### 1.2 Gate Drive Support

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| R100-R129 | RC0805FR-0710KL | Yageo | 10kΩ, 1%, 0805 (IS pulldown) | 30 | $0.02 | $0.60 |
| R200-R229 | RC0805FR-0710KL | Yageo | 10kΩ, 1%, 0805 (Kilis pullup) | 30 | $0.02 | $0.60 |
| C100-C129 | GRM21BR71C105KA12L | Murata | 1µF, 16V, X7R, 0805 (local decoupling) | 30 | $0.10 | $3.00 |

---

## 2. Microcontroller System

### 2.1 Main MCU

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| U1 | STM32H743VIT6 | STMicroelectronics | MCU, 480MHz, Cortex-M7, 2MB Flash, 1MB RAM, LQFP-100 | 1 | $15.00 | $15.00 |

**Alternatives:**
- STM32H753VIT6 (with crypto)
- STM32H750VBT6 (128KB flash, external flash required)

### 2.2 MCU Support Components

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| Y1 | ABM8-25.000MHZ-B2-T | Abracon | 25MHz Crystal, ±20ppm, 18pF | 1 | $0.50 | $0.50 |
| Y2 | ABS07-32.768KHZ-T | Abracon | 32.768kHz Crystal, RTC | 1 | $0.40 | $0.40 |
| C1, C2 | GRM1555C1H180JA01D | Murata | 18pF, 50V, C0G, 0402 (crystal load) | 2 | $0.05 | $0.10 |
| C3, C4 | GRM155R61A105KA01D | Murata | 1µF, 10V, X5R, 0402 (decoupling) | 6 | $0.02 | $0.12 |
| C5 | GRM21BR61C106KE15L | Murata | 10µF, 16V, X5R, 0805 (bulk) | 2 | $0.15 | $0.30 |
| R1 | RC0805FR-0710KL | Yageo | 10kΩ, 1%, 0805 (NRST pullup) | 1 | $0.02 | $0.02 |
| R2 | RC0805FR-07100KL | Yageo | 100kΩ, 1%, 0805 (Boot0) | 1 | $0.02 | $0.02 |

### 2.3 External Memory

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| U2 | W25Q512JVEIQ | Winbond | 512Mb (64MB) Serial Flash, QSPI, SOIC-16 | 1 | $8.50 | $8.50 |
| C10 | GRM188R71C104KA01D | Murata | 100nF, 16V, X7R, 0603 | 1 | $0.02 | $0.02 |

**Alternatives:**
- MT25QL512ABB (Micron)
- IS25LP512M (ISSI)

### 2.4 Backup Power (RTC)

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| BT1 | CR2032-BS-6-1 | MPD | CR2032 Coin Cell Holder | 1 | $0.50 | $0.50 |
| BAT1 | CR2032 | Panasonic | 3V Lithium Coin Cell, 225mAh | 1 | $0.30 | $0.30 |
| D1 | BAT54C | Diodes Inc. | Dual Schottky Diode, SOT-23 | 1 | $0.10 | $0.10 |

---

## 3. Communication Interfaces

### 3.1 CAN FD Transceivers (2x)

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| U3, U4 | TCAN1044VDRQ1 | Texas Instruments | CAN FD Transceiver, 5Mbps, SOIC-8 | 2 | $2.50 | $5.00 |
| R10, R11 | RC0805FR-07120RL | Yageo | 120Ω, 1%, 0805 (termination, optional) | 2 | $0.02 | $0.04 |
| C20, C21 | GRM188R71C104KA01D | Murata | 100nF, 16V, X7R, 0603 | 2 | $0.02 | $0.04 |

**Optional Isolation:**
| U3A, U4A | ADuM1201ARZ | Analog Devices | Dual-channel Digital Isolator, SOIC-8 | 2 | $3.50 | $7.00 |

### 3.2 USB Interface

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| U5 | USB3300-EZK | Microchip | USB 2.0 HS PHY, ULPI, QFN-32 | 1 | $3.00 | $3.00 |
| J1 | USB4105-GF-A | GCT | USB Type-C Receptacle, 16-pin | 1 | $0.80 | $0.80 |
| R20, R21 | RC0805FR-075K1L | Yageo | 5.1kΩ, 1%, 0805 (CC pulldown) | 2 | $0.02 | $0.04 |
| C30-C33 | GRM188R71C104KA01D | Murata | 100nF, 16V, X7R, 0603 | 4 | $0.02 | $0.08 |

**Alternative (integrated USB):**
- Use STM32H7 internal USB PHY (no external PHY needed)

### 3.3 WiFi/Bluetooth Module

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| U6 | ESP32-C3-MINI-1-N4 | Espressif | WiFi + BLE Module, 4MB Flash, SMD | 1 | $2.50 | $2.50 |
| C40-C42 | GRM188R71C104KA01D | Murata | 100nF, 16V, X7R, 0603 | 3 | $0.02 | $0.06 |
| R30, R31 | RC0805FR-0710KL | Yageo | 10kΩ, 1%, 0805 (pullup) | 2 | $0.02 | $0.04 |

**Note:** ESP32-C3 includes PCB antenna. For better range, use U.FL connector version and external antenna.

---

## 4. Sensors

### 4.1 Accelerometer

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| U7 | LIS3DHTR | STMicroelectronics | 3-Axis Accelerometer, ±16g, I2C/SPI, LGA-16 | 1 | $2.00 | $2.00 |
| C50-C51 | GRM188R71C104KA01D | Murata | 100nF, 16V, X7R, 0603 | 2 | $0.02 | $0.04 |

**Alternatives:**
- ADXL345BCCZ (Analog Devices)
- LSM6DS3TR (STM, 6-axis with gyro)

### 4.2 Temperature Sensor (Board)

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| U8 | TMP102AIDRLR | Texas Instruments | Digital Temperature Sensor, I2C, SOT-563 | 1 | $1.50 | $1.50 |
| C52 | GRM188R71C104KA01D | Murata | 100nF, 16V, X7R, 0603 | 1 | $0.02 | $0.02 |

**Alternative:**
- Use NTC thermistor + ADC (lower cost)
- LM75BDP (NXP)

### 4.3 Voltage/Current Sensing

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| R300-R329 | RC0805FR-07100KL | Yageo | 100kΩ, 1%, 0805 (Kilis pullup, temp) | 30 | $0.02 | $0.60 |
| R330-R359 | RC0805FR-0710KL | Yageo | 10kΩ, 1%, 0805 (current sense div) | 30 | $0.02 | $0.60 |
| U9 | CD74HC4067M | Texas Instruments | 16-Channel Analog Mux, SOIC-24 | 2 | $0.80 | $1.60 |

---

## 5. Analog Inputs/Outputs

### 5.1 ADC Inputs (10x)

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| R400-R419 | RC0805FR-0710KL | Yageo | 10kΩ, 1%, 0805 (voltage divider) | 20 | $0.02 | $0.40 |
| R420-R429 | RC0805FR-071KL | Yageo | 1kΩ, 1%, 0805 (series protection) | 10 | $0.02 | $0.20 |
| C60-C69 | GRM188R71C103KA01D | Murata | 10nF, 16V, X7R, 0603 (filter) | 10 | $0.02 | $0.20 |
| D10-D19 | SMAJ30A | Littelfuse | TVS Diode, 30V, SMA | 10 | $0.30 | $3.00 |

### 5.2 DAC Outputs (10x)

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| U40, U41 | MCP4728-E/UN | Microchip | Quad 12-bit DAC, I2C, MSOP-10 | 3 | $2.50 | $7.50 |
| C70-C79 | GRM188R71C104KA01D | Murata | 100nF, 16V, X7R, 0603 | 6 | $0.02 | $0.12 |
| R430-R439 | RC0805FR-07100RL | Yageo | 100Ω, 1%, 0805 (output series) | 10 | $0.02 | $0.20 |

---

## 6. Power Supply

### 6.1 Input Protection

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| D2 | SMAJ18A | Littelfuse | TVS Diode, 18V, 400W, SMA | 1 | $0.50 | $0.50 |
| F1 | 0ZCJ0150FF2E | Bel Fuse | PTC Resettable Fuse, 1.5A hold, Radial | 1 | $0.40 | $0.40 |
| Q1 | IRFR5305TRPBF | Infineon | P-MOSFET, -55V, -31A, DPAK (reverse protection) | 1 | $1.00 | $1.00 |
| R3 | RC2512FK-0710KL | Yageo | 10kΩ, 1%, 2512 (gate pulldown) | 1 | $0.10 | $0.10 |

### 6.2 Bulk Capacitance

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| C80-C83 | EEH-ZA1V221P | Panasonic | 220µF, 35V, Electrolytic, Radial | 4 | $1.50 | $6.00 |
| C84-C86 | GRM32ER61A107ME20L | Murata | 100µF, 10V, X5R, 1210 | 3 | $1.00 | $3.00 |

### 6.3 5V Buck Converter

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| U50 | TPS54531DDA | Texas Instruments | 5A, 28V Buck Converter, SOIC-8 | 1 | $2.50 | $2.50 |
| L1 | SRR1260-4R7M | Bourns | 4.7µH, 6A, Shielded Inductor | 1 | $1.20 | $1.20 |
| C90-C91 | GRM21BR61C106KE15L | Murata | 10µF, 16V, X5R, 0805 | 2 | $0.15 | $0.30 |
| C92 | GRM32ER61A107ME20L | Murata | 100µF, 10V, X5R, 1210 | 1 | $1.00 | $1.00 |
| R50, R51 | RC0805FR-0710KL | Yageo | 10kΩ, 1%, 0805 (divider) | 2 | $0.02 | $0.04 |

### 6.4 3.3V LDO

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| U51 | AMS1117-3.3 | Advanced Monolithic | 3.3V, 1A LDO, SOT-223 | 1 | $0.30 | $0.30 |
| C93, C94 | GRM21BR61C106KE15L | Murata | 10µF, 16V, X5R, 0805 | 2 | $0.15 | $0.30 |

**Alternative (higher current):**
- TLV1117-33 (800mA, lower dropout)
- LD1117S33TR (1.3A)

---

## 7. LEDs and Indicators

### 7.1 Channel Status LEDs (30x)

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| LED1-LED30 | LTST-C235KGKRKT | Lite-On | LED Red/Green, 0805 | 30 | $0.20 | $6.00 |
| R500-R559 | RC0805FR-071KL | Yageo | 1kΩ, 1%, 0805 (current limit) | 60 | $0.02 | $1.20 |

### 7.2 LED Drivers

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| U60, U61 | TLC5947DAP | Texas Instruments | 24-Channel LED Driver, PWM, HTSSOP-32 | 2 | $3.50 | $7.00 |
| C100-C101 | GRM188R71C104KA01D | Murata | 100nF, 16V, X7R, 0603 | 2 | $0.02 | $0.04 |

**Alternative:**
- Use shift registers (74HC595) for simple on/off
- Direct MCU GPIO (if pins available)

### 7.3 System Status LEDs

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| LED31 | APHHS1005CGCK | Kingbright | LED RGB, 0805 (system status) | 1 | $0.40 | $0.40 |
| LED32-LED34 | LTST-C170KGKT | Lite-On | LED Green, 0603 (CAN1, CAN2, USB) | 3 | $0.10 | $0.30 |
| R560-R566 | RC0805FR-071KL | Yageo | 1kΩ, 1%, 0805 | 7 | $0.02 | $0.14 |

---

## 8. Connectors

### 8.1 Power Input

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| J10 | DTM06-4S | Deutsch | DTM 4-pin Socket, 13A per pin | 1 | $8.00 | $8.00 |

**Alternative:**
- AMP Superseal 1.5 (282104-1, lower cost)

### 8.2 Power Outputs (30x)

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| J20-J49 | 282104-1 | TE Connectivity | AMP Superseal 1.5, 2-pin Socket | 30 | $1.50 | $45.00 |

**Alternative:**
- DTM series for higher vibration resistance

### 8.3 CAN Bus (2x)

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| J50, J51 | DTM06-4S | Deutsch | DTM 4-pin Socket | 2 | $8.00 | $16.00 |

### 8.4 Analog Inputs

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| J60 | 1-1586040-0 | TE Connectivity | 20-pin MicroTimer Header | 1 | $3.00 | $3.00 |

### 8.5 Programming/Debug

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| J70 | TC2050-IDC-NL | Tag-Connect | 10-pin SWD, No-legs | 1 | $0.00 | $0.00 |

**Alternative:**
- Standard 2.54mm header (if space permits)

---

## 9. Miscellaneous

### 9.1 Test Points

| Ref Des | Part Number | Manufacturer | Description | Qty | Unit Price | Total |
|---------|-------------|--------------|-------------|-----|------------|-------|
| TP1-TP20 | 5000 | Keystone | Compact SMT Test Point, Red/Black | 20 | $0.20 | $4.00 |

### 9.2 Hardware

| Item | Description | Qty | Unit Price | Total |
|------|-------------|-----|------------|-------|
| Mounting | M4 x 10mm Hex Standoff | 4 | $0.30 | $1.20 |
| Screws | M4 x 8mm Button Head | 8 | $0.10 | $0.80 |

---

## 10. PCB Specification

| Parameter | Specification |
|-----------|--------------|
| **Dimensions** | 150mm × 120mm |
| **Layers** | 8-layer |
| **Material** | FR-4, TG170 |
| **Thickness** | 1.6mm |
| **Copper Weight** | 2oz outer, 1oz inner |
| **Min Trace/Space** | 6/6 mil |
| **Min Via** | 0.3mm drill, 0.6mm pad |
| **Surface Finish** | ENIG (Electroless Nickel Immersion Gold) |
| **Solder Mask** | Green LPI, both sides |
| **Silkscreen** | White, both sides |
| **Impedance Control** | Yes (USB, CAN, QSPI) |
| **UL Rating** | 94V-0 |

**Estimated Cost:** $150 for 5 pieces (prototype)

---

## 11. Assembly Notes

### 11.1 Critical Components
- **PROFET devices**: Ensure proper thermal relief, thermal vias
- **STM32H7**: Use stencil for fine-pitch (0.5mm)
- **ESP32 module**: Reflow profile per datasheet
- **USB-C**: Hand solder or selective solder

### 11.2 Rework Considerations
- Add extra test points on power rails
- DNP (Do Not Populate) options for cost reduction:
  - CAN isolation (if not needed)
  - Bluetooth (if WiFi only)
  - Some DAC channels

---

## 12. Sourcing Strategy

### 12.1 Preferred Distributors
- **Digi-Key**: Primary (North America)
- **Mouser**: Secondary
- **LCSC**: Cost-effective (Asia, high MOQ)
- **Alibaba/AliExpress**: Connectors, passives (longer lead times)

### 12.2 Lead Time Expectations
- **STM32H7**: 12-20 weeks (as of 2025)
- **PROFET devices**: 8-16 weeks
- **Standard components**: 1-4 weeks
- **PCB fabrication**: 2-3 weeks (prototype), 4-6 weeks (production)

### 12.3 Inventory Strategy
- **Long-lead items**: Order early (MCU, PROFET)
- **Passives**: Bulk purchase (1000+ pcs)
- **Connectors**: Per project (custom needs)

---

## 13. Cost Analysis

### 13.1 Prototype (Qty: 5)
| Item | Cost |
|------|------|
| Components | $960 × 5 = $4,800 |
| PCB | $150 (for 5 pcs) |
| Assembly | $500 (manual/semi-auto) |
| **Total** | **$5,450** |
| **Per Unit** | **$1,090** |

### 13.2 Low Volume (Qty: 100)
| Item | Cost |
|------|------|
| Components | $650 × 100 = $65,000 (volume pricing) |
| PCB | $30 × 100 = $3,000 |
| Assembly | $15 × 100 = $1,500 (automated) |
| **Total** | **$69,500** |
| **Per Unit** | **$695** |

### 13.3 Production (Qty: 1000)
| Item | Cost |
|------|------|
| Components | $450 × 1000 = $450,000 |
| PCB | $15 × 1000 = $15,000 |
| Assembly | $8 × 1000 = $8,000 |
| **Total** | **$473,000** |
| **Per Unit** | **$473** |

**Target Retail Price:** $1,200 - $1,500 (competitive with ECUMaster PMU24)

---

## 14. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-21 | PMU-30 Team | Initial BOM |

---

## 15. Notes

1. **Part substitution**: Always verify pinout and electrical compatibility
2. **Obsolescence**: Monitor PROFET and STM32 availability
3. **Cost reduction**: Consider integration (e.g., STM32 with internal USB PHY)
4. **Future revisions**: Move to PROFET 3 when available for better efficiency

---

**End of BOM**
