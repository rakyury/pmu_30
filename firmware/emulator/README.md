# PMU-30 Hardware Emulator

Эмулятор аппаратного обеспечения для PMU-30, позволяющий запускать прошивку на ПК без реального железа.

## Возможности

### Эмулируемые компоненты

| Компонент | Описание | API |
|-----------|----------|-----|
| **ADC (20 каналов)** | Аналоговые/цифровые/частотные входы | `PMU_Emu_ADC_*` |
| **CAN шина (4 шины)** | 2x CAN FD + 2x CAN 2.0 | `PMU_Emu_CAN_*` |
| **PROFET (30 выходов)** | Силовые выходы с токовым контролем | `PMU_Emu_PROFET_*` |
| **H-Bridge (4 моста)** | Мотор-контроллеры с PID | `PMU_Emu_HBridge_*` |
| **Protection** | Защита по напряжению/температуре | `PMU_Emu_Protection_*` |

### Ключевые функции

- **Data Injection** - программное задание значений всех входов
- **CAN Frame Injection** - инжекция CAN сообщений с периодическим повторением
- **Fault Injection** - инжекция ошибок для тестирования защиты
- **JSON Scenarios** - загрузка тестовых сценариев из файлов
- **Real-time Simulation** - симуляция моторов и токовых нагрузок

## Сборка

```bash
cd firmware

# Сборка эмулятора
pio run -e pmu30_emulator

# Запуск
.pio/build/pmu30_emulator/program
```

## Использование

### Интерактивный режим

```bash
./pmu30_emulator
```

Доступные команды:

```
ADC Commands:
  adc <ch> <value>      - Set ADC channel raw value (0-1023)
  adcv <ch> <voltage>   - Set ADC channel voltage (0.0-3.3V)
  freq <ch> <hz>        - Set frequency input (Hz)

CAN Commands:
  can <bus> <id> <d0-d7> - Inject CAN message
  canp <bus> <id> <int> <d0-d7> - Add periodic CAN message
  canoff <bus>          - Set CAN bus offline
  canon <bus>           - Set CAN bus online

Protection Commands:
  volt <mV>             - Set battery voltage
  temp <C>              - Set temperature
  fault <flags>         - Inject protection fault
  clear                 - Clear all faults

Control Commands:
  pause                 - Pause emulator
  resume                - Resume emulator
  speed <x>             - Set time scale
  status                - Print full status
  reset                 - Reset emulator
```

### Сценарии тестирования

```bash
# Загрузка сценария
./pmu30_emulator --scenario scenarios/can_test.json
```

### Примеры сценариев

- `basic_test.json` - базовый тест всех подсистем
- `can_test.json` - тест CAN коммуникации
- `fault_test.json` - тест системы защиты

## Формат JSON сценария

```json
{
    "name": "Test Name",
    "description": "Test description",

    "adc": [512, 512, ...],  // 20 значений ADC (0-1023)

    "voltage_mV": 12000,     // Напряжение батареи
    "temperature_C": 25,     // Температура

    "can_messages": [
        {
            "bus": 0,
            "id": "0x100",
            "data": [1, 2, 3, 4, 5, 6, 7, 8],
            "interval_ms": 100
        }
    ]
}
```

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

### Инжекция ADC данных

```c
// Установка напряжения
PMU_Emu_ADC_SetVoltage(0, 2.5f);  // Канал 0, 2.5V

// Установка raw значения
PMU_Emu_ADC_SetRaw(1, 512);  // Канал 1, mid-scale

// Установка частоты
PMU_Emu_ADC_SetFrequency(2, 1000);  // Канал 2, 1000 Hz
```

### Инжекция CAN сообщений

```c
// Одиночное сообщение
uint8_t data[] = {0x01, 0x02, 0x03, 0x04};
PMU_Emu_CAN_InjectMessage(0, 0x100, data, 4);

// Периодическое сообщение
int idx = PMU_Emu_CAN_AddPeriodicMessage(0, 0x200, data, 4, 100);

// Удаление периодического сообщения
PMU_Emu_CAN_RemovePeriodicMessage(idx);
```

### Инжекция ошибок

```c
// Установка напряжения ниже порога
PMU_Emu_Protection_SetVoltage(5000);  // 5V - undervoltage

// Прямая инжекция fault
PMU_Emu_Protection_InjectFault(0x0001);  // UNDERVOLTAGE

// Инжекция ошибки PROFET
PMU_Emu_PROFET_InjectFault(0, 0x01);  // Overcurrent on channel 0
```

### Мониторинг выходов

```c
// Callback для CAN TX
void OnCanTx(uint8_t bus, uint32_t id, uint8_t* data, uint8_t len) {
    printf("CAN TX: bus=%d, id=0x%X\n", bus, id);
}
PMU_Emu_CAN_SetTxCallback(OnCanTx);

// Получение состояния PROFET
const PMU_Emu_PROFET_Channel_t* ch = PMU_Emu_PROFET_GetState(0);
printf("PROFET[0]: state=%d, current=%d mA\n", ch->state, ch->current_mA);
```

## Архитектура

```
┌─────────────────────────────────────────────┐
│          Test Application / CLI              │
├─────────────────────────────────────────────┤
│          PMU Emulator API                    │
│    (pmu_emulator.h / pmu_emulator.c)         │
├─────────────────────────────────────────────┤
│          HAL Emulation Layer                 │
│    (stm32_hal_emu.h / stm32_hal_emu.c)       │
├─────────────────────────────────────────────┤
│          Firmware Source Code                │
│    (pmu_adc.c, pmu_can.c, pmu_profet.c, ...) │
└─────────────────────────────────────────────┘
```

## Ограничения

- FreeRTOS не эмулируется (single-threaded)
- Timing не гарантирован (зависит от хост-системы)
- SPI диагностика возвращает заглушки
- Нет эмуляции флэш-памяти

## Лицензия

Copyright (c) 2025 R2 m-sport. All rights reserved.
