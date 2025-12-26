"""
3D Table Configuration Dialog
Lookup table with X and Y axis channels and auto-generated values
Features MoTeC M1-style 3D surface visualization
"""

from PyQt6.QtWidgets import (
    QGroupBox, QSpinBox, QDoubleSpinBox, QPushButton,
    QLabel, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QVBoxLayout, QHBoxLayout, QMessageBox,
    QTabWidget, QWidget, QSplitter, QCheckBox, QSlider, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QPainter
from typing import Dict, Any, Optional, List
import numpy as np

from .base_channel_dialog import BaseChannelDialog
from models.channel import ChannelType

# Try to import pyqtgraph for 3D visualization
try:
    import pyqtgraph as pg
    import pyqtgraph.opengl as gl
    HAS_3D = True
except ImportError:
    HAS_3D = False
    pg = None
    gl = None


class VerticalLabel(QLabel):
    """Label that displays text vertically (rotated 90 degrees counter-clockwise)"""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setMinimumWidth(20)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.translate(0, self.height())
        painter.rotate(-90)
        painter.drawText(0, 0, self.height(), self.width(), Qt.AlignmentFlag.AlignCenter, self.text())

    def minimumSizeHint(self):
        size = super().minimumSizeHint()
        return QSize(size.height(), size.width())

    def sizeHint(self):
        size = super().sizeHint()
        return QSize(size.height(), size.width())


class Table3DDialog(BaseChannelDialog):
    """Dialog for configuring 3D lookup table channels."""

    def __init__(self, parent=None,
                 config: Optional[Dict[str, Any]] = None,
                 available_channels: Optional[Dict[str, List[str]]] = None,
                 existing_channels: Optional[List[Dict[str, Any]]] = None):
        super().__init__(parent, config, available_channels, ChannelType.TABLE_3D, existing_channels)

        self._create_axis_group()
        self._create_table_group()

        # Connect signals
        self.x_min_spin.valueChanged.connect(self._update_size_labels)
        self.x_max_spin.valueChanged.connect(self._update_size_labels)
        self.x_step_spin.valueChanged.connect(self._update_size_labels)
        self.y_min_spin.valueChanged.connect(self._update_size_labels)
        self.y_max_spin.valueChanged.connect(self._update_size_labels)
        self.y_step_spin.valueChanged.connect(self._update_size_labels)

        # Load config if editing
        if config:
            self._load_specific_config(config)

        self._update_size_labels()

        # Finalize UI sizing
        self._finalize_ui()

    def _create_axis_group(self):
        """Create axis configuration group"""
        axis_group = QGroupBox("Axis Configuration")
        layout = QGridLayout()
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)
        row = 0

        # Decimal places
        layout.addWidget(QLabel("Decimal places:"), row, 0)
        self.decimal_spin = QSpinBox()
        self.decimal_spin.setRange(0, 6)
        self.decimal_spin.setValue(0)
        layout.addWidget(self.decimal_spin, row, 1)
        row += 1

        # X axis channel (full width)
        layout.addWidget(QLabel("Axis X channel: *"), row, 0)
        self.x_channel_widget, self.x_channel_edit = self._create_channel_selector(
            "Select X axis channel..."
        )
        layout.addWidget(self.x_channel_widget, row, 1, 1, 3)
        row += 1

        # X axis: min, max
        layout.addWidget(QLabel("min:"), row, 0)
        self.x_min_spin = QDoubleSpinBox()
        self.x_min_spin.setRange(-1000000, 1000000)
        self.x_min_spin.setDecimals(2)
        self.x_min_spin.setValue(0)
        layout.addWidget(self.x_min_spin, row, 1)

        layout.addWidget(QLabel("max:"), row, 2)
        self.x_max_spin = QDoubleSpinBox()
        self.x_max_spin.setRange(-1000000, 1000000)
        self.x_max_spin.setDecimals(2)
        self.x_max_spin.setValue(100)
        layout.addWidget(self.x_max_spin, row, 3)
        row += 1

        # X axis: step and columns
        layout.addWidget(QLabel("step:"), row, 0)
        self.x_step_spin = QDoubleSpinBox()
        self.x_step_spin.setRange(0.001, 100000)
        self.x_step_spin.setDecimals(2)
        self.x_step_spin.setValue(10)
        layout.addWidget(self.x_step_spin, row, 1)

        self.columns_label = QLabel("columns: 11")
        self.columns_label.setStyleSheet("color: #0078d4;")
        layout.addWidget(self.columns_label, row, 2, 1, 2)
        row += 1

        # Y axis channel (full width)
        layout.addWidget(QLabel("Axis Y channel: *"), row, 0)
        self.y_channel_widget, self.y_channel_edit = self._create_channel_selector(
            "Select Y axis channel..."
        )
        layout.addWidget(self.y_channel_widget, row, 1, 1, 3)
        row += 1

        # Y axis: min, max
        layout.addWidget(QLabel("min:"), row, 0)
        self.y_min_spin = QDoubleSpinBox()
        self.y_min_spin.setRange(-1000000, 1000000)
        self.y_min_spin.setDecimals(2)
        self.y_min_spin.setValue(0)
        layout.addWidget(self.y_min_spin, row, 1)

        layout.addWidget(QLabel("max:"), row, 2)
        self.y_max_spin = QDoubleSpinBox()
        self.y_max_spin.setRange(-1000000, 1000000)
        self.y_max_spin.setDecimals(2)
        self.y_max_spin.setValue(100)
        layout.addWidget(self.y_max_spin, row, 3)
        row += 1

        # Y axis: step and rows
        layout.addWidget(QLabel("step:"), row, 0)
        self.y_step_spin = QDoubleSpinBox()
        self.y_step_spin.setRange(0.001, 100000)
        self.y_step_spin.setDecimals(2)
        self.y_step_spin.setValue(10)
        layout.addWidget(self.y_step_spin, row, 1)

        self.rows_label = QLabel("rows: 11")
        self.rows_label.setStyleSheet("color: #0078d4;")
        layout.addWidget(self.rows_label, row, 2, 1, 2)
        row += 1

        # Create button
        self.create_btn = QPushButton("Create Table")
        self.create_btn.clicked.connect(self._create_table)
        layout.addWidget(self.create_btn, row, 0, 1, 4)

        axis_group.setLayout(layout)
        self.content_layout.addWidget(axis_group)

    def _create_table_group(self):
        """Create table editor group with 2D and 3D views"""
        table_group = QGroupBox("Table Data")
        main_layout = QVBoxLayout()

        # Create tab widget for 2D/3D views
        self.view_tabs = QTabWidget()

        # === 2D Table View Tab ===
        table_tab = QWidget()
        table_layout = QVBoxLayout(table_tab)

        # X axis label (horizontal, centered above table)
        self.x_axis_label = QLabel("X: -")
        self.x_axis_label.setStyleSheet("font-weight: bold; color: #0078d4;")
        table_layout.addWidget(self.x_axis_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Horizontal layout for Y label + table
        table_row = QHBoxLayout()

        # Y axis label (vertical, on the left of table)
        self.y_axis_label = VerticalLabel("Y: -")
        self.y_axis_label.setStyleSheet("font-weight: bold; color: #0078d4;")
        table_row.addWidget(self.y_axis_label)

        self.table_widget = QTableWidget()
        self.table_widget.setMinimumHeight(200)
        self.table_widget.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table_widget.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table_widget.cellChanged.connect(self._update_heat_map)
        self.table_widget.cellChanged.connect(self._update_3d_view)
        table_row.addWidget(self.table_widget)

        table_layout.addLayout(table_row)
        self.view_tabs.addTab(table_tab, "2D Table")

        # === 3D Surface View Tab ===
        if HAS_3D:
            self._create_3d_view_tab()
        else:
            # Fallback if pyqtgraph OpenGL not available
            no_3d_tab = QWidget()
            no_3d_layout = QVBoxLayout(no_3d_tab)
            no_3d_label = QLabel(
                "3D visualization requires pyqtgraph with OpenGL support.\n"
                "Install with: pip install pyqtgraph PyOpenGL"
            )
            no_3d_label.setStyleSheet("color: #b0b0b0;")
            no_3d_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_3d_layout.addWidget(no_3d_label)
            self.view_tabs.addTab(no_3d_tab, "3D View")

        main_layout.addWidget(self.view_tabs)

        # Info label
        info = QLabel("Click 'Create Table' to generate axis values, then edit output values.")
        info.setStyleSheet("color: #b0b0b0; font-style: italic;")
        main_layout.addWidget(info)

        table_group.setLayout(main_layout)
        self.content_layout.addWidget(table_group)

    def _create_3d_view_tab(self):
        """Create 3D surface visualization tab"""
        view_3d_tab = QWidget()
        layout = QVBoxLayout(view_3d_tab)

        # Controls bar
        controls = QHBoxLayout()

        # Wireframe toggle
        self.wireframe_check = QCheckBox("Wireframe")
        self.wireframe_check.setChecked(False)
        self.wireframe_check.stateChanged.connect(self._update_3d_view)
        controls.addWidget(self.wireframe_check)

        # Smooth shading toggle
        self.smooth_check = QCheckBox("Smooth")
        self.smooth_check.setChecked(True)
        self.smooth_check.stateChanged.connect(self._update_3d_view)
        controls.addWidget(self.smooth_check)

        # Show grid
        self.grid_check = QCheckBox("Grid")
        self.grid_check.setChecked(True)
        self.grid_check.stateChanged.connect(self._toggle_grid)
        controls.addWidget(self.grid_check)

        controls.addStretch()

        # Reset view button
        reset_btn = QPushButton("Reset View")
        reset_btn.clicked.connect(self._reset_3d_view)
        controls.addWidget(reset_btn)

        layout.addLayout(controls)

        # 3D OpenGL widget
        self.gl_widget = gl.GLViewWidget()
        self.gl_widget.setBackgroundColor('#1e1e1e')  # Dark background
        self.gl_widget.setCameraPosition(distance=50, elevation=30, azimuth=45)
        # Make widget expand to fill available space
        self.gl_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.gl_widget.setMinimumHeight(300)

        # Add grid
        self.grid_item = gl.GLGridItem()
        self.grid_item.scale(10, 10, 1)
        self.grid_item.setColor((100, 100, 100, 100))
        self.gl_widget.addItem(self.grid_item)

        # Placeholder for surface plot
        self.surface_item = None

        layout.addWidget(self.gl_widget, stretch=1)

        # Instructions
        instr = QLabel("Left-drag to rotate, Right-drag to pan, Scroll to zoom")
        instr.setStyleSheet("color: #808080; font-size: 10px;")
        instr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(instr)

        self.view_tabs.addTab(view_3d_tab, "3D View")

    def _update_3d_view(self):
        """Update the 3D surface visualization"""
        if not HAS_3D or not hasattr(self, 'gl_widget'):
            return

        if self.table_widget.rowCount() == 0 or self.table_widget.columnCount() == 0:
            return

        # Get data from table
        rows = self.table_widget.rowCount()
        cols = self.table_widget.columnCount()

        # Create numpy arrays for x, y, z
        x_values = []
        for col in range(cols):
            header = self.table_widget.horizontalHeaderItem(col)
            if header:
                try:
                    x_values.append(float(header.text()))
                except ValueError:
                    x_values.append(col)
            else:
                x_values.append(col)

        y_values = []
        for row in range(rows):
            header = self.table_widget.verticalHeaderItem(row)
            if header:
                try:
                    y_values.append(float(header.text()))
                except ValueError:
                    y_values.append(row)
            else:
                y_values.append(row)

        # Get Z data (table values)
        z_data = np.zeros((rows, cols))
        for row in range(rows):
            for col in range(cols):
                item = self.table_widget.item(row, col)
                if item:
                    try:
                        z_data[row, col] = float(item.text())
                    except ValueError:
                        z_data[row, col] = 0.0

        # Normalize axes for better visualization
        x = np.array(x_values)
        y = np.array(y_values)

        # Scale to reasonable range
        x_range = max(x) - min(x) if len(x) > 1 else 1
        y_range = max(y) - min(y) if len(y) > 1 else 1
        z_range = z_data.max() - z_data.min() if z_data.max() != z_data.min() else 1

        scale_factor = max(x_range, y_range, z_range)
        if scale_factor == 0:
            scale_factor = 1

        x_norm = (x - x.min()) / scale_factor * 20 - 10
        y_norm = (y - y.min()) / scale_factor * 20 - 10
        z_norm = (z_data - z_data.min()) / scale_factor * 20

        # Create meshgrid
        X, Y = np.meshgrid(x_norm, y_norm)

        # Create color map (blue to red gradient based on Z value)
        z_normalized = (z_data - z_data.min()) / (z_range if z_range > 0 else 1)
        colors = np.zeros((rows, cols, 4), dtype=np.float32)

        for r in range(rows):
            for c in range(cols):
                val = z_normalized[r, c]
                # Blue -> Cyan -> Green -> Yellow -> Red
                if val < 0.25:
                    t = val / 0.25
                    colors[r, c] = [0, t, 1, 0.9]  # Blue to Cyan
                elif val < 0.5:
                    t = (val - 0.25) / 0.25
                    colors[r, c] = [0, 1, 1 - t, 0.9]  # Cyan to Green
                elif val < 0.75:
                    t = (val - 0.5) / 0.25
                    colors[r, c] = [t, 1, 0, 0.9]  # Green to Yellow
                else:
                    t = (val - 0.75) / 0.25
                    colors[r, c] = [1, 1 - t, 0, 0.9]  # Yellow to Red

        # Remove old surface
        if self.surface_item is not None:
            self.gl_widget.removeItem(self.surface_item)

        # Create new surface
        smooth = self.smooth_check.isChecked() if hasattr(self, 'smooth_check') else True
        wireframe = self.wireframe_check.isChecked() if hasattr(self, 'wireframe_check') else False

        self.surface_item = gl.GLSurfacePlotItem(
            x=x_norm, y=y_norm, z=z_norm,
            colors=colors,
            shader='shaded' if smooth else 'normalColor',
            drawEdges=wireframe,
            edgeColor=(1, 1, 1, 0.3)
        )
        self.gl_widget.addItem(self.surface_item)

    def _toggle_grid(self, state):
        """Toggle grid visibility"""
        if HAS_3D and hasattr(self, 'grid_item'):
            self.grid_item.setVisible(state == Qt.CheckState.Checked.value)

    def _reset_3d_view(self):
        """Reset 3D view to default camera position"""
        if HAS_3D and hasattr(self, 'gl_widget'):
            self.gl_widget.setCameraPosition(distance=50, elevation=30, azimuth=45)

    def _update_size_labels(self):
        """Update the columns and rows count labels"""
        x_values = self._generate_axis_values(
            self.x_min_spin.value(),
            self.x_max_spin.value(),
            self.x_step_spin.value()
        )
        y_values = self._generate_axis_values(
            self.y_min_spin.value(),
            self.y_max_spin.value(),
            self.y_step_spin.value()
        )
        self.columns_label.setText(f"columns: {len(x_values)}")
        self.rows_label.setText(f"rows: {len(y_values)}")

    def _generate_axis_values(self, min_val: float, max_val: float, step: float) -> List[float]:
        """Generate axis values based on min, max, step"""
        if step <= 0 or min_val >= max_val:
            return [min_val]

        values = []
        v = min_val
        while v <= max_val + 0.0001:  # Small epsilon for floating point
            values.append(round(v, 2))
            v += step
        return values

    def _create_table(self):
        """Generate table based on axis configuration"""
        # Validate axis channels are selected
        x_channel = self.x_channel_edit.text().strip()
        y_channel = self.y_channel_edit.text().strip()
        if not x_channel or not y_channel:
            errors = []
            if not x_channel:
                errors.append("X axis channel")
            if not y_channel:
                errors.append("Y axis channel")
            QMessageBox.warning(
                self, "Validation Error",
                f"Please select: {', '.join(errors)}"
            )
            return

        x_values = self._generate_axis_values(
            self.x_min_spin.value(),
            self.x_max_spin.value(),
            self.x_step_spin.value()
        )
        y_values = self._generate_axis_values(
            self.y_min_spin.value(),
            self.y_max_spin.value(),
            self.y_step_spin.value()
        )

        self.table_widget.blockSignals(True)
        self.table_widget.setRowCount(len(y_values))
        self.table_widget.setColumnCount(len(x_values))

        # Update axis labels
        self.x_axis_label.setText(f"X: {x_channel}")
        self.y_axis_label.setText(f"Y: {y_channel}")

        # Set headers
        x_headers = [str(v) for v in x_values]
        y_headers = [str(v) for v in y_values]
        self.table_widget.setHorizontalHeaderLabels(x_headers)
        self.table_widget.setVerticalHeaderLabels(y_headers)

        # Initialize cells with 0
        for row in range(len(y_values)):
            for col in range(len(x_values)):
                item = QTableWidgetItem("0")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_widget.setItem(row, col, item)

        self.table_widget.blockSignals(False)
        self._update_heat_map()
        self._update_3d_view()

    def _get_heat_map_color(self, value: float, min_val: float, max_val: float) -> QColor:
        """Calculate heat map color for a value (blue -> green -> yellow -> red)"""
        if max_val == min_val:
            return QColor(255, 255, 255)  # White for uniform values

        # Normalize to 0-1 range
        normalized = (value - min_val) / (max_val - min_val)
        normalized = max(0.0, min(1.0, normalized))

        # Color gradient: blue (0) -> cyan (0.25) -> green (0.5) -> yellow (0.75) -> red (1)
        if normalized < 0.25:
            t = normalized / 0.25
            r, g, b = 0, int(255 * t), 255
        elif normalized < 0.5:
            t = (normalized - 0.25) / 0.25
            r, g, b = 0, 255, int(255 * (1 - t))
        elif normalized < 0.75:
            t = (normalized - 0.5) / 0.25
            r, g, b = int(255 * t), 255, 0
        else:
            t = (normalized - 0.75) / 0.25
            r, g, b = 255, int(255 * (1 - t)), 0

        return QColor(r, g, b)

    def _update_heat_map(self):
        """Update cell colors based on values"""
        if self.table_widget.rowCount() == 0 or self.table_widget.columnCount() == 0:
            return

        # Collect all values
        values = []
        for row in range(self.table_widget.rowCount()):
            for col in range(self.table_widget.columnCount()):
                item = self.table_widget.item(row, col)
                if item:
                    try:
                        values.append(float(item.text()))
                    except ValueError:
                        values.append(0.0)

        if not values:
            return

        min_val = min(values)
        max_val = max(values)

        # Apply colors
        self.table_widget.blockSignals(True)
        for row in range(self.table_widget.rowCount()):
            for col in range(self.table_widget.columnCount()):
                item = self.table_widget.item(row, col)
                if item:
                    try:
                        val = float(item.text())
                    except ValueError:
                        val = 0.0
                    color = self._get_heat_map_color(val, min_val, max_val)
                    item.setBackground(color)
        self.table_widget.blockSignals(False)

    def _load_specific_config(self, config: Dict[str, Any]):
        """Load type-specific configuration"""
        # Axis configuration - use helper to show channel names
        self._set_channel_edit_value(self.x_channel_edit, config.get("x_axis_channel"))
        self._set_channel_edit_value(self.y_channel_edit, config.get("y_axis_channel"))
        self.x_min_spin.setValue(config.get("x_min", 0.0))
        self.x_max_spin.setValue(config.get("x_max", 100.0))
        self.x_step_spin.setValue(config.get("x_step", 10.0))
        self.y_min_spin.setValue(config.get("y_min", 0.0))
        self.y_max_spin.setValue(config.get("y_max", 100.0))
        self.y_step_spin.setValue(config.get("y_step", 10.0))
        self.decimal_spin.setValue(config.get("decimal_places", 0))

        # Load existing table data
        x_values = config.get("x_values", [])
        y_values = config.get("y_values", [])
        data = config.get("data", [])

        if x_values and y_values and data:
            self.table_widget.blockSignals(True)
            self.table_widget.setRowCount(len(y_values))
            self.table_widget.setColumnCount(len(x_values))

            # Update axis labels with display names
            x_channel_display = self.x_channel_edit.text() or "-"
            y_channel_display = self.y_channel_edit.text() or "-"
            self.x_axis_label.setText(f"X: {x_channel_display}")
            self.y_axis_label.setText(f"Y: {y_channel_display}")

            x_headers = [str(v) for v in x_values]
            y_headers = [str(v) for v in y_values]
            self.table_widget.setHorizontalHeaderLabels(x_headers)
            self.table_widget.setVerticalHeaderLabels(y_headers)

            for row_idx, row_data in enumerate(data):
                if row_idx < len(y_values):
                    for col_idx, val in enumerate(row_data):
                        if col_idx < len(x_values):
                            item = QTableWidgetItem(str(val))
                            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                            self.table_widget.setItem(row_idx, col_idx, item)

            self.table_widget.blockSignals(False)
            self._update_heat_map()
            self._update_3d_view()

    def _validate_specific(self) -> List[str]:
        """Validate type-specific fields"""
        errors = []

        if not self.x_channel_edit.text().strip():
            errors.append("X axis channel is required")

        if not self.y_channel_edit.text().strip():
            errors.append("Y axis channel is required")

        if self.x_min_spin.value() >= self.x_max_spin.value():
            errors.append("X min must be less than X max")

        if self.x_step_spin.value() <= 0:
            errors.append("X step must be greater than 0")

        if self.y_min_spin.value() >= self.y_max_spin.value():
            errors.append("Y min must be less than Y max")

        if self.y_step_spin.value() <= 0:
            errors.append("Y step must be greater than 0")

        if self.table_widget.rowCount() == 0 or self.table_widget.columnCount() == 0:
            errors.append("Please create table first")

        return errors

    def get_config(self) -> Dict[str, Any]:
        """Get full configuration"""
        config = self.get_base_config()

        # Get X values from headers
        x_values = []
        for col in range(self.table_widget.columnCount()):
            header = self.table_widget.horizontalHeaderItem(col)
            if header:
                try:
                    x_values.append(float(header.text()))
                except ValueError:
                    x_values.append(0.0)

        # Get Y values from headers
        y_values = []
        for row in range(self.table_widget.rowCount()):
            header = self.table_widget.verticalHeaderItem(row)
            if header:
                try:
                    y_values.append(float(header.text()))
                except ValueError:
                    y_values.append(0.0)

        # Get data from cells (2D matrix)
        data = []
        for row in range(self.table_widget.rowCount()):
            row_data = []
            for col in range(self.table_widget.columnCount()):
                item = self.table_widget.item(row, col)
                if item:
                    try:
                        row_data.append(float(item.text()))
                    except ValueError:
                        row_data.append(0.0)
                else:
                    row_data.append(0.0)
            data.append(row_data)

        # Get channel IDs using helper method
        x_axis_channel_id = self._get_channel_id_from_edit(self.x_channel_edit)
        y_axis_channel_id = self._get_channel_id_from_edit(self.y_channel_edit)

        config.update({
            "x_axis_channel": x_axis_channel_id if x_axis_channel_id else "",
            "y_axis_channel": y_axis_channel_id if y_axis_channel_id else "",
            "x_min": self.x_min_spin.value(),
            "x_max": self.x_max_spin.value(),
            "x_step": self.x_step_spin.value(),
            "x_values": x_values,
            "y_min": self.y_min_spin.value(),
            "y_max": self.y_max_spin.value(),
            "y_step": self.y_step_spin.value(),
            "y_values": y_values,
            "data": data,
            "decimal_places": self.decimal_spin.value()
        })

        return config
