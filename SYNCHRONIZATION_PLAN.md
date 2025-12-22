# PMU-30 Synchronization Plan: Firmware ↔ Configurator

## Current Status Analysis

### What IS Synchronized

| Component | Firmware | Configurator | Status |
|-----------|----------|--------------|--------|
| **PROFET Outputs** | 30 channels, PWM, protection | Full support | **SYNCHRONIZED** |
| **H-Bridge** | 4 bridges, Park for Wipers | Full support | **SYNCHRONIZED** |
| **ADC Inputs** | 20 channels, 6 types | Full support | **SYNCHRONIZED** |
| **CAN Bus** | 2x FD + 2x 2.0, DBC | Full support | **SYNCHRONIZED** |
| **JSON Config** | Load/save | Full support | **SYNCHRONIZED** |
| **Protocol** | Binary protocol | Full support | **SYNCHRONIZED** |
| **Channel Architecture** | Unified channels | Unified channels | **SYNCHRONIZED** |

### What is NOT Synchronized

| Component | Firmware | Configurator | Issue |
|-----------|----------|--------------|-------|
| **Logic Functions** | **64 function types** | **Only 16 types** | **CRITICAL** |
| **PID Controllers** | Built into Logic | Separate tab | Duplication |
| **Lua Scripting** | Lua 5.4 + API | Basic editor | No syntax highlight, debugging |
| **Virtual Channels** | Channel Abstraction | Simplified model | Incomplete |
| **Filters** | 5 filter types | No support | Missing |
| **Tables** | 1D/2D with interpolation | No support | Missing |

---

## Action Plan (in priority order)

### STAGE 1: Critical Logic Functions Sync

#### 1.1 Update Logic Function Dialog - **CRITICAL**

**Problem:**
- Configurator supports only 16 operations
- Firmware has 64 function types

**Tasks:**

**Add missing function types (48 types):**

**Mathematical operations (add 4):**
```python
"Math Min", "Math Max", "Math Average", "Math Abs",
"Math Scale", "Math Clamp"
```

**Comparisons (add 3):**
```python
"Compare >=", "Compare <=", "Compare !=", "In Range"
```

**Filters (add 5):**
```python
"Filter Moving Average", "Filter Low-Pass",
"Filter Min Window", "Filter Max Window", "Filter Median"
```

**Controllers (add 4):**
```python
"PID Controller", "Hysteresis", "Rate Limiter", "Debounce"
```

**Tables (add 2):**
```python
"Table 1D Lookup", "Table 2D Map"
```

**Special (add 3):**
```python
"Multiplexer", "Demultiplexer", "Conditional"
```

**Files to modify:**
- `configurator/src/ui/dialogs/logic_function_dialog.py`
- `configurator/src/ui/tabs/logic_tab.py`
- `configurator/src/models/config_schema.py`

**Priority:** CRITICAL

---

#### 1.2 Merge PID Tab with Logic Tab

**Problem:**
- PID controllers duplicated in two places
- In firmware, PID is a type of logic function

**Solution:**
1. **Remove** `configurator/src/ui/tabs/pid_tab.py`
2. **Integrate** PID as function type in Logic Tab
3. **Migrate** existing configurations

**Files:**
- Remove: `configurator/src/ui/tabs/pid_tab.py`
- Remove: `configurator/src/ui/dialogs/pid_controller_dialog.py`
- Update: `configurator/src/ui/main.py` (remove PID tab)
- Update: `configurator/src/ui/main_professional.py`

**Priority:** MEDIUM

---

### STAGE 2: Lua Scripting Enhancement

#### 2.1 Advanced Lua Editor

**Current state:**
- Basic text editor
- No syntax highlighting
- No API auto-completion

**Requirements:**

**Must-have features:**
1. **Syntax Highlighting** (Lua syntax)
   - Keywords
   - Strings, numbers, comments
   - PMU API functions

2. **Auto-completion**
   ```lua
   channel.  → [get, set, find, info, list]
   logic.    → [add, pid, hysteresis, ...]
   system.   → [voltage, current, temperature, uptime]
   ```

3. **API Reference Panel**
   - Built-in documentation
   - Usage examples
   - Quick function search

4. **Error Checking**
   - Syntax errors
   - Unknown API functions
   - Incorrect arguments

5. **Example Templates**
   - Launch Control
   - Traction Control
   - Boost Control
   - Progressive Nitrous
   - Intelligent Cooling

**Files:**
- `configurator/src/ui/tabs/lua_tab.py` - full rework
- Create: `configurator/src/ui/widgets/lua_editor.py`
- Create: `configurator/src/ui/widgets/lua_api_reference.py`

**Priority:** MEDIUM

---

#### 2.2 Lua Examples Library

**Create examples library:**

```
configurator/examples/lua/
├── basic/
│   ├── hello_world.lua
│   ├── simple_logic.lua
│   └── channel_access.lua
├── racing/
│   ├── launch_control.lua
│   ├── traction_control.lua
│   ├── boost_control.lua
│   ├── progressive_nitrous.lua
│   └── rpm_limiter.lua
├── automotive/
│   ├── intelligent_cooling.lua
│   ├── wiper_park.lua
│   ├── headlight_delay.lua
│   └── window_one_touch.lua
└── advanced/
    ├── can_processing.lua
    ├── state_machine.lua
    └── data_logger.lua
```

**Priority:** LOW

---

### STAGE 3: Models and Schema Sync

#### 3.1 Update PMU Config Model

**Problem:**
- `configurator/src/models/pmu_config.py` is almost empty
- No complete configuration model

**Solution:**
Create complete configuration model with all 64 function types.

**Files:**
- `configurator/src/models/pmu_config.py` - full rework
- `configurator/src/models/config_manager.py` - update for new model

**Priority:** MEDIUM

---

#### 3.2 Update JSON Schema

**Sync schema with firmware:**

**Files:**
- `configurator/src/models/config_schema.py`

**Add validation for:**
- All 64 logic function types
- PID, Hysteresis, Filters parameters
- 1D/2D tables
- Lua scripts

**Priority:** MEDIUM

---

### STAGE 4: UI/UX Improvements

#### 4.1 Logic Functions Visual Editor

**Create visual logic editor:**

**Node-based editor (like Unreal Engine Blueprints):**

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│ INPUT       │         │ LOGIC        │         │ OUTPUT      │
│             │         │              │         │             │
│ Throttle ───┼────────→│  ADD         │────────→│ Virtual_Sum │
│             │         │              │         │             │
│ Brake    ───┼────────→│              │         │             │
└─────────────┘         └──────────────┘         └─────────────┘
```

**Drag & Drop:**
- Drag inputs/outputs
- Connect with lines
- Group functions

**Live Preview:**
- Show current values on nodes
- Highlight active paths
- Error indicators

**Technology:**
- PyQt6 Graphics View Framework
- Or JavaScript library integration (vis.js, joint.js)

**Files:**
- Create: `configurator/src/ui/widgets/logic_visual_editor.py`
- `configurator/src/ui/tabs/logic_tab.py` - add mode switching

**Priority:** OPTIONAL (Nice to have)

---

#### 4.2 Channel Name Auto-completion

**Problem:**
- Channel names/numbers must be entered manually

**Solution:**
- Dropdown with auto-completion
- Filter by type (Input/Output/Virtual)
- Show current channel value

**Files:**
- Create: `configurator/src/ui/widgets/channel_autocomplete.py`
- Update all dialogs with channel selection

**Priority:** MEDIUM

---

### STAGE 5: Testing and Validation

#### 5.1 Unit Tests

**Create tests for:**
- Configuration model (PMUConfig)
- JSON parsing/serialization
- Schema validation
- Format conversion

**Files:**
- `configurator/tests/test_models.py`
- `configurator/tests/test_json_config.py`
- `configurator/tests/test_schema_validation.py`

**Priority:** MEDIUM

---

#### 5.2 Integration Tests

**Full cycle tests:**
1. Create configuration in GUI
2. Export to JSON
3. Load in firmware (simulator)
4. Verify function execution

**Files:**
- `configurator/tests/test_integration.py`
- `firmware/tests/test_json_import.c`

**Priority:** MEDIUM

---

## Priorities Summary

### CRITICAL Priority (Must Have)
1. **Logic Functions Sync (64 types)**
2. **JSON Schema Update**
3. **PMU Config Model**

### MEDIUM Priority (Should Have)
4. **Merge PID Tab with Logic**
5. **Lua Editor improvements**
6. **Channel Auto-completion**
7. **Unit Tests**

### LOW Priority (Nice to Have)
8. **Lua Examples Library**
9. **Integration Tests**

### OPTIONAL (Future)
10. **Visual Logic Editor**
11. **Advanced monitoring**

---

## Success Criteria

### Quantitative
- **64/64 function types** supported in GUI
- **100% JSON compatibility** firmware ↔ configurator
- **80%+ code coverage** with tests

### Qualitative
- User can create **any logic function** from GUI
- Configuration loads in firmware **without errors**
- **No programming required** for basic tasks

---

## Completed Tasks

### GPIO → Channel Terminology Refactoring (2025-12-22)

The following refactoring has been completed:

**Python Configurator:**
- `channel.py` - New unified channel model (replaces gpio.py)
- `base_channel_dialog.py` - Renamed base dialog class
- All dialog files - Updated imports
- `config_manager.py` - Updated to use channel_type
- `config_schema.py` - Uses channel_type field
- `project_tree.py` - Uses ChannelType enum
- `main_window_professional.py` - Uses ChannelType

**Firmware (C):**
- `pmu_config.h` - PMU_ChannelType_t enum (with GPIO backward compat)
- `pmu_config_json.c` - Parses channel_type with gpio_type fallback
- `pmu_config_json.h` - Updated documentation
- `config_examples.json` - Uses channel_type field

---

**Document created:** 2025-12-21
**Last updated:** 2025-12-22
**Version:** 1.1
**Project:** PMU-30 Racing Controller
