# PMU-30 PCB Routing Guide

## Board Overview

- **Size**: 160mm × 120mm
- **Layers**: 4 (F.Cu / GND / +12V / B.Cu)
- **Copper Weight**: 70μm (2oz) outer layers, 35μm inner
- **Min Track/Space**: 0.2mm / 0.2mm
- **Via**: 0.3mm drill, 0.6mm pad

## Layer Stack-Up

| Layer  | Function       | Copper | Notes                        |
|--------|----------------|--------|------------------------------|
| F.Cu   | Signal + Power | 70μm   | High-current power traces    |
| In1.Cu | GND Plane      | 35μm   | Solid ground reference       |
| In2.Cu | +12V Plane     | 35μm   | Power distribution plane     |
| B.Cu   | Signal + Power | 70μm   | MCU routing, connectors      |

## Power Routing Strategy

### Main Power Bus (40A+)

The main +12V input must handle 40A continuous current.

**Track Width Calculator (70μm copper, 10°C rise):**
- 10A: 3.0mm
- 15A: 5.0mm
- 20A: 7.0mm
- 30A: 12.0mm
- 40A: 18.0mm

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

### Copper Pours

1. Top layer: +12V pour around power section
2. Bottom layer: GND pour, MCU area
3. Keep pours connected with via stitching (every 5mm)

## Design Rules Summary

| Parameter            | Value     | Notes                    |
|----------------------|-----------|--------------------------|
| Min Track Width      | 0.2mm     | Signal traces            |
| Power Track Width    | 3-18mm    | Based on current         |
| Min Clearance        | 0.2mm     | Signal-signal            |
| Power Clearance      | 0.5mm     | Power-signal             |
| Via Drill            | 0.3mm     | Standard via             |
| Via Pad              | 0.6mm     | Standard via             |
| Thermal Via Drill    | 0.3mm     | Under ICs                |
| USB Impedance        | 90Ω       | Differential             |
| CAN Impedance        | 120Ω      | Differential             |

## Routing Checklist

### Phase 1: Power
- [ ] Main +12V input polygon
- [ ] Via arrays to +12V plane
- [ ] PROFET VBB connections (star topology)
- [ ] H-Bridge VS connections
- [ ] Output connector traces
- [ ] GND via stitching

### Phase 2: Critical Signals
- [ ] USB differential pair
- [ ] CAN FD pairs (4 buses)
- [ ] QSPI to Flash
- [ ] Crystal circuit
- [ ] Reset/Boot circuits

### Phase 3: Control Signals
- [ ] PROFET DEN/DSEL signals
- [ ] H-Bridge control (INH, IS)
- [ ] SPI to ADCs
- [ ] GPIO to LEDs

### Phase 4: Analog
- [ ] Current sense (IS) signals
- [ ] Analog inputs with filtering
- [ ] Reference voltage distribution
- [ ] Analog ground island

### Phase 5: Cleanup
- [ ] Copper pour fill
- [ ] Via stitching
- [ ] Silkscreen labels
- [ ] DRC clean

## KiCad Commands

```
# Set track widths
Edit → Track & Via Properties:
  - Signal: 0.2mm
  - Power: 3.0mm
  - High Power: 10.0mm

# Create differential pairs
Route → Differential Pairs
  - USB_DP/USB_DM: 90Ω
  - CAN_H/CAN_L: 120Ω

# Via stitching
Place → Via → Set Net: GND
  - Spacing: 5mm grid
```

## References

- Infineon PROFET Application Note AN: BTS700x-1EPP
- Infineon BTN8982TA Datasheet
- STM32H743 Reference Manual RM0433
- IPC-2221 Generic Standard on PCB Design
