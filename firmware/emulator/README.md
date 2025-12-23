# PMU-30 Hardware Emulator

Эмулятор аппаратного обеспечения для PMU-30, позволяющий запускать прошивку на ПК без реального железа.

## Содержание

- [Возможности](#возможности)
- [Сборка и запуск](#сборка-и-запуск)
- [Подключение конфигуратора](#подключение-конфигуратора)
- [Интерактивный режим](#интерактивный-режим)
- [UI визуализация](#ui-визуализация)
- [Lua скрипты](#lua-скрипты)
- [Сценарии тестирования](#сценарии-тестирования)
- [API для программного использования](#api-для-программного-использования)
- [Архитектура](#архитектура)

---

## Возможности

### Эмулируемые компоненты

| Компонент | Описание | API |
|-----------|----------|-----|
| **ADC (20 каналов)** | Аналоговые/цифровые/частотные входы | `PMU_Emu_ADC_*` |
| **CAN шина (4 шины)** | 2x CAN FD + 2x CAN 2.0 | `PMU_Emu_CAN_*` |
| **PROFET (30 выходов)** | Силовые выходы с токовым контролем | `PMU_Emu_PROFET_*` |
| **H-Bridge (4 моста)** | Мотор-контроллеры с PID | `PMU_Emu_HBridge_*` |
| **Protection** | Защита по напряжению/температуре | `PMU_Emu_Protection_*` |
| **TCP Server** | Подключение конфигуратора | Порт `9876` |
| **Console UI** | Визуализация состояния каналов | Команда `ui` |
| **Lua Scripting** | Программируемые тестовые сценарии | `pmu.*` API |

### Ключевые функции

- **Data Injection** - программное задание значений всех входов
- **CAN Frame Injection** - инжекция CAN сообщений с периодическим повторением
- **Fault Injection** - инжекция ошибок для тестирования защиты
- **JSON Scenarios** - загрузка тестовых сценариев из файлов
- **Real-time Simulation** - симуляция моторов и токовых нагрузок
- **Configurator Connection** - полная совместимость с PMU-30 Configurator
- **Lua Scripting** - автоматизация тестов с помощью Lua 5.4

---

## Сборка и запуск

### Требования

- PlatformIO Core
- GCC (Linux/macOS) или MinGW (Windows)
- Lua 5.4 (опционально, для скриптов)

### Установка зависимостей (Linux)

```bash
# Lua для скриптов (опционально)
sudo apt install liblua5.4-dev
```

### Сборка

```bash
cd firmware

# Сборка эмулятора
pio run -e pmu30_emulator

# Запуск
.pio/build/pmu30_emulator/program
```

### Режимы запуска

```bash
# Интерактивный режим (по умолчанию)
./pmu30_emulator

# Запуск сценария
./pmu30_emulator --scenario scenarios/can_test.json

# Headless режим (без консоли, только TCP сервер)
./pmu30_emulator --headless

# Справка
./pmu30_emulator --help
```

---

## Подключение конфигуратора

Эмулятор автоматически запускает TCP сервер на порту **9876**, к которому может подключиться PMU-30 Configurator.

### Шаги подключения

1. **Запустите эмулятор:**
   ```bash
   ./pmu30_emulator
   ```

   В консоли появится сообщение:
   ```
   >>> Configurator can connect to: localhost:9876
   ```

2. **Откройте Configurator:**
   ```bash
   cd configurator
   python launch.py
   ```

3. **В Configurator:**
   - Нажмите **Connect** или **File → Connect**
   - Выберите тип подключения: **Emulator**
   - Host: `localhost`
   - Port: `9876`
   - Нажмите **Check Emulator** (должен показать "ONLINE")
   - Нажмите **Connect**

### Что происходит при подключении

```
╔════════════════════════════════════════════════════════════╗
║          PMU-30 Emulator - Configurator Connected          ║
╚════════════════════════════════════════════════════════════╝

[SRV] Client 0 connected from 127.0.0.1:54321
[SRV] RX msg 0x10, len 0          <- GET_INFO
[SRV] RX msg 0x30, len 2          <- SUBSCRIBE_TELEM
[SRV] Telemetry enabled at 50 Hz
```

### Загрузка конфигурации

Когда вы отправляете конфигурацию из Configurator:

```
╔════════════════════════════════════════════════════════════╗
║          CONFIGURATION LOADED FROM CONFIGURATOR            ║
╠════════════════════════════════════════════════════════════╣
║  Total Channels:    42                                     ║
║  ├─ Digital Inputs: 8                                      ║
║  ├─ Analog Inputs:  12                                     ║
║  ├─ Power Outputs:  15                                     ║
║  ├─ Logic Functions:5                                      ║
║  ├─ CAN RX:         2                                      ║
║  └─ CAN TX:         0                                      ║
║  CAN Messages:      10                                     ║
║  Config saved to:   last_config.json                       ║
╚════════════════════════════════════════════════════════════╝
```

### Удалённое подключение

Эмулятор можно запустить на удалённой машине:

```bash
# На сервере
./pmu30_emulator --headless

# В Configurator
Host: 192.168.1.100
Port: 9876
```

---

## Интерактивный режим

### Полный список команд

```
--- Emulator Commands ---

  ADC Commands:
    adc <ch> <value>      - Set ADC channel (0-19) raw value (0-1023)
    adcv <ch> <voltage>   - Set ADC channel voltage (0.0-3.3V)
    freq <ch> <hz>        - Set frequency input (Hz)

  CAN Commands:
    can <bus> <id> <d0> [d1-d7] - Inject CAN message
    canp <bus> <id> <int> <d0-d7> - Add periodic CAN message
    canoff <bus>          - Set CAN bus offline
    canon <bus>           - Set CAN bus online

  Protection Commands:
    volt <mV>             - Set battery voltage (mV)
    temp <C>              - Set temperature (C)
    fault <flags>         - Inject protection fault
    clear                 - Clear all faults

  PROFET Commands:
    load <ch> <ohm>       - Set PROFET load resistance
    pfault <ch> <flags>   - Inject PROFET fault

  H-Bridge Commands:
    hpos <br> <pos>       - Set H-Bridge position (0-1000)
    hmotor <br> <spd> <i> - Set motor params (speed, inertia)
    hfault <br> <flags>   - Inject H-Bridge fault

  Control Commands:
    pause                 - Pause emulator
    resume                - Resume emulator
    speed <x>             - Set time scale (1.0 = real-time)
    reset                 - Reset emulator
    status                - Print full status
    tick                  - Run single tick

  Scenario Commands:
    load <file>           - Load scenario from JSON file
    save <file>           - Save current state to JSON

  UI Visualization:
    ui                    - Show channel state grid
    ui <ch>               - Show detailed info for channel
    ui on                 - Enable auto visualization
    ui off                - Disable auto visualization

  General:
    help                  - Show this help
    quit / exit           - Exit emulator
```

### Примеры использования

```bash
EMU> adc 0 512
ADC[0] = 512

EMU> adcv 1 2.5
ADC[1] = 2.500V

EMU> volt 14000
Voltage = 14000 mV

EMU> temp 45
Temperature = 45 C

EMU> can 0 0x100 01 02 03 04
CAN[0] TX: ID=0x100, DLC=4

EMU> load 5 4.7
PROFET[5] load = 4.7 ohm

EMU> pfault 0 0x01
PROFET[0] fault: 0x01

EMU> status
--- Emulator Status ---
Time: 12345 ms
Voltage: 14000 mV
Temperature: 45 C
...
```

---

## UI визуализация

Эмулятор поддерживает визуальный мониторинг состояния каналов в консоли.

### Команды UI

| Команда | Описание |
|---------|----------|
| `ui` | Показать сетку состояний всех каналов |
| `ui <ch>` | Детальная информация о канале (0-29) |
| `ui on` | Включить автоматическое обновление |
| `ui off` | Выключить автоматическое обновление |

### Пример: сетка каналов

```
EMU> ui

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Status: RUNNING  |  ON: 5  |  PWM: 2  |  FAULT: 0
┌─────────────────────────────────────────────────────────┐
│                   CHANNEL STATUS                        │
├─────────────────────────────────────────────────────────┤
│  0  1  2  3  4  5  6  7  8  9     │
│  ●  ○  ○  ●  ○  ◐  ○  ○  ○  ●     │
│                                                         │
│ 10 11 12 13 14 15 16 17 18 19     │
│  ○  ○  ●  ○  ○  ○  ○  ○  ○  ○     │
│                                                         │
│ 20 21 22 23 24 25 26 27 28 29     │
│  ○  ○  ○  ○  ◐  ○  ○  ○  ○  ●     │
└─────────────────────────────────────────────────────────┘
  Legend: ○=OFF  ●=ON  ◐=PWM  ●=FAULT
```

### Пример: детали канала

```
EMU> ui 5

═══ Channel 5 Details ═══
  State:       PWM (75.5%)
  Current:     2340 mA
  Temperature: 42 °C
  On time:     15230 ms
  Faults:      0x00 (0 total)
```

### Автоматическое отображение изменений

При изменении состояния канала выводится лог:

```
[OUT 05] OFF → ON
[OUT 12] ON → PWM
[OUT 03] ON → FAULT
```

---

## Lua скрипты

Эмулятор поддерживает Lua 5.4 для автоматизации тестов.

### Доступные функции

```lua
-- Управление выходами
pmu.setOutput(channel, state)         -- 0=OFF, 1=ON
pmu.setOutput(channel, 1, pwm_duty)   -- PWM (0-1000 = 0-100%)

-- Чтение входов
value = pmu.getInput(channel)         -- ADC raw value (0-1023)

-- Управление CAN
pmu.canSend(bus, id, {d0, d1, ...})   -- Отправка CAN сообщения

-- Логирование
pmu.log("message")                    -- Вывод в консоль

-- Пауза
pmu.sleep(ms)                         -- Задержка в миллисекундах
```

### Пример скрипта

```lua
-- test_outputs.lua
-- Тестирование всех выходов

pmu.log("Starting output test...")

for i = 0, 29 do
    pmu.setOutput(i, 1)
    pmu.sleep(100)
    pmu.log("Channel " .. i .. " ON")
end

pmu.sleep(1000)

for i = 0, 29 do
    pmu.setOutput(i, 0)
end

pmu.log("Test complete!")
```

### Пример: PWM тест

```lua
-- pwm_ramp.lua
-- Плавное изменение PWM

local channel = 5

for duty = 0, 1000, 50 do
    pmu.setOutput(channel, 1, duty)
    pmu.log("CH" .. channel .. " PWM: " .. (duty/10) .. "%")
    pmu.sleep(100)
end
```

### Пример: CAN тест

```lua
-- can_test.lua
-- Отправка CAN сообщений

-- Отправляем сообщение на шину 0
pmu.canSend(0, 0x100, {0x01, 0x02, 0x03, 0x04})

-- Читаем аналоговый вход
local adc = pmu.getInput(0)
pmu.log("ADC[0] = " .. adc)

-- Управляем выходом на основе входа
if adc > 512 then
    pmu.setOutput(0, 1)
else
    pmu.setOutput(0, 0)
end
```

---

## Сценарии тестирования

### Формат JSON

```json
{
    "name": "Test Name",
    "description": "Test description",

    "adc": [512, 512, 0, 0, 0, 0, 0, 0, 0, 0,
           0, 0, 0, 0, 0, 0, 0, 0, 0, 0],

    "voltage_mV": 12000,
    "temperature_C": 25,

    "can_messages": [
        {
            "bus": 0,
            "id": "0x100",
            "data": [1, 2, 3, 4, 5, 6, 7, 8],
            "interval_ms": 100
        }
    ],

    "profet_loads": [
        {"channel": 0, "resistance_ohm": 4.7},
        {"channel": 1, "resistance_ohm": 10.0}
    ]
}
```

### Запуск сценария

```bash
./pmu30_emulator --scenario scenarios/basic_test.json
```

---

## API для программного использования

### Инициализация

```c
#include "pmu_emulator.h"

// Инициализация
PMU_Emu_Init();

// Основной цикл
while (running) {
    PMU_Emu_Tick(1);  // 1ms tick
    usleep(1000);
}

// Завершение
PMU_Emu_Deinit();
```

### Инжекция данных

```c
// ADC
PMU_Emu_ADC_SetVoltage(0, 2.5f);     // Канал 0, 2.5V
PMU_Emu_ADC_SetRaw(1, 512);           // Канал 1, raw
PMU_Emu_ADC_SetFrequency(2, 1000);    // Канал 2, 1000 Hz

// CAN
uint8_t data[] = {0x01, 0x02, 0x03, 0x04};
PMU_Emu_CAN_InjectMessage(0, 0x100, data, 4);

// Protection
PMU_Emu_Protection_SetVoltage(12000);
PMU_Emu_Protection_SetTemperature(25);

// Fault injection
PMU_Emu_Protection_InjectFault(0x0001);
PMU_Emu_PROFET_InjectFault(0, 0x01);
```

### Мониторинг

```c
// Callback для CAN TX
void OnCanTx(uint8_t bus, uint32_t id, uint8_t* data, uint8_t len) {
    printf("CAN TX: bus=%d, id=0x%X\n", bus, id);
}
PMU_Emu_CAN_SetTxCallback(OnCanTx);

// Получение состояния
const PMU_Emu_PROFET_Channel_t* ch = PMU_Emu_PROFET_GetState(0);
printf("PROFET[0]: state=%d, current=%d mA\n", ch->state, ch->current_mA);
```

---

## Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                   PMU-30 Configurator                   │
│                    (TCP client)                          │
└──────────────────────────┬──────────────────────────────┘
                           │ TCP:9876
                           ▼
┌─────────────────────────────────────────────────────────┐
│                Protocol Server                           │
│          (emu_protocol_server.c)                         │
├─────────────────────────────────────────────────────────┤
│                Interactive Console                       │
│          (emu_main.c)                                    │
├─────────────────────────────────────────────────────────┤
│                  Console UI                              │
│          (emu_ui.c) - channel visualization              │
├─────────────────────────────────────────────────────────┤
│                  Lua Engine                              │
│          (pmu_lua.c) - scripting                         │
├─────────────────────────────────────────────────────────┤
│                PMU Emulator Core                         │
│          (pmu_emulator.c)                                │
├─────────────────────────────────────────────────────────┤
│                HAL Emulation Layer                       │
│          (stm32_hal_emu.c)                               │
├─────────────────────────────────────────────────────────┤
│                Firmware Sources                          │
│     (pmu_adc.c, pmu_can.c, pmu_profet.c, ...)           │
└─────────────────────────────────────────────────────────┘
```

### Протокол коммуникации

| Код | Сообщение | Описание |
|-----|-----------|----------|
| 0x01 | PING | Проверка связи |
| 0x02 | PONG | Ответ на PING |
| 0x10 | GET_INFO | Запрос информации об устройстве |
| 0x11 | INFO_RESP | Ответ с информацией |
| 0x20 | GET_CONFIG | Запрос конфигурации |
| 0x21 | CONFIG_DATA | Данные конфигурации |
| 0x22 | SET_CONFIG | Установка конфигурации |
| 0x23 | CONFIG_ACK | Подтверждение |
| 0x30 | SUBSCRIBE_TELEM | Подписка на телеметрию |
| 0x31 | UNSUBSCRIBE_TELEM | Отписка от телеметрии |
| 0x32 | TELEMETRY_DATA | Данные телеметрии |
| 0x40 | SET_CHANNEL | Установка значения канала |
| 0x41 | CHANNEL_ACK | Подтверждение |
| 0x50 | ERROR | Ошибка |

---

## Ограничения

- FreeRTOS не эмулируется (single-threaded)
- Timing не гарантирован (зависит от хост-системы)
- SPI диагностика возвращает заглушки
- Нет эмуляции флэш-памяти

---

## Лицензия

Copyright (c) 2025 R2 m-sport. All rights reserved.
