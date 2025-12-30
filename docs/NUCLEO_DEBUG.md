# PMU-30 Debug Build for Nucleo Boards

Руководство по использованию отладочных сборок PMU-30 на платах STM Nucleo.

## Поддерживаемые платы

| Плата | MCU | Особенности |
|-------|-----|-------------|
| **Nucleo-F446RE** | STM32F446RE (Cortex-M4 @ 180MHz) | CAN 2.0, 6 выходов, 5 ADC, 8 DIN |
| **Nucleo-H743ZI** | STM32H743ZI (Cortex-M7 @ 480MHz) | FDCAN, 30 выходов (стабы), 20 входов |

---

## Nucleo-F446RE

### Сборка и прошивка

```bash
cd firmware

# Сборка
pio run -e nucleo_f446re

# Прошивка
pio run -e nucleo_f446re --target upload

# Мониторинг UART (115200 baud)
pio device monitor -b 115200
```

### Распиновка

```
                    Nucleo-F446RE
                   ┌─────────────┐
                   │   ST-LINK   │
                   │  ┌───────┐  │
                   │  │       │  │
                   │  │ USB   │  │
                   │  │       │  │
                   │  └───────┘  │
              CN7  │             │  CN10
           ───────┤             ├───────
              PC10│             │PB8
              PC12│             │PB9
               VDD│             │AVDD
             BOOT0│             │GND
              NC  │             │PA5  ◄── USER LED (LD2)
              NC  │             │PA6
              PA13│             │PA7
              PA14│             │PB6
              PA15│             │PC7
               GND│             │PA9  ◄── TIM1_CH2 (PWM OUT1)
              PB7 │             │PA8  ◄── TIM1_CH1 (PWM OUT0)
             PC13 ◄── USER BTN  │PB10
              PC14│             │PB4  ◄── TIM3_CH1 (PWM OUT4)
              PC15│             │PB5  ◄── TIM3_CH2 (PWM OUT5)
              PH0 │             │PB3
              PH1 │             │PA10
              VBAT│             │PA2  ◄── USART2 TX (Debug)
              PC2 │             │PA3  ◄── USART2 RX (Debug)
              PC3 │             │GND
           ───────┤             ├───────
              CN8 │             │  CN9
           ───────┤             ├───────
              PA0 ◄── ADC CH0   │PA12 ◄── CAN1 TX
              PA1 ◄── ADC CH1   │PA11 ◄── CAN1 RX
              PA4 ◄── ADC CH2   │PB12
              PB0 ◄── ADC CH3   │NC
              PC1 ◄── ADC CH4   │PB2
              PC0 │             │PB1
           ───────┴─────────────┴───────
```

### Подключение CAN трансивера

CAN трансивер (MCP2551, SN65HVD230 и т.д.) подключается к:

```
     Nucleo                  CAN Transceiver
    ────────                 ───────────────
    PA12 (TX) ─────────────► TXD
    PA11 (RX) ◄───────────── RXD
    3.3V      ─────────────► VCC
    GND       ─────────────► GND
                             CANH ───┬─── CAN Bus H
                             CANL ───┴─── CAN Bus L
```

**Важно:** Терминатор 120 Ом требуется на концах CAN шины.

### Цифровые входы (8 каналов)

| DIN | Пин | Описание |
|-----|-----|----------|
| DIN0 | PC13 | User Button (active-low) |
| DIN1 | PC10 | Digital input |
| DIN2 | PC12 | Digital input |
| DIN3 | PB2 | Digital input |
| DIN4 | PB15 | Digital input |
| DIN5 | PB14 | Digital input |
| DIN6 | PB13 | Digital input |
| DIN7 | PB12 | Digital input |

Все цифровые входы (кроме DIN0) имеют внутренний pull-down. Для активации подать 3.3V.

### Что тестируется на F446RE

| Функционал | Статус | Примечания |
|------------|--------|------------|
| ✅ Config parsing | Работает | JSON парсинг через cJSON |
| ✅ Channel abstraction | Работает | 6 симулированных выходов |
| ✅ Logic engine | Работает | Условия, таймеры, логика |
| ✅ CAN RX/TX | Работает | Требует внешний трансивер |
| ✅ CAN Stream | Работает | Телеметрия по CAN |
| ✅ ADC inputs | Работает | 5 каналов (PA0, PA1, PA4, PB0, PC1) |
| ✅ Digital inputs | Работает | 8 каналов (PC13, PC10, PC12, PB2, PB12-15) |
| ✅ PWM outputs | Работает | 6 каналов (TIM1, TIM3) |
| ✅ Debug UART | Работает | 115200 через ST-LINK VCP |
| ✅ Protocol (Serial) | Работает | Подключение конфигуратора |
| ❌ PROFET outputs | Стабы | Нет реального железа |
| ❌ H-Bridge | Стабы | Нет реального железа |
| ❌ Current sensing | Стабы | Возвращает 0 |

### Пример вывода

```
╔═══════════════════════════════════════════════════════════════╗
║       PMU-30 Debug Firmware - Nucleo-F446RE                   ║
║                 R2 m-sport (c) 2025                           ║
╠═══════════════════════════════════════════════════════════════╣
║  MCU:              STM32F446RE @ 180 MHz                      ║
║  Config Parsing:   ENABLED                                    ║
║  Outputs:          6 (PWM on GPIO)                            ║
║  Analog Inputs:    5 (ADC)                                    ║
║  Digital Inputs:   8 (GPIO)                                   ║
║  Logic Engine:     ENABLED                                    ║
║  CAN:              CAN1 (PA11/PA12) @ 500kbit                 ║
║  Debug UART:       USART2 (115200 baud)                       ║
║  Protocol:         UART (Configurator support)               ║
╚═══════════════════════════════════════════════════════════════╝

[INIT] CAN1_Init...
[OK] CAN1 initialized @ 500 kbit/s
[INIT] ADC1_Init...
[OK] ADC1 initialized (5 channels)
[INIT] TIM_PWM_Init...
[OK] PWM timers initialized (6 channels @ 1kHz)
...
[READY] All subsystems initialized. Starting FreeRTOS...

[1] Ticks: 1000 | Logic: 500 | CAN RX: 0 TX: 5
  Outputs:  [0:OFF] [1:OFF] [2:OFF] [3:OFF] [4:OFF] [5:OFF]
  DIN:      [0:0] [1:0] [2:0] [3:0] [4:0] [5:0] [6:0] [7:0]
[2] Ticks: 2000 | Logic: 1000 | CAN RX: 3 TX: 10
  Outputs:  [0:ON] [1:OFF] [2:PWM] [3:OFF] [4:OFF] [5:OFF]
  DIN:      [0:1] [1:0] [2:0] [3:1] [4:0] [5:0] [6:0] [7:0]
```

---

## Nucleo-H743ZI

### Сборка и прошивка

```bash
cd firmware

# Сборка
pio run -e pmu30_nucleo

# Прошивка
pio run -e pmu30_nucleo --target upload

# Мониторинг UART
pio device monitor -b 115200
```

### Распиновка

```
Nucleo-H743ZI LEDs:
  - LD1 (Green)  : PB0
  - LD2 (Yellow) : PE1
  - LD3 (Red)    : PB14

User Button: PC13

Debug UART (USART3): PD8 (TX), PD9 (RX) - через ST-LINK VCP
```

### Что тестируется на H743ZI

| Функционал | Статус |
|------------|--------|
| ✅ Config parsing | Работает |
| ✅ Channels (30) | Стабы |
| ✅ Logic engine | Работает |
| ✅ FDCAN | Работает |
| ✅ LED индикация | 3 LED |
| ❌ PROFET/H-Bridge | Стабы |

---

## Подключение конфигуратора

Nucleo-F446RE поддерживает подключение конфигуратора PMU-30 через Serial (UART).

### Настройка подключения

1. Подключите Nucleo к ПК через USB (ST-LINK)
2. Определите COM порт (например, COM3 или /dev/ttyACM0)
3. Откройте конфигуратор PMU-30
4. Выберите подключение: **Serial**
5. Укажите параметры:
   - **Порт:** COM порт ST-LINK
   - **Скорость:** 115200 baud
   - **Формат:** 8N1

### Протокол

Конфигуратор использует бинарный протокол PMU-30:

| Команда | Код | Описание |
|---------|-----|----------|
| PING | 0x01 | Проверка связи |
| GET_VERSION | 0x02 | Получить версию firmware |
| START_STREAM | 0x20 | Начать телеметрию |
| STOP_STREAM | 0x21 | Остановить телеметрию |
| GET_OUTPUTS | 0x22 | Получить состояния выходов |
| GET_INPUTS | 0x23 | Получить значения входов |
| SET_OUTPUT | 0x40 | Установить состояние выхода |
| SET_PWM | 0x41 | Установить PWM выхода |
| LOAD_CONFIG | 0x60 | Загрузить конфигурацию |

### Формат пакета

```
┌────────┬─────────┬────────┬────────────┬───────┐
│ Marker │ Command │ Length │   Data     │ CRC16 │
│  0xAA  │  1 byte │ 2 bytes│ 0-256 bytes│2 bytes│
└────────┴─────────┴────────┴────────────┴───────┘
```

### Телеметрия

При активном стриме (START_STREAM) устройство передает:
- Состояния 6 выходов
- Значения 5 ADC входов
- Состояния 8 цифровых входов
- Напряжение питания
- Статус защиты

**Важно:** Debug-вывод и протокол используют один UART. При активном подключении конфигуратора debug-сообщения будут смешиваться с протоколом. Конфигуратор игнорирует текстовые сообщения.

---

## Тестовые сценарии

### 1. Тест парсинга конфигурации

1. Подключитесь к Nucleo через Serial Monitor
2. Отправьте JSON конфигурацию через CAN или UART
3. Проверьте вывод:
   ```
   [JSON] Parsing config...
   [JSON] Found 6 channels
   [JSON] Channel 0: type=output, name="Headlights"
   [JSON] Config loaded successfully
   ```

### 2. Тест Logic Engine

Создайте конфигурацию с логическим правилом:
```json
{
  "channels": [
    {"id": 0, "type": "output", "name": "LED1"},
    {"id": 1, "type": "input", "name": "Button", "gpio": "PC13"}
  ],
  "logic": [
    {
      "condition": "input[1] == 1",
      "action": "output[0] = 1"
    }
  ]
}
```

Нажмите USER кнопку и проверьте, что выход активируется.

### 3. Тест CAN коммуникации

1. Подключите CAN анализатор (PCAN, CANalyzer и т.д.)
2. Отправьте CAN сообщение с ID 0x100
3. Проверьте вывод:
   ```
   [CAN RX] ID=0x100, DLC=8, Data=01 02 03 04 05 06 07 08
   ```

4. Проверьте телеметрию:
   ```
   [CAN TX] ID=0x600, DLC=8  <- Ecumaster-compatible frame
   ```

---

## Отладка проблем

### CAN не работает

1. Проверьте подключение трансивера
2. Убедитесь в наличии терминаторов
3. Проверьте скорость CAN (по умолчанию 500 kbit/s)

### Нет вывода в UART

1. Проверьте COM порт ST-LINK
2. Установите скорость 115200 baud
3. Проверьте что выбран правильный порт

### Сборка не проходит

```bash
# Очистить кэш PlatformIO
pio run -e nucleo_f446re --target clean

# Обновить зависимости
pio lib update

# Пересобрать
pio run -e nucleo_f446re
```

---

## Различия между платами

| Параметр | Nucleo-F446RE | Nucleo-H743ZI | PMU-30 |
|----------|---------------|---------------|--------|
| MCU | STM32F446RE | STM32H743ZI | STM32H743VIT6 |
| Частота | 180 MHz | 480 MHz | 480 MHz |
| RAM | 128 KB | 1 MB | 1 MB |
| Flash | 512 KB | 2 MB | 2 MB |
| CAN | CAN 2.0 | FDCAN | 2x FDCAN + 2x CAN |
| Выходы | 6 (PWM) | 30 (стабы) | 30 (PROFET) |
| Входы | 5 (ADC) | 20 (стабы) | 20 (ADC) |
| LED | 1 | 3 | 30 RGB |

---

## Лицензия

Copyright (c) 2025 R2 m-sport. All rights reserved.
