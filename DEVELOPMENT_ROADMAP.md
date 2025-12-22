# PMU-30 Development Roadmap
## Актуальный план на декабрь 2025

---

## Фаза 1: Критические исправления (1-2 недели)

### 1.1 Синхронизация Configurator ↔ Firmware [КРИТИЧНО]

**Проблема:** Configurator показывает только 16 из 64 логических функций

| Категория | Функции | В UI | Статус |
|-----------|---------|------|--------|
| Arithmetic | ADD, SUB, MUL, DIV, MIN, MAX | 4 | ⚠️ Частично |
| Comparisons | EQ, NE, LT, LE, GT, GE, IN_RANGE, OUT_RANGE | 6 | ⚠️ Частично |
| Bitwise | AND, OR, XOR, NOT, NAND, NOR, LSHIFT, RSHIFT | 0 | ❌ Нет |
| Boolean | AND, OR, XOR, NOT, NAND, NOR, IMPLIES, EQUIV | 4 | ⚠️ Частично |
| State | TOGGLE, LATCH_SR, PULSE, DELAY_ON, DELAY_OFF, FLASHER, TIMER, COUNTER | 2 | ⚠️ Частично |
| Data | TABLE_1D, TABLE_2D, MOVING_AVG, HYSTERESIS, RATE_LIMIT, INTERP_1D, FILTER_LP, FILTER_HP, MEDIAN, KALMAN | 0 | ❌ Нет |
| Control | PID, PI, PWM_DUTY, SOFT_START, RAMP, PROFILE, SCHEDULER, PRIORITY | 0 | ❌ Нет |

**Задачи:**
- [ ] Обновить `logic_function_dialog.py` - добавить все 64 типа функций
- [ ] Объединить PID tab с Logic tab (дублирование)
- [ ] Добавить UI для фильтров (LP, HP, Median, Kalman)
- [ ] Добавить UI для таблиц интерполяции (1D, 2D)
- [ ] Синхронизировать enum значения между firmware и configurator

**Файлы:**
- `configurator/src/ui/dialogs/logic_function_dialog.py`
- `configurator/src/ui/tabs/logic_tab.py`
- `firmware/include/pmu_logic.h`

### 1.2 Валидация конфигурации

- [ ] Проверка границ значений для всех типов каналов
- [ ] Проверка ссылок между каналами (input → logic → output)
- [ ] Обнаружение циклических зависимостей
- [ ] Предупреждения о несовместимых настройках

---

## Фаза 2: Hardware Integration (2-4 недели)

### 2.1 STM32CubeMX конфигурация [БЛОКИРУЮЩАЯ]

**Необходимо сгенерировать:**
```
Периферия STM32H743VIT6:
├── TIM1-TIM4: PWM для PROFET (30 каналов)
├── TIM5-TIM8: PWM для H-Bridge (8 полумостов)
├── ADC1: Channels 0-7 (8 входов)
├── ADC2: Channels 8-13 (6 входов)
├── ADC3: Channels 14-19 (6 входов)
├── FDCAN1: CAN FD Bus 1 (5 Mbps)
├── FDCAN2: CAN FD Bus 2 (5 Mbps)
├── FDCAN3: CAN 2.0 Bus 3 (1 Mbps) - если доступен
├── SPI1: Flash W25Q512JV
├── SPI2: External ADC (ADS8688)
├── USART1: Debug console
├── USART2: ESP32-C3 communication
├── I2C1: IMU, RTC
├── GPIO: LEDs (30 bicolor), buttons, buzzer
└── DMA: ADC, SPI, CAN transfers
```

**Задачи:**
- [ ] Создать проект STM32CubeMX для STM32H743VIT6
- [ ] Настроить Clock Tree (480 MHz, USB 48 MHz)
- [ ] Сгенерировать HAL код
- [ ] Интегрировать в PlatformIO проект
- [ ] Заменить hal_stubs.c реальным кодом

### 2.2 Драйверы периферии

| Драйвер | Приоритет | Сложность | Статус |
|---------|----------|-----------|--------|
| ADC + DMA | P0 | Высокая | Заглушки |
| PWM Timers | P0 | Средняя | Заглушки |
| CAN FD | P0 | Высокая | Частично |
| SPI Flash | P1 | Средняя | Заглушки |
| SPI ADC | P1 | Средняя | ✅ Готов |
| I2C (IMU, RTC) | P2 | Низкая | Не начат |
| UART (ESP32) | P1 | Низкая | Не начат |

### 2.3 KiCad PCB Layout

**Приоритеты layout:**
1. Power distribution (VBAT → DC-DC → rails)
2. MCU placement (центр платы)
3. PROFET размещение (по периметру, теплоотвод)
4. CAN transceivers (близко к разъемам)
5. Analog inputs (изоляция от power)

**Файлы:**
- `hardware/kicad/PMU30/PMU30.kicad_pcb` - создать
- Design rules: 6mil trace, 12mil space (power: 50mil+)
- Stack-up: 8 layers per specification

---

## Фаза 3: Device Communication (2-3 недели)

### 3.1 USB Serial Protocol

**Команды протокола:**
```
READ_CONFIG      0x01  - Прочитать конфигурацию
WRITE_CONFIG     0x02  - Записать конфигурацию
READ_LIVE_DATA   0x03  - Текущие значения каналов
WRITE_OUTPUT     0x04  - Установить выход
FIRMWARE_INFO    0x05  - Версия прошивки
START_LOG        0x10  - Начать запись лога
STOP_LOG         0x11  - Остановить запись
DOWNLOAD_LOG     0x12  - Скачать лог
FIRMWARE_UPDATE  0x20  - Начать обновление
```

**Задачи:**
- [ ] Реализовать `pmu_protocol.c` - firmware side
- [ ] Реализовать `serial_transport.py` - configurator side
- [ ] Добавить CRC проверку пакетов
- [ ] Реализовать timeout и retry логику
- [ ] Тестировать с реальным USB CDC

### 3.2 WiFi Communication (ESP32-C3)

- [ ] Протокол UART между STM32 ↔ ESP32
- [ ] AT commands или custom protocol
- [ ] WebSocket server для real-time данных
- [ ] REST API для конфигурации
- [ ] mDNS для device discovery

### 3.3 Real-time Monitoring

**Связать UI widgets с device:**
- [ ] `analog_monitor.py` → ADC values (20 каналов)
- [ ] `output_monitor.py` → PROFET status (30 каналов)
- [ ] `variables_inspector.py` → CAN signals + Virtual channels

**Частота обновления:**
- ADC/Outputs: 100 Hz (каждые 10 ms)
- CAN signals: по приёму
- Virtual channels: 50 Hz

---

## Фаза 4: Advanced Features (3-4 недели)

### 4.1 Lua Integration [ЗАБЛОКИРОВАНО]

**Зависимость:** Lua 5.4 library в PlatformIO

**Когда разблокируется:**
- [ ] Добавить Lua library в platformio.ini
- [ ] Реализовать 15 API функций в `pmu_lua.c`
- [ ] Memory allocator configuration
- [ ] Script loading from flash
- [ ] Error handling и sandbox

### 4.2 Data Logging

**Flash Storage (W25Q512JV - 64 MB):**
```
Layout:
├── Sector 0-15: Configuration backup (256 KB)
├── Sector 16-31: Firmware backup (256 KB)
├── Sector 32+: Data logs (~63 MB)
    ├── Log Header (4 KB per session)
    ├── Data frames (variable size)
    └── Index table (for fast search)
```

**Задачи:**
- [ ] SPI driver для W25Q512JV
- [ ] Wear leveling алгоритм
- [ ] Session management
- [ ] Data compression (optional)
- [ ] Download protocol

### 4.3 Protection System Enhancement

- [ ] Load shedding priority algorithm
- [ ] Predictive overcurrent detection
- [ ] Temperature derating curves
- [ ] Fault recovery sequences
- [ ] Diagnostic codes (DTC) система

---

## Фаза 5: Testing & Validation (2-3 недели)

### 5.1 Unit Tests

**Firmware:**
- [ ] Logic functions (все 64 типа)
- [ ] Channel operations
- [ ] CAN message parsing
- [ ] Configuration validation

**Configurator:**
- [ ] Расширить существующие 28 тестов
- [ ] Добавить integration tests
- [ ] Communication protocol tests

### 5.2 Hardware Testing

- [ ] Power supply verification (9-32V input)
- [ ] PROFET switching tests (inrush, sustained)
- [ ] H-bridge motor control
- [ ] CAN bus compliance
- [ ] EMC pre-compliance
- [ ] Thermal testing

### 5.3 Integration Testing

- [ ] End-to-end configuration flow
- [ ] Real-time monitoring accuracy
- [ ] Firmware update procedure
- [ ] Fault injection tests
- [ ] Long-term stability (72h burn-in)

---

## Приоритеты по неделям

### Неделя 1-2: Синхронизация
```
[████████░░░░░░░░░░░░] 40%
- Logic function UI (48 типов)
- PID/Logic tab merge
- Validation rules
```

### Неделя 3-4: HAL Integration
```
[░░░░░░░░░░░░░░░░░░░░] 0%
- STM32CubeMX project
- Peripheral drivers
- Replace stubs
```

### Неделя 5-6: Communication
```
[░░░░░░░░░░░░░░░░░░░░] 0%
- USB protocol
- Real-time monitoring
- Config upload/download
```

### Неделя 7-8: Hardware
```
[░░░░░░░░░░░░░░░░░░░░] 0%
- PCB layout
- Gerber generation
- Prototype order
```

### Неделя 9-12: Integration & Testing
```
[░░░░░░░░░░░░░░░░░░░░] 0%
- Hardware bring-up
- Full system test
- Bug fixes
```

---

## Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|------------|---------|-----------|
| STM32 HAL сложности | Высокая | Высокое | Инкрементальная интеграция |
| PCB ошибки | Средняя | Высокое | DRC checks, review |
| Lua memory issues | Средняя | Среднее | Memory pool, limits |
| EMC проблемы | Средняя | Высокое | Proper layout, shielding |
| Component availability | Низкая | Среднее | Alternative parts identified |

---

## Метрики успеха

### Milestone 1 (Неделя 2)
- [ ] Configurator показывает все 64 логические функции
- [ ] Configuration validation работает
- [ ] Unit tests pass

### Milestone 2 (Неделя 4)
- [ ] Firmware компилируется с реальным HAL
- [ ] ADC читает все 20 каналов
- [ ] PWM управляет PROFET

### Milestone 3 (Неделя 6)
- [ ] USB communication работает
- [ ] Real-time monitoring в configurator
- [ ] Configuration upload/download

### Milestone 4 (Неделя 8)
- [ ] PCB layout завершён
- [ ] Prototype заказан
- [ ] DRC errors = 0

### Milestone 5 (Неделя 12)
- [ ] Hardware prototype работает
- [ ] All 30 outputs tested
- [ ] CAN communication verified
- [ ] Ready for field testing

---

## Следующее действие

**Рекомендация:** Начать с Фазы 1.1 - синхронизация логических функций между firmware и configurator.

**Почему:** Это критический разрыв, который блокирует полноценное использование системы. Без UI для 48 функций пользователи не смогут использовать большую часть возможностей PMU-30.

**Конкретные шаги:**
1. Обновить `logic_function_dialog.py` с полным списком функций
2. Добавить UI элементы для параметров каждого типа функции
3. Синхронизировать enum между Python и C

---

*Документ создан: 2025-12-22*
*Последнее обновление: автоматически*
