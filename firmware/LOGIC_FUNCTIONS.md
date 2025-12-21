# PMU-30 Logic Functions & Lua Scripting

**Version**: 1.0
**Author**: R2 m-sport
**Date**: 2025-12-21

---

## Overview

Система логических функций PMU-30 предоставляет мощные инструменты для создания сложной логики управления без необходимости перекомпиляции прошивки. Поддерживаются два подхода:

1. **C API** - регистрация логических функций в коде прошивки
2. **Lua Scripting** - динамическое создание логики через скрипты

Обе системы работают через **универсальную абстракцию каналов**, что обеспечивает единообразный доступ ко всем входам и выходам.

---

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                     Physical Layer                          │
│  ADC    PROFET    H-Bridge    CAN    Flash    Sensors       │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────┴──────────────────────────────────────────┐
│            Universal Channel Abstraction                     │
│  PMU_Channel_GetValue() / PMU_Channel_SetValue()           │
└──────────────────┬──────────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
┌───────┴─────────┐  ┌────────┴──────────┐
│ Logic Functions │  │   Lua Scripting    │
│   (C API)       │  │   (Dynamic)        │
└─────────────────┘  └───────────────────┘
```

---

## Типы логических функций

### Математические операции (0x00-0x1F)

| Функция | Описание | Пример |
|---------|----------|--------|
| **ADD** | Сложение двух входов | `output = A + B` |
| **SUBTRACT** | Вычитание | `output = A - B` |
| **MULTIPLY** | Умножение (fixed-point) | `output = (A * B) / 1000` |
| **DIVIDE** | Деление | `output = (A * 1000) / B` |
| **MIN** | Минимум из N входов | `output = min(A, B, C, ...)` |
| **MAX** | Максимум из N входов | `output = max(A, B, C, ...)` |
| **AVERAGE** | Среднее значение | `output = (A + B + ...) / N` |
| **ABS** | Абсолютное значение | `output = |A|` |
| **SCALE** | Масштабирование | `output = (A * scale) + offset` |
| **CLAMP** | Ограничение диапазона | `output = clamp(A, min, max)` |

### Операции сравнения (0x20-0x3F)

| Функция | Описание | Результат |
|---------|----------|-----------|
| **GREATER** | A > B | 1 или 0 |
| **LESS** | A < B | 1 или 0 |
| **EQUAL** | A == B | 1 или 0 |
| **NOT_EQUAL** | A != B | 1 или 0 |
| **GREATER_EQUAL** | A >= B | 1 или 0 |
| **LESS_EQUAL** | A <= B | 1 или 0 |
| **IN_RANGE** | min <= A <= max | 1 или 0 |

### Логические операции (0x40-0x5F)

| Функция | Описание | Пример |
|---------|----------|--------|
| **AND** | Логическое И | Все входы != 0 |
| **OR** | Логическое ИЛИ | Хотя бы один вход != 0 |
| **NOT** | Логическое НЕ | Инверсия входа |
| **XOR** | Исключающее ИЛИ | Нечетное число ненулевых входов |
| **NAND** | НЕ-И | Инверсия AND |
| **NOR** | НЕ-ИЛИ | Инверсия OR |

### Таблицы (0x60-0x7F)

| Функция | Описание | Применение |
|---------|----------|------------|
| **TABLE_1D** | 1D lookup с линейной интерполяцией | Кривая дросселя, температурная компенсация |
| **TABLE_2D** | 2D lookup (карта) | Калибровочные карты, VE table |

### Фильтры (0x80-0x9F)

| Функция | Описание | Применение |
|---------|----------|------------|
| **MOVING_AVG** | Скользящее среднее | Подавление шума |
| **MIN_WINDOW** | Минимум за окно времени | Детектирование просадок |
| **MAX_WINDOW** | Максимум за окно времени | Детектирование пиков |
| **MEDIAN** | Медианный фильтр | Удаление выбросов |
| **LOW_PASS** | Низкочастотный фильтр (RC) | Сглаживание сигналов |

### Управление (0xA0-0xBF)

| Функция | Описание | Параметры |
|---------|----------|-----------|
| **PID** | PID-регулятор | Kp, Ki, Kd, setpoint |
| **HYSTERESIS** | Гистерезис (триггер Шмитта) | threshold_on, threshold_off |
| **RATE_LIMIT** | Ограничитель скорости изменения | max_rate |
| **DEBOUNCE** | Подавление дребезга | debounce_ms |

---

## C API

### Инициализация

```c
#include "pmu_logic_functions.h"
#include "pmu_channel.h"

// Инициализация модуля
PMU_LogicFunctions_Init();
```

### Создание функций

#### Простые математические операции

```c
// Пример: Сложить два датчика давления
uint16_t brake_front = 0;   // Канал переднего тормоза
uint16_t brake_rear = 1;    // Канал заднего тормоза
uint16_t brake_total = 200; // Виртуальный канал суммы

uint16_t func_id = PMU_LogicFunctions_CreateMath(
    PMU_FUNC_ADD,       // Тип операции
    brake_total,        // Выходной канал
    brake_front,        // Вход A
    brake_rear          // Вход B
);
```

#### PID контроллер

```c
// Пример: Управление бустом через PID
uint16_t boost_sensor = 5;    // Датчик давления
uint16_t wastegate = 105;     // PWM выход wastegate

uint16_t pid_id = PMU_LogicFunctions_CreatePID(
    wastegate,          // Выходной канал
    boost_sensor,       // Измеряемая величина (PV)
    1500,               // Уставка (1.5 bar = 1500 mbar)
    2.0f,               // Kp (пропорциональный коэффициент)
    0.5f,               // Ki (интегральный коэффициент)
    0.1f                // Kd (дифференциальный коэффициент)
);
```

#### Гистерезис (вентилятор охлаждения)

```c
// Пример: Вентилятор с гистерезисом
uint16_t temp_sensor = 10;    // Датчик температуры
uint16_t fan = 110;           // Реле вентилятора

uint16_t hyst_id = PMU_LogicFunctions_CreateHysteresis(
    fan,                // Выходной канал
    temp_sensor,        // Входной канал (температура)
    85,                 // Включить при 85°C
    75                  // Выключить при 75°C
);
```

### Ручная регистрация

```c
// Создание сложной функции вручную
PMU_LogicFunction_t func = {0};
func.type = PMU_FUNC_TABLE_1D;
func.output_channel = 300;
func.input_channels[0] = 5;
func.input_count = 1;
func.enabled = 1;

// Настройка таблицы (например, кривая дросселя)
static int32_t throttle_x[] = {0, 250, 500, 750, 1000};
static int32_t throttle_y[] = {0, 100, 300, 600, 1000};

func.params.table_1d.size = 5;
func.params.table_1d.x_values = throttle_x;
func.params.table_1d.y_values = throttle_y;

PMU_LogicFunctions_Register(&func);
```

### Обновление функций

```c
// Вызывать периодически (например, в main loop на частоте 1 kHz)
void Control_Task(void) {
    PMU_LogicFunctions_Update();
}
```

---

## Lua API

### Инициализация скрипта

```lua
-- Lua скрипты автоматически имеют доступ к PMU API
print("PMU-30 Lua Script Started")
```

### Доступ к каналам

```lua
-- Чтение значения канала
local rpm = channel.get(250)  -- Канал 250 = Engine RPM

-- Запись значения
channel.set(100, 1000)  -- Установить канал 100 на 100%

-- Поиск канала по имени
local brake_ch = channel.find("Brake_Pressure")
if brake_ch then
    local pressure = channel.get(brake_ch)
    print("Brake pressure: " .. pressure)
end

-- Получить информацию о канале
local info = channel.info(250)
if info then
    print("Name: " .. info.name)
    print("Min: " .. info.min .. ", Max: " .. info.max)
    print("Unit: " .. info.unit)
end
```

### Создание логических функций

```lua
-- Математика
local power_ch = 200
local voltage_ch = 1000
local current_ch = 1001

-- P = V * I
local func_id = logic.multiply(power_ch, voltage_ch, current_ch)

-- Сравнение
local oil_pressure = channel.find("Oil_Pressure")
local warning_led = channel.find("Oil_Warning")

-- Включить LED если давление < 20
logic.compare(warning_led, oil_pressure, 20, "<")

-- PID контроллер
local boost_sensor = channel.find("Boost_Pressure")
local wastegate = channel.find("Wastegate_PWM")

logic.pid(
    wastegate,      -- Выход
    boost_sensor,   -- Вход
    1500,           -- Уставка (1.5 bar)
    2.0,            -- Kp
    0.5,            -- Ki
    0.1             -- Kd
)

-- Гистерезис
local temp = channel.find("Engine_Temp")
local fan = channel.find("Cooling_Fan")

logic.hysteresis(fan, temp, 85, 75)  -- ON=85°C, OFF=75°C
```

### Системные функции

```lua
-- Получить напряжение батареи
local voltage = system.voltage()
print("Battery: " .. voltage .. " mV")

-- Ток потребления
local current = system.current()
print("Current: " .. current .. " mA")

-- Температура MCU
local temp = system.temperature()
print("MCU Temp: " .. temp .. " °C")

-- Время работы
local uptime = system.uptime()
print("Uptime: " .. (uptime / 1000) .. " seconds")
```

### Утилиты

```lua
-- Вывод в лог
print("Hello from Lua!")

-- Получить время в мс
local now = millis()

-- Задержка
sleep(100)  -- 100 ms
```

---

## Примеры применения

### 1. Launch Control (Контроль старта)

```c
// C API версия
void Setup_LaunchControl(void) {
    // Условие: RPM > 4000 И скорость < 5 км/ч И кнопка нажата
    uint16_t rpm_ch = PMU_Channel_GetByName("Engine_RPM")->channel_id;
    uint16_t speed_ch = PMU_Channel_GetByName("Vehicle_Speed")->channel_id;
    uint16_t button_ch = PMU_Channel_GetByName("Launch_Button")->channel_id;
    uint16_t cut_ch = PMU_Channel_GetByName("Ignition_Cut")->channel_id;

    // RPM > 4000
    uint16_t rpm_high_ch = 301;
    PMU_LogicFunctions_CreateComparison(PMU_FUNC_GREATER, rpm_high_ch, rpm_ch, 4000);

    // Speed < 5
    uint16_t speed_low_ch = 302;
    PMU_LogicFunctions_CreateComparison(PMU_FUNC_LESS, speed_low_ch, speed_ch, 5);

    // AND all conditions
    PMU_LogicFunction_t and_func = {0};
    and_func.type = PMU_FUNC_AND;
    and_func.output_channel = cut_ch;
    and_func.input_channels[0] = rpm_high_ch;
    and_func.input_channels[1] = speed_low_ch;
    and_func.input_channels[2] = button_ch;
    and_func.input_count = 3;
    and_func.enabled = 1;

    PMU_LogicFunctions_Register(&and_func);
}
```

```lua
-- Lua версия
function launch_control()
    local rpm = channel.get(channel.find("Engine_RPM"))
    local speed = channel.get(channel.find("Vehicle_Speed"))
    local button = channel.get(channel.find("Launch_Button"))
    local cut_ch = channel.find("Ignition_Cut")

    if button == 1 and speed < 5 and rpm > 4000 then
        channel.set(cut_ch, 1)  -- Cut ignition
    else
        channel.set(cut_ch, 0)
    end
end
```

### 2. Traction Control (Контроль тяги)

```lua
function traction_control()
    -- Сравнить скорости передних и задних колес
    local fl = channel.get(channel.find("Wheel_FL"))
    local fr = channel.get(channel.find("Wheel_FR"))
    local rl = channel.get(channel.find("Wheel_RL"))
    local rr = channel.get(channel.find("Wheel_RR"))

    local front_avg = (fl + fr) / 2
    local rear_avg = (rl + rr) / 2

    -- Если задние колеса буксуют (на 10% быстрее передних)
    if rear_avg > front_avg * 1.1 then
        -- Уменьшить мощность на 20%
        local throttle = channel.get(channel.find("Throttle"))
        channel.set(channel.find("Throttle_Output"), throttle * 0.8)

        -- Включить индикатор
        channel.set(channel.find("TC_Light"), 1)
    else
        -- Без вмешательства
        local throttle = channel.get(channel.find("Throttle"))
        channel.set(channel.find("Throttle_Output"), throttle)
        channel.set(channel.find("TC_Light"), 0)
    end
end
```

### 3. Boost Control (Управление турбиной)

```c
// PID контроллер для wastegate
void Setup_BoostControl(void) {
    uint16_t boost_sensor = 5;
    uint16_t wastegate = 105;

    // Target: 1.5 bar (1500 mbar)
    // Tuning: Kp=2.0, Ki=0.5, Kd=0.1
    uint16_t pid_id = PMU_LogicFunctions_CreatePID(
        wastegate, boost_sensor,
        1500,  // Setpoint
        2.0f,  // Kp
        0.5f,  // Ki
        0.1f   // Kd
    );
}
```

### 4. Cooling Fan Control (Управление вентилятором)

```c
// Гистерезис: ON=85°C, OFF=75°C
void Setup_FanControl(void) {
    uint16_t temp = 10;
    uint16_t fan = 110;

    PMU_LogicFunctions_CreateHysteresis(fan, temp, 85, 75);
}
```

---

## Best Practices

### 1. Именование каналов
Используйте осмысленные имена для простоты работы с Lua:

```c
// Хорошо
PMU_Channel_t ch = {
    .channel_id = 0,
    .name = "Brake_Pressure_Front",
    ...
};

// Плохо
PMU_Channel_t ch = {
    .channel_id = 0,
    .name = "CH0",
    ...
};
```

### 2. Виртуальные каналы для промежуточных результатов

```lua
-- Использовать виртуальные каналы (200-999) для промежуточных вычислений
local rpm_limit_ch = 300
logic.compare(rpm_limit_ch, rpm_ch, 9000, ">")

local speed_ok_ch = 301
logic.compare(speed_ok_ch, speed_ch, 5, "<")

-- Затем объединить результаты
logic.and(cut_ch, rpm_limit_ch, speed_ok_ch, button_ch)
```

### 3. Обработка ошибок в Lua

```lua
function safe_channel_access()
    local ch = channel.find("Some_Channel")
    if ch then
        local value = channel.get(ch)
        -- Используем value
    else
        print("ERROR: Channel not found")
    end
end
```

### 4. Оптимизация производительности

- Используйте C API для критичных по времени функций
- Lua скрипты для настраиваемой логики
- Избегайте тяжелых вычислений в каждом цикле

---

## Performance Considerations

- **C API**: Выполнение ~2-5 µs на функцию
- **Lua API**: Выполнение ~50-200 µs на вызов
- **Рекомендуемая частота обновления**: 100-1000 Hz
- **Максимум функций**: 64 одновременно

---

## Troubleshooting

### Функция не выполняется
- Проверьте `func->enabled == 1`
- Убедитесь, что `PMU_LogicFunctions_Update()` вызывается периодически
- Проверьте корректность ID каналов

### Lua скрипт не работает
- Проверьте синтаксис через `PMU_Lua_LoadScript()`
- Убедитесь, что скрипт зарегистрирован и включен
- Проверьте лог ошибок через `PMU_Lua_GetStats()`

### Неправильные значения
- Проверьте форматы каналов (RAW, PERCENT, VOLTAGE, etc.)
- Убедитесь в корректности масштабирования
- Проверьте диапазоны min/max

---

**© 2025 R2 m-sport. All rights reserved.**
