# PMU-30 Roadmap

**Last Updated:** December 2025

---

## Current Status: v0.2.x Development

Firmware emulator working. Configurator functional. Integration tests passing.

---

## Version 0.2.x (Current)

### Completed
- [x] 30 PROFET outputs with protection (emulator)
- [x] 4 H-bridge motor control
- [x] 20 analog inputs
- [x] 4 CAN buses
- [x] Unified Channel System
- [x] Logic Functions (core operations)
- [x] JSON configuration save/load
- [x] Numeric channel ID system
- [x] Integration tests with emulator

### In Progress
- [ ] BlinkMarine CAN keypad support
- [ ] Full logic function UI
- [ ] PID tuner widget

---

## Version 1.0.0 (Target: Q1 2025)

### Core Features
- [ ] All 64 logic functions in UI
- [ ] Hardware prototype testing
- [ ] Full CAN signal support
- [ ] Data logging (500Hz)
- [ ] Real-time monitoring

### Configurator
- [x] Modern dock-based UI
- [x] Classic tab-based UI
- [x] JSON configuration save/load
- [x] DBC import/export
- [x] Real-time monitoring panels
- [ ] Lua script editor
- [ ] Advanced diagnostics

### Documentation
- [x] Architecture documentation
- [x] API reference
- [x] Getting started guides
- [x] Examples
- [x] Ecumaster comparison

---

## Version 1.1.0 (Planned Q2 2025)

### Enhancements
- [ ] Lua 5.4 scripting engine
- [ ] Custom script library
- [ ] Script editor with syntax highlighting
- [ ] Script debugging tools

### New Features
- [ ] Ecumaster CAN keypad support
- [ ] MoTeC/Grayhill keypad support
- [ ] Delayed turn off
- [ ] Autosaved channels
- [ ] Multiple PMU support (up to 5)

---

## Version 1.2.0 (Planned Q3 2025)

### Features
- [ ] Data logging export (CSV, MoTeC LD)
- [ ] Log analysis tools
- [ ] Session overlay comparison
- [ ] GPS integration support
- [ ] RTC with backup power

### Cloud Integration
- [ ] Remote monitoring via WiFi
- [ ] Cloud backup
- [ ] Configuration sharing

---

## Version 2.0.0 (Future 2026)

### Hardware Revision
- [ ] Increased channel count (40+)
- [ ] Higher current capacity
- [ ] Integrated GPS module
- [ ] CAN FD 8Mbps support

### Software
- [ ] Machine learning fault prediction
- [ ] Adaptive protection thresholds
- [ ] Auto-tuning PID controllers

---

## Priority System

| Priority | Description |
|----------|-------------|
| P0 | Critical - blocks release |
| P1 | High - important feature |
| P2 | Medium - nice to have |
| P3 | Low - future consideration |

---

## Release Schedule

| Version | Target | Status |
|---------|--------|--------|
| 0.2.x | Dec 2024 | Current |
| 1.0.0 | Q1 2025 | In Development |
| 1.1.0 | Q2 2025 | Planned |
| 1.2.0 | Q3 2025 | Planned |
| 2.0.0 | 2026 | Future |

---

## See Also

- [CHANGELOG.md](CHANGELOG.md)
- [ECUMASTER_COMPARISON.md](ECUMASTER_COMPARISON.md)
- [ECUMASTER_COMPATIBILITY_TASKS.md](ECUMASTER_COMPATIBILITY_TASKS.md)
- [REFACTORING_AND_TEST_PLAN.md](REFACTORING_AND_TEST_PLAN.md)
- [README.md](../README.md)
