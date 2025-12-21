# Конфигурация PMU-30 через JSON

## Обзор

PMU-30 поддерживает полную конфигурацию устройства через JSON файлы. Все логические функции, созданные в системе, могут быть описаны в JSON конфигурации, что позволяет:

- ✅ Настраивать устройство без перепрошивки
- ✅ Использовать конфигуратор с графическим интерфейсом
- ✅ Сохранять и загружать различные конфигурации
- ✅ Создавать сложную логику управления без программирования

## Структура JSON конфигурации

```json
{
  "version": "1.0",
  "device": { ... },
  "inputs": [ ... ],
  "outputs": [ ... ],
  "hbridges": [ ... ],
  "logic_functions": [ ... ],
  "virtual_channels": [ ... ],
  "can_buses": [ ... ],
  "system": { ... }
}
```

## Раздел `logic_functions`

Это основной раздел для описания логических функций. Каждая функция имеет следующую структуру:

```json
{
  "type": "тип_функции",
  "name": "Имя_Функции",
  "enabled": true,
  "output": "канал_выхода",
  "inputs": ["вход1", "вход2", ...],
  "parameters": { ... }
}
```

### Поля функции:

- **type** - тип логической функции (см. список ниже)
- **name** - имя функции (опционально, для удобства)
- **enabled** - включена ли функция (true/false)
- **output** - выходной канал (номер или имя канала)
- **inputs** - массив входных каналов (номера или имена)
- **parameters** - специфичные параметры функции (зависят от типа)

### Указание каналов

Каналы можно указывать двумя способами:

1. **По номеру**: `"output": 100`
2. **По имени**: `"output": "Wastegate_PWM"`

Имена каналов ищутся в системе автоматически через `PMU_Channel_FindByName()`.

## Типы логических функций

### 1. Математические операции

#### Сложение (add)
```json
{
  "type": "add",
  "output": "Result_Channel",
  "inputs": ["Input_A", "Input_B"]
}
```

#### Вычитание (subtract)
```json
{
  "type": "subtract",
  "output": "Difference",
  "inputs": ["Input_A", "Input_B"]
}
```

#### Умножение (multiply)
```json
{
  "type": "multiply",
  "output": "Product",
  "inputs": ["Input_A", "Input_B"]
}
```
*Примечание: использует fixed-point арифметику (делит на 1000)*

#### Деление (divide)
```json
{
  "type": "divide",
  "output": "Quotient",
  "inputs": ["Dividend", "Divisor"]
}
```

#### Минимум (min)
```json
{
  "type": "min",
  "output": "Min_Value",
  "inputs": ["Value1", "Value2", "Value3"]
}
```

#### Максимум (max)
```json
{
  "type": "max",
  "output": "Max_Value",
  "inputs": ["Value1", "Value2", "Value3"]
}
```

#### Среднее (average)
```json
{
  "type": "average",
  "output": "Average_Value",
  "inputs": ["Value1", "Value2", "Value3", "Value4"]
}
```

#### Абсолютное значение (abs)
```json
{
  "type": "abs",
  "output": "Absolute_Value",
  "inputs": ["Input_Value"]
}
```

#### Масштабирование (scale)
```json
{
  "type": "scale",
  "output": "Scaled_Value",
  "inputs": ["Input_Value"],
  "parameters": {
    "multiplier": 0.1,
    "offset": -40.0
  }
}
```
*Формула: `output = (input * multiplier) + offset`*

#### Ограничение (clamp)
```json
{
  "type": "clamp",
  "output": "Limited_Value",
  "inputs": ["Input_Value"],
  "parameters": {
    "min": 0,
    "max": 1000
  }
}
```

### 2. Операции сравнения

#### Больше (greater, >)
```json
{
  "type": "greater",
  "output": "Is_Greater",
  "inputs": ["Value_A", "Value_B"]
}
```
*Результат: 1 если A > B, иначе 0*

#### Меньше (less, <)
```json
{
  "type": "less",
  "output": "Is_Less",
  "inputs": ["Value_A", "Value_B"]
}
```

#### Равно (equal, ==)
```json
{
  "type": "equal",
  "output": "Is_Equal",
  "inputs": ["Value_A", "Value_B"]
}
```

#### Не равно (not_equal, !=)
```json
{
  "type": "not_equal",
  "output": "Is_Not_Equal",
  "inputs": ["Value_A", "Value_B"]
}
```

#### В диапазоне (in_range)
```json
{
  "type": "in_range",
  "output": "In_Range",
  "inputs": ["Value"],
  "parameters": {
    "min": 70,
    "max": 110
  }
}
```

### 3. Логические операции

#### AND (и)
```json
{
  "type": "and",
  "output": "All_True",
  "inputs": ["Condition1", "Condition2", "Condition3"]
}
```

#### OR (или)
```json
{
  "type": "or",
  "output": "Any_True",
  "inputs": ["Condition1", "Condition2", "Condition3"]
}
```

#### NOT (не)
```json
{
  "type": "not",
  "output": "Inverted",
  "inputs": ["Input_Condition"]
}
```

#### XOR (исключающее или)
```json
{
  "type": "xor",
  "output": "Exclusive_Or",
  "inputs": ["Condition1", "Condition2"]
}
```

### 4. Фильтры

#### Скользящее среднее (moving_avg)
```json
{
  "type": "moving_avg",
  "output": "Smoothed_Value",
  "inputs": ["Noisy_Input"],
  "parameters": {
    "window_size": 10
  }
}
```

#### Фильтр низких частот (low_pass)
```json
{
  "type": "low_pass",
  "output": "Filtered_Value",
  "inputs": ["Input_Signal"],
  "parameters": {
    "time_constant": 0.1
  }
}
```

### 5. Контроллеры

#### PID-регулятор (pid)
```json
{
  "type": "pid",
  "name": "Boost_Controller",
  "output": "Wastegate_PWM",
  "inputs": ["Boost_Pressure"],
  "parameters": {
    "setpoint": 1500,
    "kp": 2.0,
    "ki": 0.5,
    "kd": 0.1
  }
}
```

**Параметры:**
- `setpoint` - уставка (целевое значение)
- `kp` - пропорциональный коэффициент
- `ki` - интегральный коэффициент
- `kd` - дифференциальный коэффициент

#### Гистерезис (hysteresis)
```json
{
  "type": "hysteresis",
  "name": "Fan_Control",
  "output": "Fan_Relay",
  "inputs": ["Engine_Temp"],
  "parameters": {
    "threshold_on": 90,
    "threshold_off": 80
  }
}
```

**Параметры:**
- `threshold_on` - порог включения
- `threshold_off` - порог выключения

## Практические примеры

### Пример 1: Launch Control (Контроль старта)

```json
{
  "logic_functions": [
    {
      "type": "greater",
      "name": "RPM_Above_4000",
      "output": "RPM_Check",
      "inputs": ["Engine_RPM", 4000]
    },
    {
      "type": "less",
      "name": "Speed_Below_5",
      "output": "Speed_Check",
      "inputs": ["Vehicle_Speed", 5]
    },
    {
      "type": "and",
      "name": "Launch_Conditions_Met",
      "output": "Launch_Active",
      "inputs": ["Launch_Button", "RPM_Check", "Speed_Check"]
    },
    {
      "type": "scale",
      "name": "Ignition_Cut_Output",
      "output": "Ignition_Cut",
      "inputs": ["Launch_Active"],
      "parameters": {
        "multiplier": 1000,
        "offset": 0
      }
    }
  ]
}
```

**Логика:**
1. Проверяем что RPM > 4000
2. Проверяем что скорость < 5 км/ч
3. Проверяем что кнопка нажата
4. Если все условия TRUE - активируем отсечку зажигания

### Пример 2: Traction Control (Контроль тяги)

```json
{
  "logic_functions": [
    {
      "type": "average",
      "name": "Front_Avg_Speed",
      "output": "Front_Speed",
      "inputs": ["Wheel_FL", "Wheel_FR"]
    },
    {
      "type": "average",
      "name": "Rear_Avg_Speed",
      "output": "Rear_Speed",
      "inputs": ["Wheel_RL", "Wheel_RR"]
    },
    {
      "type": "scale",
      "name": "Front_Speed_110",
      "output": "Front_Speed_Target",
      "inputs": ["Front_Speed"],
      "parameters": {
        "multiplier": 1.1,
        "offset": 0
      }
    },
    {
      "type": "greater",
      "name": "Slip_Detected",
      "output": "TC_Active",
      "inputs": ["Rear_Speed", "Front_Speed_Target"]
    },
    {
      "type": "scale",
      "name": "Throttle_Reduction",
      "output": "Throttle_Output",
      "inputs": ["Throttle_Input"],
      "parameters": {
        "multiplier": 0.8,
        "offset": 0
      }
    }
  ]
}
```

**Логика:**
1. Вычисляем среднюю скорость передних колес
2. Вычисляем среднюю скорость задних колес
3. Если задние колеса вращаются на 10% быстрее - детектируем пробуксовку
4. Уменьшаем газ на 20%

### Пример 3: Boost Control (Контроль наддува)

```json
{
  "logic_functions": [
    {
      "type": "low_pass",
      "name": "Filtered_Boost",
      "output": "Boost_Filtered",
      "inputs": ["Boost_Pressure_Raw"],
      "parameters": {
        "time_constant": 0.05
      }
    },
    {
      "type": "pid",
      "name": "Boost_PID",
      "output": "Wastegate_Duty",
      "inputs": ["Boost_Filtered"],
      "parameters": {
        "setpoint": 1500,
        "kp": 3.0,
        "ki": 0.8,
        "kd": 0.2
      }
    },
    {
      "type": "clamp",
      "name": "Wastegate_Limiter",
      "output": "Wastegate_PWM",
      "inputs": ["Wastegate_Duty"],
      "parameters": {
        "min": 0,
        "max": 1000
      }
    }
  ]
}
```

**Логика:**
1. Фильтруем сигнал датчика давления
2. PID-регулятор поддерживает давление 1.5 бар
3. Ограничиваем ШИМ вестгейта в диапазоне 0-1000

### Пример 4: Multi-Stage Temperature Control

```json
{
  "logic_functions": [
    {
      "type": "max",
      "name": "Max_Temperature",
      "output": "Max_Temp",
      "inputs": ["Engine_Temp", "Coolant_Temp", "Oil_Temp"]
    },
    {
      "type": "hysteresis",
      "name": "Fan_Stage_1",
      "output": "Fan1_Active",
      "inputs": ["Max_Temp"],
      "parameters": {
        "threshold_on": 85,
        "threshold_off": 80
      }
    },
    {
      "type": "hysteresis",
      "name": "Fan_Stage_2",
      "output": "Fan2_Active",
      "inputs": ["Max_Temp"],
      "parameters": {
        "threshold_on": 95,
        "threshold_off": 90
      }
    },
    {
      "type": "greater",
      "name": "Overheat_Warning",
      "output": "Warning_Light",
      "inputs": ["Max_Temp", 105]
    }
  ]
}
```

**Логика:**
1. Находим максимальную температуру из трех датчиков
2. При 85°C включаем первую ступень вентиляции
3. При 95°C включаем вторую ступень
4. При 105°C включаем предупреждение о перегреве

## Виртуальные каналы

Для использования в логических функциях нужно создавать виртуальные каналы:

```json
{
  "virtual_channels": [
    {
      "id": 1000,
      "name": "Boost_Filtered",
      "initial_value": 1000
    },
    {
      "id": 1001,
      "name": "Wastegate_Duty",
      "initial_value": 0
    },
    {
      "id": 1002,
      "name": "TC_Active",
      "initial_value": 0
    }
  ]
}
```

**Параметры:**
- `id` - уникальный ID канала (рекомендуется >= 1000 для виртуальных)
- `name` - имя канала (используется в функциях)
- `initial_value` - начальное значение при старте

## Загрузка конфигурации

### Из строки в коде:
```c
const char* json_config = "{ ... }";
PMU_JSON_LoadStats_t stats;
PMU_JSON_Status_t result = PMU_JSON_LoadFromString(json_config, strlen(json_config), &stats);

if (result == PMU_JSON_OK) {
    printf("Loaded %d logic functions\n", stats.logic_functions_loaded);
}
```

### Из Flash памяти:
```c
PMU_JSON_LoadStats_t stats;
PMU_JSON_Status_t result = PMU_JSON_LoadFromFlash(0x08100000, &stats);
```

## Валидация конфигурации

Перед загрузкой можно проверить корректность JSON:

```c
char error_msg[256];
bool valid = PMU_JSON_Validate(json_string, length, error_msg, sizeof(error_msg));

if (!valid) {
    printf("Validation error: %s\n", error_msg);
}
```

## Полная поддержка функций

### ✅ Математические
- add, subtract, multiply, divide
- min, max, average
- abs, scale, clamp

### ✅ Сравнения
- greater (>), less (<), equal (==), not_equal (!=)
- greater_equal (>=), less_equal (<=)
- in_range

### ✅ Логические
- and, or, not, xor, nand, nor

### ✅ Фильтры
- moving_avg (скользящее среднее)
- low_pass (RC фильтр)
- min_window, max_window
- median

### ✅ Контроллеры
- pid (PID регулятор)
- hysteresis (триггер Шмитта)
- rate_limit (ограничитель скорости изменения)
- debounce (подавление дребезга)

### ⏳ В разработке
- table_1d (1D таблица с интерполяцией)
- table_2d (2D карта)
- mux, demux (мультиплексоры)
- conditional (условный оператор)

## Советы и рекомендации

1. **Именование каналов**: Используйте понятные имена с префиксами (Input_, Output_, Virtual_)
2. **Виртуальные каналы**: Создавайте с ID >= 1000 для избежания конфликтов
3. **Порядок функций**: Порядок в JSON не важен, функции выполняются на каждом цикле
4. **Производительность**: До 100 функций на 500Hz без потери производительности
5. **Отладка**: Используйте `"enabled": false` для временного отключения функций

## Интеграция с конфигуратором

Графический конфигуратор PMU-30 (Python/Qt) поддерживает:
- ✅ Визуальное создание логических функций
- ✅ Drag-and-drop соединение каналов
- ✅ Живой предпросмотр значений
- ✅ Экспорт/импорт JSON конфигурации
- ✅ Валидация в реальном времени

## См. также

- [LOGIC_FUNCTIONS.md](LOGIC_FUNCTIONS.md) - Полное описание C API
- [lua_examples.lua](examples/lua_examples.lua) - Примеры Lua скриптов
- [config_examples.json](examples/config_examples.json) - Готовые примеры конфигураций

---

**© 2025 R2 m-sport | PMU-30 Racing Controller**
