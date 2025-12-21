# PMU-30 Configurator - ECUMaster Style UI

## Запуск

Есть два варианта интерфейса:

### 1. ECUMaster Style (Рекомендуется) ⭐
```bash
cd configurator
python src/main_ecumaster.py
```

**Особенности:**
- Dock-based layout как в ECUMaster PMU Client
- Project Tree с иерархической структурой
- Real-time мониторинг (Output Monitor, Analog Monitor)
- Variables Inspector для CAN данных и PMU статуса
- Перетаскивание панелей (drag & drop)
- Сохранение/восстановление layout
- Более компактный - всё на одном экране

### 2. Classic Style (Табы)
```bash
cd configurator
python src/main.py
```

**Особенности:**
- Традиционный интерфейс с вкладками
- Каждая функция на отдельной вкладке
- Подходит для детальной настройки

## ECUMaster Style - Основные компоненты

### Project Tree (Центральная панель)
Иерархическое дерево всех элементов конфигурации:

```
├─ OUT
│  ├─ o_IgnitionCoils
│  ├─ o_Injectors
│  └─ o_WaterPump
├─ IN
│  ├─ in.Wipers
│  ├─ in.BrakeSwitch
│  └─ in.ClutchSwitch
├─ Functions
│  └─ s_boost_counter
├─ H-Bridge
├─ PID Controllers
└─ Lua Scripts
```

**Кнопки управления:**
- **Add** - Добавить новый элемент
- **Duplicate** - Дублировать выбранный
- **Delete** - Удалить
- **Edit** - Редактировать
- **Move up/down** - Переместить вверх/вниз
- **Group** - Создать группу/папку
- **Ungroup** - Разгруппировать

**Контекстное меню:** Правый клик на элементе

### Output Monitor
Мониторинг выходных каналов в реальном времени:

| Pin | Name | Status | V | Load |
|-----|------|--------|---|------|
| O1  | o_IgnitionCoils | ? | ? | ? |
| O2  | o_Injectors | ? | ? | ? |

**При подключении к устройству:**
- Status: ON/OFF/FAULT
- V: Voltage
- Load: Current (A)

### Analog Monitor
Мониторинг аналоговых входов:

| Pin | Name | Value | V |
|-----|------|-------|---|
| A1  | in.Wipers | ? | ? |
| A2  | in.BrakeSwitch | ? | ? |

### Variables Inspector
Инспектор переменных:
- **CAN Variables** - c_ecu_rpm, c_ecu_map, c_ecu_boost и т.д.
- **PMU** - Board temperature, Battery voltage, Flash temperature

## Работа с панелями

### Перетаскивание (Drag & Drop)
1. Захватите заголовок панели
2. Перетащите в нужное место:
   - Слева от центра
   - Справа от центра
   - Сверху
   - Снизу
   - Или сделайте плавающей

### Resize (Изменение размера)
- Перетащите границу между панелями
- Пропорции сохранятся

### Скрыть/Показать
- **Windows → Output Monitor** - переключить видимость
- **Windows → Analog Monitor**
- **Windows → Variables Inspector**
- Кнопка **X** на панели закрывает её

### Сохранение Layout
1. **Desktops → Save Layout** - сохранить текущее расположение
2. **Desktops → Restore Default Layout** - вернуть к дефолту
3. Layout автоматически сохраняется при закрытии

## Горячие клавиши

### Файл
- **Ctrl+N** - New Configuration
- **Ctrl+O** - Open Configuration
- **Ctrl+S** - Save Configuration
- **Ctrl+Shift+S** - Save As
- **Ctrl+Q** - Exit

### Устройство
- **Ctrl+D** - Connect to Device

## Меню

### File
- New Configuration
- Open Configuration
- Save Configuration
- Save Configuration As
- Exit

### Edit
- Settings

### Desktops
- Save Layout
- Restore Default Layout

### Devices
- Connect
- Disconnect
- Read Configuration
- Write Configuration

### Tools
- CAN Monitor
- Data Logger

### Windows
- Output Monitor
- Analog Monitor
- Variables Inspector

### View
- Dark Mode (on/off)
- Application Style
  - Fluent Design (Custom)
  - windows11
  - windowsvista
  - Windows
  - Fusion

### Help
- Documentation
- About

## Добавление элементов

### Способ 1: Через кнопки
1. Выберите папку в дереве (например, OUT)
2. Нажмите кнопку **Add**
3. Заполните диалог
4. Нажмите OK

### Способ 2: Контекстное меню
1. Правый клик на папке
2. Выберите "Add Item"
3. Заполните диалог

### Способ 3: Двойной клик
- Двойной клик на элементе открывает редактор

## Группировка элементов

### Создать группу
1. Выберите папку или элемент
2. Нажмите кнопку **Group**
3. Появится "New Group"
4. Переименуйте двойным кликом

### Разгруппировать
1. Выберите группу
2. Нажмите кнопку **Ungroup**
3. Все элементы переместятся в родительскую папку

## Статусбар

Нижняя панель показывает:
- Статус устройства: **OFFLINE** / **ONLINE**
- CAN1: Статус CAN шины 1
- CAN2: Статус CAN шины 2
- OUTPUTS: Статус выходных каналов

## Различия между Classic и ECUMaster Style

| Функция | Classic | ECUMaster |
|---------|---------|-----------|
| Layout | Табы | Dock widgets |
| Мониторинг | Отдельная вкладка | Всегда видим |
| Организация | По типу | Иерархическое дерево |
| Группировка | Нет | Есть (папки) |
| Drag & Drop | Нет | Есть |
| Компактность | Средняя | Высокая |
| Все на экране | Нет | Да |

## Рекомендации

### Для начинающих
**Classic Style** - проще для первого знакомства

### Для опытных пользователей
**ECUMaster Style** - больше возможностей, компактнее, удобнее

### Для больших конфигураций
**ECUMaster Style** - группировка и дерево помогают организовать

### Для мониторинга
**ECUMaster Style** - real-time мониторинг всегда виден

## Известные ограничения

1. Real-time данные требуют подключения к устройству (пока не реализовано)
2. Некоторые функции будут добавлены позже:
   - CAN Monitor
   - Data Logger
   - Live Tuning

## Совместимость

Оба интерфейса используют одинаковый формат конфигурации (JSON).
Можно открыть файл, созданный в Classic, в ECUMaster и наоборот.

## Обратная связь

Если найдете проблемы или есть предложения:
- GitHub Issues: https://github.com/r2msport/pmu-30-configurator/issues

---

**© 2025 R2 m-sport. All rights reserved.**
