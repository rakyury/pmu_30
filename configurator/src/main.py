#!/usr/bin/env python3
"""
PMU-30 Configurator - Main Entry Point

Owner: R2 m-sport
Date: 2025-12-21
License: Proprietary

© 2025 R2 m-sport. All rights reserved.
"""

import sys
import argparse
import logging
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from ui.main_window_professional import MainWindowProfessional
from ui.dialogs.startup_dialog import StartupDialog, StartupAction
from utils.logger import setup_logger


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="PMU-30 Configurator - Power Management Unit Configuration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Normal startup with dialog
  %(prog)s -c                       # Auto-connect to emulator (localhost:9876)
  %(prog)s -c 192.168.1.100:9876    # Connect to remote emulator
  %(prog)s -f config.json           # Open configuration file
  %(prog)s -c -f config.json        # Connect and load config
  %(prog)s --no-startup             # Skip startup dialog
"""
    )

    parser.add_argument(
        "-c", "--connect",
        nargs="?",
        const="localhost:9876",
        metavar="HOST:PORT",
        help="Auto-connect to emulator (default: localhost:9876)"
    )

    parser.add_argument(
        "-f", "--file",
        metavar="FILE",
        help="Open configuration file on startup"
    )

    parser.add_argument(
        "--no-startup",
        action="store_true",
        help="Skip startup dialog"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    return parser.parse_args()


def main():
    """Main application entry point."""
    # Parse command line arguments first
    args = parse_args()

    # Setup logging
    setup_logger()
    logger = logging.getLogger(__name__)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("Starting PMU-30 Configurator...")
    if args.connect:
        logger.info(f"  Auto-connect: {args.connect}")
    if args.file:
        logger.info(f"  Config file: {args.file}")

    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("PMU-30 Configurator")
    app.setOrganizationName("R2 m-sport")
    app.setApplicationVersion("1.0.0")

    # Apply dark theme BEFORE showing any dialogs
    from utils.theme import ThemeManager
    app.setStyle("Fusion")
    ThemeManager.apply_dark_theme(app)

    # Determine startup action based on command line args
    if args.connect or args.file or args.no_startup:
        # Skip startup dialog when using command line args
        action = StartupAction.NEW_CONFIG
        file_path = args.file
    else:
        # Show startup dialog
        action, file_path = StartupDialog.show_startup()

        if action == StartupAction.CANCEL:
            logger.info("User cancelled startup, exiting")
            sys.exit(0)

    # Create main window
    window = MainWindowProfessional()
    window.show()

    # Handle command line auto-connect
    if args.connect:
        logger.info(f"Auto-connecting to emulator: {args.connect}")

        def auto_connect():
            config = {
                "type": "Emulator",
                "address": args.connect
            }
            success = window.device_controller.connect(config)
            if success:
                window.status_message.setText(f"Connected to {args.connect}")
                window.device_status_label.setText("ONLINE")
                window.device_status_label.setStyleSheet("color: #10b981;")
                window.pmu_monitor.set_connected(True)
                window.output_monitor.set_connected(True)
                window.analog_monitor.set_connected(True)
                window.variables_inspector.set_connected(True)
                logger.info(f"Auto-connect successful: {args.connect}")

                # Auto-read configuration from device after short delay
                QTimer.singleShot(500, window.read_from_device)
            else:
                window.status_message.setText(f"Failed to connect to {args.connect}")
                logger.error(f"Auto-connect failed: {args.connect}")

        QTimer.singleShot(100, auto_connect)

    # Handle file loading (from command line or startup dialog)
    if file_path:
        logger.info(f"Loading configuration file: {file_path}")
        QTimer.singleShot(200, lambda: window._load_configuration_file(file_path))

    # Handle startup dialog action (if no command line args)
    elif action == StartupAction.CONNECT_DEVICE:
        logger.info("Startup action: Connect to device")
        QTimer.singleShot(100, window.connect_device)

    logger.info("Application started successfully")

    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
