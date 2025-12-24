"""
Channel Dependency Graph - Visual representation of channel relationships.

Shows how channels depend on each other:
- Inputs → Logic → Outputs
- Timers, Filters, Tables as intermediate nodes
- Interactive: click to edit, hover for details
"""

import logging
import math
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QPushButton,
    QComboBox, QLabel, QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsTextItem,
    QGraphicsRectItem, QMenu, QToolTip, QCheckBox, QSpinBox,
    QGraphicsPathItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QTimer
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath,
    QRadialGradient, QLinearGradient, QAction, QWheelEvent
)

logger = logging.getLogger(__name__)


# Channel type colors
CHANNEL_COLORS = {
    'digital_input': '#4CAF50',   # Green
    'analog_input': '#8BC34A',    # Light Green
    'power_output': '#2196F3',    # Blue
    'hbridge': '#3F51B5',         # Indigo
    'can_rx': '#00BCD4',          # Cyan
    'can_tx': '#009688',          # Teal
    'logic': '#FF9800',           # Orange
    'number': '#FFC107',          # Amber
    'table_2d': '#795548',        # Brown
    'table_3d': '#795548',        # Brown
    'switch': '#9C27B0',          # Purple
    'timer': '#E91E63',           # Pink
    'filter': '#607D8B',          # Blue Grey
    'enum': '#673AB7',            # Deep Purple
    'lua_script': '#FF5722',      # Deep Orange
    'pid': '#F44336',             # Red
    'blinkmarine_keypad': '#CDDC39',  # Lime
}

# Category grouping
CHANNEL_CATEGORIES = {
    'Inputs': ['digital_input', 'analog_input', 'can_rx', 'blinkmarine_keypad'],
    'Processing': ['logic', 'number', 'filter', 'timer', 'table_2d', 'table_3d', 'enum', 'switch', 'pid', 'lua_script'],
    'Outputs': ['power_output', 'hbridge', 'can_tx'],
}


@dataclass
class GraphNode:
    """Represents a channel node in the graph."""
    id: str
    name: str
    channel_type: str
    x: float = 0
    y: float = 0
    inputs: List[str] = None
    outputs: List[str] = None
    item: QGraphicsItem = None
    label_item: QGraphicsTextItem = None
    is_active: bool = False
    value: float = 0.0

    def __post_init__(self):
        if self.inputs is None:
            self.inputs = []
        if self.outputs is None:
            self.outputs = []


class ChannelNodeItem(QGraphicsEllipseItem):
    """Visual representation of a channel node."""

    def __init__(self, node: GraphNode, radius: float = 25):
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.node = node
        self.radius = radius
        self._hovered = False
        self._selected = False

        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

        self._update_appearance()

    def _update_appearance(self):
        """Update node appearance based on state."""
        color = QColor(CHANNEL_COLORS.get(self.node.channel_type, '#888888'))

        if self.node.is_active:
            color = color.lighter(130)

        # Create gradient
        gradient = QRadialGradient(0, 0, self.radius)
        gradient.setColorAt(0, color.lighter(150))
        gradient.setColorAt(0.7, color)
        gradient.setColorAt(1, color.darker(120))

        self.setBrush(QBrush(gradient))

        # Border
        pen_width = 3 if self._selected else 2 if self._hovered else 1
        pen_color = Qt.GlobalColor.white if self._selected else color.darker(150)
        self.setPen(QPen(pen_color, pen_width))

    def hoverEnterEvent(self, event):
        self._hovered = True
        self._update_appearance()
        # Show tooltip
        tooltip = f"{self.node.name}\nType: {self.node.channel_type}"
        if self.node.value != 0:
            tooltip += f"\nValue: {self.node.value:.2f}"
        QToolTip.showText(event.screenPos(), tooltip)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self._update_appearance()
        super().hoverLeaveEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.node.x = value.x()
            self.node.y = value.y()
            # Update label position
            if self.node.label_item:
                label = self.node.label_item
                label.setPos(value.x() - label.boundingRect().width() / 2, value.y() + 30)
            # Update connected edges
            scene = self.scene()
            if scene and hasattr(scene, 'update_edges'):
                scene.update_edges()
        return super().itemChange(change, value)

    def set_active(self, active: bool, value: float = 0.0):
        """Set node active state (for real-time highlighting)."""
        self.node.is_active = active
        self.node.value = value
        self._update_appearance()


class EdgeItem(QGraphicsPathItem):
    """Arrow edge connecting two nodes."""

    def __init__(self, source: ChannelNodeItem, target: ChannelNodeItem):
        super().__init__()
        self.source = source
        self.target = target
        self._active = False

        self.setZValue(-1)  # Behind nodes
        self._update_path()

    def _update_path(self):
        """Update edge path based on node positions."""
        if not self.source or not self.target:
            return

        # Get positions
        src_pos = self.source.scenePos()
        tgt_pos = self.target.scenePos()

        # Calculate direction
        dx = tgt_pos.x() - src_pos.x()
        dy = tgt_pos.y() - src_pos.y()
        length = math.sqrt(dx * dx + dy * dy)

        if length < 1:
            return

        # Normalize
        dx /= length
        dy /= length

        # Start and end points (at node edges)
        src_radius = self.source.radius
        tgt_radius = self.target.radius

        start = QPointF(src_pos.x() + dx * src_radius, src_pos.y() + dy * src_radius)
        end = QPointF(tgt_pos.x() - dx * tgt_radius, tgt_pos.y() - dy * tgt_radius)

        # Create path
        path = QPainterPath()
        path.moveTo(start)

        # Curved line (bezier)
        ctrl_offset = length * 0.3
        ctrl1 = QPointF(start.x() + dx * ctrl_offset, start.y() + dy * ctrl_offset)
        ctrl2 = QPointF(end.x() - dx * ctrl_offset, end.y() - dy * ctrl_offset)
        path.cubicTo(ctrl1, ctrl2, end)

        # Arrow head
        arrow_size = 10
        angle = math.atan2(-dy, -dx)
        arrow_p1 = QPointF(
            end.x() + arrow_size * math.cos(angle - math.pi / 6),
            end.y() + arrow_size * math.sin(angle - math.pi / 6)
        )
        arrow_p2 = QPointF(
            end.x() + arrow_size * math.cos(angle + math.pi / 6),
            end.y() + arrow_size * math.sin(angle + math.pi / 6)
        )
        path.moveTo(end)
        path.lineTo(arrow_p1)
        path.moveTo(end)
        path.lineTo(arrow_p2)

        self.setPath(path)

        # Style
        color = QColor('#4CAF50') if self._active else QColor('#666666')
        pen = QPen(color, 2 if self._active else 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self.setPen(pen)

    def set_active(self, active: bool):
        """Set edge active state."""
        self._active = active
        self._update_path()


class ChannelGraphScene(QGraphicsScene):
    """Scene containing the channel dependency graph."""

    node_clicked = pyqtSignal(str)  # channel_id
    node_double_clicked = pyqtSignal(str)  # channel_id

    def __init__(self):
        super().__init__()
        self.nodes: Dict[str, GraphNode] = {}
        self.node_items: Dict[str, ChannelNodeItem] = {}
        self.edges: List[EdgeItem] = []

        self.setBackgroundBrush(QBrush(QColor('#1e1e1e')))

    def build_graph(self, channels: List[Dict[str, Any]]):
        """Build graph from channel list."""
        self.clear()
        self.nodes.clear()
        self.node_items.clear()
        self.edges.clear()

        # Build channel_id -> node_id mapping for resolving numeric references
        channel_id_to_node_id = {}

        # Create nodes
        for ch in channels:
            ch_id = ch.get('id', '')
            if not ch_id:
                continue

            node = GraphNode(
                id=ch_id,
                name=ch.get('name', ch_id),
                channel_type=ch.get('type', 'logic'),
                inputs=ch.get('input_channels', [])
            )
            self.nodes[ch_id] = node

            # Map numeric channel_id to node id
            numeric_id = ch.get('channel_id')
            if numeric_id is not None:
                channel_id_to_node_id[numeric_id] = ch_id

        # Resolve numeric input references to node IDs
        for node in self.nodes.values():
            resolved_inputs = []
            for input_ref in node.inputs:
                if isinstance(input_ref, int):
                    # Numeric reference - look up in mapping
                    if input_ref in channel_id_to_node_id:
                        resolved_inputs.append(channel_id_to_node_id[input_ref])
                elif isinstance(input_ref, str):
                    # String reference - use as-is
                    resolved_inputs.append(input_ref)
            node.inputs = resolved_inputs

        # Calculate outputs (reverse of inputs)
        for node in self.nodes.values():
            for input_id in node.inputs:
                if input_id in self.nodes:
                    self.nodes[input_id].outputs.append(node.id)

        # Layout nodes
        self._layout_nodes()

        # Create visual items
        for node in self.nodes.values():
            self._create_node_item(node)

        # Create edges
        for node in self.nodes.values():
            for input_id in node.inputs:
                if input_id in self.node_items:
                    edge = EdgeItem(self.node_items[input_id], self.node_items[node.id])
                    self.edges.append(edge)
                    self.addItem(edge)

    def _layout_nodes(self):
        """Layout nodes in columns by category."""
        # Group by category
        categories = {'Inputs': [], 'Processing': [], 'Outputs': [], 'Other': []}

        for node in self.nodes.values():
            placed = False
            for cat_name, types in CHANNEL_CATEGORIES.items():
                if node.channel_type in types:
                    categories[cat_name].append(node)
                    placed = True
                    break
            if not placed:
                categories['Other'].append(node)

        # Position nodes
        x_positions = {'Inputs': 0, 'Processing': 250, 'Outputs': 500, 'Other': 500}
        y_spacing = 70

        for cat_name, nodes in categories.items():
            if not nodes:
                continue
            x = x_positions[cat_name]
            y_start = -(len(nodes) - 1) * y_spacing / 2

            for i, node in enumerate(nodes):
                node.x = x
                node.y = y_start + i * y_spacing

    def _create_node_item(self, node: GraphNode):
        """Create visual item for node."""
        item = ChannelNodeItem(node)
        item.setPos(node.x, node.y)
        self.addItem(item)
        self.node_items[node.id] = item
        node.item = item

        # Label
        label = QGraphicsTextItem(node.name[:12])
        label.setDefaultTextColor(Qt.GlobalColor.white)
        font = QFont('Segoe UI', 8)
        label.setFont(font)
        label.setPos(node.x - label.boundingRect().width() / 2, node.y + 30)
        self.addItem(label)
        node.label_item = label

    def update_edges(self):
        """Update all edge paths after node movement."""
        for edge in self.edges:
            edge._update_path()

    def update_telemetry(self, channel_values: Dict[str, float]):
        """Update node active states from telemetry."""
        for ch_id, value in channel_values.items():
            if ch_id in self.node_items:
                item = self.node_items[ch_id]
                item.set_active(value != 0, value)

        # Update edge highlighting
        for edge in self.edges:
            src_active = edge.source.node.is_active if edge.source else False
            edge.set_active(src_active)

    def mousePressEvent(self, event):
        item = self.itemAt(event.scenePos(), self.views()[0].transform() if self.views() else None)
        if isinstance(item, ChannelNodeItem):
            self.node_clicked.emit(item.node.id)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.scenePos(), self.views()[0].transform() if self.views() else None)
        if isinstance(item, ChannelNodeItem):
            self.node_double_clicked.emit(item.node.id)
        super().mouseDoubleClickEvent(event)


class ChannelGraphView(QGraphicsView):
    """View for the channel graph with zoom/pan."""

    def __init__(self, scene: ChannelGraphScene):
        super().__init__(scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._zoom = 1.0

    def wheelEvent(self, event: QWheelEvent):
        """Zoom with mouse wheel."""
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._zoom *= factor
        self._zoom = max(0.2, min(3.0, self._zoom))
        self.setTransform(self.transform().scale(factor, factor))

    def fit_in_view(self):
        """Fit all content in view."""
        self.fitInView(self.scene().itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom = 1.0


class ChannelGraphWidget(QWidget):
    """Widget for visualizing channel dependencies."""

    channel_selected = pyqtSignal(str)  # channel_id
    channel_edit_requested = pyqtSignal(str)  # channel_id
    refresh_requested = pyqtSignal()  # Request data refresh from parent

    def __init__(self, parent=None):
        super().__init__(parent)

        self.channels: List[Dict[str, Any]] = []

        self._init_ui()

    def _init_ui(self):
        """Initialize UI."""
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Toolbar
        toolbar = QToolBar()
        toolbar.setMovable(False)

        # Zoom controls
        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setFixedSize(28, 28)
        zoom_in_btn.clicked.connect(self._zoom_in)
        toolbar.addWidget(zoom_in_btn)

        zoom_out_btn = QPushButton("-")
        zoom_out_btn.setFixedSize(28, 28)
        zoom_out_btn.clicked.connect(self._zoom_out)
        toolbar.addWidget(zoom_out_btn)

        fit_btn = QPushButton("Fit")
        fit_btn.setFixedSize(40, 28)
        fit_btn.clicked.connect(self._fit_view)
        toolbar.addWidget(fit_btn)

        toolbar.addSeparator()

        # Filter by type
        toolbar.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All", "all")
        self.filter_combo.addItem("Inputs", "inputs")
        self.filter_combo.addItem("Processing", "processing")
        self.filter_combo.addItem("Outputs", "outputs")
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self.filter_combo)

        toolbar.addSeparator()

        # Live update toggle
        self.live_checkbox = QCheckBox("Live")
        self.live_checkbox.setChecked(False)
        self.live_checkbox.toggled.connect(self._on_live_toggled)
        toolbar.addWidget(self.live_checkbox)

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_graph)
        toolbar.addWidget(refresh_btn)

        layout.addWidget(toolbar)

        # Graph view
        self.scene = ChannelGraphScene()
        self.scene.node_clicked.connect(self.channel_selected.emit)
        self.scene.node_double_clicked.connect(self.channel_edit_requested.emit)

        self.view = ChannelGraphView(self.scene)
        self.view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.view, 1)  # Stretch factor 1 to fill space

        # Status bar
        self.status_label = QLabel("No channels loaded")
        layout.addWidget(self.status_label)

    def set_channels(self, channels: List[Dict[str, Any]]):
        """Set channel list and rebuild graph."""
        self.channels = channels
        self._rebuild_graph()

    def _rebuild_graph(self):
        """Rebuild the graph from channels."""
        # Filter channels if needed
        filter_value = self.filter_combo.currentData()
        filtered = self.channels

        if filter_value == "inputs":
            types = CHANNEL_CATEGORIES['Inputs']
            filtered = [c for c in self.channels if c.get('type') in types]
        elif filter_value == "processing":
            types = CHANNEL_CATEGORIES['Processing']
            filtered = [c for c in self.channels if c.get('type') in types]
        elif filter_value == "outputs":
            types = CHANNEL_CATEGORIES['Outputs']
            filtered = [c for c in self.channels if c.get('type') in types]

        self.scene.build_graph(filtered)
        self.status_label.setText(f"Showing {len(filtered)} channels, {len(self.scene.edges)} connections")

        # Fit view after short delay
        QTimer.singleShot(100, self._fit_view)

    def update_from_telemetry(self, telemetry_data: dict):
        """Update graph from telemetry (real-time highlighting)."""
        if not self.live_checkbox.isChecked():
            return

        # Extract channel values
        channel_values = {}

        # Output states
        if 'channel_states' in telemetry_data:
            for i, state in enumerate(telemetry_data['channel_states']):
                channel_values[f'out_{i+1}'] = float(state) if state else 0.0

        # Logic/virtual channels would need to be tracked separately
        # For now, just update output states

        self.scene.update_telemetry(channel_values)

    def _zoom_in(self):
        self.view.scale(1.2, 1.2)

    def _zoom_out(self):
        self.view.scale(1 / 1.2, 1 / 1.2)

    def _fit_view(self):
        self.view.fit_in_view()

    def _on_filter_changed(self, index):
        self._rebuild_graph()

    def _on_live_toggled(self, checked):
        if not checked:
            # Reset all nodes to inactive
            for item in self.scene.node_items.values():
                item.set_active(False)
            for edge in self.scene.edges:
                edge.set_active(False)

    def _refresh_graph(self):
        # Emit signal to request fresh data from parent
        self.refresh_requested.emit()
        # Then rebuild with current data
        self._rebuild_graph()
