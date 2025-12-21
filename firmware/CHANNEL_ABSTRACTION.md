# PMU-30 Universal Channel Abstraction

**Version**: 1.0
**Author**: R2 m-sport
**Date**: 2025-12-21

---

## Overview

Универсальная система абстракции каналов (Universal Channel Abstraction) предоставляет единый API для работы со всеми типами входов и выходов PMU-30, независимо от их физической или виртуальной природы.

### Ключевые преимущества

- **Единый интерфейс**: `PMU_Channel_GetValue()` и `PMU_Channel_SetValue()` для всех типов каналов
- **Автоматическая маршрутизация**: Система сама определяет, какой драйвер использовать
- **Виртуальные каналы**: Поддержка вычисляемых значений, CAN, функций, таблиц
- **Поиск по имени**: Доступ к каналам по символьному имени
- **Метаданные**: Каждый канал содержит информацию о типе, диапазоне, единицах измерения

---

## Типы каналов

### Физические входы (0x00-0x1F)

| Тип | Код | Описание | Пример |
|-----|-----|----------|--------|
| `PMU_CHANNEL_INPUT_ANALOG` | 0x00 | Аналоговый вход (0-5V) | Датчик давления |
| `PMU_CHANNEL_INPUT_DIGITAL` | 0x01 | Цифровой вход (вкл/выкл) | Концевик двери |
| `PMU_CHANNEL_INPUT_SWITCH` | 0x02 | Переключатель | Тумблер на руле |
| `PMU_CHANNEL_INPUT_ROTARY` | 0x03 | Поворотный переключатель | Многопозиционный селектор |
| `PMU_CHANNEL_INPUT_FREQUENCY` | 0x04 | Частотный вход | Датчик скорости |

### Виртуальные входы (0x20-0x3F)

| Тип | Код | Описание | Пример |
|-----|-----|----------|--------|
| `PMU_CHANNEL_INPUT_CAN` | 0x20 | Вход с CAN шины | Обороты двигателя из ECU |
| `PMU_CHANNEL_INPUT_CALCULATED` | 0x21 | Вычисляемое значение | Мощность (V × I) |
| `PMU_CHANNEL_INPUT_SYSTEM` | 0x22 | Системное значение | Напряжение батареи |

### Физические выходы (0x40-0x5F)

| Тип | Код | Описание | Пример |
|-----|-----|----------|--------|
| `PMU_CHANNEL_OUTPUT_POWER` | 0x40 | Силовой выход (PROFET) | Реле топливного насоса |
| `PMU_CHANNEL_OUTPUT_PWM` | 0x41 | ШИМ выход | Управление вентилятором |
| `PMU_CHANNEL_OUTPUT_HBRIDGE` | 0x42 | H-мост | Стеклоподъемник |
| `PMU_CHANNEL_OUTPUT_ANALOG` | 0x43 | Аналоговый выход (DAC) | 0-10V управление |

### Виртуальные выходы (0x60-0x7F)

| Тип | Код | Описание | Пример |
|-----|-----|----------|--------|
| `PMU_CHANNEL_OUTPUT_FUNCTION` | 0x60 | Логическая функция | AND/OR/NOT |
| `PMU_CHANNEL_OUTPUT_TABLE` | 0x61 | Таблица преобразования | Кривая дроссельной заслонки |
| `PMU_CHANNEL_OUTPUT_ENUM` | 0x62 | Перечисление | Режим работы (1=OFF, 2=ON, 3=AUTO) |
| `PMU_CHANNEL_OUTPUT_NUMBER` | 0x63 | Константа | Уставка регулятора |
| `PMU_CHANNEL_OUTPUT_CAN` | 0x64 | Выход в CAN | Отправка температуры на дисплей |
| `PMU_CHANNEL_OUTPUT_PID` | 0x65 | PID регулятор | Контроллер температуры |

---

## Диапазоны ID каналов

```
0-99:      Физические входы (ADC 0-19)
100-199:   Физические выходы (PROFET 0-29, H-bridge 0-3)
200-999:   Виртуальные каналы (CAN, функции, таблицы)
1000-1023: Системные каналы (напряжение, температура, uptime)
```

### Предопределенные системные каналы

| ID | Имя | Описание | Единицы |
|----|-----|----------|---------|
| 1000 | Battery Voltage | Напряжение батареи | mV |
| 1001 | Total Current | Общий ток потребления | mA |
| 1002 | MCU Temperature | Температура MCU | °C |
| 1003 | Board Temperature | Температура платы | °C |
| 1004 | System Uptime | Время работы | секунды |

---

## Форматы значений

| Формат | Описание | Диапазон |
|--------|----------|----------|
| `PMU_CHANNEL_FORMAT_RAW` | Сырое значение ADC/PWM | 0-1023 |
| `PMU_CHANNEL_FORMAT_PERCENT` | Проценты | 0-1000 (0.0-100.0%) |
| `PMU_CHANNEL_FORMAT_VOLTAGE` | Напряжение | мВ |
| `PMU_CHANNEL_FORMAT_CURRENT` | Ток | мА |
| `PMU_CHANNEL_FORMAT_BOOLEAN` | Логический | 0/1 |
| `PMU_CHANNEL_FORMAT_ENUM` | Перечисление | 0-255 |
| `PMU_CHANNEL_FORMAT_SIGNED` | Знаковое | -32768 до +32767 |

---

## API Reference

### Инициализация

```c
// Инициализация системы каналов
HAL_StatusTypeDef PMU_Channel_Init(void);

// Регистрация нового канала
PMU_Channel_t channel = {
    .channel_id = 0,
    .type = PMU_CHANNEL_INPUT_ANALOG,
    .direction = PMU_CHANNEL_DIR_INPUT,
    .format = PMU_CHANNEL_FORMAT_RAW,
    .physical_index = 0,  // ADC channel 0
    .flags = PMU_CHANNEL_FLAG_ENABLED,
    .min_value = 0,
    .max_value = 1023,
    .name = "Brake Pressure",
    .unit = "bar"
};
PMU_Channel_Register(&channel);
```

### Чтение значений

```c
// Чтение по ID
int32_t value = PMU_Channel_GetValue(0);  // Читаем канал 0

// Чтение по имени
const PMU_Channel_t* ch = PMU_Channel_GetByName("Brake Pressure");
if (ch) {
    int32_t pressure = PMU_Channel_GetValue(ch->channel_id);
}

// Чтение системного значения
int32_t battery_mv = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BATTERY_V);
```

### Запись значений

```c
// Установка силового выхода на 50%
PMU_Channel_SetValue(100, 500);  // Channel 100, 50.0%

// Установка H-моста на движение вперед с 70% мощности
PMU_Channel_SetValue(150, 700);  // Положительное = вперед

// Установка H-моста на движение назад
PMU_Channel_SetValue(150, -700);  // Отрицательное = назад
```

### Информация о канале

```c
// Получение метаданных
const PMU_Channel_t* info = PMU_Channel_GetInfo(0);
if (info) {
    printf("Channel: %s\n", info->name);
    printf("Type: 0x%02X\n", info->type);
    printf("Value: %ld %s\n", info->value, info->unit);
    printf("Range: %ld - %ld\n", info->min_value, info->max_value);
}

// Проверка типа
if (PMU_Channel_IsInput(info->type)) {
    // Это вход
}
if (PMU_Channel_IsVirtual(info->type)) {
    // Это виртуальный канал
}
```

### Управление каналами

```c
// Включение/выключение канала
PMU_Channel_SetEnabled(0, true);   // Включить
PMU_Channel_SetEnabled(0, false);  // Выключить

// Получение списка всех каналов
PMU_Channel_t channels[100];
uint16_t count = PMU_Channel_List(channels, 100);

for (uint16_t i = 0; i < count; i++) {
    printf("%d: %s = %ld %s\n",
           channels[i].channel_id,
           channels[i].name,
           channels[i].value,
           channels[i].unit);
}

// Статистика
const PMU_ChannelStats_t* stats = PMU_Channel_GetStats();
printf("Total: %d, Inputs: %d, Outputs: %d, Virtual: %d\n",
       stats->total_channels,
       stats->input_channels,
       stats->output_channels,
       stats->virtual_channels);
```

---

## Примеры использования

### Пример 1: Регистрация физических каналов из конфигурации

```c
// При загрузке конфигурации из JSON
void RegisterPhysicalChannels(void)
{
    PMU_Channel_t channel;

    // Регистрация всех физических входов (ADC 0-19)
    for (uint8_t i = 0; i < 20; i++) {
        memset(&channel, 0, sizeof(channel));
        channel.channel_id = i;  // ID 0-19
        channel.type = PMU_CHANNEL_INPUT_ANALOG;
        channel.direction = PMU_CHANNEL_DIR_INPUT;
        channel.format = PMU_CHANNEL_FORMAT_RAW;
        channel.physical_index = i;
        channel.flags = PMU_CHANNEL_FLAG_ENABLED;
        channel.min_value = 0;
        channel.max_value = 1023;

        snprintf(channel.name, sizeof(channel.name), "Input %d", i);
        strncpy(channel.unit, "raw", sizeof(channel.unit));

        PMU_Channel_Register(&channel);
    }

    // Регистрация всех силовых выходов (PROFET 0-29)
    for (uint8_t i = 0; i < 30; i++) {
        memset(&channel, 0, sizeof(channel));
        channel.channel_id = 100 + i;  // ID 100-129
        channel.type = PMU_CHANNEL_OUTPUT_POWER;
        channel.direction = PMU_CHANNEL_DIR_OUTPUT;
        channel.format = PMU_CHANNEL_FORMAT_PERCENT;
        channel.physical_index = i;
        channel.flags = PMU_CHANNEL_FLAG_ENABLED;
        channel.min_value = 0;
        channel.max_value = 1000;

        snprintf(channel.name, sizeof(channel.name), "Output %d", i);
        strncpy(channel.unit, "%", sizeof(channel.unit));

        PMU_Channel_Register(&channel);
    }
}
```

### Пример 2: Логическая функция с использованием каналов

```c
// Включить вентилятор если температура > 80°C ИЛИ давление > 3 бар
void UpdateCoolingFan(void)
{
    int32_t temp = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_MCU_TEMP);
    int32_t pressure = PMU_Channel_GetValue(5);  // Pressure sensor on input 5

    bool fan_on = (temp > 80) || (pressure > 3000);

    // Канал 105 = вентилятор (PROFET output 5)
    PMU_Channel_SetValue(105, fan_on ? 1000 : 0);  // 100% или 0%
}
```

### Пример 3: Виртуальный канал с вычислением

```c
// Регистрация виртуального канала для мощности (P = V × I)
void RegisterPowerChannel(void)
{
    PMU_Channel_t channel = {
        .channel_id = 200,
        .type = PMU_CHANNEL_INPUT_CALCULATED,
        .direction = PMU_CHANNEL_DIR_INPUT,
        .format = PMU_CHANNEL_FORMAT_RAW,
        .physical_index = 0,  // Logic function index
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .min_value = 0,
        .max_value = 100000,  // 100 kW max
        .name = "Total Power",
        .unit = "W"
    };
    strncpy(channel.unit, "W", sizeof(channel.unit));

    PMU_Channel_Register(&channel);
}

// Обновление вычисляемого значения (вызывается периодически)
void UpdatePowerCalculation(void)
{
    int32_t voltage = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BATTERY_V);
    int32_t current = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_TOTAL_I);

    // P = V × I (в мВт, затем конвертируем в Вт)
    int32_t power_w = (voltage * current) / 1000000;

    // Сохраняем в виртуальный канал через logic module
    PMU_Logic_SetVirtualChannel(0, power_w);
}
```

### Пример 4: CAN виртуальный вход

```c
// Регистрация CAN входа для оборотов двигателя
void RegisterEngineRPM(void)
{
    PMU_Channel_t channel = {
        .channel_id = 250,
        .type = PMU_CHANNEL_INPUT_CAN,
        .direction = PMU_CHANNEL_DIR_INPUT,
        .format = PMU_CHANNEL_FORMAT_RAW,
        .physical_index = 0,  // CAN message index
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .min_value = 0,
        .max_value = 9000,
        .name = "Engine RPM",
        .unit = "rpm"
    };

    PMU_Channel_Register(&channel);
}

// Чтение RPM из любого места в коде
void DisplayEngineRPM(void)
{
    int32_t rpm = PMU_Channel_GetValue(250);
    printf("Engine RPM: %ld\n", rpm);
}
```

---

## Интеграция с существующими модулями

### Обновление pmu_logging.c

```c
static uint16_t Logging_GetChannelValue(PMU_LogChannel_t* channel)
{
    // Старый способ - множественные case statements
    // Новый способ - один вызов:
    return (uint16_t)PMU_Channel_GetValue(channel->channel_id);
}
```

### Обновление pmu_logic.c

```c
// Вместо прямого обращения к PMU_ADC_GetValue(), PMU_PROFET_GetState():
int32_t input_value = PMU_Channel_GetValue(input_channel_id);
PMU_Channel_SetValue(output_channel_id, result);
```

### Обновление pmu_protocol.c

```c
// Команда получения значения канала по имени
static void Protocol_HandleGetChannelByName(const PMU_Protocol_Packet_t* packet)
{
    const char* name = (const char*)packet->data;
    const PMU_Channel_t* ch = PMU_Channel_GetByName(name);

    if (ch) {
        int32_t value = PMU_Channel_GetValue(ch->channel_id);
        uint8_t response[8];
        memcpy(&response[0], &ch->channel_id, 2);
        memcpy(&response[2], &value, 4);
        Protocol_SendData(PMU_CMD_GET_CHANNEL, response, 6);
    } else {
        Protocol_SendNACK(PMU_CMD_GET_CHANNEL, "Channel not found");
    }
}
```

---

## Performance

- **Lookup time**: O(1) для доступа по ID (прямая индексация в массиве)
- **Memory overhead**: ~80 байт на канал
- **Maximum channels**: 1024
- **Total memory**: ~80 KB для полной регистрации

---

## Best Practices

1. **Используйте осмысленные имена каналов**: `"Brake_Pressure"` вместо `"Input_5"`
2. **Устанавливайте корректные диапазоны**: Помогает обнаружить ошибки
3. **Указывайте единицы измерения**: Упрощает отладку и логирование
4. **Регистрируйте каналы при инициализации**: Не создавайте динамически во время работы
5. **Используйте системные каналы**: Вместо прямых вызовов `PMU_Protection_GetVoltage()`

---

## Future Enhancements

- Callback-функции при изменении значения
- Фильтрация значений (debounce, averaging)
- Алиасы для каналов
- Группы каналов
- Сохранение/загрузка регистра каналов из flash

---

**© 2025 R2 m-sport. All rights reserved.**
