"""
Quantity/Unit Selector Widget

Reusable widget for selecting quantity type, unit, and decimal places.
Used in Number, Table, CAN Input, and Analog Input dialogs.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QComboBox, QSpinBox, QFormLayout, QGroupBox
)
from PyQt6.QtCore import pyqtSignal as Signal

from models.quantities import (
    QUANTITIES, get_quantity_names, get_units_for_quantity,
    get_default_unit, DisplayConfig
)


class QuantityUnitSelector(QWidget):
    """
    Widget for selecting quantity, unit, and decimal places.

    Emits changed signal when any value changes.
    """

    changed = Signal()

    def __init__(self, parent=None, show_decimal_places: bool = True,
                 layout_mode: str = "horizontal"):
        """
        Initialize the selector.

        Args:
            parent: Parent widget
            show_decimal_places: Whether to show decimal places spinbox
            layout_mode: "horizontal" or "vertical" layout
        """
        super().__init__(parent)
        self._show_decimal_places = show_decimal_places
        self._updating = False

        self._setup_ui(layout_mode)
        self._connect_signals()

    def _setup_ui(self, layout_mode: str):
        """Setup the UI components."""
        if layout_mode == "horizontal":
            layout = QHBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(8)

            # Quantity/Unit label
            layout.addWidget(QLabel("Quantity/Unit:"))

            # Quantity combo
            self.quantity_combo = QComboBox()
            self.quantity_combo.setMinimumWidth(120)
            for name in get_quantity_names():
                self.quantity_combo.addItem(name)
            layout.addWidget(self.quantity_combo)

            # Unit combo
            self.unit_combo = QComboBox()
            self.unit_combo.setMinimumWidth(80)
            layout.addWidget(self.unit_combo)

            if self._show_decimal_places:
                # Decimal places
                layout.addWidget(QLabel("Decimal places:"))
                self.decimal_spin = QSpinBox()
                self.decimal_spin.setRange(0, 4)
                self.decimal_spin.setValue(0)
                self.decimal_spin.setMinimumWidth(50)
                layout.addWidget(self.decimal_spin)

            layout.addStretch()

        else:  # vertical / form layout
            layout = QFormLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)

            # Quantity combo
            self.quantity_combo = QComboBox()
            for name in get_quantity_names():
                self.quantity_combo.addItem(name)

            # Unit combo
            self.unit_combo = QComboBox()

            # Horizontal for quantity and unit
            qu_layout = QHBoxLayout()
            qu_layout.setSpacing(4)
            qu_layout.addWidget(self.quantity_combo, 2)
            qu_layout.addWidget(self.unit_combo, 1)

            layout.addRow("Quantity/Unit:", qu_layout)

            if self._show_decimal_places:
                self.decimal_spin = QSpinBox()
                self.decimal_spin.setRange(0, 4)
                self.decimal_spin.setValue(0)
                layout.addRow("Decimal places:", self.decimal_spin)

        # Initialize unit combo
        self._update_units()

    def _connect_signals(self):
        """Connect widget signals."""
        self.quantity_combo.currentTextChanged.connect(self._on_quantity_changed)
        self.unit_combo.currentTextChanged.connect(self._on_value_changed)
        if self._show_decimal_places:
            self.decimal_spin.valueChanged.connect(self._on_value_changed)

    def _on_quantity_changed(self, quantity: str):
        """Handle quantity selection change."""
        if self._updating:
            return
        self._update_units()
        self._on_value_changed()

    def _on_value_changed(self):
        """Handle any value change."""
        if not self._updating:
            self.changed.emit()

    def _update_units(self):
        """Update unit combo based on selected quantity."""
        self._updating = True

        quantity = self.quantity_combo.currentText()
        units = get_units_for_quantity(quantity)
        default_unit = get_default_unit(quantity)

        self.unit_combo.clear()
        for unit in units:
            self.unit_combo.addItem(unit.symbol)

        # Select default unit
        index = self.unit_combo.findText(default_unit)
        if index >= 0:
            self.unit_combo.setCurrentIndex(index)

        self._updating = False

    def get_quantity(self) -> str:
        """Get selected quantity name."""
        return self.quantity_combo.currentText()

    def set_quantity(self, quantity: str):
        """Set selected quantity."""
        self._updating = True
        index = self.quantity_combo.findText(quantity)
        if index >= 0:
            self.quantity_combo.setCurrentIndex(index)
            self._update_units()
        self._updating = False

    def get_unit(self) -> str:
        """Get selected unit symbol."""
        return self.unit_combo.currentText()

    def set_unit(self, unit: str):
        """Set selected unit."""
        self._updating = True
        index = self.unit_combo.findText(unit)
        if index >= 0:
            self.unit_combo.setCurrentIndex(index)
        self._updating = False

    def get_decimal_places(self) -> int:
        """Get decimal places value."""
        if self._show_decimal_places:
            return self.decimal_spin.value()
        return 0

    def set_decimal_places(self, places: int):
        """Set decimal places value."""
        if self._show_decimal_places:
            self._updating = True
            self.decimal_spin.setValue(places)
            self._updating = False

    def get_config(self) -> DisplayConfig:
        """Get current configuration as DisplayConfig."""
        return DisplayConfig(
            quantity=self.get_quantity(),
            unit=self.get_unit(),
            decimal_places=self.get_decimal_places()
        )

    def set_config(self, config: DisplayConfig):
        """Set configuration from DisplayConfig."""
        self._updating = True
        self.set_quantity(config.quantity)
        self.set_unit(config.unit)
        self.set_decimal_places(config.decimal_places)
        self._updating = False

    def get_dict(self) -> dict:
        """Get configuration as dictionary."""
        return self.get_config().to_dict()

    def set_from_dict(self, data: dict):
        """Set configuration from dictionary."""
        self.set_config(DisplayConfig.from_dict(data))


class QuantityUnitGroup(QGroupBox):
    """
    Grouped version of quantity/unit selector for use in dialogs.
    """

    changed = Signal()

    def __init__(self, title: str = "Display Settings", parent=None):
        super().__init__(title, parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI."""
        layout = QVBoxLayout(self)

        self.selector = QuantityUnitSelector(
            self,
            show_decimal_places=True,
            layout_mode="vertical"
        )
        self.selector.changed.connect(self.changed.emit)
        layout.addWidget(self.selector)

    def get_config(self) -> DisplayConfig:
        return self.selector.get_config()

    def set_config(self, config: DisplayConfig):
        self.selector.set_config(config)

    def get_dict(self) -> dict:
        return self.selector.get_dict()

    def set_from_dict(self, data: dict):
        self.selector.set_from_dict(data)


class CompactQuantitySelector(QWidget):
    """
    Compact inline quantity/unit selector.

    Shows: [Quantity v] [Unit v] [0 ^v] (decimal places)
    """

    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._updating = False
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Setup compact UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Quantity combo
        self.quantity_combo = QComboBox()
        self.quantity_combo.setMinimumWidth(100)
        self.quantity_combo.setMaximumWidth(150)
        for name in get_quantity_names():
            self.quantity_combo.addItem(name)
        layout.addWidget(self.quantity_combo)

        # Unit combo
        self.unit_combo = QComboBox()
        self.unit_combo.setMinimumWidth(60)
        self.unit_combo.setMaximumWidth(80)
        layout.addWidget(self.unit_combo)

        # Decimal places spinbox
        self.decimal_spin = QSpinBox()
        self.decimal_spin.setRange(0, 4)
        self.decimal_spin.setPrefix(".")
        self.decimal_spin.setToolTip("Decimal places")
        self.decimal_spin.setMaximumWidth(50)
        layout.addWidget(self.decimal_spin)

        self._update_units()

    def _connect_signals(self):
        """Connect signals."""
        self.quantity_combo.currentTextChanged.connect(self._on_quantity_changed)
        self.unit_combo.currentTextChanged.connect(self._on_changed)
        self.decimal_spin.valueChanged.connect(self._on_changed)

    def _on_quantity_changed(self, quantity: str):
        """Handle quantity change."""
        if not self._updating:
            self._update_units()
            self._on_changed()

    def _on_changed(self):
        """Handle any value change."""
        if not self._updating:
            self.changed.emit()

    def _update_units(self):
        """Update unit combo for selected quantity."""
        self._updating = True

        quantity = self.quantity_combo.currentText()
        units = get_units_for_quantity(quantity)
        default_unit = get_default_unit(quantity)

        self.unit_combo.clear()
        for unit in units:
            self.unit_combo.addItem(unit.symbol)

        index = self.unit_combo.findText(default_unit)
        if index >= 0:
            self.unit_combo.setCurrentIndex(index)

        self._updating = False

    def get_config(self) -> DisplayConfig:
        """Get current display configuration."""
        return DisplayConfig(
            quantity=self.quantity_combo.currentText(),
            unit=self.unit_combo.currentText(),
            decimal_places=self.decimal_spin.value()
        )

    def set_config(self, config: DisplayConfig):
        """Set display configuration."""
        self._updating = True

        index = self.quantity_combo.findText(config.quantity)
        if index >= 0:
            self.quantity_combo.setCurrentIndex(index)
        self._update_units()

        index = self.unit_combo.findText(config.unit)
        if index >= 0:
            self.unit_combo.setCurrentIndex(index)

        self.decimal_spin.setValue(config.decimal_places)

        self._updating = False

    def get_dict(self) -> dict:
        """Get as dictionary."""
        return self.get_config().to_dict()

    def set_from_dict(self, data: dict):
        """Set from dictionary."""
        self.set_config(DisplayConfig.from_dict(data))
