#!/usr/bin/env python3
"""
PMU-30 Configurator - Main Entry Point

Owner: R2 m-sport
Date: 2025-12-21
License: Proprietary

© 2025 R2 m-sport. All rights reserved.
"""

import sys
import logging
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from ui.main_window_professional import MainWindowProfessional
from ui.dialogs.startup_dialog import StartupDialog, StartupAction
from utils.logger import setup_logger


def main():
    """Main application entry point."""

    # Setup logging
    setup_logger()
    logger = logging.getLogger(__name__)
    logger.info("Starting PMU-30 Configurator...")

    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("PMU-30 Configurator")
    app.setOrganizationName("R2 m-sport")
    app.setApplicationVersion("1.0.0")

    # Show startup dialog
    action, file_path = StartupDialog.show_startup()

    if action == StartupAction.CANCEL:
        logger.info("User cancelled startup, exiting")
        sys.exit(0)

    # Create main window
    window = MainWindowProfessional()

    # Handle startup action
    if action == StartupAction.CONNECT_DEVICE:
        logger.info("Startup action: Connect to device")
        window.show()
        # Trigger connection dialog after window is shown
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, window.connect_device)

    elif action == StartupAction.OPEN_FILE:
        logger.info(f"Startup action: Open file {file_path}")
        window.show()
        # Load the file after window is shown
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, lambda: window._load_configuration_file(file_path))

    elif action == StartupAction.NEW_CONFIG:
        logger.info("Startup action: New configuration")
        window.show()
        # Already starts with empty config

    logger.info("Application started successfully")

    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
