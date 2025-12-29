# Data Logger

The Data Logger provides multi-channel data recording with real-time graphing, similar to professional ECU data logging software.

## Overview

This widget enables recording of system variables over time for analysis, tuning, and diagnostics.

## Main Layout

```
+------------------------------------------------------------------+
| Toolbar: [Record ●] [Live] [Zoom] [Pan] [Export]  Rate: [100 Hz] |
+------------------------------------------------------------------+
|                                                                  |
|  Graph Display Area (pyqtgraph)                                  |
|  _______________________________________________________________  |
| |                                                               | |
| |   RPM ────────────────────────────────────────               | |
| |   Temp ═══════════════════════════════════                   | |
| |   TPS ─·─·─·─·─·─·─·─·─·─·─·─·─·─·─·─·─·─                    | |
| |                                                               | |
| |_______________________________________________________________| |
|                                                                  |
+------------------------------------------------------------------+
| Channel Selector                    | Statistics                  |
| [☑] Battery Voltage (0-30V)        | Min: 12.1V                  |
| [☑] Board Temp L (-40-125°C)       | Max: 14.2V                  |
| [☐] Total Current (0-200A)         | Avg: 13.5V                  |
| [+] Add Channel                    | Cur: 13.8V                  |
+------------------------------------------------------------------+
| Time Cursor: 00:01:23.456  |  Window: [10s ▼]  |  Samples: 12345 |
+------------------------------------------------------------------+
```

## Toolbar Controls

| Control | Description |
|---------|-------------|
| **Record** | Start/stop data recording |
| **Live** | Toggle live scrolling mode |
| **Zoom** | Enable zoom mode (scroll wheel) |
| **Pan** | Enable pan mode (drag) |
| **Export** | Save data to CSV file |
| **Rate** | Sample rate selector |

### Sample Rates

| Rate | Use Case |
|------|----------|
| 50 Hz | Long-term monitoring |
| 100 Hz | General purpose (default) |
| 200 Hz | Detailed analysis |
| 500 Hz | High-speed events |

## Graph Display

### Features

- **Multiple traces**: Up to 8 channels simultaneously
- **Auto-scaling**: Y-axis adjusts to visible data
- **Color-coded**: Each channel has unique color
- **Grid**: Background grid for reference
- **Cursor**: Vertical line shows current time position

### Graph Colors

| Channel | Color |
|---------|-------|
| Channel 1 | Red (#FF0000) |
| Channel 2 | Green (#00FF00) |
| Channel 3 | Blue (#0000FF) |
| Channel 4 | Yellow (#FFFF00) |
| Channel 5 | Cyan (#00FFFF) |
| Channel 6 | Magenta (#FF00FF) |
| Channel 7 | Orange (#FFA500) |
| Channel 8 | White (#FFFFFF) |

### Axis Labels

- **X-axis**: Time (seconds from start)
- **Y-axis**: Value (scaled per channel)

## Channel Selector

### Default Channels

| Channel | Range | Unit |
|---------|-------|------|
| Battery Voltage | 0-30 | V |
| Board Temp L | -40-125 | °C |
| Board Temp R | -40-125 | °C |
| 5V Output | 0-6 | V |
| 3.3V Output | 0-4 | V |
| Total Current | 0-200 | A |

### Adding Channels

Click **[+] Add Channel** to select from:
- All system variables
- User-defined channels
- CAN signals
- Virtual channels

### Channel Configuration

Each channel has:
- **Enable checkbox**: Show/hide in graph
- **Name**: Display name
- **Range**: Y-axis min/max
- **Unit**: Unit label

## Statistics Panel

Shows statistics for selected channel:

| Stat | Description |
|------|-------------|
| **Min** | Minimum value in visible range |
| **Max** | Maximum value in visible range |
| **Avg** | Average value in visible range |
| **Cur** | Current (latest) value |

## Time Controls

### Time Window

Visible time range selector:

| Option | Duration |
|--------|----------|
| 1s | 1 second |
| 5s | 5 seconds |
| 10s | 10 seconds (default) |
| 30s | 30 seconds |
| 1m | 1 minute |
| 5m | 5 minutes |
| All | Entire recording |

### Time Cursor

- **Click graph**: Move cursor to position
- **Drag cursor**: Scrub through time
- **Shows**: Timestamp and all channel values at cursor

## Recording

### Start Recording

1. Select channels to record
2. Click **Record** button (turns red)
3. Data begins logging to memory

### Stop Recording

1. Click **Record** button again
2. Data preserved for analysis
3. Can export to file

### Recording Status

| Indicator | Meaning |
|-----------|---------|
| ● (red) | Recording active |
| ○ (gray) | Not recording |
| Samples | Total samples recorded |

## Live Mode

When **Live** is enabled:
- Graph auto-scrolls to show newest data
- Time window follows latest samples
- Best for real-time monitoring

When **Live** is disabled:
- Graph stays at current position
- Use Pan/Zoom to navigate
- Best for analyzing recorded data

## Export

### CSV Format

```csv
Time,Battery Voltage,Board Temp L,Total Current
0.000,13.82,45.2,12.5
0.010,13.81,45.2,12.6
0.020,13.83,45.3,12.4
...
```

### Export Options

| Option | Description |
|--------|-------------|
| **All Data** | Export entire recording |
| **Visible** | Export only visible range |
| **Selected** | Export only enabled channels |

## Mouse Interactions

### Zoom Mode

| Action | Effect |
|--------|--------|
| Scroll Up | Zoom in (time axis) |
| Scroll Down | Zoom out (time axis) |
| Ctrl+Scroll | Zoom Y-axis |
| Double-click | Reset zoom |

### Pan Mode

| Action | Effect |
|--------|--------|
| Drag | Move view |
| Right-drag | Reset view |

## Performance

### Optimization Features

- **Downsampling**: Reduces points for large datasets
- **Lazy rendering**: Only draws visible data
- **Buffer management**: Circular buffer for long recordings

### Limits

| Parameter | Limit |
|-----------|-------|
| Max channels | 8 simultaneous |
| Max samples | ~1 million per channel |
| Max duration | ~3 hours at 100 Hz |

## pyqtgraph Requirement

The Data Logger requires pyqtgraph for graphing:

```bash
pip install pyqtgraph
```

If not installed, a placeholder message is shown.

## Use Cases

### Engine Tuning
- Log RPM, TPS, AFR, timing
- Analyze WOT runs
- Compare before/after changes

### Electrical Diagnostics
- Monitor voltage drops
- Track current draw patterns
- Identify intermittent faults

### Temperature Monitoring
- Board temperature under load
- Thermal soak testing
- Cooling system verification

### CAN Signal Analysis
- Decode and log CAN signals
- Correlate with other parameters
- Verify signal timing

## Styling

```css
GraphWidget {
  background: #000000;
}

Grid {
  color: #333333;
}

ChannelSelector {
  background: #1a1a1a;
  border: 1px solid #333333;
}

StatisticsPanel {
  background: #0a0a0a;
  font-family: monospace;
}

Toolbar {
  background: #2d2d2d;
}
```
