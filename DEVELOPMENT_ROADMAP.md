# PMU-30 Development Roadmap

**Последнее обновление:** 2025-12-26

---

## Текущий статус: v0.2.x

| Компонент | Статус |
|-----------|--------|
| Firmware (эмулятор) | ✅ Работает |
| Configurator | ✅ Работает |
| Integration tests | ✅ 13 файлов |
| Hardware prototype | ⬜ Не начат |

---

## Фаза 1: Ecumaster совместимость (Текущая)

### 1.1 CAN клавиатуры [P1]
- [ ] BlinkMarine PKP-2600/2800 (в процессе)
- [ ] Ecumaster 4/6/8/12 keys
- [ ] MoTeC/RaceGrade keypad
- [ ] Grayhill keypad

### 1.2 Системные функции [P1]
- [ ] Delayed turn off
- [ ] Autosaved channels
- [ ] Увеличить CAN messages до 100

### 1.3 Логические функции UI [P2]

| Категория | Функции | В UI | Статус |
|-----------|---------|------|--------|
| Arithmetic | ADD, SUB, MUL, DIV, MIN, MAX | 4 | ⚠️ Частично |
| Comparisons | EQ, NE, LT, LE, GT, GE, IN_RANGE | 6 | ⚠️ Частично |
| Boolean | AND, OR, XOR, NOT, NAND, NOR | 4 | ⚠️ Частично |
| State | TOGGLE, LATCH, PULSE, DELAY, FLASH | 2 | ⚠️ Частично |
| Data | TABLE_1D, TABLE_2D, HYSTERESIS, FILTER | 0 | ❌ Нет |
| Control | PID, PWM_DUTY, SOFT_START, RAMP | 0 | ❌ Нет |

---

## Фаза 2: Hardware Integration (Q1 2025)

### 2.1 STM32CubeMX [БЛОКИРУЮЩАЯ]
- [ ] Проект для STM32H743VIT6
- [ ] Clock Tree (480 MHz)
- [ ] Замена hal_stubs.c

### 2.2 Драйверы периферии

| Драйвер | Приоритет | Статус |
|---------|----------|--------|
| ADC + DMA | P0 | Заглушки |
| PWM Timers | P0 | Заглушки |
| CAN FD | P0 | Частично |
| SPI Flash | P1 | Заглушки |
| SPI ADC (ADS8688) | P1 | ✅ Готов |
| I2C (IMU, RTC) | P2 | Не начат |

### 2.3 PCB Layout
- [ ] KiCad PCB design
- [ ] Design review
- [ ] Prototype order

---

## Фаза 3: Device Communication (Q1 2025)

### 3.1 USB Protocol
- [ ] Config upload/download
- [ ] Real-time monitoring
- [ ] Firmware update

### 3.2 WiFi (ESP32-C3)
- [ ] WebSocket server
- [ ] REST API
- [ ] mDNS discovery

---

## Фаза 4: Advanced Features (Q2 2025)

### 4.1 Lua Integration
- [ ] Lua 5.4 library
- [ ] 15 API функций
- [ ] Script editor

### 4.2 Data Logging
- [ ] SPI Flash driver (W25Q512JV)
- [ ] Session management
- [ ] 500Hz logging

### 4.3 Protection Enhancement
- [ ] Load shedding
- [ ] DTC система

---

## Фаза 5: Testing (Q2 2025)

### 5.1 Unit Tests
- [ ] Logic functions (64 типа)
- [ ] Channel operations
- [ ] CAN parsing

### 5.2 Hardware Testing
- [ ] Power supply (9-32V)
- [ ] PROFET switching
- [ ] EMC pre-compliance
- [ ] Thermal testing

---

## Метрики

| Метрика | Текущее | Цель |
|---------|---------|------|
| Firmware tests | ~24% | 85% |
| Configurator tests | 28 | 80+ |
| Integration tests | 13 files | 50+ |
| Logic functions UI | ~16 | 64 |

---

## Документация

| Документ | Описание |
|----------|----------|
| [docs/ROADMAP.md](docs/ROADMAP.md) | Версии и релизы |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | История изменений |
| [docs/ECUMASTER_COMPARISON.md](docs/ECUMASTER_COMPARISON.md) | Сравнение с Ecumaster |
| [docs/ECUMASTER_COMPATIBILITY_TASKS.md](docs/ECUMASTER_COMPATIBILITY_TASKS.md) | Задачи совместимости |
| [docs/REFACTORING_AND_TEST_PLAN.md](docs/REFACTORING_AND_TEST_PLAN.md) | План тестирования |

---

*Создано: 2025-12-22 | Обновлено: 2025-12-26*
