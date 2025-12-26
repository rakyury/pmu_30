# План рефакторинга и тестового покрытия PMU-30

## Текущее состояние (обновлено 2025-12-26)

### Firmware (C)

**Модули (31 файл в firmware/src/)** - **445 тестов в 15 файлах**:
| Модуль | Тесты | Кол-во | Статус |
|--------|-------|--------|--------|
| pmu_protection.c | test_protection.c | 11 | ✅ |
| pmu_can.c | test_can.c | 10 | ✅ |
| pmu_logging.c | test_logging.c | 16 | ✅ |
| pmu_ui.c | test_ui.c | 15 | ✅ |
| pmu_lua.c | test_lua.c | 24 | ✅ |
| pmu_channel.c | test_channel.c | 34 | ✅ |
| pmu_config_json.c | test_config_json.c | 28 | ✅ |
| pmu_logic.c | test_logic_ext.c | 29 | ✅ |
| pmu_profet.c | test_profet.c | 37 | ✅ |
| pmu_adc.c | test_adc.c | 23 | ✅ |
| pmu_timer.c | test_timer.c | 28 | ✅ |
| pmu_pid.c | test_pid.c | 44 | ✅ |
| pmu_hbridge.c | test_hbridge.c | 47 | ✅ |
| pmu_can_stream.c | test_can_stream.c | 53 | ✅ |
| pmu_protocol.c | test_protocol.c | 46 | ✅ |
| pmu_handler.c | ❌ Нет | 0 | 🟢 Средний |
| pmu_datalog.c | ❌ Нет | 0 | 🟢 Средний |
| pmu_wifi.c | ❌ Нет | 0 | 🟢 Средний |
| pmu_bluetooth.c | ❌ Нет | 0 | 🟢 Средний |
| pmu_lin.c | ❌ Нет | 0 | 🟢 Средний |
| pmu_blinkmarine.c | ❌ Нет | 0 | 🟢 Средний |

**Текущее покрытие**: 15/21 основных модулей (~71%)

### Configurator (Python)

**~654 тестов в 33 файлах**:
```
tests/
├── ui/                    # PyQt6 диалоги и виджеты (10 файлов, 242 теста)
├── integration/           # Интеграция с эмулятором (14 файлов, 172 теста)
├── unit/                  # Unit тесты (4 файла, 135 тестов)
├── test_config_*.py       # Валидация конфигов (28 тестов)
├── test_protocol.py       # Протокол связи (27 тестов)
├── test_telemetry.py      # Телеметрия (30 тестов)
└── test_comm_manager.py   # Менеджер соединений (20 тестов)
```

**Статус тестирования**:
| Категория | Модули | Покрытие |
|-----------|--------|----------|
| Dialogs | 25+ диалогов | ~75% ✅ |
| Widgets | 15+ виджетов | ~65% ✅ |
| Tabs | 8 вкладок | ~20% |
| Models | channel.py, undo_manager.py | ~80% ✅ |
| Controllers | device_controller.py | ~50% |
| Utils | theme.py, dbc_parser.py | ~30% |

---

## Фаза 1: Критические тесты Firmware (1 неделя)

### 1.1 test_channel.c - Система каналов
```c
// Тестируемые функции:
void test_channel_init(void);
void test_channel_register(void);
void test_channel_get_value(void);
void test_channel_set_value(void);
void test_channel_get_by_name(void);
void test_channel_list(void);
void test_channel_id_ranges(void);
void test_system_channels(void);

// Сценарии:
// - Регистрация 100+ каналов
// - Поиск по ID и имени
// - Граничные значения (min/max)
// - Переполнение буфера
```

### 1.2 test_config_json.c - JSON парсер
```c
// Тестируемые функции:
void test_json_parse_digital_input(void);
void test_json_parse_analog_input(void);
void test_json_parse_power_output(void);
void test_json_parse_logic_function(void);
void test_json_parse_can_config(void);
void test_json_parse_hbridge(void);
void test_json_get_channel_ref(void);

// Сценарии:
// - Валидный JSON
// - Невалидный JSON (graceful failure)
// - Отсутствующие поля (defaults)
// - Numeric channel IDs
// - Все типы каналов
```

### 1.3 test_logic.c - Логические функции
```c
// Тестируемые функции:
void test_logic_and(void);
void test_logic_or(void);
void test_logic_not(void);
void test_logic_xor(void);
void test_logic_greater_than(void);
void test_logic_less_than(void);
void test_logic_equal(void);
void test_logic_timer_delay(void);
void test_logic_chain(void);  // Цепочка функций

// Сценарии:
// - Все логические операции
// - Сравнения с константами
// - Цепочки функций
// - Циклические зависимости (ошибка)
```

### 1.4 test_profet.c - Управление выходами
```c
// Тестируемые функции:
void test_profet_init(void);
void test_profet_set_duty(void);
void test_profet_get_current(void);
void test_profet_protection_short(void);
void test_profet_protection_overcurrent(void);
void test_profet_soft_start(void);
void test_profet_pwm_frequency(void);

// Сценарии:
// - PWM 0-100%
// - Режимы защиты
// - Soft-start рампа
// - Чтение тока
```

---

## Фаза 2: Важные тесты Firmware (1 неделя)

### 2.1 test_adc.c
```c
void test_adc_init(void);
void test_adc_read_channel(void);
void test_adc_calibration(void);
void test_adc_averaging(void);
void test_adc_voltage_conversion(void);
```

### 2.2 test_timer.c
```c
void test_timer_create(void);
void test_timer_start_stop(void);
void test_timer_oneshot(void);
void test_timer_periodic(void);
void test_timer_delay_on_off(void);
```

### 2.3 test_pid.c
```c
void test_pid_init(void);
void test_pid_update(void);
void test_pid_limits(void);
void test_pid_reset(void);
void test_pid_tuning(void);
```

### 2.4 test_hbridge.c
```c
void test_hbridge_init(void);
void test_hbridge_set_direction(void);
void test_hbridge_pwm_control(void);
void test_hbridge_position_control(void);
void test_hbridge_protection(void);
```

### 2.5 test_can_stream.c
```c
void test_can_stream_init(void);
void test_can_stream_tx(void);
void test_can_stream_rx(void);
void test_can_stream_signals(void);
void test_can_stream_compound(void);
```

### 2.6 test_protocol.c
```c
void test_protocol_parse_command(void);
void test_protocol_build_response(void);
void test_protocol_config_transfer(void);
void test_protocol_telemetry(void);
```

---

## Фаза 3: Рефакторинг Configurator (2 недели)

### 3.1 Архитектурные улучшения

#### 3.1.1 Унификация BaseChannelDialog
Все диалоги каналов наследуют от единого базового класса:
```python
class BaseChannelDialog(QDialog):
    """Унифицированный базовый диалог для всех типов каналов."""

    # Общие методы
    def _create_identification_group(self) -> QGroupBox
    def _create_channel_selector(self) -> ChannelSelectorWidget
    def _validate_channel_id(self) -> bool
    def get_config(self) -> Dict[str, Any]
    def _load_config(self, config: Dict[str, Any])
```

#### 3.1.2 Удаление дублирования
- [ ] Объединить `input_config_dialog.py` с `base_channel_dialog.py`
- [ ] Вынести общую логику channel selector
- [ ] Унифицировать валидацию во всех диалогах

#### 3.1.3 Модульность виджетов
```python
# Новые реиспользуемые виджеты:
class ChannelIdSpinBox(QSpinBox)      # Выбор channel_id с валидацией
class CANIdInput(QWidget)              # CAN ID с hex/dec переключением
class TimeIntervalInput(QWidget)       # Ввод времени (ms/s/min)
class ThresholdInput(QWidget)          # Ввод порога с единицами
```

### 3.2 Тесты для Configurator

#### 3.2.1 Unit тесты (tests/unit/)
```python
# test_channel_model.py
def test_channel_id_assignment()
def test_channel_type_detection()
def test_channel_validation()
def test_channel_serialization()

# test_config_validation.py
def test_duplicate_channel_ids()
def test_invalid_channel_references()
def test_circular_dependencies()
def test_missing_required_fields()

# test_undo_manager.py
def test_undo_redo()
def test_undo_limit()
def test_compound_operations()
```

#### 3.2.2 Тесты диалогов (tests/ui/)
```python
# test_dialogs_complete.py - расширить существующие
def test_all_dialogs_open_close()
def test_all_dialogs_validation()
def test_all_dialogs_save_load()

# Новые файлы:
# test_dialogs_tables.py - Table2D, Table3D
# test_dialogs_hbridge.py - HBridge, Wiper, Blinker
# test_dialogs_can.py - CAN Message, CAN Input, CAN Output
# test_dialogs_special.py - PID, Timer, Filter
```

#### 3.2.3 Тесты виджетов (tests/ui/)
```python
# test_widgets_monitors.py
def test_analog_monitor()
def test_digital_monitor()
def test_output_monitor()
def test_can_monitor()
def test_hbridge_monitor()

# test_widgets_controls.py
def test_channel_selector()
def test_quantity_selector()
def test_time_input()
```

#### 3.2.4 Интеграционные тесты (tests/integration/)
```python
# Уже есть хорошая основа, добавить:
# test_full_config_cycle.py
def test_create_config_from_scratch()
def test_modify_existing_config()
def test_config_upload_download()
def test_real_time_monitoring()

# test_channel_id_migration.py
def test_legacy_config_fails()  # Подтвердить что старые конфиги не работают
def test_new_config_format()
```

---

## Фаза 4: CI/CD улучшения

### 4.1 Расширение GitHub Actions

```yaml
# .github/workflows/ci.yml additions

  # Firmware Tests (add after build)
  firmware-tests:
    name: Firmware Unit Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install PlatformIO
        run: pip install platformio
      - name: Run Tests
        run: |
          cd firmware
          pio test -e pmu30_test

  # Integration Tests (optional, with emulator)
  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: [firmware-build, configurator-tests]
    steps:
      - uses: actions/checkout@v4
      - name: Build Emulator
        run: |
          cd firmware
          pio run -e pmu30_emulator
      - name: Start Emulator
        run: |
          ./firmware/.pio/build/pmu30_emulator/program &
          sleep 3
      - name: Run Integration Tests
        run: |
          cd configurator
          pip install -r requirements.txt
          python -m pytest tests/integration -v --timeout=120

  # Coverage Report
  coverage:
    name: Code Coverage
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install Coverage Tools
        run: pip install pytest-cov
      - name: Run Coverage
        run: |
          cd configurator
          python -m pytest tests/ --cov=src --cov-report=xml
      - name: Upload Coverage
        uses: codecov/codecov-action@v3
```

### 4.2 Pre-commit hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.0
    hooks:
      - id: mypy
        additional_dependencies: [types-PyQt6]
```

---

## Фаза 5: Документация и метрики

### 5.1 Цели покрытия

| Компонент | Текущее | Цель |
|-----------|---------|------|
| Firmware критичные модули | 24% | 85% |
| Firmware все модули | 10% | 70% |
| Configurator models | 30% | 90% |
| Configurator dialogs | 50% | 80% |
| Configurator widgets | 20% | 70% |
| Integration tests | N/A | 50 сценариев |

### 5.2 Метрики качества

```python
# Добавить в CI:
# - Cyclomatic complexity < 15
# - Function length < 50 lines
# - File length < 500 lines
# - No TODO/FIXME в production code
```

---

## Приоритезация задач

### Фаза 1-2: Критичные тесты Firmware ✅ ЗАВЕРШЕНО
1. ✅ test_channel.c (34 теста)
2. ✅ test_config_json.c (28 тестов)
3. ✅ test_logic.c (29 тестов)
4. ✅ test_profet.c (37 тестов)
5. ✅ test_adc.c (23 теста)
6. ✅ test_timer.c (28 тестов)
7. ✅ test_pid.c (44 теста)
8. ✅ test_hbridge.c (47 тестов)
9. ✅ test_can_stream.c (53 теста)
10. ✅ test_protocol.c (46 тестов)

### Фаза 3: Рефакторинг Configurator ✅ ЗАВЕРШЕНО
11. ✅ Унификация диалогов
12. ✅ Расширение UI тестов (242 теста)
13. ✅ Integration тесты (172 теста)

### Фаза 4: CI/CD и покрытие ✅ ЗАВЕРШЕНО
14. ✅ GitHub Actions интеграция
15. ✅ Coverage reports (Codecov)
16. ✅ Pre-commit hooks
17. ✅ pyproject.toml с конфигурацией

### Фаза 5: Документация ✅ ЗАВЕРШЕНО
18. ✅ Обновление test README (firmware)
19. ✅ Обновление test README (configurator)
20. ✅ Обновление плана тестирования

---

## Команды для запуска тестов

### Firmware
```bash
# Все тесты
cd firmware && pio test -e pmu30_test

# Конкретный модуль
pio test -e pmu30_test -f test_protection

# С verbose
pio test -e pmu30_test -v
```

### Configurator
```bash
# Unit тесты
cd configurator && python -m pytest tests/unit -v

# UI тесты
python -m pytest tests/ui -v --timeout=60

# Integration тесты (требует эмулятор)
python -m pytest tests/integration -v

# Все тесты с coverage
python -m pytest tests/ --cov=src --cov-report=html
```

---

## Риски и митигация

| Риск | Митигация |
|------|-----------|
| Qt тесты виснут в CI | --timeout=60, skip MainWindow |
| Эмулятор недоступен | Skip integration tests |
| Flaky tests | Retry logic, stable fixtures |
| Coverage regress | Minimum coverage gate in CI |
