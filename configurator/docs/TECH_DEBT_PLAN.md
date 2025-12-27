# PMU-30 Configurator: Technical Debt & Refactoring Plan

> Created: 2025-12-26
> Status: Active
> Priority: High

## Executive Summary

Analysis of 35 dialogs revealed that only 11 inherit from `BaseChannelDialog`. The remaining 24 duplicate channel handling logic. Found 23 TODO comments and significant architectural debt.

**Estimated total effort**: 2-3 weeks of focused refactoring

---

## 🔴 Critical Priority (Blocking Issues)

### 1. Channel Display Name Logic Duplication

| File | Lines | Issue |
|------|-------|-------|
| `base_channel_dialog.py` | 383-431 | Main implementation |
| `blinker_dialog.py` | 321 | Duplicate |
| `hbridge_dialog.py` | 639 | Duplicate |
| `wiper_dialog.py` | 305 | Duplicate |
| `switch_dialog.py` | 151 | Minimal stub |

**Solution**: Create `ChannelDisplayService` in `models/`:

```python
# models/channel_display_service.py
class ChannelDisplayService:
    @staticmethod
    def get_display_name(channel_id: int, available_channels: Dict,
                         system_channels: List = None) -> str:
        """Single implementation of lookup logic"""
```

**Effort**: 1-2 days

---

### 2. Inconsistent Dialog Inheritance

**24 dialogs do NOT inherit from BaseChannelDialog** despite working with channels:

| Dialog | Should Inherit | Reason |
|--------|----------------|--------|
| OutputConfigDialog | ✅ Yes | Manages channel_id, name validation |
| HBridgeDialog | ✅ Yes | 5 channels (source, direction, pwm, position, target) |
| WiperDialog | ✅ Yes | Manages channel_id, config load/save |
| BlinkerDialog | ✅ Yes | Multiple channel browse methods |
| SwitchDialog | ✅ Yes | Channel up/down + validation |
| CANInputDialog | ✅ Yes | channel_name, channel_id auto-generation |
| CANOutputDialog | ✅ Yes | channel_name, channel_id auto-generation |

**Effort**: 3-4 days

---

### 3. DialogFactory Constructor Signature Chaos

Current state in `dialog_factory.py`:

```python
# 5 different signatures for similar dialogs:
OutputConfigDialog(parent, output_config, used_channels, available_channels, existing_channels)
HBridgeDialog(parent, hbridge_config, used_bridges, available_channels, existing_channels)
CANInputDialog(parent, input_config=None, message_ids=None, existing_channel_ids=None)
CANOutputDialog(parent, output_config=None, existing_ids=None, available_channels=None)
WiperDialog(parent, config, used_numbers, available_channels, existing_channels)
```

**Solution**: Standardize signature:

```python
def __init__(self, parent=None,
             config: Optional[Dict[str, Any]] = None,
             available_channels: Optional[Dict[str, List]] = None,
             existing_channels: Optional[List[Dict]] = None,
             **kwargs):  # Type-specific args
```

**Effort**: 2-3 days

---

## 🟠 High Priority (Architectural Issues)

### 4. Transport Layer Duplication

**Two separate transport systems:**

| Path | Status | Description |
|------|--------|-------------|
| `controllers/transport.py` | Legacy | Old implementation |
| `communication/transport_base.py` | New | New abstract base |

**Solution**: Deprecate `controllers/transport.py`, consolidate to `communication/`

**Effort**: 5-7 days

---

### 5. Global State for Channel ID Generation

In `base_channel_dialog.py:26-48`:

```python
_next_user_channel_id = 1  # Global mutable variable!

def get_next_channel_id(existing_channels: List[Dict]) -> int:
    global _next_user_channel_id
    # ...not thread-safe!
```

**Solution**: Move to `ConfigManager` or dedicated service

**Effort**: 1 day

---

### 6. Large Files Violating SRP

| File | Lines | Issue |
|------|-------|-------|
| `main_window_professional.py` | 2100+ | UI + logic + telemetry |
| `config_manager.py` | 800+ | I/O + validation + migration |
| `hbridge_dialog.py` | 900+ | Too many responsibilities |

**Solution**: Split into components:
- `MainWindowUI`, `MainWindowController`, `TelemetryHandler`
- `ConfigLoader`, `ConfigSaver`, `ConfigValidator`, `ConfigMigrator`

**Effort**: 5-8 days

---

## 🟡 Medium Priority (TODO & Missing Features)

### 7. Unimplemented Communication Protocols

| Feature | File | Line | Status |
|---------|------|------|--------|
| Bluetooth discovery | `device_controller.py` | 130 | TODO |
| Bluetooth connect | `transport.py` | 193 | TODO |
| CAN connection | `transport.py` | 219 | TODO |
| Firmware update | `device_controller.py` | 379 | TODO |
| Connection test | `connection_dialog.py` | 267 | TODO |

---

### 8. Live Device Communication

| Feature | File | Line | Issue |
|---------|------|------|-------|
| PID live update | `main_window_professional.py` | 1945 | Logged but not sent |
| PID reset | `main_window_professional.py` | 1957 | Not sent to device |
| CAN message send | `main_window_professional.py` | 1992 | Logged but not sent |
| Lua execution | `main_window_professional.py` | 1968 | Requires PMU_CMD_EXEC_LUA |

---

### 9. Missing Dialog Tests

**Current coverage: ~65% codebase, ~30% dialogs**

| Dialog | Tests | Priority |
|--------|-------|----------|
| CANInputDialog | ❌ None | High |
| CANOutputDialog | ❌ None | High |
| OutputConfigDialog | ❌ None | High |
| WiperDialog | ❌ None | Medium |
| BlinkerDialog | ⚠️ Minimal | Medium |
| SwitchDialog | ❌ None | Medium |
| Table2D/3DDialog | ❌ None | Low |
| FilterDialog | ❌ None | Low |
| PIDControllerDialog | ❌ None | Low |

**Effort**: 5-8 days

---

## 🟢 Low Priority (Improvements)

### 10. UI/Monitoring Widgets

| Feature | File | Description |
|---------|------|-------------|
| Output status widgets | `monitoring_tab.py:60` | Visualize 30 outputs |
| Device polling | `monitoring_tab.py:99` | `update_values()` is empty |
| Binary log loading | `data_logger.py:1131` | PLOG format |
| DBC parsing | `can_tab.py:523` | Requires cantools |

---

## 📊 Quality Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Test coverage | ~65% | >85% |
| Dialog test coverage | ~30% | >70% |
| Max cyclomatic complexity | 30+ | <15 |
| Max file size | 2100 lines | <500 lines |
| Type hints | ~50% | >90% |
| Docstrings | ~30% | >80% |

---

## 🗓️ Recommended Work Order

### Phase 1: Quick Wins (1 week)
- [ ] Extract `ChannelDisplayService` (1-2 days)
- [ ] Centralize channel ID generation (1 day)
- [ ] Standardize constructor signatures (2-3 days)

### Phase 2: Testing (1 week)
- [ ] Add tests for CAN dialogs
- [ ] Add tests for OutputConfigDialog
- [ ] Add tests for DialogFactory

### Phase 3: Inheritance Refactoring (2 weeks)
- [ ] Move OutputConfigDialog to BaseChannelDialog
- [ ] Move HBridgeDialog to BaseChannelDialog
- [ ] Move remaining dialogs (Wiper, Blinker, Switch, CAN)

### Phase 4: Architecture (2-3 weeks)
- [ ] Split main_window_professional.py
- [ ] Unify Transport layer
- [ ] Split config_manager.py

---

## Progress Tracking

### Completed
- [x] System channel display name resolution (2025-12-26)
- [x] Added `get_system_channel_name()` to ChannelSelectorDialog
- [x] Fixed all dialogs to show system channel names correctly
- [x] Added 49 tests for channel selection
- [x] Created `ChannelDisplayService` - centralized channel lookup (2025-12-26)
- [x] Created `ChannelIdGenerator` - stateless channel ID generation
- [x] Updated all dialogs to use centralized services
- [x] Removed global mutable state from base_channel_dialog.py
- [x] Added 34 unit tests for services
- [x] Standardized OutputConfigDialog constructor signature (2025-12-27)
- [x] Standardized HBridgeDialog constructor signature (2025-12-27)
- [x] Standardized WiperDialog constructor signature (2025-12-27)
- [x] Standardized BlinkerDialog constructor signature (2025-12-27)
- [x] Added 21 tests for CAN dialogs (2025-12-27)
- [x] Fixed channel ID handling in PID, Table, Number dialogs for Python 3.11 (2025-12-27)
- [x] Added 38 tests for FilterDialog, SwitchDialog, Table2D/3D, PIDControllerDialog (2025-12-27)
- [x] Refactored OutputConfigDialog to inherit from BaseChannelDialog (2025-12-27)
- [x] Refactored HBridgeDialog to inherit from BaseChannelDialog (2025-12-27)
  - Reduced 114 lines of duplicated code
  - Both dialogs now use base class for channel_id, name, enabled
  - HBridgeDialog preserves tabbed UI structure
- [x] Refactored WiperDialog to inherit from BaseChannelDialog (2025-12-27)
- [x] Refactored BlinkerDialog to inherit from BaseChannelDialog (2025-12-27)
- [x] Refactored SwitchDialog to inherit from BaseChannelDialog (2025-12-27)
  - Total ~260 lines of duplicated code removed
  - Fixed BaseChannelDialog to preserve config name when auto-generating

### In Progress
- [x] Phase 1: Quick Wins ✅ COMPLETE
- [x] Phase 2: Testing ✅ COMPLETE (437 UI tests total)
- [x] Phase 3: Inheritance Refactoring ✅ COMPLETE (7/7 dialogs)
- [ ] Phase 4: Architecture improvements (IN PROGRESS)
  - [x] MainWindow uses MainWindowTelemetryMixin inheritance (2025-12-27)
    - Moved _on_telemetry_received, _update_led_indicator, _on_log_received
    - Reduced main_window from 2373 to 2222 lines (-151 lines)
  - [x] MainWindow uses MainWindowDeviceMixin inheritance (2025-12-27)
    - Moved connect_device, disconnect_device, read/write methods
    - Updated DeviceMixin with LED indicator support
    - Reduced main_window from 2222 to 1836 lines (-386 lines)
  - [x] MainWindow uses MainWindowConfigMixin inheritance (2025-12-27)
    - Moved new/open/save configuration methods
    - Moved _load_config_to_ui, _save_config_from_ui, _update_channel_graph
    - Reduced main_window from 1836 to 1574 lines (-262 lines)
    - Total reduction: 2373 → 1574 lines (-33.7%)
  - [ ] MainWindow uses ChannelsMixin

### Next Up
- [ ] Split config_manager.py

### Blocked
- None

---

## References

- [CHANNEL_SELECTOR.md](CHANNEL_SELECTOR.md) - Channel selector architecture
- [REFACTORING_PLAN.md](../REFACTORING_PLAN.md) - Original refactoring notes
