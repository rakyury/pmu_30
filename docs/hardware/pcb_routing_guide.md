# PMU-30 PCB Routing Guide

## Board Overview

- **Size**: 150mm × 120mm
- **Layers**: 8 (see stack-up below)
- **Copper Weight**: 105μm (3oz) outer layers, 70μm (2oz) planes, 35μm (1oz) signal
- **Min Track/Space**: 0.15mm / 0.15mm (signal), 0.3mm / 0.3mm (power)
- **Via**: 0.3mm drill, 0.6mm pad (signal), 0.5mm drill for power

## Layer Stack-Up (8-Layer)

| Layer  | Function           | Copper | Thickness | Notes                           |
|--------|--------------------|---------|-----------|---------------------------------|
| L1     | Signal + Power     | 105μm   | 105μm     | High-current power, components  |
| PP1    | Prepreg 1080×2     | -       | 200μm     | Dielectric                      |
| L2     | GND Plane          | 70μm    | 70μm      | Solid ground reference          |
| Core1  | FR4                | -       | 200μm     | Core material                   |
| L3     | Signal             | 35μm    | 35μm      | High-speed signals (USB, QSPI)  |
| PP2    | Prepreg 2116       | -       | 120μm     | Dielectric                      |
| L4     | Power (12V)        | 70μm    | 70μm      | Main 12V distribution           |
| Core2  | FR4                | -       | 400μm     | Core material                   |
| L5     | Power (5V/3.3V)    | 70μm    | 70μm      | Logic power planes              |
| PP3    | Prepreg 2116       | -       | 120μm     | Dielectric                      |
| L6     | Signal             | 35μm    | 35μm      | CAN, I2C, SPI routing           |
| Core3  | FR4                | -       | 200μm     | Core material                   |
| L7     | GND Plane          | 70μm    | 70μm      | Return path for signals         |
| PP4    | Prepreg 1080×2     | -       | 200μm     | Dielectric                      |
| L8     | Signal + Power     | 105μm   | 105μm     | Bottom components, power        |
| **Total** |                 |         | **~2.4mm**| Finished board thickness        |

## Power Routing Strategy

### Main Power Bus (40A+)

The main +12V input must handle 40A continuous current.

**Track Width Calculator (105μm/3oz outer copper, 20°C rise):**
- 10A: 2.0mm
- 15A: 3.0mm
- 20A: 4.0mm
- 30A: 8.0mm
- 40A: 12.0mm

**Track Width Calculator (70μm/2oz inner planes, 20°C rise):**
- 5A: 1.5mm
- 10A: 3.0mm
- 20A: 6.0mm

**Routing Rules:**
1. Use polygon pours for main power distribution
2. Multiple vias to inner +12V plane (minimum 10× 0.8mm vias per 10A)
3. Thermal relief for power connections
4. Keep power traces on outer layers where possible

### Input Power Section

```
+12V IN ──────┬──────────────────────────────┬─────────> To PROFET VBB
              │                              │
        [Reverse                        [TVS Diode]
         Protection]                    SMBJ16CA
              │                              │
              └──────────────────────────────┴─────────> GND
```

**Components:**
- Input connector: TE Connectivity 1-1123723-2 (40A rated)
- Reverse protection: MOSFET + gate driver or Schottky
- TVS: SMBJ16CA (clamping at 25.7V)
- Input capacitors: 4× 1000μF 25V electrolytic + 10× 100μF MLCC

### PROFET Power Distribution

Each PROFET BTS7008-2EPA handles 2 channels at 11A each.

```
+12V Plane
    │
    ├──[VIA Array]──> PROFET U1 (Ch 1-2)   ──> Output 1, 2
    │   (8× 0.8mm)
    │
    ├──[VIA Array]──> PROFET U2 (Ch 3-4)   ──> Output 3, 4
    │
    ...
    │
    └──[VIA Array]──> PROFET U15 (Ch 29-30) ──> Output 29, 30
```

**PROFET Routing Rules:**
1. VBB pin: 5mm track minimum, star connection from main bus
2. GND pins: Multiple vias directly to GND plane
3. Output pins: 3mm tracks to output connectors
4. IS (current sense): Keep short, away from power traces
5. DEN/DSEL: 0.2mm tracks, can route on B.Cu

### H-Bridge Power (BTN8982TA)

Each H-Bridge can handle 43A peak, 25A continuous.

```
+12V ────[15mm polygon]───┬──> BTN8982TA U20 (Motor 1)
                          │
                          ├──> BTN8982TA U21 (Motor 2)
                          │
                          ├──> BTN8982TA U22 (Motor 3)
                          │
                          └──> BTN8982TA U23 (Motor 4)
```

**H-Bridge Layout:**
1. Place motor output connectors at board edge
2. Short, wide traces from VS pin to +12V bus
3. Thermal vias under PowerPAD (36 vias minimum)
4. GND connection via PowerPAD to GND plane
5. Bootstrap capacitors close to IC

### Output Connector Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  OUT1  OUT2  OUT3  ... OUT15    OUT16 OUT17 ... OUT30           │
│   ○     ○     ○    ...   ○        ○     ○   ...   ○             │ <- F.Cu
│                                                                  │
│  Motor outputs: M1+ M1- M2+ M2- M3+ M3- M4+ M4-                 │
│                  ○   ○   ○   ○   ○   ○   ○   ○                  │
└─────────────────────────────────────────────────────────────────┘
```

## Signal Routing Strategy

### MCU Section (STM32H743)

**Critical Signals:**
- USB: 90Ω differential, length matched ±0.5mm
- CAN FD: 120Ω differential, 0.3mm tracks
- QSPI Flash: Length matched, max 30mm
- Crystal: Keep traces short (<5mm), ground guard

**Pin Groups:**
```
            ┌─────────────────┐
    USB ────┤ PA11, PA12      │
   CAN1 ────┤ PD0, PD1        │
   CAN2 ────┤ PB12, PB13      │
   CAN3 ────┤ PA15, PB3       │
   CAN4 ────┤ PB5, PB6        │
    SPI ────┤ PA5-PA7, PB4    │
   QSPI ────┤ PB1-2, PE7-10   │
    ADC ────┤ PA0-3, PC0-3    │
            └─────────────────┘
```

### PROFET Control Signals

Each PROFET requires:
- DEN (Enable): Active high
- DSEL (Diagnosis select): Channel select
- IS (Current sense): Analog output

**Routing:**
1. Route DEN/DSEL on B.Cu layer
2. IS signals to dedicated ADC channels
3. Keep IS traces away from PWM/switching noise
4. 0.2mm tracks sufficient for control signals

### CAN Bus Routing

```
MCU ──┬── [CAN Transceiver] ──┬── 120Ω ──┬── Connector
      │    TJA1463            │          │
     TX                      CANH       CAN H
     RX                      CANL       CAN L
```

**Routing Rules:**
1. CANH/CANL as differential pair, 120Ω impedance
2. Keep CAN traces away from power switching
3. ESD protection at connector: PESD2CAN
4. Stub length to transceiver: <25mm

### ADC Input Routing

20 analog inputs for sensors and current sense.

```
Input ──[ESD]──[RC Filter]──[Voltage Divider]──> ADC Pin
         │        │              │
        TVS    100Ω+100nF     10k/10k
```

**Routing Rules:**
1. Star ground for analog section
2. Keep analog traces short
3. Guard traces around sensitive signals
4. Separate analog ground island, single point connection

## Thermal Management

### Power Stage Thermal

PROFET and H-Bridge ICs need thermal vias:

```
     ┌───────────────┐
     │   PROFET IC   │
     │   ┌─────┐     │
     │   │ PAD │     │
     │   │○○○○○│     │ <- Thermal vias (0.3mm)
     │   │○○○○○│     │    Pattern: 5×5 grid
     │   │○○○○○│     │
     │   │○○○○○│     │
     │   │○○○○○│     │
     │   └─────┘     │
     └───────────────┘
           │
           v
    GND Plane (heat spreader)
```

**Thermal Via Rules:**
- Minimum 25 vias per PROFET
- Minimum 36 vias per H-Bridge
- 0.3mm drill, 0.6mm pad
- No thermal relief on thermal pad vias

### Copper Pours (8-Layer Design)

1. **L1 (Top)**: +12V pour around power section, signal routing
2. **L2**: Solid GND plane (max 10% voids for vias)
3. **L3**: Signal routing, minimal pour (QSPI, USB area)
4. **L4**: +12V plane (main power distribution)
5. **L5**: Split plane (5V and 3.3V regions)
6. **L6**: Signal routing, minimal pour (CAN, I2C area)
7. **L7**: Solid GND plane (return path)
8. **L8 (Bottom)**: GND pour in MCU area, +12V pour in power area
9. Keep pours connected with via stitching (every 5mm on GND, every 10mm on power)

## Design Rules Summary

| Parameter            | Value        | Notes                      |
|----------------------|--------------|----------------------------|
| Board Size           | 150×120mm    | 8-layer, 2.4mm thick       |
| Min Track Width      | 0.15mm       | Signal traces (L3, L6)     |
| Power Track Width    | 2-12mm       | Based on current (L1, L8)  |
| Min Clearance        | 0.15mm       | Signal-signal              |
| Power Clearance      | 0.3mm        | Power-signal               |
| Via Drill (Signal)   | 0.3mm        | Pad 0.6mm                  |
| Via Drill (Power)    | 0.5mm        | Pad 0.9mm                  |
| Via Drill (Thermal)  | 0.4mm        | Plugged, under ICs         |
| Via-to-Via           | 0.3mm        | Minimum spacing            |
| Via-to-Trace         | 0.2mm        | Minimum spacing            |
| USB Impedance        | 90Ω ±10%     | Differential pair          |
| CAN Impedance        | 120Ω ±10%    | Differential pair          |
| QSPI Impedance       | 50Ω ±10%     | Single-ended               |

## Routing Checklist

### Phase 1: Power (L1, L4, L8)
- [ ] Main +12V input polygon (L1)
- [ ] Via arrays to L4 (+12V plane)
- [ ] PROFET VBB connections (star topology from L4)
- [ ] H-Bridge VS connections
- [ ] Output connector traces (L1, L8)
- [ ] 5V/3.3V distribution on L5
- [ ] GND via stitching (L2, L7)

### Phase 2: Critical Signals (L3, L6)
- [ ] USB differential pair (L3, 90Ω)
- [ ] CAN FD pairs (L6, 120Ω, 4 buses)
- [ ] QSPI to Flash (L3, length matched)
- [ ] Crystal circuit (L1, short traces)
- [ ] Reset/Boot circuits
- [ ] GPS UART (L6)

### Phase 3: Control Signals (L3, L6, L8)
- [ ] PROFET DEN/DSEL signals
- [ ] H-Bridge control (INH, IS)
- [ ] SPI to ADCs
- [ ] GPIO to LEDs
- [ ] BlinkMarine keypad CAN messages

### Phase 4: Analog (L1, L8)
- [ ] Current sense (IS) signals
- [ ] Analog inputs with filtering
- [ ] Reference voltage distribution
- [ ] Analog ground island
- [ ] GPS antenna feed (50Ω)

### Phase 5: Cleanup
- [ ] Copper pour fill (all layers)
- [ ] Via stitching (GND every 5mm)
- [ ] Silkscreen labels
- [ ] DRC clean (8-layer rules)
- [ ] Impedance verification

## KiCad Commands

```
# Set track widths (8-layer design)
Edit → Track & Via Properties:
  - Signal (L3, L6): 0.15mm
  - Power (L1, L8): 3.0mm
  - High Power: 8.0mm
  - Via (Signal): 0.3mm/0.6mm
  - Via (Power): 0.5mm/0.9mm

# Create differential pairs
Route → Differential Pairs
  - USB_DP/USB_DM: 90Ω (0.15mm trace, 0.15mm gap)
  - CAN_H/CAN_L: 120Ω (0.2mm trace, 0.2mm gap)

# Via stitching
Place → Via → Set Net: GND
  - Spacing: 5mm grid
  - Around power stages: 2mm grid

# Layer assignment
L1/L8: Power, components
L3/L6: High-speed signals
L2/L7: GND planes (solid)
L4: +12V plane
L5: 5V/3.3V split plane
```

## References

- Infineon PROFET Application Note AN: BTS700x-1EPP
- Infineon BTN8982TA Datasheet
- STM32H743 Reference Manual RM0433
- IPC-2221 Generic Standard on PCB Design
