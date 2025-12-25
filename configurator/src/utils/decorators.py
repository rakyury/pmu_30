"""
Decorators for common patterns in the configurator.
"""
import functools
import logging
from typing import Callable, Any, Optional

from .error_handler import (
    get_error_handler,
    ErrorCategory,
    ErrorSeverity,
    ErrorInfo
)

logger = logging.getLogger(__name__)


def safe_slot(category: ErrorCategory = ErrorCategory.INTERNAL,
              show_dialog: bool = False,
              message: str = "",
              severity: ErrorSeverity = ErrorSeverity.ERROR):
    """
    Decorator for PyQt slots that wraps them in error handling.

    Catches exceptions and routes them through the centralized ErrorHandler.
    This prevents unhandled exceptions from crashing the application.

    Usage:
        @safe_slot(category=ErrorCategory.DEVICE)
        def on_connect_clicked(self):
            ...

        @safe_slot(category=ErrorCategory.FILE, show_dialog=True)
        def on_save_clicked(self):
            ...

    Args:
        category: Error category for classification
        show_dialog: Whether to show error dialog to user
        message: Custom error message (uses exception message if not provided)
        severity: Error severity level
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler = get_error_handler()
                error_msg = message or f"Error in {func.__name__}: {str(e)}"
                error_handler.handle_exception(
                    exception=e,
                    message=error_msg,
                    category=category,
                    severity=severity,
                    show_dialog=show_dialog
                )
                return None
        return wrapper
    return decorator


def safe_async_slot(category: ErrorCategory = ErrorCategory.INTERNAL,
                    show_dialog: bool = False,
                    message: str = ""):
    """
    Decorator for async PyQt slots with error handling.

    Usage:
        @safe_async_slot(category=ErrorCategory.NETWORK)
        async def on_fetch_data(self):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_handler = get_error_handler()
                error_msg = message or f"Error in {func.__name__}: {str(e)}"
                error_handler.handle_exception(
                    exception=e,
                    message=error_msg,
                    category=category,
                    show_dialog=show_dialog
                )
                return None
        return wrapper
    return decorator


def validate_connected(method: Callable) -> Callable:
    """
    Decorator that checks if device is connected before executing method.

    The decorated method's class must have a 'device_controller' attribute
    with an 'is_connected()' method.

    Usage:
        @validate_connected
        def write_to_device(self):
            ...
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs) -> Any:
        if hasattr(self, 'device_controller'):
            if not self.device_controller.is_connected():
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self if hasattr(self, 'isWidgetType') else None,
                    "Not Connected",
                    "Please connect to a device first."
                )
                return None
        return method(self, *args, **kwargs)
    return wrapper
