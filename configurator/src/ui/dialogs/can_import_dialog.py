"""
CAN Import Dialog - Import CAN channels from .canx and .dbc files

Provides a dialog similar to ECUMaster PMU Client for importing
CAN message and channel definitions from external files.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLineEdit, QComboBox, QSpinBox, QLabel,
    QCheckBox, QTreeWidget, QTreeWidgetItem, QFileDialog,
    QMessageBox, QHeaderView, QWidget, QSplitter, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from utils.canx_parser import CanxParser, CanxData, CanxChannel, CanxMob, CanxFrame
from utils.dbc_parser import DbcParser, DbcData, DbcSignal, DbcMessage
import logging

logger = logging.getLogger(__name__)


class CANImportDialog(QDialog):
    """Dialog for importing CAN channels from .canx and .dbc files."""

    import_completed = pyqtSignal(list, list)  # (messages, channels)

    FILE_FILTERS = "CAN Files (*.canx *.dbc);;ECUMaster CANX (*.canx);;DBC Database (*.dbc);;All Files (*)"

    def __init__(self, parent=None, config_manager=None):
        """
        Initialize CAN Import Dialog.

        Args:
            parent: Parent widget
            config_manager: Config manager for accessing existing IDs
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.parsed_data: Optional[CanxData | DbcData] = None
        self.file_type: str = ""  # "canx" or "dbc"

        self.setWindowTitle("Import CAN Channels")
        self.setModal(True)
        self.resize(700, 600)

        self._init_ui()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)

        # File selection group
        file_group = QGroupBox("File")
        file_layout = QHBoxLayout()

        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select a .canx or .dbc file...")
        self.file_path_edit.setReadOnly(True)
        file_layout.addWidget(self.file_path_edit, 1)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(self.browse_btn)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Settings group
        settings_group = QGroupBox("Import Settings")
        settings_layout = QFormLayout()

        # Name field
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Auto-generated from file")
        settings_layout.addRow("Name:", self.name_edit)

        # CAN Bus selection
        bus_row = QHBoxLayout()
        self.can_bus_combo = QComboBox()
        self.can_bus_combo.addItems(["CAN 1", "CAN 2", "CAN 3", "CAN 4"])
        bus_row.addWidget(self.can_bus_combo)
        bus_row.addStretch()
        settings_layout.addRow("CAN Bus:", bus_row)

        # Base ID with Standard/Extended option
        id_row = QHBoxLayout()
        self.base_id_spin = QSpinBox()
        self.base_id_spin.setRange(0, 0x7FF)
        self.base_id_spin.setDisplayIntegerBase(16)
        self.base_id_spin.setPrefix("0x")
        self.base_id_spin.setToolTip("Base CAN ID (will be overridden by file data)")
        id_row.addWidget(self.base_id_spin)

        self.id_type_combo = QComboBox()
        self.id_type_combo.addItems(["Standard", "Extended"])
        self.id_type_combo.currentIndexChanged.connect(self._on_id_type_changed)
        id_row.addWidget(self.id_type_combo)
        id_row.addStretch()
        settings_layout.addRow("Base ID:", id_row)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Channel selection group
        channel_group = QGroupBox("Channels")
        channel_layout = QVBoxLayout()

        # Options row
        options_row = QHBoxLayout()

        self.show_frames_check = QCheckBox("Show frames")
        self.show_frames_check.setChecked(True)
        self.show_frames_check.toggled.connect(self._populate_channels)
        options_row.addWidget(self.show_frames_check)

        options_row.addStretch()

        options_row.addWidget(QLabel("Filter:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Search channels...")
        self.filter_edit.setMaximumWidth(200)
        self.filter_edit.textChanged.connect(self._filter_channels)
        options_row.addWidget(self.filter_edit)

        channel_layout.addLayout(options_row)

        # Selection buttons
        btn_row = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self._select_all)
        btn_row.addWidget(self.select_all_btn)

        self.select_none_btn = QPushButton("Select None")
        self.select_none_btn.clicked.connect(self._select_none)
        btn_row.addWidget(self.select_none_btn)

        btn_row.addStretch()
        channel_layout.addLayout(btn_row)

        # Tree widget for channels
        self.channel_tree = QTreeWidget()
        self.channel_tree.setHeaderLabels(["Channel", "Type", "Unit", "Offset"])
        self.channel_tree.setRootIsDecorated(True)
        self.channel_tree.setAlternatingRowColors(False)
        self.channel_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.channel_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.channel_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.channel_tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.channel_tree.itemChanged.connect(self._on_item_changed)
        channel_layout.addWidget(self.channel_tree)

        # Stats label
        self.stats_label = QLabel("No file loaded")
        self.stats_label.setStyleSheet("color: #b0b0b0;")
        channel_layout.addWidget(self.stats_label)

        channel_group.setLayout(channel_layout)
        layout.addWidget(channel_group)

        # Dialog buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.import_btn = QPushButton("Import")
        self.import_btn.clicked.connect(self._on_import)
        self.import_btn.setEnabled(False)
        self.import_btn.setDefault(True)
        btn_layout.addWidget(self.import_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

    def _on_id_type_changed(self, index: int):
        """Handle ID type change (Standard/Extended)."""
        if index == 1:  # Extended
            self.base_id_spin.setRange(0, 0x1FFFFFFF)
        else:  # Standard
            self.base_id_spin.setRange(0, 0x7FF)
            if self.base_id_spin.value() > 0x7FF:
                self.base_id_spin.setValue(0x7FF)

    def _browse_file(self):
        """Open file dialog to select .canx or .dbc file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select CAN Definition File",
            "",
            self.FILE_FILTERS
        )

        if filepath:
            self._load_file(filepath)

    def _load_file(self, filepath: str):
        """Load and parse the selected file."""
        path = Path(filepath)
        ext = path.suffix.lower()

        try:
            logger.info(f"Loading file: {filepath}")
            if ext == ".canx":
                parser = CanxParser()
                self.parsed_data = parser.parse_file(filepath)
                self.file_type = "canx"
                logger.info(f"Parsed {len(self.parsed_data.mobs)} MOBs")
            elif ext == ".dbc":
                parser = DbcParser()
                self.parsed_data = parser.parse_file(filepath)
                self.file_type = "dbc"
            else:
                QMessageBox.warning(
                    self, "Unsupported File",
                    f"File type '{ext}' is not supported.\nPlease select a .canx or .dbc file."
                )
                return

            self.file_path_edit.setText(filepath)
            self.name_edit.setText(path.stem)

            # Update settings from parsed data
            logger.info("Updating settings from data...")
            self._update_settings_from_data()
            logger.info("Settings updated")

            # Populate channel tree
            logger.info("Populating channels...")
            self._populate_channels()
            logger.info("Channels populated")

            self.import_btn.setEnabled(True)

        except Exception as e:
            logger.exception(f"Error loading file: {e}")
            QMessageBox.critical(
                self, "Parse Error",
                f"Failed to parse file:\n{str(e)}"
            )

    def _update_settings_from_data(self):
        """Update settings controls from parsed data."""
        if isinstance(self.parsed_data, CanxData) and self.parsed_data.mobs:
            mob = self.parsed_data.mobs[0]
            # Set CAN bus
            self.can_bus_combo.setCurrentIndex(mob.can_bus_if - 1)
            # Set base ID from first frame
            if mob.frames:
                frame = mob.frames[0]
                is_extended = frame.can_id > 0x7FF
                self.id_type_combo.setCurrentIndex(1 if is_extended else 0)
                self.base_id_spin.setValue(frame.can_id)

        elif isinstance(self.parsed_data, DbcData) and self.parsed_data.messages:
            msg = self.parsed_data.messages[0]
            is_extended = msg.id > 0x7FF
            self.id_type_combo.setCurrentIndex(1 if is_extended else 0)
            self.base_id_spin.setValue(msg.id & 0x1FFFFFFF)

    def _populate_channels(self):
        """Populate the channel tree with parsed data."""
        logger.debug("_populate_channels: clearing tree")
        self.channel_tree.clear()
        self.channel_tree.blockSignals(True)

        show_frames = self.show_frames_check.isChecked()
        filter_text = self.filter_edit.text().lower()

        total_channels = 0
        selected_channels = 0

        if isinstance(self.parsed_data, CanxData):
            logger.debug("_populate_channels: populating CANX channels")
            self._populate_canx_channels(show_frames, filter_text)
        elif isinstance(self.parsed_data, DbcData):
            logger.debug("_populate_channels: populating DBC channels")
            self._populate_dbc_channels(show_frames, filter_text)

        logger.debug("_populate_channels: expanding all")
        self.channel_tree.expandAll()
        self.channel_tree.blockSignals(False)

        # Update stats
        logger.debug("_populate_channels: updating stats")
        self._update_stats()
        logger.debug("_populate_channels: done")

    def _populate_canx_channels(self, show_frames: bool, filter_text: str):
        """Populate tree with CANX data."""
        for mob in self.parsed_data.mobs:
            if show_frames:
                for frame in mob.frames:
                    frame_item = QTreeWidgetItem([
                        f"Frame {frame.offset} (0x{frame.can_id:X})",
                        f"{frame.frequency}Hz",
                        "",
                        ""
                    ])
                    frame_item.setFlags(frame_item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate)
                    frame_item.setCheckState(0, Qt.CheckState.Checked)
                    frame_item.setData(0, Qt.ItemDataRole.UserRole, ("frame", frame))

                    has_visible_children = False
                    for channel in frame.channels:
                        if filter_text and filter_text not in channel.id.lower():
                            continue
                        has_visible_children = True
                        self._add_canx_channel_item(frame_item, channel)

                    if has_visible_children:
                        self.channel_tree.addTopLevelItem(frame_item)
            else:
                for frame in mob.frames:
                    for channel in frame.channels:
                        if filter_text and filter_text not in channel.id.lower():
                            continue
                        self._add_canx_channel_item(self.channel_tree.invisibleRootItem(), channel)

    def _add_canx_channel_item(self, parent: QTreeWidgetItem, channel: CanxChannel):
        """Add a CANX channel item to the tree."""
        # Channel now has data_type and data_format as strings directly
        type_str = f"{channel.data_type} {channel.data_format}"

        item = QTreeWidgetItem([
            channel.id,
            type_str,
            channel.unit,
            f"byte {channel.byte_offset}"
        ])
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Checked)
        item.setData(0, Qt.ItemDataRole.UserRole, ("channel", channel))

        if isinstance(parent, QTreeWidgetItem):
            parent.addChild(item)
        else:
            self.channel_tree.addTopLevelItem(item)

    def _populate_dbc_channels(self, show_frames: bool, filter_text: str):
        """Populate tree with DBC data."""
        for msg in self.parsed_data.messages:
            if show_frames:
                msg_item = QTreeWidgetItem([
                    f"{msg.name} (0x{msg.id:X})",
                    f"DLC {msg.length}",
                    "",
                    ""
                ])
                msg_item.setFlags(msg_item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate)
                msg_item.setCheckState(0, Qt.CheckState.Checked)
                msg_item.setData(0, Qt.ItemDataRole.UserRole, ("message", msg))

                has_visible_children = False
                for signal in msg.signals:
                    if filter_text and filter_text not in signal.name.lower():
                        continue
                    has_visible_children = True
                    self._add_dbc_signal_item(msg_item, signal)

                if has_visible_children:
                    self.channel_tree.addTopLevelItem(msg_item)
            else:
                for signal in msg.signals:
                    if filter_text and filter_text not in signal.name.lower():
                        continue
                    self._add_dbc_signal_item(self.channel_tree.invisibleRootItem(), signal)

    def _add_dbc_signal_item(self, parent: QTreeWidgetItem, signal: DbcSignal):
        """Add a DBC signal item to the tree."""
        type_str = f"{signal.value_type} {signal.length}bit"

        item = QTreeWidgetItem([
            signal.name,
            type_str,
            signal.unit,
            f"bit {signal.start_bit}"
        ])
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Checked)
        item.setData(0, Qt.ItemDataRole.UserRole, ("signal", signal))

        if isinstance(parent, QTreeWidgetItem):
            parent.addChild(item)
        else:
            self.channel_tree.addTopLevelItem(item)

    def _filter_channels(self, text: str):
        """Filter channels by search text."""
        self._populate_channels()

    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        """Handle item check state change."""
        self._update_stats()

    def _select_all(self):
        """Select all channels."""
        self.channel_tree.blockSignals(True)
        for i in range(self.channel_tree.topLevelItemCount()):
            item = self.channel_tree.topLevelItem(i)
            item.setCheckState(0, Qt.CheckState.Checked)
        self.channel_tree.blockSignals(False)
        self._update_stats()

    def _select_none(self):
        """Deselect all channels."""
        self.channel_tree.blockSignals(True)
        for i in range(self.channel_tree.topLevelItemCount()):
            item = self.channel_tree.topLevelItem(i)
            item.setCheckState(0, Qt.CheckState.Unchecked)
        self.channel_tree.blockSignals(False)
        self._update_stats()

    def _update_stats(self):
        """Update the stats label."""
        total = 0
        selected = 0
        frames = set()

        def count_items(item: QTreeWidgetItem):
            nonlocal total, selected, frames
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data:
                item_type, obj = data
                if item_type in ("channel", "signal"):
                    total += 1
                    if item.checkState(0) == Qt.CheckState.Checked:
                        selected += 1
                        if hasattr(obj, 'frame_offset'):
                            frames.add(obj.frame_offset)
                        elif hasattr(obj, 'message_id'):
                            frames.add(obj.message_id)
            for i in range(item.childCount()):
                count_items(item.child(i))

        for i in range(self.channel_tree.topLevelItemCount()):
            count_items(self.channel_tree.topLevelItem(i))

        if total > 0:
            self.stats_label.setText(
                f"Selected: {selected} of {total} channels from {len(frames)} frame(s)"
            )
        else:
            self.stats_label.setText("No channels found")

    def _get_existing_ids(self) -> Tuple[List[str], List[str]]:
        """Get existing message and channel IDs from config manager."""
        msg_ids = []
        channel_ids = []

        if self.config_manager:
            config = self.config_manager.get_config()
            msg_ids = [m.get("id", "") for m in config.get("can_messages", [])]
            channel_ids = [c.get("id", "") for c in config.get("channels", [])]

        return msg_ids, channel_ids

    def _generate_unique_id(self, base_id: str, existing_ids: List[str]) -> str:
        """Generate a unique ID by appending _N suffix if needed."""
        if base_id not in existing_ids:
            return base_id

        counter = 1
        while f"{base_id}_{counter}" in existing_ids:
            counter += 1
        return f"{base_id}_{counter}"

    def _on_import(self):
        """Import selected channels."""
        existing_msg_ids, existing_channel_ids = self._get_existing_ids()

        messages = []
        channels = []
        can_bus = self.can_bus_combo.currentIndex() + 1

        # Collect selected items
        selected_channels = []

        def collect_selected(item: QTreeWidgetItem):
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data:
                item_type, obj = data
                if item_type in ("channel", "signal") and item.checkState(0) == Qt.CheckState.Checked:
                    selected_channels.append((item_type, obj))
            for i in range(item.childCount()):
                collect_selected(item.child(i))

        for i in range(self.channel_tree.topLevelItemCount()):
            collect_selected(self.channel_tree.topLevelItem(i))

        if not selected_channels:
            QMessageBox.warning(self, "No Selection", "Please select at least one channel to import.")
            return

        # Group channels by frame/message to create CAN messages
        if isinstance(self.parsed_data, CanxData):
            messages, channels = self._import_canx_channels(
                selected_channels, can_bus, existing_msg_ids, existing_channel_ids
            )
        elif isinstance(self.parsed_data, DbcData):
            messages, channels = self._import_dbc_channels(
                selected_channels, can_bus, existing_msg_ids, existing_channel_ids
            )

        # Emit signal with imported data
        self.import_completed.emit(messages, channels)

        QMessageBox.information(
            self, "Import Complete",
            f"Imported {len(messages)} message(s) and {len(channels)} channel(s)."
        )

        self.accept()

    def _import_canx_channels(
        self,
        selected_channels: List[Tuple[str, CanxChannel]],
        can_bus: int,
        existing_msg_ids: List[str],
        existing_channel_ids: List[str]
    ) -> Tuple[List[Dict], List[Dict]]:
        """Import CANX channels and create corresponding messages."""
        messages = []
        channels = []

        # Group channels by frame
        frames_map: Dict[int, List[CanxChannel]] = {}
        for item_type, channel in selected_channels:
            if channel.frame_offset not in frames_map:
                frames_map[channel.frame_offset] = []
            frames_map[channel.frame_offset].append(channel)

        # Find the MOB and frames
        mob = self.parsed_data.mobs[0] if self.parsed_data.mobs else None
        if not mob:
            return messages, channels

        # Determine if we need a compound message
        frame_count = len(frames_map)
        is_compound = frame_count > 1 or (mob.msg_type == "compound")

        # Create a single message for all frames
        name = self.name_edit.text() or self.parsed_data.filename
        base_msg_id = f"msg_{name.replace(' ', '_').replace('-', '_').lower()}"
        msg_id = self._generate_unique_id(base_msg_id, existing_msg_ids)
        existing_msg_ids.append(msg_id)

        # Get base frame ID
        base_frame = mob.frames[0] if mob.frames else None
        base_can_id = base_frame.can_id if base_frame else 0
        frequency = base_frame.frequency if base_frame else 50

        msg_config = {
            "id": msg_id,
            "name": name,
            "can_bus": can_bus,
            "base_id": base_can_id,
            "is_extended": base_can_id > 0x7FF,
            "message_type": "compound" if is_compound else "normal",
            "frame_count": max(frame_count, len(mob.frames)),
            "dlc": 8,
            "timeout_ms": int(2000 / frequency) if frequency > 0 else 500,
            "enabled": True,
            "description": f"Imported from {self.parsed_data.filename}.canx"
        }
        messages.append(msg_config)

        # Create channel configs
        for item_type, channel in selected_channels:
            channel_config = channel.to_can_input_config(msg_id)
            # Generate unique channel ID
            channel_config["id"] = self._generate_unique_id(
                channel_config["id"], existing_channel_ids
            )
            existing_channel_ids.append(channel_config["id"])
            channels.append(channel_config)

        return messages, channels

    def _import_dbc_channels(
        self,
        selected_channels: List[Tuple[str, DbcSignal]],
        can_bus: int,
        existing_msg_ids: List[str],
        existing_channel_ids: List[str]
    ) -> Tuple[List[Dict], List[Dict]]:
        """Import DBC signals and create corresponding messages."""
        messages = []
        channels = []

        # Group signals by message
        msgs_map: Dict[int, Tuple[DbcMessage, List[DbcSignal]]] = {}
        for item_type, signal in selected_channels:
            if signal.message_id not in msgs_map:
                # Find the message
                for msg in self.parsed_data.messages:
                    if msg.id == signal.message_id:
                        msgs_map[signal.message_id] = (msg, [])
                        break
            if signal.message_id in msgs_map:
                msgs_map[signal.message_id][1].append(signal)

        # Create messages and channels
        for msg_id_int, (msg, signals) in msgs_map.items():
            # Create message config
            base_msg_id = f"msg_{msg.name.replace(' ', '_').replace('-', '_').lower()}"
            msg_id = self._generate_unique_id(base_msg_id, existing_msg_ids)
            existing_msg_ids.append(msg_id)

            msg_config = msg.to_can_message_config(msg_id)
            msg_config["can_bus"] = can_bus
            messages.append(msg_config)

            # Create channel configs for each signal
            for signal in signals:
                channel_config = signal.to_can_input_config(msg_id)
                channel_config["id"] = self._generate_unique_id(
                    channel_config["id"], existing_channel_ids
                )
                existing_channel_ids.append(channel_config["id"])
                channels.append(channel_config)

        return messages, channels

    def get_imported_data(self) -> Tuple[List[Dict], List[Dict]]:
        """Get the imported messages and channels (for external use)."""
        # This would be populated after import
        return [], []
