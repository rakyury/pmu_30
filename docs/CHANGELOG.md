# Changelog

All notable changes to PMU-30 will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Ecumaster PMU comparison documentation
- Ecumaster compatibility tasks tracking
- Documentation cleanup and consolidation

### Changed
- Consolidated roadmap documentation
- Removed duplicate planning documents

### Removed
- `SYNCHRONIZATION_PLAN.md` (superseded)
- `PROJECT_ACTION_PLAN.md` (too verbose, generic)
- `PROJECT_DEVELOPMENT_ROADMAP.md` (duplicate)
- `DOCUMENTATION_UPDATE_PLAN.md` (superseded)
- `docs/DEVELOPMENT_PLAN.md` (duplicate)
- `docs/IMPROVEMENT_PLAN.md` (superseded by ECUMASTER_COMPARISON)

---

## [0.2.1] - 2025-12-25

### Added
- **Logic Operations**: Full implementation of all logic operations in firmware:
  - Basic: IS_TRUE, IS_FALSE, AND, OR, XOR, NOT, NAND, NOR
  - Comparison: EQUAL, NOT_EQUAL, LESS, GREATER, LESS_EQUAL, GREATER_EQUAL
  - Range: IN_RANGE (lower <= value <= upper)
  - Stateful: HYSTERESIS, SET_RESET_LATCH, TOGGLE, FLASH, PULSE, CHANGED
  - Edge detection: EDGE_RISING, EDGE_FALLING (one-shot pulse on transitions)

### Changed
- **Channel references**: Now use numeric channel_id instead of string names
- **Comparison constants**: Removed x1000 scaling - constants are now in same units as channel values
- **Timer elapsed**: Now outputs raw milliseconds (was incorrectly outputting seconds)

### Fixed
- Logic functions (IS_TRUE, IS_GREATER, etc.) not working with timer channels
- Timer elapsed channel comparison with constants
- Channel selector returning correct IDs for firmware

---

## [0.2.0] - 2025-12-22

### Added
- **Channel Refactoring**: GPIO → Channel terminology migration
  - `channel.py` - New unified channel model
  - `base_channel_dialog.py` - Renamed base dialog class
  - Numeric channel ID system (0-1023)

### Changed
- All dialogs updated to use channel_type instead of gpio_type
- Firmware parses channel_type with gpio_type fallback
- Project tree uses ChannelType enum

---

## [0.1.0] - 2025-12-XX

### Added
- Initial development release
- 30 PROFET power outputs with protection (emulator)
- 4 dual H-bridge outputs
- 20 analog inputs (10-bit ADC)
- 8 digital inputs with configurable pull-up/down
- 4 CAN buses (2x CAN FD, 2x CAN 2.0)
- Unified Channel System
- Logic Functions at 500Hz
- PID controllers with anti-windup
- Lookup tables (1D and 2D)
- Modern dock-based UI (Professional)
- Classic tab-based UI
- JSON configuration save/load
- DBC import/export for CAN signals
- Integration tests with emulator

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 0.2.1 | 2025-12-25 | Logic operations, channel fixes |
| 0.2.0 | 2025-12-22 | Channel system refactoring |
| 0.1.0 | 2025-12-XX | Initial development release |

---

## See Also

- [ROADMAP.md](ROADMAP.md)
- [README.md](../README.md)
