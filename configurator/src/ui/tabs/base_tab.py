"""
Base Tab Widget

Owner: R2 m-sport
© 2025 R2 m-sport. All rights reserved.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal


class BaseTab(QWidget):
    """Base class for all configuration tabs."""

    # Signal emitted when configuration changes
    configuration_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def load_configuration(self, config: dict):
        """
        Load configuration into tab UI.

        Args:
            config: Configuration dictionary
        """
        raise NotImplementedError("Subclass must implement load_configuration")

    def get_configuration(self) -> dict:
        """
        Get current configuration from tab UI.

        Returns:
            Configuration dictionary
        """
        raise NotImplementedError("Subclass must implement get_configuration")

    def validate_configuration(self) -> tuple[bool, str]:
        """
        Validate current configuration.

        Returns:
            Tuple of (is_valid, error_message)
        """
        return (True, "")

    def reset_to_defaults(self):
        """Reset tab configuration to defaults."""
        raise NotImplementedError("Subclass must implement reset_to_defaults")
