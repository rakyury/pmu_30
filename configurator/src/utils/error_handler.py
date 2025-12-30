"""
Centralized Error Handler

Provides unified error handling, logging, and user notification.
"""

from typing import Optional, Callable, Dict, Any, List
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox, QWidget
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime
import traceback
import logging
import sys

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    DEBUG = auto()      # Development info
    INFO = auto()       # User info
    WARNING = auto()    # Recoverable issue
    ERROR = auto()      # Operation failed
    CRITICAL = auto()   # Application may be unstable


class ErrorCategory(Enum):
    """Error categories for filtering and handling."""
    NETWORK = "network"         # Connection, timeout, protocol
    CONFIG = "config"           # Configuration parsing, validation
    DEVICE = "device"           # Hardware communication
    FILE = "file"               # File operations
    VALIDATION = "validation"   # Input validation
    INTERNAL = "internal"       # Programming errors
    USER = "user"               # User-caused issues
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """Container for error information."""
    message: str
    severity: ErrorSeverity = ErrorSeverity.ERROR
    category: ErrorCategory = ErrorCategory.UNKNOWN
    exception: Optional[Exception] = None
    details: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""
    recoverable: bool = True
    user_action: str = ""  # Suggested action for user

    def __str__(self):
        return f"[{self.severity.name}] {self.category.value}: {self.message}"


class ErrorHandler(QObject):
    """
    Centralized error handler with notification and logging.

    Features:
    - Unified error logging
    - User notification via signals
    - Error history
    - Recovery suggestions
    - Error filtering by category/severity
    """

    # Signals
    error_occurred = pyqtSignal(object)  # ErrorInfo
    warning_occurred = pyqtSignal(str)   # Simple warning message
    info_message = pyqtSignal(str)       # Info message

    def __init__(self, parent: QWidget = None, max_history: int = 100):
        super().__init__(parent)
        self._parent_widget = parent
        self._max_history = max_history
        self._error_history: List[ErrorInfo] = []
        self._suppressed_categories: set = set()
        self._error_callbacks: Dict[ErrorCategory, List[Callable]] = {}

        # Install global exception hook
        self._original_excepthook = sys.excepthook

    def install_global_handler(self):
        """Install global exception handler for uncaught exceptions."""
        sys.excepthook = self._global_exception_handler

    def uninstall_global_handler(self):
        """Restore original exception handler."""
        sys.excepthook = self._original_excepthook

    def _global_exception_handler(self, exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions globally."""
        if issubclass(exc_type, KeyboardInterrupt):
            # Don't handle keyboard interrupt
            self._original_excepthook(exc_type, exc_value, exc_traceback)
            return

        error = ErrorInfo(
            message=f"Unhandled exception: {exc_value}",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.INTERNAL,
            exception=exc_value,
            details="\n".join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
            recoverable=False,
            user_action="Please restart the application"
        )

        self.handle(error)

    def handle(self, error: ErrorInfo, show_dialog: bool = None):
        """
        Handle an error.

        Args:
            error: Error information
            show_dialog: Override automatic dialog display decision
        """
        # Add to history
        self._add_to_history(error)

        # Log to Python logger
        self._log_error(error)

        # Check if category is suppressed
        if error.category in self._suppressed_categories:
            return

        # Emit signal
        self.error_occurred.emit(error)

        # Call category-specific callbacks
        callbacks = self._error_callbacks.get(error.category, [])
        for callback in callbacks:
            try:
                callback(error)
            except Exception as e:
                logger.error(f"Error callback failed: {e}")

        # Show dialog if appropriate
        if show_dialog is None:
            show_dialog = error.severity in (ErrorSeverity.ERROR, ErrorSeverity.CRITICAL)

        if show_dialog and self._parent_widget:
            self._show_error_dialog(error)

    def handle_exception(self, exception: Exception, message: str = "",
                         category: ErrorCategory = ErrorCategory.UNKNOWN,
                         severity: ErrorSeverity = ErrorSeverity.ERROR,
                         show_dialog: bool = None):
        """
        Handle an exception.

        Args:
            exception: The exception that occurred
            message: Custom message (uses exception message if not provided)
            category: Error category
            severity: Error severity
            show_dialog: Whether to show dialog
        """
        error = ErrorInfo(
            message=message or str(exception),
            severity=severity,
            category=category,
            exception=exception,
            details=traceback.format_exc(),
            source=exception.__class__.__name__
        )
        self.handle(error, show_dialog)

    def warning(self, message: str, category: ErrorCategory = ErrorCategory.UNKNOWN):
        """Log and emit a warning."""
        error = ErrorInfo(
            message=message,
            severity=ErrorSeverity.WARNING,
            category=category
        )
        self._add_to_history(error)
        logger.warning(message)
        self.warning_occurred.emit(message)

    def info(self, message: str):
        """Emit an info message."""
        logger.info(message)
        self.info_message.emit(message)

    def register_callback(self, category: ErrorCategory,
                          callback: Callable[[ErrorInfo], None]):
        """Register a callback for a specific error category."""
        if category not in self._error_callbacks:
            self._error_callbacks[category] = []
        self._error_callbacks[category].append(callback)

    def suppress_category(self, category: ErrorCategory):
        """Suppress errors of a specific category."""
        self._suppressed_categories.add(category)

    def unsuppress_category(self, category: ErrorCategory):
        """Unsuppress errors of a specific category."""
        self._suppressed_categories.discard(category)

    def get_history(self, category: ErrorCategory = None,
                    severity: ErrorSeverity = None,
                    limit: int = None) -> List[ErrorInfo]:
        """
        Get error history with optional filtering.

        Args:
            category: Filter by category
            severity: Filter by minimum severity
            limit: Maximum number of errors to return
        """
        errors = self._error_history

        if category:
            errors = [e for e in errors if e.category == category]

        if severity:
            severity_order = list(ErrorSeverity)
            min_idx = severity_order.index(severity)
            errors = [e for e in errors if severity_order.index(e.severity) >= min_idx]

        if limit:
            errors = errors[-limit:]

        return errors

    def clear_history(self):
        """Clear error history."""
        self._error_history.clear()

    def _add_to_history(self, error: ErrorInfo):
        """Add error to history with size limit."""
        self._error_history.append(error)
        while len(self._error_history) > self._max_history:
            self._error_history.pop(0)

    def _log_error(self, error: ErrorInfo):
        """Log error to Python logger."""
        log_message = f"[{error.category.value}] {error.message}"
        if error.details:
            log_message += f"\nDetails: {error.details}"

        if error.severity == ErrorSeverity.DEBUG:
            logger.debug(log_message)
        elif error.severity == ErrorSeverity.INFO:
            logger.info(log_message)
        elif error.severity == ErrorSeverity.WARNING:
            logger.warning(log_message)
        elif error.severity == ErrorSeverity.ERROR:
            logger.error(log_message)
        elif error.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)

    def _show_error_dialog(self, error: ErrorInfo):
        """Show error dialog to user."""
        if not self._parent_widget:
            return

        # Choose dialog type based on severity
        if error.severity == ErrorSeverity.CRITICAL:
            icon = QMessageBox.Icon.Critical
            title = "Critical Error"
        elif error.severity == ErrorSeverity.ERROR:
            icon = QMessageBox.Icon.Critical
            title = "Error"
        elif error.severity == ErrorSeverity.WARNING:
            icon = QMessageBox.Icon.Warning
            title = "Warning"
        else:
            icon = QMessageBox.Icon.Information
            title = "Information"

        dialog = QMessageBox(self._parent_widget)
        dialog.setIcon(icon)
        dialog.setWindowTitle(title)
        dialog.setText(error.message)

        # Add details if available
        if error.details:
            dialog.setDetailedText(error.details)

        # Add user action suggestion
        if error.user_action:
            dialog.setInformativeText(error.user_action)

        dialog.exec()


# Singleton instance
_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def set_error_handler(handler: ErrorHandler):
    """Set the global error handler instance."""
    global _error_handler
    _error_handler = handler


def handle_error(message: str, category: ErrorCategory = ErrorCategory.UNKNOWN,
                 severity: ErrorSeverity = ErrorSeverity.ERROR,
                 exception: Exception = None, show_dialog: bool = None):
    """Convenience function to handle an error."""
    error = ErrorInfo(
        message=message,
        category=category,
        severity=severity,
        exception=exception,
        details=traceback.format_exc() if exception else ""
    )
    get_error_handler().handle(error, show_dialog)


def handle_exception(exception: Exception, message: str = "",
                     category: ErrorCategory = ErrorCategory.UNKNOWN):
    """Convenience function to handle an exception."""
    get_error_handler().handle_exception(exception, message, category)
