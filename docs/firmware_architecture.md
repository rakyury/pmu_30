# PMU-30 Firmware Architecture

**Document Version:** 1.0
**Date:** 2025-12-21
**Target Platform:** STM32H743/H753
**Owner:** R2 m-sport
**Confidentiality:** Proprietary - Internal Use Only

---

**© 2025 R2 m-sport. All rights reserved.**

---

## 1. Overview

### 1.1 Purpose
This document describes the firmware architecture for the PMU-30 power distribution module.

### 1.2 Development Environment
- **IDE**: VSCode with PlatformIO
- **Framework**: STM32 HAL/LL + FreeRTOS
- **Language**: C (C11 standard)
- **Build System**: PlatformIO (CMake-based)
- **Debugger**: ST-Link V3 or J-Link

### 1.3 Key Requirements
- Real-time operation (RTOS-based)
- Deterministic 1kHz control loop
- Safety-critical protection systems
- Low latency communication
- Robust error handling
- Field-upgradeable (OTA)

---

## 2. System Architecture

See full document for complete architecture details including:
- Layered architecture diagram
- Module hierarchy
- Task architecture (FreeRTOS)
- Core subsystems
- Communication interfaces
- Configuration management
- Boot sequence
- Safety and fault handling
- Memory map
- Performance targets

---

**End of Firmware Architecture Document**
