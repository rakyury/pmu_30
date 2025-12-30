# PMU-30 Device Reboot and Configuration Reload

## Overview

This document describes how device reboots work, how configuration is reloaded, and the communication flow between the configurator and the PMU-30 device during restart operations.

## Restart Flow

```
┌─────────────────┐                    ┌─────────────────┐
│   Configurator  │                    │    PMU-30       │
│   Application   │                    │    Device       │
└────────┬────────┘                    └────────┬────────┘
         │                                       │
         │  1. RESTART_DEVICE (0x70)            │
         │──────────────────────────────────────►│
         │                                       │
         │  2. RESTART_ACK (0x71)               │
         │◄──────────────────────────────────────│
         │                                       │
         │     [Connection lost]                 │
         │         ...                           │
         │     [Device rebooting]                │
         │         ...                           │
         │                                       │
         │  3. Auto-reconnect attempts           │
         │──────────────────────────────────────►│
         │                                       │
         │  4. BOOT_COMPLETE (0x72)             │
         │◄──────────────────────────────────────│
         │                                       │
         │  5. GET_CONFIG (0x20)                │
         │──────────────────────────────────────►│
         │                                       │
         │  6. CONFIG_DATA chunks (0x21)        │
         │◄──────────────────────────────────────│
         │                                       │
```

## Protocol Messages

### RESTART_DEVICE (0x70)

Request device restart. Empty payload.

```python
# Using DeviceController
controller.restart_device()
```

**Frame Format:**
```
┌──────┬────────┬───────┬───────┐
│ 0xAA │ 0x0000 │ 0x70  │ CRC16 │
│ 1B   │ 2B     │ 1B    │ 2B    │
└──────┴────────┴───────┴───────┘
```

### RESTART_ACK (0x71)

Acknowledgment from device before restart. Empty payload.

### BOOT_COMPLETE (0x72)

Sent by device after successful initialization. Signals that:
- Device has finished booting
- Configuration has been loaded from flash
- All subsystems are ready
- Telemetry can be subscribed

## Configuration Reload

After a restart, the configurator must reload configuration from the device to ensure synchronization.

### Configuration Storage

```
┌─────────────────────────────────────────────────────┐
│                   PMU-30 Device                      │
├─────────────────────────────────────────────────────┤
│  ┌──────────────┐        ┌──────────────────────┐  │
│  │   RAM        │        │   Flash Storage      │  │
│  │   (Active)   │        │   (Persistent)       │  │
│  │              │◄───────│                      │  │
│  │  - Channels  │ load   │  last_config.json    │  │
│  │  - States    │ on     │  (~32KB max)         │  │
│  │  - Values    │ boot   │                      │  │
│  └──────────────┘        └──────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### Boot Sequence

1. **Power On / Restart**
   - Hardware initialization
   - Peripherals configured
   - CAN buses initialized

2. **Configuration Load**
   - Read JSON from flash storage
   - Parse and validate configuration
   - Initialize channels based on config
   - Apply default states

3. **Subsystem Start**
   - Start control loop (1000 Hz)
   - Start logic evaluation loop (1000 Hz)
   - Enable CAN message processing
   - Start telemetry timer

4. **Boot Complete Signal**
   - Send BOOT_COMPLETE (0x72) message
   - Ready for host commands

## Auto-Reconnect

The DeviceController supports automatic reconnection after connection loss.

### Configuration

```python
controller.set_auto_reconnect(
    enabled=True,           # Enable auto-reconnect
    interval=3.0,           # Seconds between attempts
    max_attempts=10         # Maximum attempts (0 = unlimited)
)
```

### Reconnect Flow

```python
# Signals emitted during reconnection
controller.reconnecting.connect(on_reconnecting)  # (attempt, max_attempts)
controller.reconnect_failed.connect(on_failed)    # All attempts exhausted
controller.connected.connect(on_connected)        # Successful reconnect
```

### Implementation Details

1. **Connection Loss Detection**
   - Socket error in receive loop
   - Send command failure
   - Transport disconnect detected

2. **Reconnect Behavior**
   - User-initiated disconnect: No auto-reconnect
   - Connection lost: Auto-reconnect if enabled
   - Saves last connection config for retry

3. **After Reconnect**
   - Clear protocol buffers
   - Re-subscribe to telemetry
   - Emit `connected` signal

## Configuration Synchronization

### Reading Configuration from Device

```python
# Read configuration after boot/reconnect
config = controller.read_configuration(timeout=5.0)

if config:
    config_manager.load_from_dict(config)
    print("Configuration synchronized")
```

### Handling BOOT_COMPLETE Signal

```python
# Connect to boot_complete signal
controller.boot_complete.connect(on_boot_complete)

def on_boot_complete():
    """Device finished restarting - reload configuration."""
    config = controller.read_configuration()
    if config:
        config_manager.load_from_dict(config)
        # Refresh UI to show new config
        main_window.refresh_project_tree()
```

### Configuration Transfer Protocol

**GET_CONFIG (0x20)**: Request configuration from device

**CONFIG_DATA (0x21)**: Configuration data chunk
```
┌─────────────┬──────────────┬─────────────────┐
│ chunk_index │ total_chunks │ JSON data       │
│ 2 bytes     │ 2 bytes      │ up to 4000 bytes│
└─────────────┴──────────────┴─────────────────┘
```

Multiple chunks are assembled by `ConfigAssembler`:

```python
# Internal assembly process
assembler = ConfigAssembler()
for chunk_idx, total, data in chunks:
    if assembler.add_chunk(chunk_idx, total, data):
        # All chunks received
        config_json = assembler.get_data()
```

## Save to Flash

Configuration changes are held in RAM until explicitly saved to flash.

### SAVE_TO_FLASH (0x24)

Request to save current configuration to flash storage.

```python
success = controller.save_to_flash(timeout=5.0)
if success:
    print("Configuration saved to flash")
```

### FLASH_ACK (0x25)

Acknowledgment of flash save operation.

| Offset | Size   | Field    | Description              |
|--------|--------|----------|--------------------------|
| 0      | 1 byte | success  | 1=success, 0=failure     |

### Write + Save Flow

For persistent configuration changes:

```python
# 1. Upload new configuration to device RAM
success = controller.write_configuration(config)

if success:
    # 2. Save to flash for persistence
    saved = controller.save_to_flash()

    if saved:
        print("Configuration saved permanently")
    else:
        print("Warning: Config in RAM only, will be lost on restart")
```

## Error Handling

### Connection Errors

```python
controller.error.connect(on_error)

def on_error(message: str):
    if "Connection lost" in message:
        # Will auto-reconnect if enabled
        status_bar.showMessage("Connection lost, reconnecting...")
```

### Configuration Errors

| Error Code | Description              | Action                    |
|------------|--------------------------|---------------------------|
| 0x20       | Config parse error       | Check JSON syntax         |
| 0x21       | Config validation error  | Fix validation issues     |
| 0x22       | Config write error       | Check flash health        |

### Timeout Handling

```python
# Timeouts for operations
config = controller.read_configuration(timeout=5.0)   # 5 second timeout
success = controller.write_configuration(config, timeout=10.0)  # 10 seconds
saved = controller.save_to_flash(timeout=5.0)  # 5 seconds
```

## Best Practices

1. **Always reload after BOOT_COMPLETE**
   ```python
   controller.boot_complete.connect(self.reload_configuration)
   ```

2. **Check config before restart**
   ```python
   if config_manager.is_modified():
       if user_confirms("Save changes before restart?"):
           controller.write_configuration(config)
           controller.save_to_flash()
   ```

3. **Handle reconnect gracefully**
   ```python
   def on_connected():
       # Reload config after any reconnection
       config = controller.read_configuration()
       if config:
           config_manager.load_from_dict(config)
   ```

4. **Verify flash save success**
   ```python
   if not controller.save_to_flash():
       QMessageBox.warning(self, "Warning",
           "Failed to save to flash. Changes may be lost on restart.")
   ```

## See Also

- [Protocol Specification](protocol_specification.md) - Full protocol documentation
- [Configuration Schema](configuration_schema.md) - JSON configuration format
- [Telemetry](telemetry.md) - Telemetry streaming
