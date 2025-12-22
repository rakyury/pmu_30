# Changelog

All notable changes to PMU-30 will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Complete documentation suite
- Unified Channel System architecture
- 64 Logic Functions framework
- Testing documentation

### Changed
- Updated README with documentation links

### Fixed
- None

---

## [1.0.0] - 2024-12-XX

### Added
- Initial release
- 30 PROFET power outputs (40A continuous each)
- 4 dual H-bridge outputs (30A each)
- 20 analog inputs (10-bit ADC)
- 8 digital inputs with configurable pull-up/down
- 4 CAN buses (2x CAN FD, 2x CAN 2.0)
- Unified Channel System (1024 channels)
- 64 Logic Functions at 500Hz
- PID controllers with anti-windup
- Lookup tables (1D and 2D)
- WiFi Access Point mode
- Bluetooth Low Energy
- USB-C configuration
- Web interface
- 500Hz data logging to 512MB storage
- Real-time clock with battery backup
- 3-axis accelerometer + gyroscope
- Per-channel current monitoring
- Over-current, over-temperature protection
- Soft-start functionality
- DBC import/export for CAN signals

### Hardware
- STM32H743VIT6 (480MHz Cortex-M7)
- PROFET 2 high-side switches
- BTN8982 H-bridge drivers
- TJA1463 CAN FD transceivers
- 8-layer PCB, 3oz copper
- CNC aluminum enclosure
- Deutsch DTM connectors
- IP67 rated

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | 2024-12-XX | Initial release |

---

## Migration Guides

### Migrating from 0.x to 1.0

No migration required - initial release.

---

## See Also

- [ROADMAP.md](ROADMAP.md)
- [README.md](../README.md)
