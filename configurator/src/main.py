"""
PMU-30 Configurator - Modern Style
Entry point for modern dock-based UI

Owner: R2 m-sport
© 2025 R2 m-sport. All rights reserved.
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Setup logging
from utils.logger import setup_logger
setup_logger()

logger = logging.getLogger(__name__)


def main():
    """Main entry point for modern dock-based configurator."""

    logger.info("Starting PMU-30 Configurator (Modern Style)...")

    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("PMU-30 Configurator")
    app.setOrganizationName("R2msport")
    app.setOrganizationDomain("r2msport.com")

    # Create and show main window
    from ui.main_window_professional import MainWindowProfessional
    window = MainWindowProfessional()
    window.show()

    logger.info("Application started successfully (Modern Style)")

    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
