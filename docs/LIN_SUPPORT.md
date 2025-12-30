# PMU-30 LIN Bus Support

**Document Version:** 1.0
**Date:** 2025-12-29
**Status:** Implementation Phase

---

## 1. Overview

The PMU-30 includes a single LIN (Local Interconnect Network) bus interface for communication with LIN-compatible peripherals such as dashboard clusters, climate controls, seat modules, window controllers, and other body electronics.

---

## 2. Hardware Specification

### 2.1 LIN Transceiver

| Parameter | Specification |
|-----------|---------------|
| **Part Number** | TJA1021T/20 |
| **Manufacturer** | NXP Semiconductors |
| **Standard** | LIN 2.2A / ISO 17987 |
| **Package** | SO8 |
| **Supply Voltage** | 5V to 27V (from battery) |
| **Operating Temperature** | -40°C to +150°C |
| **Data Rate** | 1 kbps to 20 kbps |

### 2.2 Electrical Characteristics

| Parameter | Min | Typ | Max | Unit |
|-----------|-----|-----|-----|------|
| Bus Voltage (recessive) | VBAT - 2 | VBAT | VBAT | V |
| Bus Voltage (dominant) | 0 | - | 2.0 | V |
| Slew Rate | - | 2 | - | V/µs |
| Bus Load Capacitance | - | - | 6.8 | nF |
| Maximum Nodes | - | - | 16 | - |

### 2.3 Pin Configuration

| MCU Pin | Function | Description |
|---------|----------|-------------|
| PA2 | USART2_TX | LIN TX (to transceiver TXD) |
| PA3 | USART2_RX | LIN RX (from transceiver RXD) |
| PB12 | GPIO | LIN CS/NSLP (sleep control) |

### 2.4 Circuit Design

```
                    +12V (VBAT)
                      │
                      ├──[1kΩ]──┬── LIN Bus
                      │         │
                 ┌────┴────┐    │
                 │ TJA1021 │    │
    MCU TX ──────┤ TXD  LIN├────┘
    MCU RX ──────┤ RXD     │
       CS ───────┤ NSLP INH├────── Inhibit (optional)
                 │    GND  │
                 └────┬────┘
                      │
                     GND
```

### 2.5 Protection Components

| Component | Value | Function |
|-----------|-------|----------|
| Pull-up Resistor | 1 kΩ (on master) | LIN bus pull-up |
| Series Resistor | 1 kΩ (on slave) | Current limiting |
| TVS Diode | SM712-02HTG | ESD and transient protection |
| Decoupling Cap | 100 nF | Transceiver supply filtering |

### 2.6 Connector

| Parameter | Specification |
|-----------|---------------|
| **Type** | Deutsch DTM04-2P |
| **Pin 1** | LIN Signal |
| **Pin 2** | Ground |
| **Sealing** | IP67 |

---

## 3. Protocol Specification

### 3.1 LIN Frame Structure

```
┌──────────────────────────────────────────────────────────────────┐
│  Break  │  Sync  │   PID    │  Data (1-8 bytes)  │  Checksum   │
│ (13bit) │ (0x55) │ (6+2bit) │                    │  (classic/  │
│  + del  │        │          │                    │  enhanced)  │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 Frame Types

| Type | Description | Direction |
|------|-------------|-----------|
| Unconditional | Regular data frame | Master → Slave or Slave → Master |
| Event-triggered | On-change transmission | Slave → Master |
| Sporadic | Non-periodic data | Master → Slave |
| Diagnostic | 60 (0x3C), 61 (0x3D) | Both directions |

### 3.3 Protected Identifier (PID)

| ID Range | Purpose |
|----------|---------|
| 0x00-0x3B | Signal-carrying frames |
| 0x3C | Master Request (diagnostic) |
| 0x3D | Slave Response (diagnostic) |
| 0x3E-0x3F | Reserved |

### 3.4 Timing Parameters

| Parameter | Value |
|-----------|-------|
| Bit Rate | 19200 baud (default) |
| Break Length | 13 bits minimum |
| Break Delimiter | 1 bit |
| Inter-byte Space | 0-4 bits |
| Response Space | 0-10 bits |
| Frame Slot Max | 100 ms typical |

---

## 4. Software Implementation

### 4.1 LIN Driver Configuration

```c
// LIN configuration structure
typedef struct {
    uint32_t baudrate;          // 1000-20000 bps
    lin_mode_t mode;            // LIN_MODE_MASTER or LIN_MODE_SLAVE
    uint8_t node_address;       // NAD for slave mode (1-126)
    bool auto_checksum;         // Use enhanced checksum
    uint16_t schedule_period;   // Schedule table period (ms)
} lin_config_t;

// Default configuration
static const lin_config_t lin_default_config = {
    .baudrate = 19200,
    .mode = LIN_MODE_MASTER,
    .node_address = 0x01,
    .auto_checksum = true,
    .schedule_period = 10
};
```

### 4.2 LIN API Functions

```c
// Initialize LIN interface
bool lin_init(const lin_config_t* config);

// Send a LIN frame (master mode)
bool lin_send_frame(uint8_t pid, const uint8_t* data, uint8_t length);

// Request data from slave (master mode)
bool lin_request_frame(uint8_t pid, uint8_t* data, uint8_t* length);

// Register response data (slave mode)
bool lin_register_response(uint8_t pid, const uint8_t* data, uint8_t length);

// Set schedule table
bool lin_set_schedule(const lin_schedule_entry_t* schedule, uint8_t count);

// Enable/disable LIN transceiver
void lin_set_power(bool enabled);

// Get LIN bus status
lin_status_t lin_get_status(void);
```

### 4.3 Schedule Table Example

```c
// Example schedule table for dashboard communication
static const lin_schedule_entry_t dashboard_schedule[] = {
    { .pid = 0x10, .type = LIN_UNCONDITIONAL, .period_ms = 50 },   // Output status
    { .pid = 0x11, .type = LIN_UNCONDITIONAL, .period_ms = 100 },  // Current values
    { .pid = 0x12, .type = LIN_UNCONDITIONAL, .period_ms = 100 },  // Temperature
    { .pid = 0x20, .type = LIN_SPORADIC,      .period_ms = 0 },    // Fault codes
    { .pid = 0x3C, .type = LIN_DIAGNOSTIC,    .period_ms = 0 },    // Diagnostics
};

void setup_lin_communication(void) {
    lin_config_t config = {
        .baudrate = 19200,
        .mode = LIN_MODE_MASTER,
        .node_address = 0x01,
        .auto_checksum = true,
        .schedule_period = 10
    };

    lin_init(&config);
    lin_set_schedule(dashboard_schedule, 5);
}
```

### 4.4 LIN Message Handling

```c
// Callback for received LIN frames
void lin_rx_callback(uint8_t pid, const uint8_t* data, uint8_t length) {
    switch (pid) {
        case 0x10:  // Dashboard request
            // Process dashboard command
            break;
        case 0x20:  // Sensor data
            // Update sensor values
            break;
        case 0x3D:  // Slave response
            // Handle diagnostic response
            break;
    }
}

// Register callback
lin_set_rx_callback(lin_rx_callback);
```

---

## 5. Configurator Integration

### 5.1 LIN Channel Configuration

```json
{
  "channel_id": 700,
  "channel_type": "lin_rx",
  "channel_name": "Dashboard Speed Request",
  "enabled": true,
  "frame_id": 16,
  "byte_offset": 0,
  "data_format": "16bit",
  "byte_order": "little_endian",
  "multiplier": 0.1,
  "offset": 0,
  "timeout_ms": 500
}
```

### 5.2 LIN TX Channel

```json
{
  "channel_id": 710,
  "channel_type": "lin_tx",
  "channel_name": "Output Status Report",
  "enabled": true,
  "frame_id": 17,
  "schedule_slot": 0,
  "signals": [
    {
      "byte_offset": 0,
      "data_format": "8bit",
      "source_channel_id": 100
    },
    {
      "byte_offset": 1,
      "data_format": "8bit",
      "source_channel_id": 101
    }
  ]
}
```

### 5.3 LIN Bus Settings

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| enabled | boolean | - | Enable LIN interface |
| mode | string | master, slave | Operating mode |
| baudrate | integer | 1000-20000 | Bit rate in bps |
| node_address | integer | 1-126 | NAD for slave mode |
| checksum_type | string | classic, enhanced | Checksum algorithm |

---

## 6. Use Cases

### 6.1 Dashboard Integration

PMU-30 can communicate with aftermarket dashboards via LIN:

**PMU → Dashboard:**
- Output channel states (on/off, PWM %)
- Current consumption per channel
- Fault status and codes
- Battery voltage
- Board temperature

**Dashboard → PMU:**
- Output control commands
- Configuration changes
- Wake-up trigger

### 6.2 Window/Mirror Control

```
PMU-30 (Master)
    │
    └──LIN──┬── Window Motor Module (Slave NAD=0x10)
            │      └── Position feedback
            │      └── Pinch protection
            │
            ├── Mirror Module (Slave NAD=0x11)
            │      └── Position feedback
            │      └── Heater status
            │
            └── Seat Module (Slave NAD=0x12)
                   └── Position memory
                   └── Heater control
```

### 6.3 Climate Control

```
PMU-30 (Master)
    │
    └──LIN──┬── HVAC Module (Slave)
            │      └── Fan speed
            │      └── Temperature setpoint
            │      └── AC compressor
            │
            └── Temperature Sensors (Slave)
                   └── Cabin temp
                   └── Evaporator temp
```

---

## 7. Diagnostic Features

### 7.1 LIN Diagnostic Protocol

| Frame ID | Direction | Function |
|----------|-----------|----------|
| 0x3C | Master → Slave | Master Request |
| 0x3D | Slave → Master | Slave Response |

### 7.2 Diagnostic Services (ISO 14229 subset)

| SID | Service | Description |
|-----|---------|-------------|
| 0x22 | Read Data By Identifier | Read parameter |
| 0x2E | Write Data By Identifier | Write parameter |
| 0x19 | Read DTC Information | Read fault codes |
| 0x14 | Clear DTC Information | Clear fault codes |
| 0x3E | Tester Present | Keep session alive |

### 7.3 Node Configuration Services

| NAD | SID | Data | Function |
|-----|-----|------|----------|
| Initial | 0xB0 | New NAD | Assign NAD |
| Wildcard | 0xB1 | - | Read NAD |
| Specific | 0xB2 | Supplier ID | Conditional change NAD |

---

## 8. Error Handling

### 8.1 LIN Error Types

| Error | Detection | Recovery |
|-------|-----------|----------|
| No Response | Timeout | Retry + fault flag |
| Checksum Error | CRC mismatch | Discard + retry |
| Framing Error | Break/sync issue | Resync on next break |
| Bus Stuck | Recessive timeout | Transceiver reset |

### 8.2 Error Reporting

```c
typedef enum {
    LIN_ERR_NONE = 0,
    LIN_ERR_NO_RESPONSE,
    LIN_ERR_CHECKSUM,
    LIN_ERR_SYNC,
    LIN_ERR_PARITY,
    LIN_ERR_BUS_STUCK,
    LIN_ERR_TIMEOUT
} lin_error_t;

// Get last error
lin_error_t lin_get_last_error(void);

// Get error count per slave
uint16_t lin_get_error_count(uint8_t slave_nad);
```

---

## 9. Power Management

### 9.1 Sleep Mode

The TJA1021 supports LIN wake-up:

```c
// Enter sleep mode
void lin_enter_sleep(void) {
    GPIO_WritePin(LIN_NSLP_PIN, 0);  // Pull NSLP low
}

// Wake-up is automatic via LIN dominant pulse
// Or manual:
void lin_wake(void) {
    GPIO_WritePin(LIN_NSLP_PIN, 1);  // Pull NSLP high
    delay_us(100);                    // Wait for transceiver
}
```

### 9.2 Wake-up Sources

| Source | Description |
|--------|-------------|
| LIN Bus | Dominant pulse from master or slave |
| MCU | Software-initiated via NSLP pin |
| INH Pin | External inhibit signal |

---

## 10. PCB Layout Guidelines

### 10.1 Component Placement

- Place transceiver close to connector
- Keep LIN trace short (<50mm to connector)
- Separate from high-current traces

### 10.2 Routing

| Parameter | Requirement |
|-----------|-------------|
| Trace Width | 0.3mm minimum |
| Impedance | Not critical (low speed) |
| Ground Return | Direct path to transceiver GND |

### 10.3 EMC Considerations

- Series resistor (1kΩ) on slave nodes
- Common mode choke optional
- TVS diode close to connector
- Shielded cable recommended for >2m

---

## 11. Testing

### 11.1 Loopback Test

```c
// Self-test with internal loopback
bool lin_self_test(void) {
    uint8_t test_data[] = {0x55, 0xAA, 0x12, 0x34};
    uint8_t rx_data[4];
    uint8_t rx_len;

    // Enable loopback mode
    lin_set_loopback(true);

    // Send and receive
    lin_send_frame(0x10, test_data, 4);
    lin_request_frame(0x10, rx_data, &rx_len);

    // Compare
    return (memcmp(test_data, rx_data, 4) == 0);
}
```

### 11.2 Bus Analyzer

Recommended tools for LIN debugging:
- Peak PLIN-USB
- Kvaser Leaf Light v2
- Vector VN1630
- intrepidcs ValueCAN

---

## 12. Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-29 | Initial release |

---

## See Also

- [BOM Specification](BOM_SPECIFICATION.md) - LIN transceiver components
- [Technical Specification](technical_specification.md) - Full hardware specification
- [Protocol Specification](../protocol_specification.md) - Communication protocols

---

**END OF DOCUMENT**

*R2 m-sport - Proprietary Information*
