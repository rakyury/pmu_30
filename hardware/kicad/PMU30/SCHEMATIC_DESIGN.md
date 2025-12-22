# PMU-30 Schematic Design Guide

**Project:** PMU-30 Power Management Unit
**Revision:** A
**Date:** December 2024
**Author:** R2 m-sport

---

## 1. Block Diagram

```
                                PMU-30 Block Diagram
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ┌─────────────┐     ┌─────────────────────────────────────────────┐       │
│  │  POWER IN   │     │              STM32H743VIT6                  │       │
│  │  6-22V DC   │────▶│  ┌─────────┐  ┌─────────┐  ┌─────────┐     │       │
│  │  (DTM-2)    │     │  │  GPIO   │  │  ADC    │  │  TIM    │     │       │
│  └─────────────┘     │  │ (PWM)   │  │ (1-3)   │  │ (1-8)   │     │       │
│         │            │  └────┬────┘  └────┬────┘  └────┬────┘     │       │
│         ▼            │       │            │            │           │       │
│  ┌─────────────┐     │  ┌────┴────────────┴────────────┴────┐     │       │
│  │   DC-DC     │     │  │            Peripherals             │     │       │
│  │  TPS54360B  │     │  │  CAN FD x2  │  CAN 2.0 x2  │ SPI  │     │       │
│  │  12V→3.3/5V │     │  │  FDCAN1/2   │  CAN1/2      │ I2C  │     │       │
│  └──────┬──────┘     │  └─────────────────────────────────────┘     │       │
│         │            └──────────────────────────────────────────────┘       │
│         │                    │            │            │                    │
│         ▼                    ▼            ▼            ▼                    │
│  ┌─────────────┐     ┌─────────────┐  ┌──────────┐  ┌──────────┐          │
│  │    LDOs     │     │   PROFET 2  │  │ H-Bridge │  │   CAN    │          │
│  │  3.3V/5V    │     │ BTS7008x15  │  │ BTN8982  │  │ TJA1463  │          │
│  └─────────────┘     │  30 outputs │  │ 4x dual  │  │ 4 buses  │          │
│                      └──────┬──────┘  └────┬─────┘  └────┬─────┘          │
│                             │              │              │                 │
│                             ▼              ▼              ▼                 │
│                      ┌─────────────────────────────────────────┐           │
│                      │              DTM CONNECTORS              │           │
│                      │  Outputs (DTM-12 x3)  │  CAN (DTM-8)    │           │
│                      │  H-Bridge (DTM-8)     │  Inputs (DTM-12)│           │
│                      └─────────────────────────────────────────┘           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Schematic Sheets

### Sheet 1: Power Input (power_input.kicad_sch)

**Components:**
| Ref | Part | Package | Description |
|-----|------|---------|-------------|
| J1 | DTM04-2P | DTM | Main power input |
| F1 | 0154250 | ATO | 250A main fuse holder |
| D1 | SM6T36CA | SMC | TVS diode 36V |
| C1-C4 | 100µF/50V | 1210 | Input capacitors |
| U1 | TPS54360B | HTSSOP-20 | 60V/3.5A Buck |
| U2 | TPS54360B | HTSSOP-20 | 60V/3.5A Buck (5V) |
| U3 | AMS1117-3.3 | SOT-223 | 3.3V LDO |

**Power Rails:**
- VBAT: 6-22V input
- +12V: Regulated 12V (for PROFET, H-Bridge)
- +5V: Regulated 5V (for sensors, CAN)
- +3.3V: Regulated 3.3V (for MCU, logic)

---

### Sheet 2: MCU Core (mcu_core.kicad_sch)

**Components:**
| Ref | Part | Package | Description |
|-----|------|---------|-------------|
| U10 | STM32H743VIT6 | LQFP-100 | Main MCU |
| Y1 | 25MHz | 3215 | HSE crystal |
| Y2 | 32.768kHz | 1610 | LSE crystal |
| C10-C17 | 100nF | 0402 | Decoupling |
| C18-C21 | 4.7µF | 0603 | Bulk decoupling |
| R10 | 10K | 0402 | NRST pullup |

**Pin Allocations:**
```
PORTA: TIM1_CH1-4 (OUT0-3), USART1, SPI1
PORTB: TIM2_CH1-4 (OUT4-7), I2C1, CAN1
PORTC: TIM3_CH1-4 (OUT8-11), ADC1_IN10-15
PORTD: TIM4_CH1-4 (OUT12-15), USART3, FDCAN1
PORTE: TIM5_CH1-4 (OUT16-19), ADC3_IN
PORTF: TIM8_CH1-4 (OUT20-23), ADC2_IN
PORTG: Digital inputs, Status LEDs
PORTH: HSE, Boot
```

---

### Sheet 3: PROFET Outputs (profet_outputs.kicad_sch)

**Component per channel (x15 dual = 30 outputs):**
| Ref | Part | Package | Description |
|-----|------|---------|-------------|
| U20-U34 | BTS7008-2EPA | PG-TSDSO-14 | Dual PROFET |
| R20-R49 | 1K | 0402 | IS sense resistor |
| C20-C34 | 100nF | 0603 | Decoupling |

**PROFET Pin Connections:**
```
IN0, IN1:  MCU PWM outputs (TIM channels)
DEN:       MCU GPIO (diagnostic enable)
IS:        ADC input (current sense)
ST:        ADC input (status/temp)
OUT0, OUT1: Load outputs (to DTM connector)
VS:        +12V supply
GND:       Ground
```

**Current Sensing:**
- kILIS ratio: 4700 (typical)
- Sense resistor: 1KΩ
- ADC voltage: (I_load / 4700) × 1000Ω
- Max 40A → 8.5mA IS → 8.5V (needs divider)

---

### Sheet 4: H-Bridge Outputs (hbridge_outputs.kicad_sch)

**Components per bridge (x4):**
| Ref | Part | Package | Description |
|-----|------|---------|-------------|
| U40-U43 | BTN8982TA | TO-263-7 | Half-bridge driver |
| C40-C47 | 100nF | 0805 | Decoupling |
| D40-D47 | SS34 | SMA | Flyback diodes |

**H-Bridge Configuration:**
- 2x BTN8982 per motor (full H-bridge)
- INH: Enable (PWM capable)
- IN: Direction control
- IS: Current sense (kILIS = 8500)
- OUT: Motor connection

---

### Sheet 5: CAN Interfaces (can_interfaces.kicad_sch)

**CAN FD (x2):**
| Ref | Part | Package | Description |
|-----|------|---------|-------------|
| U50, U51 | TJA1463 | SOIC-8 | CAN FD transceiver |
| C50-C53 | 100nF | 0402 | Decoupling |
| R50-R53 | 120Ω | 0603 | Termination (optional) |
| D50-D53 | PESD1CAN | SOT-23 | ESD protection |

**CAN 2.0 (x2):**
| Ref | Part | Package | Description |
|-----|------|---------|-------------|
| U52, U53 | TJA1051 | SOIC-8 | CAN transceiver |
| C54-C57 | 100nF | 0402 | Decoupling |

---

### Sheet 6: Analog Inputs (analog_inputs.kicad_sch)

**Input Protection per channel (x20):**
| Ref | Part | Package | Description |
|-----|------|---------|-------------|
| R60-R79 | 10K | 0402 | Input resistor |
| R80-R99 | 10K | 0402 | Pull-up (optional) |
| C60-C79 | 100nF | 0402 | Filter capacitor |
| D60-D79 | BAV99 | SOT-23 | Clamping diodes |
| Z60-Z79 | 5.1V | SOD-323 | Zener protection |

**Input Types:**
- Voltage: 0-5V (protected)
- NTC: 10K/2.2K with pull-up
- Resistance: 0-10K
- Digital: 0/5V with threshold

---

### Sheet 7: Connectors (connectors.kicad_sch)

**Main Connectors:**
| Ref | Part | Pins | Description |
|-----|------|------|-------------|
| J1 | DTM04-2P | 2 | Power input |
| J2 | DTM04-12PA | 12 | Outputs 1-12 |
| J3 | DTM04-12PA | 12 | Outputs 13-24 |
| J4 | DTM04-6PA | 6 | Outputs 25-30 |
| J5 | DTM04-8PA | 8 | H-Bridge 1-4 |
| J6 | DTM04-12PA | 12 | Analog inputs |
| J7 | DTM04-8PA | 8 | CAN buses |
| J8 | DTM04-4PA | 4 | Digital inputs |
| J9 | USB-C | - | Configuration |

---

## 3. Power Budget

| Rail | Voltage | Max Current | Components |
|------|---------|-------------|------------|
| VBAT | 6-22V | 250A | PROFET, H-Bridge |
| +12V | 12V | 2A | Drivers, sensors |
| +5V | 5V | 1A | CAN, sensors |
| +3.3V | 3.3V | 500mA | MCU, logic |

---

## 4. PCB Stack-up (8-layer)

```
Layer 1: Signal (TOP) - Components, high-speed
Layer 2: Ground plane
Layer 3: Signal - Internal routing
Layer 4: Power plane (+3.3V, +5V)
Layer 5: Power plane (+12V, VBAT)
Layer 6: Signal - Internal routing
Layer 7: Ground plane
Layer 8: Signal (BOT) - Power components
```

**Copper weights:**
- Layers 1, 8: 3oz (105µm) - Power paths
- Layers 2-7: 1oz (35µm) - Signal/planes

---

## 5. Design Rules

| Parameter | Value | Notes |
|-----------|-------|-------|
| Min track width | 0.15mm | Signal |
| Min clearance | 0.15mm | Signal |
| Power track width | 2.5-6mm | 10-40A |
| Via drill | 0.3mm | Standard |
| Via pad | 0.6mm | Standard |
| Power via drill | 0.8mm | High current |
| Power via pad | 1.5mm | High current |

---

## 6. BOM Key Components

| Qty | Part Number | Manufacturer | Description |
|-----|-------------|--------------|-------------|
| 1 | STM32H743VIT6 | ST | MCU |
| 15 | BTS7008-2EPA | Infineon | Dual PROFET |
| 8 | BTN8982TA | Infineon | Half H-Bridge |
| 2 | TJA1463 | NXP | CAN FD transceiver |
| 2 | TJA1051 | NXP | CAN transceiver |
| 2 | TPS54360B | TI | 60V Buck converter |
| 1 | W25Q512JV | Winbond | 512Mb SPI Flash |
| 1 | LSM6DSO | ST | IMU (accel+gyro) |
| 1 | ESP32-C3-MINI | Espressif | WiFi/BT module |

---

## 7. Next Steps

1. [ ] Create symbol library for custom parts
2. [ ] Create footprint library
3. [ ] Complete power input schematic
4. [ ] Complete MCU core schematic
5. [ ] Complete PROFET section
6. [ ] Complete H-Bridge section
7. [ ] Complete CAN interfaces
8. [ ] Complete analog inputs
9. [ ] Complete connectors
10. [ ] Design review
11. [ ] PCB layout
12. [ ] Gerber generation

---

**Document Version:** 1.0
**Last Updated:** December 2024
