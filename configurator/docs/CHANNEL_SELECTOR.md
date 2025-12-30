# Channel Selector Implementation Guide

## Overview

The Channel Selector dialog allows users to select channels from the system. It displays channels with their names and numeric IDs, and supports both user-created channels and system channels.

## Channel Data Structure

### User Channels
- `channel_id` (int): Numeric ID (1-999 for user channels)
- `channel_name` (str): User-friendly name (e.g., "FuelLevel", "Ignition")
- `units` (str): Optional unit of measurement
- `decimal_places` (int): Optional decimal precision

### System Channels
- `channel_id` (int): Numeric ID (1000+ for system channels)
- Display name is the string ID (e.g., "pmu.batteryVoltage", "pmu.o1.current")

## Display Format

In the Channel Selector tree/list:
```
{display_name}  [#{channel_id}]  ({units}, .{decimal_places})
```

Examples:
- User channel: `FuelLevel  [#45]  (L, .1)`
- System channel: `pmu.batteryVoltage  [#1000]`
- Output sub-channel: `pmu.o1.current  [#1130]`

## Selection Flow

### When User Selects a Channel:
1. Dialog stores `channel_id` (int) in item's UserRole data
2. `get_selected_channel()` returns the numeric `channel_id`
3. Parent dialog receives `channel_id`

### Display in Parent Dialog Input Field:
1. Parent dialog receives `channel_id` from selector
2. **MUST lookup `channel_name` by `channel_id`** for display
3. Show `channel_name` in the input field (user-friendly)
4. Store `channel_id` internally for saving to config

### Saving to Config:
1. Use `channel_id` (int) when saving to JSON config
2. Never save the display name - always save numeric ID

## Lookup Functions

### IMPORTANT: Display Name Resolution

When a channel is selected from the Channel Selector:
1. `get_selected_channel()` returns `channel_id` (numeric int)
2. Parent dialog MUST resolve `channel_id` → `display_name` for user-friendly display
3. This applies to **BOTH user channels AND system channels**

**Problem scenario:**
- User selects system channel `pmu.status` (channel_id=1007)
- If display shows `#1007` instead of `pmu.status` — this is a BUG
- Must lookup the string name from the system channel table

## IMPORTANT: Dynamic System Channel Loading (Architecture)

### Core Principle

**System channels are known ONLY to the firmware.** The configurator must:

1. **Load on connection**: Request list of available system channels from firmware
2. **Store in lookup table**: Cache in memory for fast lookup
3. **Use everywhere**: Display in Channel Selectors, Monitors, Variables Inspector
4. **Support firmware updates**: New variables can be added without changing configurator

### Dynamic Loading Flow

```
[Configurator] --connect--> [Firmware/Emulator]
[Configurator] --request_system_channels--> [Firmware]
[Firmware] --system_channels_response--> [Configurator]
[Configurator] stores channels in SystemChannelRegistry
[UI components] lookup names via SystemChannelRegistry.get_name(channel_id)
```

### SystemChannelRegistry (TODO - Future Implementation)

```python
class SystemChannelRegistry:
    """Central registry for system channel name lookup.

    Loads from firmware on connection, falls back to hardcoded list.
    """
    _channels: Dict[int, Tuple[str, str]] = {}  # {channel_id: (string_name, description)}
    _loaded: bool = False

    @classmethod
    def load_from_firmware(cls, comm_manager):
        """Load system channels from connected firmware."""
        response = comm_manager.request_system_channels()
        if response:
            cls._channels = {ch['id']: (ch['name'], ch['desc']) for ch in response}
            cls._loaded = True

    @classmethod
    def get_name(cls, channel_id: int) -> Optional[str]:
        """Get display name for system channel."""
        if cls._loaded and channel_id in cls._channels:
            return cls._channels[channel_id][0]
        # Fallback to hardcoded list
        return ChannelSelectorDialog.get_system_channel_name(channel_id)

    @classmethod
    def get_all_channels(cls) -> List[Tuple[int, str, str]]:
        """Get all system channels for populating selectors."""
        if cls._loaded:
            return [(k, v[0], v[1]) for k, v in cls._channels.items()]
        return ChannelSelectorDialog.SYSTEM_CHANNELS
```

### Integration Points

1. **Connection**: Call `SystemChannelRegistry.load_from_firmware()` after successful connection
2. **Channel Selector**: Use `SystemChannelRegistry.get_all_channels()` to populate "System" category
3. **Dialogs**: Use `SystemChannelRegistry.get_name(channel_id)` for display name lookup
4. **Monitors**: Use registry for telemetry channel name display

### Current Implementation (Hardcoded Fallback)

Until dynamic loading is implemented, system channels are hardcoded in `ChannelSelectorDialog.SYSTEM_CHANNELS`:
```python
SYSTEM_CHANNELS = [
    (1000, "pmu.batteryVoltage", "Battery Voltage (mV)"),
    (1001, "pmu.totalCurrent", "Total Current (mA)"),
    # ... etc
    (1007, "pmu.status", "System Status"),
]
```

Format: `(channel_id: int, string_name: str, display_name: str)`
- `channel_id` — unique numeric ID (used in config JSON)
- `string_name` — firmware string ID (e.g., "pmu.status") — **this is what to display**
- `display_name` — human-readable description

### Get channel_name from channel_id:
```python
def _get_channel_display_name(self, channel_id: int) -> str:
    """Lookup display name by numeric channel_id.

    For user channels: returns channel_name from available_channels
    For system channels: returns string_name from SYSTEM_CHANNELS table
    """
    if channel_id is None:
        return ""

    # 1. Check user channels in available_channels
    for category, channels in self.available_channels.items():
        for ch in channels:
            if isinstance(ch, tuple) and len(ch) >= 2:
                if ch[0] == channel_id:
                    return str(ch[1])

    # 2. Check system channels (ID >= 1000 or hardware channels)
    from ui.dialogs.channel_selector_dialog import ChannelSelectorDialog
    system_name = ChannelSelectorDialog.get_system_channel_name(channel_id)
    if system_name:
        return system_name

    # 3. Fallback
    return f"#{channel_id}"
```

### Static System Channel Resolver (in ChannelSelectorDialog):
```python
@staticmethod
def get_system_channel_name(channel_id: int) -> Optional[str]:
    """Get string_name for a system channel by its numeric ID.

    Returns:
        String name (e.g., "pmu.status") or None if not a system channel
    """
    # Check predefined system channels
    for ch_id, str_name, display_name in ChannelSelectorDialog.SYSTEM_CHANNELS:
        if ch_id == channel_id:
            return str_name

    # Check hardware channels by ID ranges
    if 1220 <= channel_id <= 1239:  # Analog voltage
        idx = channel_id - 1220 + 1
        return f"pmu.a{idx}.voltage"
    if 0 <= channel_id <= 19:  # Digital inputs
        return f"pmu.d{channel_id + 1}.state"
    # ... output sub-channels, etc.

    return None
```

## Launching Emulator + Configurator

### Config Files

| File | Description |
|------|-------------|
| `releases/last_config.json` | **Default full config** (~40KB) - use this as reference |
| `firmware/last_config.json` | Config loaded by emulator at startup |
| `last_config.json` (root) | Working config saved by configurator |

### Correct Launch Procedure

**Important:** The emulator must be launched from the `firmware/` directory to load the correct config.

**Step 1: Copy the default config (if needed)**
```bash
cp "c:/Projects/pmu_30/releases/last_config.json" "c:/Projects/pmu_30/firmware/last_config.json"
```

**Step 2: Launch emulator from firmware directory**
```bash
cd c:/Projects/pmu_30/firmware && start "" ".pio/build/pmu30_emulator/program.exe"
```

**Step 3: Launch configurator**
```bash
cd c:/Projects/pmu_30/configurator && start pythonw src/main.py
```

### One-liner (after config is in place)
```bash
cd c:/Projects/pmu_30/firmware && start "" ".pio/build/pmu30_emulator/program.exe" && sleep 2 && cd c:/Projects/pmu_30/configurator && start pythonw src/main.py
```

### Full reset with default config
```bash
taskkill /F /IM program.exe 2>/dev/null
taskkill /F /IM pythonw.exe 2>/dev/null
cp "c:/Projects/pmu_30/releases/last_config.json" "c:/Projects/pmu_30/firmware/last_config.json"
cd c:/Projects/pmu_30/firmware && start "" ".pio/build/pmu30_emulator/program.exe"
sleep 2
cd c:/Projects/pmu_30/configurator && start pythonw src/main.py
```

## Channel ID Ranges (from pmu_channel.h)

| Range | Type |
|-------|------|
| 0-99 | Physical inputs |
| 100-199 | Physical outputs |
| 200-999 | Virtual/user channels |
| 1000-1023 | System channels |
| 1100-1129 | Output status |
| 1130-1159 | Output current |
| 1160-1189 | Output voltage |
| 1190-1219 | Output active |
| 1220-1239 | Analog voltage |
| 1250-1279 | Output duty cycle |
