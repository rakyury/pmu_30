# CAN Monitor

The CAN Monitor provides real-time CAN bus traffic viewing, message decoding, and manual message transmission.

## Overview

This widget displays live CAN bus traffic with automatic message decoding based on configured CAN channels.

## Main Layout

```
+----------------------------------------------------------+
| Toolbar: [Pause] [Clear] [Filter: ____] [Configured ☑]   |
+----------------------------------------------------------+
|                                                          |
|  Message Stream Table                                    |
|  Time    | Dir | ID     | Name        | DLC | Data       |
|  0.000   | RX  | 0x100  | Engine_Msg  | 8   | 00 12 34.. |
|  0.010   | TX  | 0x200  | Dash_Msg    | 8   | FF 00 00.. |
|                                                          |
+----------------------------------------------------------+
|  Decoded Values Panel                                    |
|  Engine_RPM: 3500 | Coolant_Temp: 85°C | TPS: 45%       |
+----------------------------------------------------------+
|  Send Message Tab                                        |
|  ID: [0x___] DLC: [8] Data: [__ __ __ __ __ __ __ __]   |
|  [Standard ○] [Extended ○]          [Send]               |
+----------------------------------------------------------+
| Status: RX: 1234 | TX: 56 | Errors: 0 | Bus Load: 25%   |
+----------------------------------------------------------+
```

## Message Stream Table

| Column | Width | Description |
|--------|-------|-------------|
| **Time** | 70px | Timestamp since start (seconds) |
| **Dir** | 40px | Direction (RX/TX) |
| **ID** | 70px | Arbitration ID (hex) |
| **Name** | 120px | Configured message name (if known) |
| **DLC** | 40px | Data Length Code (0-8) |
| **Data** | 200px | Data bytes in selected format |

## Toolbar Controls

| Control | Description |
|---------|-------------|
| **Pause/Resume** | Stop/start message display |
| **Clear** | Clear message history |
| **Filter** | Filter by ID or name (text input) |
| **Configured only** | Show only configured messages |
| **Format** | Display format selector |

### Data Format Options

| Format | Example |
|--------|---------|
| **Hex** | `00 12 34 56 78 9A BC DE` |
| **Decimal** | `0 18 52 86 120 154 188 222` |
| **ASCII** | `.4Vx...` (printable chars) |

## Message Colors

| Type | Color | Description |
|------|-------|-------------|
| RX | Green (#22c55e) | Received message |
| TX | Blue (#3b82f6) | Transmitted message |
| Error | Red (#ef4444) | Bus error frame |
| Highlighted | Orange (#f59e0b) | Matched filter |

## Decoded Values Panel

Automatically extracts and displays signals from configured CAN messages:

```
Engine_RPM: 3500 rpm | Coolant_Temp: 85°C | Oil_Pressure: 3.2 bar
Throttle: 45% | Brake_Pressure: 0 bar | Speed: 60 km/h
```

### Signal Decoding

Based on CAN Input channel configuration:
- Start bit and length
- Byte order (Intel/Motorola)
- Scale and offset
- Unit display

## Send Message Panel

Manual message transmission interface:

| Field | Description |
|-------|-------------|
| **ID** | Arbitration ID (hex input) |
| **DLC** | Data Length Code (0-8) |
| **Data** | 8 byte fields (hex) |
| **Frame Type** | Standard (11-bit) or Extended (29-bit) |
| **Send** | Transmit button |

### Send Example

```
ID:   [0x200]
DLC:  [8]
Data: [FF] [00] [55] [AA] [12] [34] [00] [00]
Type: [● Standard] [○ Extended]
                                    [Send]
```

## Status Bar

| Field | Description |
|-------|-------------|
| **RX** | Total messages received |
| **TX** | Total messages transmitted |
| **Errors** | Error frame count |
| **Bus Load** | Percentage of bus utilization |

## Message History

- **Buffer size**: 1000 messages (circular buffer)
- **Oldest messages** automatically removed when full
- **Clear** button resets buffer

## Filtering

### By ID
```
Filter: 0x100
Shows: Only messages with ID 0x100
```

### By Name
```
Filter: Engine
Shows: Messages containing "Engine" in name
```

### By Range
```
Filter: 0x100-0x1FF
Shows: Messages in ID range (not yet implemented)
```

## CAN Bus Selection

If multiple CAN buses available:

```
Bus: [CAN1 ▼]  [CAN2 ▼]  [All ▼]
```

## Update Behavior

- **Refresh rate**: Real-time (as messages arrive)
- **Scroll**: Auto-scroll to newest message
- **Pause**: Stops auto-scroll, allows manual review
- **Resume**: Jumps to latest and resumes auto-scroll

## Signal Connection

```python
# Emitted when user sends a message
send_message(arbitration_id: int, data: bytes, is_extended: bool)
```

## Offline Behavior

When disconnected:
- Message stream frozen
- Send panel disabled
- Status shows "Offline"
- Last values retained

## CAN Message Configuration

Messages are configured via CAN Input/Output dialogs:

### CAN Input (RX)
```json
{
  "name": "Engine_RPM",
  "can_id": "0x100",
  "start_bit": 0,
  "length": 16,
  "byte_order": "intel",
  "scale": 0.25,
  "offset": 0,
  "unit": "rpm"
}
```

### CAN Output (TX)
```json
{
  "name": "Dashboard_Status",
  "can_id": "0x200",
  "cycle_time_ms": 100,
  "signals": [
    {"name": "lights", "start_bit": 0, "length": 8},
    {"name": "wipers", "start_bit": 8, "length": 8}
  ]
}
```

## Styling

```css
Table {
  background: #000000;
  font-family: monospace;
  font-size: 11px;
}

Row.rx {
  color: #22c55e;
}

Row.tx {
  color: #3b82f6;
}

Row.error {
  color: #ef4444;
  background: #1a0000;
}

DecodedPanel {
  background: #1a1a1a;
  border-top: 1px solid #333333;
  padding: 8px;
}

SendPanel {
  background: #0a0a0a;
  border-top: 1px solid #333333;
}
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Space | Pause/Resume |
| Delete | Clear buffer |
| Ctrl+F | Focus filter |
| Escape | Clear filter |
