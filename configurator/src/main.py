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

from ui.main_window import MainWindow
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

    # Create and show main window
    window = MainWindow()
    window.show()

    logger.info("Application started successfully")

    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
