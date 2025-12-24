# PMU-30 Configurator - План рефакторинга и улучшений

## Собранные TODO из кода

### Критические (блокируют функционал)
1. **device_controller.py:337** - `TODO: Implement configuration write protocol`
2. **device_controller.py:358** - `TODO: Implement firmware update protocol`
3. **can_tab.py:525** - `TODO: Implement actual DBC parsing using cantools`

### Подключения (не реализованы)
4. **device_controller.py:77** - `TODO: Implement Bluetooth device discovery`
5. **device_controller.py:177** - `TODO: Implement CAN bus connection`
6. **device_controller.py:184** - `TODO: Implement WiFi connection`
7. **device_controller.py:192** - `TODO: Implement Bluetooth connection`
8. **connection_dialog.py:261** - `TODO: Implement Bluetooth scanning`
9. **connection_dialog.py:267** - `TODO: Implement connection test`

### UI/Мониторинг
10. **monitoring_tab.py:60** - `TODO: Add output channel status widgets`
11. **monitoring_tab.py:99** - `TODO: Request current values from device`
12. **main_window_professional.py:1243** - `TODO: Add user error tracking`

---

## 1. Архитектура и структура кода

### 1.1 Разделение ответственности (SRP)
| Файл | Проблема | Решение |
|------|----------|---------|
| `main_window_professional.py` | 1300+ строк, много ответственностей | Разбить на: `MainWindowUI`, `MainWindowController`, `TelemetryHandler` |
| `device_controller.py` | Смешивает транспорт и протокол | Выделить `ProtocolHandler` отдельно |
| `config_manager.py` | 800+ строк | Разбить на: `ConfigLoader`, `ConfigSaver`, `ConfigValidator`, `ConfigMigrator` |

### 1.2 Унификация диалогов
```
dialogs/
├── base_channel_dialog.py      # Базовый класс (уже есть)
├── input_dialogs/
│   ├── analog_input_dialog.py
│   └── digital_input_dialog.py
├── output_dialogs/
│   ├── output_config_dialog.py
│   └── hbridge_dialog.py
├── can_dialogs/
│   ├── can_message_dialog.py
│   ├── can_input_dialog.py
│   └── can_import_dialog.py
└── logic_dialogs/
    ├── logic_dialog.py
    └── logic_function_dialog.py
```

### 1.3 Паттерн Observer для телеметрии
```python
# Текущий подход (прямые вызовы)
self.pmu_monitor.update_from_telemetry(telemetry)
self.analog_monitor.update_from_telemetry(telemetry.adc_values)
self.output_monitor.update_from_telemetry(...)

# Предлагаемый подход (Observer)
class TelemetryObserver(ABC):
    def on_telemetry_update(self, telemetry: TelemetryData): pass

class TelemetryDispatcher:
    observers: List[TelemetryObserver]
    def notify(self, telemetry):
        for obs in self.observers: obs.on_telemetry_update(telemetry)
```

---

## 2. Улучшение системы логирования

### 2.1 Текущее состояние
- Базовый logging в `utils/logger.py`
- Много `logger.debug()` разбросано по коду
- Нет структурированного логирования
- Нет ротации логов

### 2.2 Улучшения
```python
# utils/logger.py - расширенная версия
import logging
from logging.handlers import RotatingFileHandler
import json

class StructuredFormatter(logging.Formatter):
    """JSON-форматированные логи для анализа"""
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        if hasattr(record, 'extra_data'):
            log_data['data'] = record.extra_data
        return json.dumps(log_data)

def setup_logger(log_level=logging.INFO, max_size_mb=10, backup_count=5):
    log_dir = Path.home() / ".pmu30" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Ротация логов
    file_handler = RotatingFileHandler(
        log_dir / "pmu30.log",
        maxBytes=max_size_mb * 1024 * 1024,
        backupCount=backup_count
    )

    # Отдельный лог для ошибок
    error_handler = RotatingFileHandler(
        log_dir / "pmu30_errors.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)

    # Отдельный лог для протокола
    protocol_handler = RotatingFileHandler(
        log_dir / "pmu30_protocol.log",
        maxBytes=20 * 1024 * 1024,
        backupCount=2
    )
    protocol_logger = logging.getLogger("protocol")
```

### 2.3 Категории логов
| Категория | Logger name | Описание |
|-----------|-------------|----------|
| Protocol | `protocol` | TX/RX фреймы, CRC, таймауты |
| Config | `config` | Загрузка/сохранение, валидация |
| UI | `ui` | Действия пользователя |
| Telemetry | `telemetry` | Данные телеметрии |
| Device | `device` | Подключение, состояние |

---

## 3. Стабильность и обработка ошибок

### 3.1 Централизованная обработка исключений
```python
# utils/error_handler.py
class ErrorHandler:
    @staticmethod
    def handle_exception(exc: Exception, context: str = ""):
        """Централизованная обработка исключений"""
        logger.exception(f"Exception in {context}: {exc}")

        if isinstance(exc, ConnectionError):
            # Показать диалог переподключения
            pass
        elif isinstance(exc, ProtocolError):
            # Показать ошибку протокола
            pass
        elif isinstance(exc, ConfigValidationError):
            # Показать ошибки валидации
            pass
        else:
            # Общая ошибка
            pass

# Декоратор для UI методов
def safe_slot(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            ErrorHandler.handle_exception(e, func.__name__)
    return wrapper
```

### 3.2 Таймауты и reconnect
```python
# communication/connection_watchdog.py
class ConnectionWatchdog:
    def __init__(self, timeout_ms=5000, max_retries=3):
        self.timeout_ms = timeout_ms
        self.max_retries = max_retries
        self.last_response_time = 0
        self.retry_count = 0

    def on_response_received(self):
        self.last_response_time = time.time()
        self.retry_count = 0

    def check_connection(self) -> bool:
        if time.time() - self.last_response_time > self.timeout_ms / 1000:
            if self.retry_count < self.max_retries:
                self.retry_count += 1
                return self._attempt_reconnect()
            else:
                self._handle_disconnect()
                return False
        return True
```

### 3.3 Валидация входных данных
```python
# utils/validators.py
class InputValidator:
    @staticmethod
    def validate_channel_id(channel_id: str) -> Tuple[bool, str]:
        if not channel_id:
            return False, "Channel ID cannot be empty"
        if not re.match(r'^[a-z][a-z0-9_]*$', channel_id):
            return False, "Channel ID must start with letter, contain only lowercase letters, numbers, underscore"
        if len(channel_id) > 31:
            return False, "Channel ID too long (max 31 chars)"
        return True, ""

    @staticmethod
    def validate_voltage(voltage: float, min_v=0.0, max_v=30.0) -> Tuple[bool, str]:
        if voltage < min_v or voltage > max_v:
            return False, f"Voltage must be between {min_v}V and {max_v}V"
        return True, ""
```

---

## 4. Улучшения UI/UX

### 4.1 Индикация состояния подключения
```python
# ui/widgets/connection_status.py
class ConnectionStatusWidget(QWidget):
    """Виджет статуса подключения в статусбаре"""

    def __init__(self):
        self.status_icon = QLabel()
        self.status_text = QLabel("Disconnected")
        self.ping_label = QLabel("--ms")

    def set_connected(self, device_info: DeviceInfo):
        self.status_icon.setPixmap(QPixmap("icons/connected.png"))
        self.status_text.setText(f"{device_info.name} v{device_info.version}")

    def set_disconnected(self):
        self.status_icon.setPixmap(QPixmap("icons/disconnected.png"))
        self.status_text.setText("Disconnected")
        self.ping_label.setText("--ms")

    def update_ping(self, ping_ms: float):
        color = "green" if ping_ms < 50 else "orange" if ping_ms < 200 else "red"
        self.ping_label.setStyleSheet(f"color: {color}")
        self.ping_label.setText(f"{ping_ms:.0f}ms")
```

### 4.2 Undo/Redo для конфигурации
```python
# models/config_history.py
class ConfigHistory:
    def __init__(self, max_history=50):
        self._history: List[Dict] = []
        self._current_index = -1
        self._max_history = max_history

    def push(self, config: Dict, description: str):
        # Удалить redo историю
        self._history = self._history[:self._current_index + 1]
        self._history.append({
            'config': copy.deepcopy(config),
            'description': description,
            'timestamp': datetime.now()
        })
        self._current_index = len(self._history) - 1

    def undo(self) -> Optional[Dict]:
        if self._current_index > 0:
            self._current_index -= 1
            return self._history[self._current_index]['config']
        return None

    def redo(self) -> Optional[Dict]:
        if self._current_index < len(self._history) - 1:
            self._current_index += 1
            return self._history[self._current_index]['config']
        return None
```

### 4.3 Поиск каналов
```python
# ui/widgets/channel_search.py
class ChannelSearchWidget(QWidget):
    channel_selected = pyqtSignal(str, str)  # channel_type, channel_id

    def __init__(self):
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search channels... (Ctrl+F)")
        self.search_input.textChanged.connect(self._on_search)

        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self._on_item_selected)

    def _on_search(self, text: str):
        if len(text) < 2:
            self.results_list.clear()
            return

        # Поиск по всем каналам
        results = self.config_manager.search_channels(text)
        self._populate_results(results)
```

---

## 5. Оптимизация производительности

### 5.1 Кэширование
```python
# utils/cache.py
from functools import lru_cache

class ConfigCache:
    """Кэш для часто используемых данных конфигурации"""

    def __init__(self, config_manager):
        self._config_manager = config_manager
        self._channel_names_cache = {}
        self._channel_list_cache = {}

    def invalidate(self):
        self._channel_names_cache.clear()
        self._channel_list_cache.clear()

    def get_channel_names(self, channel_type: ChannelType) -> List[str]:
        if channel_type not in self._channel_names_cache:
            channels = self._config_manager.get_channels_by_type(channel_type)
            self._channel_names_cache[channel_type] = [ch['id'] for ch in channels]
        return self._channel_names_cache[channel_type]
```

### 5.2 Отложенная загрузка UI
```python
# Текущий подход - все вкладки создаются сразу
self.inputs_tab = InputsTab()
self.outputs_tab = OutputsTab()
self.can_tab = CANTab()
# ...

# Предлагаемый подход - lazy loading
class LazyTab:
    def __init__(self, tab_class, *args, **kwargs):
        self._tab_class = tab_class
        self._args = args
        self._kwargs = kwargs
        self._instance = None

    def get_widget(self) -> QWidget:
        if self._instance is None:
            self._instance = self._tab_class(*self._args, **self._kwargs)
        return self._instance
```

### 5.3 Батчинг обновлений телеметрии
```python
# ui/widgets/telemetry_buffer.py
class TelemetryBuffer:
    """Буферизация обновлений для снижения нагрузки на UI"""

    def __init__(self, update_interval_ms=100):
        self._buffer = {}
        self._timer = QTimer()
        self._timer.timeout.connect(self._flush)
        self._timer.start(update_interval_ms)

    def add(self, key: str, value: Any):
        self._buffer[key] = value

    def _flush(self):
        if self._buffer:
            self.batch_updated.emit(self._buffer.copy())
            self._buffer.clear()
```

---

## 6. Тестирование

### 6.1 Unit тесты
```
tests/
├── unit/
│   ├── test_protocol.py
│   ├── test_config_manager.py
│   ├── test_config_validator.py
│   ├── test_channel.py
│   └── test_telemetry.py
├── integration/
│   ├── test_device_connection.py
│   └── test_config_transfer.py
└── ui/
    ├── test_dialogs.py
    └── test_monitors.py
```

### 6.2 Mock устройства
```python
# tests/mocks/mock_device.py
class MockDevice:
    """Эмуляция PMU-30 для тестирования без железа"""

    def __init__(self):
        self.config = create_default_config()
        self.telemetry = MockTelemetryGenerator()

    def handle_frame(self, frame: bytes) -> bytes:
        msg_type = frame[3]
        if msg_type == MessageType.PING:
            return self._create_pong()
        elif msg_type == MessageType.GET_CONFIG:
            return self._create_config_response()
        # ...
```

---

## 7. Документация

### 7.1 Docstrings
- Добавить docstrings ко всем публичным методам
- Использовать Google style docstrings
- Добавить type hints везде

### 7.2 Архитектурная документация
```
docs/
├── architecture.md       # Общая архитектура
├── protocol.md          # Описание протокола
├── config_format.md     # Формат конфигурации
├── channel_types.md     # Типы каналов
└── development.md       # Руководство разработчика
```

---

## 8. Приоритеты реализации

### Фаза 1: Критические (1-2 недели)
1. [ ] Реализовать SET_CONFIG (запись конфигурации)
2. [ ] Улучшить обработку ошибок подключения
3. [ ] Добавить ротацию логов
4. [ ] Исправить reconnect при потере связи

### Фаза 2: Стабильность (2-3 недели)
5. [ ] Централизованная обработка исключений
6. [ ] Валидация входных данных в диалогах
7. [ ] Unit тесты для protocol.py и config_manager.py
8. [ ] Connection watchdog

### Фаза 3: UI/UX (2-3 недели)
9. [ ] Undo/Redo для конфигурации
10. [ ] Поиск каналов (Ctrl+F)
11. [ ] Улучшенный статус подключения
12. [ ] Lazy loading вкладок

### Фаза 4: Новый функционал (ongoing)
13. [ ] DBC парсер (cantools)
14. [ ] Bluetooth подключение
15. [ ] WiFi подключение
16. [ ] Firmware update

---

## 9. Метрики качества

| Метрика | Текущее | Цель |
|---------|---------|------|
| Покрытие тестами | ~0% | >60% |
| Cyclomatic complexity (max) | 30+ | <15 |
| Размер файла (max lines) | 1300+ | <500 |
| Type hints coverage | ~50% | >90% |
| Docstrings coverage | ~30% | >80% |
