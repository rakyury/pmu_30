## PMU-30 Configurator - ECUMaster-Style UI Design

### Архитектура

Новый дизайн интерфейса следует концепции ECUMaster PMU Client с центральным деревом проекта и док-панелями мониторинга.

### Основные компоненты

#### 1. Project Tree (Центральное дерево проекта)
**Файл:** `src/ui/widgets/project_tree.py`

**Структура дерева:**
```
├─ OUT (Outputs 0-29)
│  ├─ o_IgnitionCoils
│  ├─ o_Injectors
│  └─ o_WaterPump
│
├─ IN (Inputs 0-19)
│  ├─ in.Wipers
│  ├─ in.BrakeSwitch
│  └─ in.ClutchSwitch
│
├─ Functions (Logic Functions)
│  ├─ s_boost_counter
│  ├─ s_als_1
│  └─ s_als_2
│
├─ Switches
├─ CAN
├─ Timers
├─ Tables
├─ Numbers
├─ H-Bridge (4 channels)
├─ PID Controllers
└─ Lua Scripts
```

**Функции:**
- Drag & Drop для реорганизации
- Группировка в папки (Group/Ungroup)
- Контекстное меню (Add, Edit, Delete, Duplicate)
- Кнопки управления: Add, Duplicate, Delete, Edit, Move up/down, Group, Ungroup

#### 2. Output Monitor (Монитор выходов)
**Файл:** `src/ui/widgets/output_monitor.py`

**Таблица:**
| Pin | Name | Status | V | Load |
|-----|------|--------|---|------|
| O1  | o_IgnitionCoils | ? | ? | ? |
| O2  | o_Injectors | ? | ? | ? |
| O3  | o_WaterPump | ? | ? | ? |

**Real-time данные** (при подключении к устройству):
- Status: ON/OFF/FAULT
- V: Voltage
- Load: Current (A)

#### 3. Analog Monitor (Монитор аналоговых входов)
**Файл:** `src/ui/widgets/analog_monitor.py`

**Таблица:**
| Pin | Name | Value | V |
|-----|------|-------|---|
| A1  | in.Wipers | ? | ? |
| A2  | in.BrakeSwitch | ? | ? |
| A3  | in.ClutchSwitch | ? | ? |

**Real-time данные:**
- Value: Текущее значение (0-100, True/False, и т.д.)
- V: Напряжение

#### 4. Variables Inspector (Инспектор переменных)
**Файл:** `src/ui/widgets/variables_inspector.py`

**Структура:**
```
Variables Inspector
├─ CAN Variables
│  ├─ c_ecu_rpm (? rpm)
│  ├─ c_ecu_map (? kPa)
│  ├─ c_ecu_boost (? bar)
│  ├─ c_ecu_tps (? %)
│  ├─ c_ecu_clt (? °C)
│  ├─ c_ecu_batt (? V)
│  └─ ...
│
└─ PMU
   ├─ Board temperature 1 (? °C)
   ├─ Battery voltage (? V)
   ├─ Board temperature 2 (? °C)
   ├─ 5V output (? V)
   └─ Flash temperature (? °C)
```

### Layout (QDockWidget)

```
┌────────────────────────────────────────────────────┐
│  Menu Bar: File | Edit | Desktops | Devices | ...  │
├────────────────────────────────────────────────────┤
│                                                    │
│  ┌──────────────┐  ┌────────────────────────────┐ │
│  │              │  │   Output Monitor           │ │
│  │              │  │  ┌──────┬─────┬──┬──┬────┐ │ │
│  │              │  │  │ O1   │ ... │  │  │    │ │ │
│  │  Project     │  │  └──────┴─────┴──┴──┴────┘ │ │
│  │  Tree        │  ├────────────────────────────┤ │
│  │              │  │   Analog Monitor           │ │
│  │ ├─ OUT       │  │  ┌──────┬─────┬────┬──┐   │ │
│  │ ├─ IN        │  │  │ A1   │ ... │    │  │   │ │
│  │ ├─ Functions │  │  └──────┴─────┴────┴──┘   │ │
│  │ ├─ CAN       │  └────────────────────────────┘ │
│  │ └─ ...       │                                  │
│  │              │  ┌────────────────────────────┐ │
│  │ [Add]        │  │  Variables Inspector       │ │
│  │ [Edit]       │  │  ├─ CAN Variables          │ │
│  │ [Delete]     │  │  │  ├─ c_ecu_rpm           │ │
│  │ [Move up]    │  │  │  └─ ...                 │ │
│  │ [Group]      │  │  └─ PMU                    │ │
│  │              │  │     ├─ Battery voltage     │ │
│  └──────────────┘  │     └─ ...                 │ │
│                    └────────────────────────────┘ │
├────────────────────────────────────────────────────┤
│  Status: OFFLINE │ CAN1: │ CAN2: ? │ OUTPUTS:    │
└────────────────────────────────────────────────────┘
```

### Возможности

1. **Перетаскивание (Drag & Drop)**
   - Dock widgets можно перетаскивать
   - Можно закреплять слева, справа, сверху, снизу
   - Можно делать плавающими окнами

2. **Resize (Изменение размера)**
   - Все панели изменяются по размеру
   - Пропорции сохраняются при изменении главного окна

3. **Hide/Show (Скрыть/Показать)**
   - Каждую панель можно скрыть через меню View
   - Кнопка "X" на панели закрывает её
   - View → Panels для переключения

4. **Сохранение Layout**
   - Layout сохраняется при выходе
   - Восстанавливается при запуске
   - Можно сбросить на дефолтный

### Интеграция с существующими вкладками

Старые вкладки (Settings, Configuration) доступны через меню или кнопки:
- **Tools → Configuration** - открывает настройки как диалог
- **Device → Settings** - открывает настройки устройства

### Преимущества нового подхода

1. **Более компактно** - всё на одном экране
2. **Как в ECUMaster** - знакомый интерфейс для пользователей
3. **Real-time monitoring** - видно всё сразу
4. **Гибкий layout** - можно настроить под себя
5. **Группировка** - легко организовать большие конфигурации

### Реализация

**Файлы:**
- `src/ui/widgets/project_tree.py` - Дерево проекта
- `src/ui/widgets/output_monitor.py` - Монитор выходов
- `src/ui/widgets/analog_monitor.py` - Монитор входов
- `src/ui/widgets/variables_inspector.py` - Инспектор переменных
- `src/ui/main_window_ecumaster.py` - Новое главное окно (будет создано)

**Статус:**
✅ Project Tree - реализован
✅ Output Monitor - реализован
✅ Analog Monitor - реализован
✅ Variables Inspector - реализован
⏳ Main Window Integration - в процессе
⏳ Dock Widgets Setup - в процессе
⏳ Layout Saving/Restore - TODO
⏳ Real-time Updates - TODO (требует подключения к устройству)

### Следующие шаги

1. Создать новое главное окно с QDockWidgets
2. Интегрировать все виджеты
3. Настроить дефолтный layout
4. Добавить сохранение/восстановление layout
5. Подключить real-time обновления
6. Тестирование с конфигурациями
