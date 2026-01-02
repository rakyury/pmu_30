"""
Startup Dialog for PMU-30 Configurator

Allows user to choose startup action:
- Connect to device and load configuration
- Open existing configuration file
- Create new configuration
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QGroupBox, QRadioButton, QButtonGroup,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class StartupAction:
    """Startup action types"""
    CONNECT_DEVICE = "connect"
    OPEN_FILE = "open"
    NEW_CONFIG = "new"
    CANCEL = "cancel"


class StartupDialog(QDialog):
    """Dialog shown at application startup to choose initial action"""

    def __init__(self, parent=None, recent_files: list = None):
        super().__init__(parent)
        self.recent_files = recent_files or []
        self.selected_action = StartupAction.CANCEL
        self.selected_file = None

        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("PMU-30 Configurator")
        self.setModal(True)
        self.setMinimumWidth(450)
        self.setMinimumHeight(380)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Title
        title_label = QLabel("Welcome to PMU-30 Configurator")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Subtitle
        subtitle = QLabel("Choose how to start:")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(10)

        # Options group
        options_group = QGroupBox()
        options_layout = QVBoxLayout(options_group)
        options_layout.setSpacing(12)

        self.button_group = QButtonGroup(self)

        # Option 1: Connect to device
        self.connect_radio = QRadioButton("Connect to device and load configuration")
        self.connect_radio.setToolTip("Connect to PMU-30 device or emulator and download current configuration")
        self.button_group.addButton(self.connect_radio, 1)
        options_layout.addWidget(self.connect_radio)

        # Option 2: Open existing file
        self.open_radio = QRadioButton("Open existing configuration file")
        self.open_radio.setToolTip("Open a previously saved .pmu30 configuration file")
        self.button_group.addButton(self.open_radio, 2)
        options_layout.addWidget(self.open_radio)

        # Option 3: Create new
        self.new_radio = QRadioButton("Create new configuration")
        self.new_radio.setToolTip("Start with a blank configuration")
        self.button_group.addButton(self.new_radio, 3)
        options_layout.addWidget(self.new_radio)

        # Default selection
        self.connect_radio.setChecked(True)

        layout.addWidget(options_group)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.ok_btn = QPushButton("Continue")
        self.ok_btn.setMinimumWidth(100)
        self.ok_btn.clicked.connect(self._on_continue)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("Exit")
        self.cancel_btn.setMinimumWidth(80)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def _on_continue(self):
        """Handle continue button click"""
        checked_id = self.button_group.checkedId()

        if checked_id == 1:
            # Connect to device
            self.selected_action = StartupAction.CONNECT_DEVICE
            self.accept()

        elif checked_id == 2:
            # Open file - show file dialog
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Open Configuration",
                str(Path.home()),
                "PMU-30 Configuration (*.pmu30);;All Files (*.*)"
            )
            if file_path:
                self.selected_file = file_path
                self.selected_action = StartupAction.OPEN_FILE
                self.accept()
            # If no file selected, stay in dialog

        elif checked_id == 3:
            # New configuration
            self.selected_action = StartupAction.NEW_CONFIG
            self.accept()

    def get_result(self) -> Tuple[str, Optional[str]]:
        """
        Get the dialog result.

        Returns:
            Tuple of (action, file_path)
            - action: StartupAction constant
            - file_path: Path to file (for OPEN_FILE action) or None
        """
        return self.selected_action, self.selected_file

    @staticmethod
    def show_startup(parent=None, recent_files: list = None) -> Tuple[str, Optional[str]]:
        """
        Show startup dialog and return result.

        Returns:
            Tuple of (action, file_path)
        """
        dialog = StartupDialog(parent, recent_files)
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            return dialog.get_result()
        else:
            return StartupAction.CANCEL, None
