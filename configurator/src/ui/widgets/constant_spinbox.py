"""
Constant Spinbox Widgets for PMU-30 Configurator

These spinboxes implement the GLOBAL RULE:
- Display values with 2 decimal places
- Store/emit values as integers (multiplied by 100)

Example:
  - User sees: 12.34
  - Internal value: 1234 (emitted via signals)
"""

from PyQt6.QtWidgets import QDoubleSpinBox, QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import pyqtSignal as Signal

from utils.constants import (
    CONSTANT_DECIMAL_PLACES,
    CONSTANT_SCALE,
    display_to_internal,
    internal_to_display,
)


class ConstantSpinBox(QDoubleSpinBox):
    """
    A spinbox that displays decimals but stores/emits integers.

    GLOBAL RULE: 2 decimal places display, integer * 100 storage.

    Signals:
        valueChangedInternal(int): Emitted when value changes, with internal integer value.

    Methods:
        setValueInternal(int): Set value using internal integer format.
        valueInternal() -> int: Get current value in internal integer format.
    """

    valueChangedInternal = Signal(int)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        # Configure for 2 decimal places display
        self.setDecimals(CONSTANT_DECIMAL_PLACES)
        self.setSingleStep(0.01)  # Step by 0.01 (1 internal unit)

        # Default range in display units
        self.setRange(-10000000.0, 10000000.0)

        # Connect to emit internal value
        self.valueChanged.connect(self._on_value_changed)

    def _on_value_changed(self, display_value: float):
        """Convert display value to internal and emit."""
        internal = display_to_internal(display_value)
        self.valueChangedInternal.emit(internal)

    def setValueInternal(self, internal_value: int):
        """
        Set the spinbox value using internal integer format.

        Args:
            internal_value: Integer value (e.g., 1234 for display of 12.34)
        """
        display_value = internal_to_display(internal_value)
        self.setValue(display_value)

    def valueInternal(self) -> int:
        """
        Get the current value in internal integer format.

        Returns:
            Integer value (e.g., 1234 for display of 12.34)
        """
        return display_to_internal(self.value())

    def setRangeInternal(self, min_internal: int, max_internal: int):
        """
        Set the range using internal integer values.

        Args:
            min_internal: Minimum internal value
            max_internal: Maximum internal value
        """
        min_display = internal_to_display(min_internal)
        max_display = internal_to_display(max_internal)
        self.setRange(min_display, max_display)

    def setMinimumInternal(self, min_internal: int):
        """Set minimum using internal value."""
        self.setMinimum(internal_to_display(min_internal))

    def setMaximumInternal(self, max_internal: int):
        """Set maximum using internal value."""
        self.setMaximum(internal_to_display(max_internal))


class ConstantSpinBoxWithSuffix(QWidget):
    """
    A constant spinbox with an attached label suffix.

    Useful for displaying units like "V", "A", "°C" etc.
    """

    valueChangedInternal = Signal(int)

    def __init__(self, suffix: str = "", parent: QWidget = None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._spinbox = ConstantSpinBox()
        layout.addWidget(self._spinbox)

        if suffix:
            self._suffix_label = QLabel(suffix)
            layout.addWidget(self._suffix_label)
        else:
            self._suffix_label = None

        # Forward signal
        self._spinbox.valueChangedInternal.connect(self.valueChangedInternal.emit)

    def spinbox(self) -> ConstantSpinBox:
        """Get the underlying spinbox."""
        return self._spinbox

    def setValueInternal(self, internal_value: int):
        """Set value using internal format."""
        self._spinbox.setValueInternal(internal_value)

    def valueInternal(self) -> int:
        """Get value in internal format."""
        return self._spinbox.valueInternal()

    def setValue(self, display_value: float):
        """Set value using display format."""
        self._spinbox.setValue(display_value)

    def value(self) -> float:
        """Get value in display format."""
        return self._spinbox.value()

    def setRange(self, min_val: float, max_val: float):
        """Set range in display values."""
        self._spinbox.setRange(min_val, max_val)

    def setRangeInternal(self, min_internal: int, max_internal: int):
        """Set range in internal values."""
        self._spinbox.setRangeInternal(min_internal, max_internal)

    def setSuffix(self, suffix: str):
        """Set or update the suffix label."""
        if self._suffix_label:
            self._suffix_label.setText(suffix)
        elif suffix:
            self._suffix_label = QLabel(suffix)
            self.layout().addWidget(self._suffix_label)


class ScalingFactorSpinBox(ConstantSpinBox):
    """
    Specialized spinbox for scaling factors (multiplier, divider, offset).

    Uses higher precision (4 decimal places) for scaling operations
    but still stores as integers (multiplied by 10000).
    """

    SCALING_DECIMAL_PLACES = 4
    SCALING_SCALE = 10000

    def __init__(self, parent: QWidget = None):
        super(ConstantSpinBox, self).__init__(parent)

        # 4 decimal places for scaling factors
        self.setDecimals(self.SCALING_DECIMAL_PLACES)
        self.setSingleStep(0.0001)

        # Default range
        self.setRange(-1000000.0, 1000000.0)

        # Connect signal
        self.valueChanged.connect(self._on_value_changed)

    def _on_value_changed(self, display_value: float):
        """Convert display value to internal and emit."""
        internal = int(round(display_value * self.SCALING_SCALE))
        self.valueChangedInternal.emit(internal)

    def setValueInternal(self, internal_value: int):
        """Set value using internal format (scaled by 10000)."""
        display_value = internal_value / self.SCALING_SCALE
        self.setValue(display_value)

    def valueInternal(self) -> int:
        """Get value in internal format (scaled by 10000)."""
        return int(round(self.value() * self.SCALING_SCALE))


class ThresholdSpinBox(ConstantSpinBox):
    """
    Specialized spinbox for threshold values.

    Uses 2 decimal places and typically constrained to positive values.
    """

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        # Thresholds are typically positive
        self.setRange(0.0, 100000.0)
        self.setSingleStep(0.1)


class PercentageSpinBox(ConstantSpinBox):
    """
    Specialized spinbox for percentage values (0-100%).

    Uses 2 decimal places, range 0.00 to 100.00.
    Internal: 0 to 10000.
    """

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        # Percentage range
        self.setRange(0.0, 100.0)
        self.setSingleStep(1.0)
        self.setSuffix(" %")


class VoltageSpinBox(ConstantSpinBox):
    """
    Specialized spinbox for voltage values.

    Uses 2 decimal places, typical range 0-30V for automotive.
    """

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        # Voltage range for automotive
        self.setRange(0.0, 30.0)
        self.setSingleStep(0.1)
        self.setSuffix(" V")


class CurrentSpinBox(ConstantSpinBox):
    """
    Specialized spinbox for current values in Amperes.

    Uses 2 decimal places.
    """

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        # Current range
        self.setRange(0.0, 100.0)
        self.setSingleStep(0.5)
        self.setSuffix(" A")


# Convenience function to create appropriate spinbox for a field type
def create_constant_spinbox(
    field_type: str = "default",
    suffix: str = "",
    min_val: float = None,
    max_val: float = None,
    parent: QWidget = None,
) -> ConstantSpinBox:
    """
    Factory function to create the appropriate constant spinbox.

    Args:
        field_type: Type of field ("default", "percentage", "voltage", "current", "scaling", "threshold")
        suffix: Optional suffix for display
        min_val: Optional minimum value (display units)
        max_val: Optional maximum value (display units)
        parent: Parent widget

    Returns:
        Appropriate ConstantSpinBox subclass
    """
    spinbox_map = {
        "percentage": PercentageSpinBox,
        "voltage": VoltageSpinBox,
        "current": CurrentSpinBox,
        "scaling": ScalingFactorSpinBox,
        "threshold": ThresholdSpinBox,
        "default": ConstantSpinBox,
    }

    spinbox_class = spinbox_map.get(field_type, ConstantSpinBox)
    spinbox = spinbox_class(parent)

    if suffix:
        spinbox.setSuffix(suffix)

    if min_val is not None and max_val is not None:
        spinbox.setRange(min_val, max_val)
    elif min_val is not None:
        spinbox.setMinimum(min_val)
    elif max_val is not None:
        spinbox.setMaximum(max_val)

    return spinbox
