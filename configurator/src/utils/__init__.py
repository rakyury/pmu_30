"""
Utils Package

Contains utility modules for PMU-30 Configurator.
"""

from .error_handler import (
    ErrorHandler,
    ErrorInfo,
    ErrorSeverity,
    ErrorCategory,
    get_error_handler,
    set_error_handler,
    handle_error,
    handle_exception,
)
from .decorators import (
    safe_slot,
    safe_async_slot,
    validate_connected,
)
from .theme import ThemeManager

__all__ = [
    'ErrorHandler',
    'ErrorInfo',
    'ErrorSeverity',
    'ErrorCategory',
    'get_error_handler',
    'set_error_handler',
    'handle_error',
    'handle_exception',
    'safe_slot',
    'safe_async_slot',
    'validate_connected',
    'ThemeManager',
]
