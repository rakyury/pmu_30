# Deployment Guide

**Version:** 1.0
**Date:** December 2024

---

## 1. Pre-Installation Checklist

### 1.1 Hardware Requirements

- [ ] Battery voltage: 9-18V DC
- [ ] Main power wire: 4 AWG minimum
- [ ] Ground wire: 4 AWG minimum
- [ ] Fuse: 250A ANL recommended
- [ ] Mounting location: dry, ventilated

### 1.2 Tools Required

- Deutsch DTM crimping tool
- Wire stripper (16-22 AWG)
- Heat gun for shrink tubing
- Multimeter
- Torque wrench

### 1.3 Software Required

- PMU-30 Configurator
- USB drivers (Windows/Mac)
- Configuration backup

---

## 2. Physical Installation

### 2.1 Mounting

**Location Requirements:**
- Away from heat sources
- Protected from water spray
- Good airflow for cooling
- Accessible for maintenance

**Mounting Specifications:**
- 4x M5 mounting holes
- Torque: 3.5 Nm
- Use vibration-dampening mounts in high-vibration environments

### 2.2 Thermal Considerations

| Current Draw | Cooling Required |
|-------------|-----------------|
| 0-100A | Passive (natural airflow) |
| 100-150A | Directed airflow |
| 150-200A | Active cooling fan |

**Heat Dissipation:**
- Mount with fins facing up when possible
- Allow 20mm clearance around enclosure
- Consider thermal pad to chassis

---

## 3. Electrical Installation

### 3.1 Power Connections

```
                    250A ANL
BATTERY (+) --------[FUSE]-------- PMU PWR+
    |
    |  4 AWG min
    |
BATTERY (-) ---------------------- PMU GND
                    (Multiple points)
```

**Power Wire Specifications:**
| Total Load | Wire Gauge | Fuse Size |
|------------|------------|-----------|
| Up to 100A | 4 AWG | 150A |
| Up to 150A | 2 AWG | 200A |
| Up to 200A | 1/0 AWG | 250A |

### 3.2 Output Wiring

**Wire Gauge by Current:**
| Max Current | Wire Gauge |
|-------------|------------|
| Up to 10A | 18 AWG |
| Up to 20A | 16 AWG |
| Up to 30A | 14 AWG |
| Up to 40A | 12 AWG |

**Best Practices:**
- Use automotive grade wire (GXL/TXL)
- Add inline fuse near load for long runs
- Label all wires at both ends
- Use split loom or braided sleeve

### 3.3 Ground Distribution

```
PMU GND ----+---- Engine block
            |
            +---- Chassis
            |
            +---- Battery (-)
```

- Use star grounding pattern
- Ground wire same gauge as power
- Clean, paint-free contact points
- Use ring terminals with lockwashers

---

## 4. Connector Pinouts

### 4.1 Main Power (DTM-2)

| Pin | Function | Wire |
|-----|----------|------|
| 1 | PWR+ (Battery) | 4 AWG Red |
| 2 | GND (Battery) | 4 AWG Black |

### 4.2 Outputs A (DTM-12)

| Pin | Channel | Function |
|-----|---------|----------|
| 1 | OUT1 | Output 1 |
| 2 | OUT2 | Output 2 |
| ... | ... | ... |
| 12 | OUT12 | Output 12 |

### 4.3 CAN Bus (DTM-4)

| Pin | Function | Wire Color |
|-----|----------|------------|
| 1 | CAN1-H | Yellow |
| 2 | CAN1-L | Green |
| 3 | CAN2-H | Yellow/Black |
| 4 | CAN2-L | Green/Black |

---

## 5. Initial Configuration

### 5.1 Connect to Configurator

1. Connect USB cable
2. Launch PMU-30 Configurator
3. Select COM port
4. Click "Connect"

### 5.2 Basic Setup Wizard

1. **Device Name**: Enter unique identifier
2. **Battery Type**: Select 12V or 24V
3. **CAN Bitrate**: Match your ECU
4. **Output Names**: Label each channel

### 5.3 Input Configuration

For each input:
1. Set input type (voltage, NTC, digital)
2. Configure scaling if needed
3. Set warning thresholds
4. Name the channel

### 5.4 Output Configuration

For each output:
1. Enable channel
2. Set current limit
3. Configure soft-start
4. Set default state (on/off at boot)

---

## 6. CAN Integration

### 6.1 DBC Import

1. File > Import DBC
2. Select your ECU's DBC file
3. Map signals to channels
4. Verify message IDs

### 6.2 Manual Signal Setup

```json
{
  "rx_messages": [{
    "id": "0x360",
    "signals": [{
      "name": "RPM",
      "start_bit": 0,
      "length": 16,
      "factor": 1.0,
      "channel": 200
    }]
  }]
}
```

### 6.3 Verify Communication

1. Open CAN Monitor
2. Check for incoming messages
3. Verify decoded values
4. Confirm no timeouts

---

## 7. Logic Function Setup

### 7.1 Basic Output Control

```
Function: Fan Control
Type: GREATER
Input A: Channel 200 (Coolant Temp)
Input B: Constant (85°C)
Output: Channel 100 (Radiator Fan)
```

### 7.2 Testing Logic

1. Enable simulation mode
2. Set test input values
3. Verify output response
4. Check timing/delays

---

## 8. Commissioning

### 8.1 Power-On Test

1. Connect battery with outputs disconnected
2. Verify power LED green
3. Check status in configurator
4. Verify battery voltage reading

### 8.2 Output Test (No Load)

1. Enable each output individually
2. Check LED indicates ON
3. Measure voltage at connector
4. Verify no fault conditions

### 8.3 Output Test (With Load)

1. Connect loads one at a time
2. Enable output
3. Verify current reading
4. Check for proper operation
5. Test at full load briefly

### 8.4 Input Verification

1. Apply known input (voltage/temp)
2. Verify reading in configurator
3. Check scaling accuracy
4. Verify thresholds work

### 8.5 CAN Verification

1. Start ECU
2. Verify messages received
3. Check signal values
4. Confirm no timeouts

---

## 9. Final Checks

### 9.1 Pre-Use Checklist

- [ ] All connections secure
- [ ] No chafing on wires
- [ ] Fuses correctly sized
- [ ] Configuration saved
- [ ] Configuration backed up
- [ ] All outputs tested
- [ ] All inputs calibrated
- [ ] CAN communication verified
- [ ] Logic functions tested
- [ ] Fault recovery tested

### 9.2 Save Configuration

1. File > Save Configuration
2. Save to device: Settings > Save to Flash
3. Create backup copy

---

## 10. Production Deployment

### 10.1 Configuration Template

Create master configuration:
1. Set up complete configuration
2. Test thoroughly
3. Export as template
4. Use for identical installations

### 10.2 Batch Programming

```bash
# Command line programming
pmu-config --port COM3 --upload config.json
pmu-config --port COM3 --verify
```

### 10.3 Documentation

For each installation, record:
- Serial number
- Configuration file version
- Installation date
- Wiring diagram
- Test results

---

## 11. Firmware Updates

### 11.1 OTA Update

1. Connect via WiFi
2. Settings > Firmware Update
3. Select firmware file
4. Wait for update complete
5. Device will reboot

### 11.2 USB Update

1. Connect USB
2. Tools > Update Firmware
3. Select firmware file
4. Wait for update
5. Verify version

### 11.3 Post-Update

1. Verify configuration intact
2. Test all outputs
3. Check CAN communication
4. Verify logic functions

---

## See Also

- [Configuration Reference](configuration-reference.md)
- [Troubleshooting Guide](troubleshooting-guide.md)
- [Quick Start Guide](../QUICKSTART.md)

---

**Document Version:** 1.0
**Last Updated:** December 2024
