"""
Time Input Widgets

Widgets for entering time values that display in seconds (with decimal places)
but store internally as integer milliseconds.

Used for: retry delays, debounce times, timer targets, soft start durations, etc.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QDoubleSpinBox, QSpinBox, QLabel, QComboBox
)
from PyQt6.QtCore import pyqtSignal as Signal


class SecondsSpinBox(QDoubleSpinBox):
    """
    SpinBox that displays time in seconds but stores as milliseconds.

    Displays: "1.50 s" for 1500ms internally
    """

    # Signal emitted with milliseconds value
    valueChangedMs = Signal(int)

    def __init__(self, parent=None, decimals: int = 2,
                 min_ms: int = 0, max_ms: int = 600000,
                 suffix: str = " s"):
        """
        Initialize seconds spinbox.

        Args:
            parent: Parent widget
            decimals: Decimal places (default 2 = hundredths of a second)
            min_ms: Minimum value in milliseconds
            max_ms: Maximum value in milliseconds (default 10 minutes)
            suffix: Suffix to display (default " s")
        """
        super().__init__(parent)

        self._decimals = decimals
        self._factor = 10 ** decimals  # Convert factor

        # Setup spinbox
        self.setDecimals(decimals)
        self.setSuffix(suffix)
        self.setRange(min_ms / 1000.0, max_ms / 1000.0)
        self.setSingleStep(0.1)

        # Connect internal signal
        self.valueChanged.connect(self._on_value_changed)

    def _on_value_changed(self, value: float):
        """Emit value in milliseconds."""
        ms = int(value * 1000)
        self.valueChangedMs.emit(ms)

    def setValueMs(self, milliseconds: int):
        """Set value from milliseconds."""
        self.setValue(milliseconds / 1000.0)

    def valueMs(self) -> int:
        """Get value in milliseconds."""
        return int(self.value() * 1000)

    def setRangeMs(self, min_ms: int, max_ms: int):
        """Set range in milliseconds."""
        self.setRange(min_ms / 1000.0, max_ms / 1000.0)


class MillisecondsSpinBox(QSpinBox):
    """
    SpinBox that displays and stores milliseconds directly.
    Used when millisecond precision is needed.
    """

    def __init__(self, parent=None, min_ms: int = 0, max_ms: int = 600000):
        super().__init__(parent)
        self.setRange(min_ms, max_ms)
        self.setSuffix(" ms")
        self.setSingleStep(10)


class TimeInputWidget(QWidget):
    """
    Composite time input widget with unit selection.

    Allows user to input time in seconds or milliseconds with automatic
    conversion to milliseconds for internal storage.
    """

    valueChanged = Signal(int)  # Emits milliseconds

    def __init__(self, parent=None, default_unit: str = "s",
                 min_ms: int = 0, max_ms: int = 600000):
        """
        Initialize time input widget.

        Args:
            parent: Parent widget
            default_unit: Default unit ("s" or "ms")
            min_ms: Minimum value in milliseconds
            max_ms: Maximum value in milliseconds
        """
        super().__init__(parent)
        self._min_ms = min_ms
        self._max_ms = max_ms
        self._updating = False

        self._setup_ui(default_unit)
        self._connect_signals()

    def _setup_ui(self, default_unit: str):
        """Setup UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Seconds input (default visible)
        self.seconds_spin = QDoubleSpinBox()
        self.seconds_spin.setDecimals(2)
        self.seconds_spin.setRange(self._min_ms / 1000.0, self._max_ms / 1000.0)
        self.seconds_spin.setSingleStep(0.1)
        layout.addWidget(self.seconds_spin)

        # Milliseconds input (hidden by default)
        self.ms_spin = QSpinBox()
        self.ms_spin.setRange(self._min_ms, self._max_ms)
        self.ms_spin.setSingleStep(10)
        self.ms_spin.setVisible(False)
        layout.addWidget(self.ms_spin)

        # Unit selector
        self.unit_combo = QComboBox()
        self.unit_combo.addItem("s", "s")
        self.unit_combo.addItem("ms", "ms")
        self.unit_combo.setMaximumWidth(50)

        if default_unit == "ms":
            self.unit_combo.setCurrentIndex(1)
            self.seconds_spin.setVisible(False)
            self.ms_spin.setVisible(True)

        layout.addWidget(self.unit_combo)

    def _connect_signals(self):
        """Connect widget signals."""
        self.seconds_spin.valueChanged.connect(self._on_seconds_changed)
        self.ms_spin.valueChanged.connect(self._on_ms_changed)
        self.unit_combo.currentTextChanged.connect(self._on_unit_changed)

    def _on_seconds_changed(self, value: float):
        """Handle seconds spinbox change."""
        if not self._updating:
            self.valueChanged.emit(int(value * 1000))

    def _on_ms_changed(self, value: int):
        """Handle milliseconds spinbox change."""
        if not self._updating:
            self.valueChanged.emit(value)

    def _on_unit_changed(self, unit: str):
        """Handle unit selection change."""
        self._updating = True

        # Get current value in ms
        if self.seconds_spin.isVisible():
            ms_value = int(self.seconds_spin.value() * 1000)
        else:
            ms_value = self.ms_spin.value()

        # Switch visibility
        if unit == "s":
            self.seconds_spin.setVisible(True)
            self.ms_spin.setVisible(False)
            self.seconds_spin.setValue(ms_value / 1000.0)
        else:
            self.seconds_spin.setVisible(False)
            self.ms_spin.setVisible(True)
            self.ms_spin.setValue(ms_value)

        self._updating = False

    def setValueMs(self, milliseconds: int):
        """Set value from milliseconds."""
        self._updating = True

        if self.unit_combo.currentText() == "s":
            self.seconds_spin.setValue(milliseconds / 1000.0)
        else:
            self.ms_spin.setValue(milliseconds)

        self._updating = False

    def valueMs(self) -> int:
        """Get value in milliseconds."""
        if self.unit_combo.currentText() == "s":
            return int(self.seconds_spin.value() * 1000)
        return self.ms_spin.value()

    def setRangeMs(self, min_ms: int, max_ms: int):
        """Set range in milliseconds."""
        self._min_ms = min_ms
        self._max_ms = max_ms
        self.seconds_spin.setRange(min_ms / 1000.0, max_ms / 1000.0)
        self.ms_spin.setRange(min_ms, max_ms)


class DelayInputWidget(QWidget):
    """
    Specialized widget for delay inputs (True delay / False delay).

    Shows two time inputs side by side with labels.
    Stores values as milliseconds internally.
    """

    valuesChanged = Signal(int, int)  # (delay_on_ms, delay_off_ms)

    def __init__(self, parent=None,
                 label_on: str = "Delay On:",
                 label_off: str = "Delay Off:",
                 max_ms: int = 60000):
        """
        Initialize delay input widget.

        Args:
            parent: Parent widget
            label_on: Label for delay on (true delay)
            label_off: Label for delay off (false delay)
            max_ms: Maximum delay in milliseconds
        """
        super().__init__(parent)
        self._setup_ui(label_on, label_off, max_ms)

    def _setup_ui(self, label_on: str, label_off: str, max_ms: int):
        """Setup UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Delay On (True delay)
        layout.addWidget(QLabel(label_on))
        self.delay_on_spin = SecondsSpinBox(self, min_ms=0, max_ms=max_ms)
        self.delay_on_spin.valueChangedMs.connect(self._emit_changed)
        layout.addWidget(self.delay_on_spin)

        # Delay Off (False delay)
        layout.addWidget(QLabel(label_off))
        self.delay_off_spin = SecondsSpinBox(self, min_ms=0, max_ms=max_ms)
        self.delay_off_spin.valueChangedMs.connect(self._emit_changed)
        layout.addWidget(self.delay_off_spin)

        layout.addStretch()

    def _emit_changed(self):
        """Emit values changed signal."""
        self.valuesChanged.emit(
            self.delay_on_spin.valueMs(),
            self.delay_off_spin.valueMs()
        )

    def setDelayOnMs(self, milliseconds: int):
        """Set delay on value from milliseconds."""
        self.delay_on_spin.setValueMs(milliseconds)

    def setDelayOffMs(self, milliseconds: int):
        """Set delay off value from milliseconds."""
        self.delay_off_spin.setValueMs(milliseconds)

    def delayOnMs(self) -> int:
        """Get delay on in milliseconds."""
        return self.delay_on_spin.valueMs()

    def delayOffMs(self) -> int:
        """Get delay off in milliseconds."""
        return self.delay_off_spin.valueMs()

    def setValues(self, delay_on_ms: int, delay_off_ms: int):
        """Set both delay values."""
        self.setDelayOnMs(delay_on_ms)
        self.setDelayOffMs(delay_off_ms)

    def getValues(self) -> tuple:
        """Get both delay values as (delay_on_ms, delay_off_ms)."""
        return (self.delayOnMs(), self.delayOffMs())


class RetryDelayWidget(QWidget):
    """
    Widget for retry count and delay configuration.

    Shows retry count (integer) and delay between retries (in seconds).
    """

    valuesChanged = Signal(int, int)  # (retry_count, delay_ms)

    def __init__(self, parent=None, max_retries: int = 10, max_delay_ms: int = 60000):
        """
        Initialize retry delay widget.

        Args:
            parent: Parent widget
            max_retries: Maximum retry count
            max_delay_ms: Maximum delay between retries
        """
        super().__init__(parent)
        self._setup_ui(max_retries, max_delay_ms)

    def _setup_ui(self, max_retries: int, max_delay_ms: int):
        """Setup UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Retry count
        layout.addWidget(QLabel("Retries:"))
        self.retry_count_spin = QSpinBox()
        self.retry_count_spin.setRange(0, max_retries)
        self.retry_count_spin.setValue(3)
        self.retry_count_spin.valueChanged.connect(self._emit_changed)
        layout.addWidget(self.retry_count_spin)

        # Delay between retries
        layout.addWidget(QLabel("Delay:"))
        self.delay_spin = SecondsSpinBox(self, min_ms=0, max_ms=max_delay_ms)
        self.delay_spin.setValueMs(1000)  # Default 1 second
        self.delay_spin.valueChangedMs.connect(self._emit_changed)
        layout.addWidget(self.delay_spin)

        layout.addStretch()

    def _emit_changed(self):
        """Emit values changed signal."""
        self.valuesChanged.emit(
            self.retry_count_spin.value(),
            self.delay_spin.valueMs()
        )

    def setRetryCount(self, count: int):
        """Set retry count."""
        self.retry_count_spin.setValue(count)

    def setDelayMs(self, milliseconds: int):
        """Set delay from milliseconds."""
        self.delay_spin.setValueMs(milliseconds)

    def retryCount(self) -> int:
        """Get retry count."""
        return self.retry_count_spin.value()

    def delayMs(self) -> int:
        """Get delay in milliseconds."""
        return self.delay_spin.valueMs()

    def setValues(self, retry_count: int, delay_ms: int):
        """Set both values."""
        self.setRetryCount(retry_count)
        self.setDelayMs(delay_ms)

    def getValues(self) -> tuple:
        """Get both values as (retry_count, delay_ms)."""
        return (self.retryCount(), self.delayMs())


class DebounceWidget(QWidget):
    """
    Widget for debounce time configuration.

    Shows debounce time in seconds with millisecond precision.
    """

    valueChanged = Signal(int)  # debounce_ms

    def __init__(self, parent=None, max_ms: int = 5000):
        """
        Initialize debounce widget.

        Args:
            parent: Parent widget
            max_ms: Maximum debounce time
        """
        super().__init__(parent)
        self._setup_ui(max_ms)

    def _setup_ui(self, max_ms: int):
        """Setup UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        layout.addWidget(QLabel("Debounce:"))
        self.debounce_spin = SecondsSpinBox(
            self,
            decimals=3,  # Millisecond precision
            min_ms=0,
            max_ms=max_ms,
            suffix=" s"
        )
        self.debounce_spin.setValueMs(10)  # Default 10ms
        self.debounce_spin.valueChangedMs.connect(self.valueChanged.emit)
        layout.addWidget(self.debounce_spin)

        layout.addStretch()

    def setValueMs(self, milliseconds: int):
        """Set debounce value from milliseconds."""
        self.debounce_spin.setValueMs(milliseconds)

    def valueMs(self) -> int:
        """Get debounce value in milliseconds."""
        return self.debounce_spin.valueMs()
