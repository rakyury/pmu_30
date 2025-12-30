# Dialog Constructor Patterns

This document describes the standard pattern for creating channel configuration dialogs in the PMU-30 Configurator.

## Base Class: BaseChannelDialog

All channel configuration dialogs inherit from `BaseChannelDialog` which provides:

- **Common UI elements**: Name field, Channel ID display, OK/Cancel buttons
- **Auto-generated channel IDs**: Numeric, unique across all channels
- **Edit mode detection**: Based on presence of valid `channel_id` in config
- **Channel selector helpers**: `_create_channel_selector()`, `_browse_channel()`
- **Validation framework**: `_validate_base()` and `_on_accept()`

## Standard Constructor Signature

All dialogs follow this constructor pattern:

```python
def __init__(self, parent=None,
             config: Optional[Dict[str, Any]] = None,
             available_channels: Optional[Dict[str, List[str]]] = None,
             existing_channels: Optional[List[Dict[str, Any]]] = None):
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `parent` | QWidget | Parent widget for the dialog |
| `config` | Dict[str, Any] | Existing channel configuration (edit mode) or None (new channel) |
| `available_channels` | Dict[str, List[str]] | Map of channel types to available channel names/IDs |
| `existing_channels` | List[Dict[str, Any]] | All existing channels (for name uniqueness validation) |

## Constructor Implementation Pattern

```python
class MyChannelDialog(BaseChannelDialog):
    """Dialog for configuring my channel type"""

    def __init__(self, parent=None,
                 config: Optional[Dict[str, Any]] = None,
                 available_channels: Optional[Dict[str, List[str]]] = None,
                 existing_channels: Optional[List[Dict[str, Any]]] = None):
        # 1. Call super().__init__ with fixed channel_type
        super().__init__(parent, config, available_channels,
                        ChannelType.MY_TYPE, existing_channels)

        # 2. Create type-specific UI groups
        self._create_operation_group()
        self._create_params_group()

        # 3. Connect signals (if any)
        self.operation_combo.currentIndexChanged.connect(self._on_operation_changed)

        # 4. Load config if editing
        if config:
            self._load_specific_config(config)

        # 5. Initialize UI state
        self._on_operation_changed()

        # 6. Finalize UI sizing (ALWAYS call last)
        self._finalize_ui()
```

## Required Method Overrides

### `_validate_specific() -> List[str]`

Return list of validation error messages. Empty list = valid.

```python
def _validate_specific(self) -> List[str]:
    errors = []
    if not self.channel_edit.text().strip():
        errors.append("Channel is required")
    return errors
```

### `get_config() -> Dict[str, Any]`

Return full configuration dictionary including base fields.

```python
def get_config(self) -> Dict[str, Any]:
    config = self.get_base_config()  # Gets channel_id, channel_name, channel_type
    config["operation"] = self.operation_combo.currentData()
    config["channel"] = self._get_channel_id_from_edit(self.channel_edit) or ""
    return config
```

### `_load_specific_config(config: Dict[str, Any])`

Load type-specific fields from config when editing.

```python
def _load_specific_config(self, config: Dict[str, Any]):
    operation = config.get("operation", "default")
    for i in range(self.operation_combo.count()):
        if self.operation_combo.itemData(i) == operation:
            self.operation_combo.setCurrentIndex(i)
            break

    self._set_channel_edit_value(self.channel_edit, config.get("channel"))
```

## Helper Methods from BaseChannelDialog

### Channel Selection

```python
# Create channel selector widget with browse button
widget, edit = self._create_channel_selector("Select channel...")

# Set channel value (handles ID -> display name lookup)
self._set_channel_edit_value(edit, config.get("channel"))

# Get channel ID from edit (returns numeric ID or None)
channel_id = self._get_channel_id_from_edit(edit)
```

### Edge Selection Combo

```python
# Create edge selection combo (Rising/Falling/Both/Level options)
combo = self._create_edge_combo(include_both=True, include_level=False)

# Set/get edge value
self._set_edge_combo_value(combo, "rising")
value = self._get_edge_combo_value(combo)
```

## UI Group Guidelines

1. **Use QGroupBox** for logical groupings of related fields
2. **Use QGridLayout** for compact two-column forms
3. **Use QStackedWidget** for operation-specific parameter panels
4. **Mark required fields** with asterisk in label (e.g., "Channel: *")
5. **Add description labels** in italic gray for additional help

## Examples

- [LogicDialog](logic_dialog.py) - Complex multi-page dialog with stacked widget
- [NumberDialog](number_dialog.py) - Math operations with dynamic pages
- [TimerDialog](timer_dialog.py) - Simple dialog with two groups
- [FilterDialog](filter_dialog.py) - Dialog with preset operations

## Channel ID Generation

Channel IDs are generated using `ChannelIdGenerator` from `models.channel_display_service`:

```python
# Option 1: When you have existing_channels list (e.g., in dialog constructors)
from models.channel_display_service import ChannelIdGenerator
next_id = ChannelIdGenerator.get_next_channel_id(existing_channels)

# Option 2: When you have access to ConfigManager
next_id = config_manager.get_next_channel_id()
```

The ID generator is stateless and fills gaps in the 200-999 user channel range.

## Specialized Dialogs

Some dialogs have specialized requirements and deviate from this pattern:

- **CANInputDialog**: Requires `message_ids` parameter for Link ECU templates
  - Constructor: `(parent, config, available_channels, message_ids, existing_channels)`
  - This dialog is specialized and intentionally differs from the standard pattern
