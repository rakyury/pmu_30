"""
Configuration Diff Dialog
Compares device configuration with UI configuration and shows differences
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QGroupBox, QSplitter, QMessageBox,
    QHeaderView, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush, QFont
from typing import Dict, Any, List, Tuple, Optional
import json
import logging

logger = logging.getLogger(__name__)


class ConfigDiffDialog(QDialog):
    """Dialog for comparing device and UI configurations."""

    # Diff types
    ADDED = "added"      # In UI but not in device
    REMOVED = "removed"  # In device but not in UI
    MODIFIED = "modified"  # Different values
    UNCHANGED = "unchanged"

    # Colors for diff types
    COLORS = {
        ADDED: QColor("#22c55e"),      # Green
        REMOVED: QColor("#ef4444"),    # Red
        MODIFIED: QColor("#f59e0b"),   # Orange/amber
        UNCHANGED: QColor("#6b7280"),  # Gray
    }

    def __init__(self, parent=None,
                 device_config: Dict[str, Any] = None,
                 ui_config: Dict[str, Any] = None):
        super().__init__(parent)
        self.device_config = device_config or {}
        self.ui_config = ui_config or {}
        self.differences = []

        self._init_ui()
        self._compute_diff()
        self._populate_tree()

    def _init_ui(self):
        """Initialize UI components."""
        self.setWindowTitle("Configuration Comparison")
        self.setModal(True)
        self.setMinimumSize(800, 600)
        self.resize(900, 700)

        layout = QVBoxLayout(self)

        # Header with summary
        header_layout = QHBoxLayout()

        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("font-size: 14px;")
        header_layout.addWidget(self.summary_label)

        header_layout.addStretch()

        # Legend
        legend_layout = QHBoxLayout()
        for diff_type, color in [
            (self.ADDED, "Added (UI only)"),
            (self.REMOVED, "Removed (Device only)"),
            (self.MODIFIED, "Modified"),
        ]:
            indicator = QLabel("●")
            indicator.setStyleSheet(f"color: {self.COLORS[diff_type].name()};")
            legend_layout.addWidget(indicator)
            legend_layout.addWidget(QLabel(color))
            legend_layout.addSpacing(10)

        header_layout.addLayout(legend_layout)
        layout.addLayout(header_layout)

        # Splitter with two panels
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Differences tree
        left_group = QGroupBox("Differences")
        left_layout = QVBoxLayout(left_group)

        self.diff_tree = QTreeWidget()
        self.diff_tree.setHeaderLabels(["Item", "Status", "Device Value", "UI Value"])
        self.diff_tree.setAlternatingRowColors(True)
        self.diff_tree.setRootIsDecorated(True)
        self.diff_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.diff_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.diff_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.diff_tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        left_layout.addWidget(self.diff_tree)

        splitter.addWidget(left_group)

        # Right panel - Details (optional, for future expansion)
        right_group = QGroupBox("Details")
        right_layout = QVBoxLayout(right_group)

        self.details_label = QLabel("Select an item to see details")
        self.details_label.setWordWrap(True)
        self.details_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        right_layout.addWidget(self.details_label)

        splitter.addWidget(right_group)
        splitter.setSizes([600, 300])

        layout.addWidget(splitter)

        # Buttons
        button_layout = QHBoxLayout()

        self.sync_to_device_btn = QPushButton("Apply UI → Device")
        self.sync_to_device_btn.setToolTip("Send current UI configuration to device")
        self.sync_to_device_btn.clicked.connect(self._on_sync_to_device)
        button_layout.addWidget(self.sync_to_device_btn)

        self.sync_from_device_btn = QPushButton("Apply Device → UI")
        self.sync_from_device_btn.setToolTip("Load configuration from device to UI")
        self.sync_from_device_btn.clicked.connect(self._on_sync_from_device)
        button_layout.addWidget(self.sync_from_device_btn)

        button_layout.addStretch()

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._on_refresh)
        button_layout.addWidget(self.refresh_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

        # Connect selection change
        self.diff_tree.currentItemChanged.connect(self._on_item_selected)

    def _compute_diff(self):
        """Compute differences between device and UI configs."""
        self.differences = []

        # Compare channels
        device_channels = {
            ch.get("channel_id", ch.get("id", ch.get("name", ""))): ch
            for ch in self.device_config.get("channels", [])
        }
        ui_channels = {
            ch.get("channel_id", ch.get("id", ch.get("name", ""))): ch
            for ch in self.ui_config.get("channels", [])
        }

        all_ids = set(device_channels.keys()) | set(ui_channels.keys())

        for ch_id in sorted(all_ids, key=lambda x: (str(type(x)), str(x))):
            device_ch = device_channels.get(ch_id)
            ui_ch = ui_channels.get(ch_id)

            if device_ch and ui_ch:
                # Check if modified
                if self._channels_equal(device_ch, ui_ch):
                    self.differences.append({
                        "type": self.UNCHANGED,
                        "category": "channels",
                        "id": ch_id,
                        "name": ui_ch.get("name", str(ch_id)),
                        "channel_type": ui_ch.get("channel_type", "unknown"),
                        "device": device_ch,
                        "ui": ui_ch,
                    })
                else:
                    self.differences.append({
                        "type": self.MODIFIED,
                        "category": "channels",
                        "id": ch_id,
                        "name": ui_ch.get("name", str(ch_id)),
                        "channel_type": ui_ch.get("channel_type", "unknown"),
                        "device": device_ch,
                        "ui": ui_ch,
                        "changes": self._get_channel_changes(device_ch, ui_ch),
                    })
            elif ui_ch:
                self.differences.append({
                    "type": self.ADDED,
                    "category": "channels",
                    "id": ch_id,
                    "name": ui_ch.get("name", str(ch_id)),
                    "channel_type": ui_ch.get("channel_type", "unknown"),
                    "device": None,
                    "ui": ui_ch,
                })
            else:
                self.differences.append({
                    "type": self.REMOVED,
                    "category": "channels",
                    "id": ch_id,
                    "name": device_ch.get("name", str(ch_id)),
                    "channel_type": device_ch.get("channel_type", "unknown"),
                    "device": device_ch,
                    "ui": None,
                })

        # Compare CAN messages
        device_msgs = {
            msg.get("id", ""): msg
            for msg in self.device_config.get("can_messages", [])
        }
        ui_msgs = {
            msg.get("id", ""): msg
            for msg in self.ui_config.get("can_messages", [])
        }

        all_msg_ids = set(device_msgs.keys()) | set(ui_msgs.keys())

        for msg_id in sorted(all_msg_ids):
            if not msg_id:
                continue
            device_msg = device_msgs.get(msg_id)
            ui_msg = ui_msgs.get(msg_id)

            if device_msg and ui_msg:
                if json.dumps(device_msg, sort_keys=True) != json.dumps(ui_msg, sort_keys=True):
                    self.differences.append({
                        "type": self.MODIFIED,
                        "category": "can_messages",
                        "id": msg_id,
                        "name": msg_id,
                        "device": device_msg,
                        "ui": ui_msg,
                    })
            elif ui_msg:
                self.differences.append({
                    "type": self.ADDED,
                    "category": "can_messages",
                    "id": msg_id,
                    "name": msg_id,
                    "device": None,
                    "ui": ui_msg,
                })
            elif device_msg:
                self.differences.append({
                    "type": self.REMOVED,
                    "category": "can_messages",
                    "id": msg_id,
                    "name": msg_id,
                    "device": device_msg,
                    "ui": None,
                })

        # Compare settings
        device_settings = self.device_config.get("settings", {})
        ui_settings = self.ui_config.get("settings", {})

        if json.dumps(device_settings, sort_keys=True) != json.dumps(ui_settings, sort_keys=True):
            self.differences.append({
                "type": self.MODIFIED,
                "category": "settings",
                "id": "settings",
                "name": "Device Settings",
                "device": device_settings,
                "ui": ui_settings,
                "changes": self._get_settings_changes(device_settings, ui_settings),
            })

    def _channels_equal(self, ch1: Dict, ch2: Dict) -> bool:
        """Check if two channel configs are equal (ignoring order)."""
        # Compare as sorted JSON strings
        return json.dumps(ch1, sort_keys=True) == json.dumps(ch2, sort_keys=True)

    def _get_channel_changes(self, device_ch: Dict, ui_ch: Dict) -> List[Tuple[str, Any, Any]]:
        """Get list of changed fields between two channel configs."""
        changes = []
        all_keys = set(device_ch.keys()) | set(ui_ch.keys())

        for key in sorted(all_keys):
            device_val = device_ch.get(key)
            ui_val = ui_ch.get(key)
            if device_val != ui_val:
                changes.append((key, device_val, ui_val))

        return changes

    def _get_settings_changes(self, device_settings: Dict, ui_settings: Dict) -> List[Tuple[str, Any, Any]]:
        """Get list of changed settings."""
        changes = []

        def compare_dict(d1: Dict, d2: Dict, prefix: str = ""):
            all_keys = set(d1.keys()) | set(d2.keys())
            for key in sorted(all_keys):
                full_key = f"{prefix}.{key}" if prefix else key
                v1 = d1.get(key)
                v2 = d2.get(key)

                if isinstance(v1, dict) and isinstance(v2, dict):
                    compare_dict(v1, v2, full_key)
                elif v1 != v2:
                    changes.append((full_key, v1, v2))

        compare_dict(device_settings, ui_settings)
        return changes

    def _populate_tree(self):
        """Populate the diff tree with computed differences."""
        self.diff_tree.clear()

        # Count by type
        counts = {self.ADDED: 0, self.REMOVED: 0, self.MODIFIED: 0, self.UNCHANGED: 0}

        # Group by category
        categories = {}
        for diff in self.differences:
            cat = diff["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(diff)
            counts[diff["type"]] += 1

        # Update summary
        total_changes = counts[self.ADDED] + counts[self.REMOVED] + counts[self.MODIFIED]
        if total_changes == 0:
            self.summary_label.setText("Configurations are identical")
            self.summary_label.setStyleSheet("color: #22c55e; font-size: 14px;")
        else:
            self.summary_label.setText(
                f"{total_changes} difference(s): "
                f"+{counts[self.ADDED]} added, "
                f"-{counts[self.REMOVED]} removed, "
                f"~{counts[self.MODIFIED]} modified"
            )
            self.summary_label.setStyleSheet("color: #f59e0b; font-size: 14px;")

        # Category display names
        cat_names = {
            "channels": "Channels",
            "can_messages": "CAN Messages",
            "settings": "Settings",
        }

        # Build tree
        for cat, diffs in categories.items():
            # Skip if only unchanged items
            if all(d["type"] == self.UNCHANGED for d in diffs):
                continue

            cat_item = QTreeWidgetItem([cat_names.get(cat, cat)])
            cat_item.setFont(0, QFont("", -1, QFont.Weight.Bold))
            self.diff_tree.addTopLevelItem(cat_item)

            for diff in diffs:
                if diff["type"] == self.UNCHANGED:
                    continue  # Skip unchanged items

                status_text = {
                    self.ADDED: "Added",
                    self.REMOVED: "Removed",
                    self.MODIFIED: "Modified",
                }[diff["type"]]

                name = diff.get("name", str(diff.get("id", "unknown")))
                if diff.get("channel_type"):
                    name = f"{name} ({diff['channel_type']})"

                device_val = self._format_value(diff.get("device"))
                ui_val = self._format_value(diff.get("ui"))

                item = QTreeWidgetItem([name, status_text, device_val, ui_val])
                item.setData(0, Qt.ItemDataRole.UserRole, diff)

                # Color by status
                color = self.COLORS[diff["type"]]
                item.setForeground(1, QBrush(color))

                cat_item.addChild(item)

                # Add changed fields as children for modified items
                if diff["type"] == self.MODIFIED and "changes" in diff:
                    for field, dev_v, ui_v in diff["changes"]:
                        change_item = QTreeWidgetItem([
                            f"  {field}",
                            "",
                            self._format_simple_value(dev_v),
                            self._format_simple_value(ui_v)
                        ])
                        change_item.setForeground(0, QBrush(QColor("#9ca3af")))
                        item.addChild(change_item)

            cat_item.setExpanded(True)

    def _format_value(self, value: Any) -> str:
        """Format a value for display in tree."""
        if value is None:
            return "—"
        if isinstance(value, dict):
            # Just show summary
            ch_type = value.get("channel_type", "")
            name = value.get("name", value.get("id", ""))
            if ch_type:
                return f"{ch_type}: {name}"
            return str(len(value)) + " fields"
        return str(value)

    def _format_simple_value(self, value: Any) -> str:
        """Format a simple value."""
        if value is None:
            return "—"
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)[:50]
        return str(value)

    def _on_item_selected(self, current: QTreeWidgetItem, previous: QTreeWidgetItem):
        """Handle item selection."""
        if not current:
            self.details_label.setText("Select an item to see details")
            return

        diff = current.data(0, Qt.ItemDataRole.UserRole)
        if not diff:
            self.details_label.setText("")
            return

        # Build details text
        lines = []
        lines.append(f"<b>Name:</b> {diff.get('name', 'unknown')}")
        lines.append(f"<b>Status:</b> {diff['type'].upper()}")

        if diff.get("channel_type"):
            lines.append(f"<b>Type:</b> {diff['channel_type']}")

        if diff["type"] == self.MODIFIED and "changes" in diff:
            lines.append("<br><b>Changes:</b>")
            for field, dev_v, ui_v in diff["changes"]:
                lines.append(f"  • <b>{field}</b>: {dev_v} → {ui_v}")

        self.details_label.setText("<br>".join(lines))

    def _on_sync_to_device(self):
        """Apply UI config to device."""
        self.done(1)  # Return 1 = sync to device

    def _on_sync_from_device(self):
        """Apply device config to UI."""
        self.done(2)  # Return 2 = sync from device

    def _on_refresh(self):
        """Refresh diff comparison."""
        self._compute_diff()
        self._populate_tree()

    def set_configs(self, device_config: Dict[str, Any], ui_config: Dict[str, Any]):
        """Update configs and refresh."""
        self.device_config = device_config or {}
        self.ui_config = ui_config or {}
        self._compute_diff()
        self._populate_tree()

    def has_differences(self) -> bool:
        """Check if there are any differences."""
        return any(d["type"] != self.UNCHANGED for d in self.differences)
