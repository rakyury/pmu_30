"""
Logging configuration for PMU-30 Configurator

Owner: R2 m-sport
© 2025 R2 m-sport. All rights reserved.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler


def setup_logger(log_level=logging.INFO, max_size_mb: int = 10, backup_count: int = 5):
    """
    Setup application logger with rotating file handler.

    Args:
        log_level: Logging level (default: INFO)
        max_size_mb: Maximum log file size in MB before rotation (default: 10)
        backup_count: Number of backup files to keep (default: 5)
    """

    # Create logs directory
    log_dir = Path.home() / ".pmu30" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Main log file (rotating)
    log_file = log_dir / "pmu30.log"

    # Error-only log file (rotating)
    error_log_file = log_dir / "pmu30_errors.log"

    # Log format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers (in case of re-initialization)
    root_logger.handlers.clear()

    # Rotating file handler for main log
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_size_mb * 1024 * 1024,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Rotating file handler for errors only
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB for errors
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set specific module log levels
    logging.getLogger("PyQt6").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Clean up old log files (older than 30 days)
    _cleanup_old_logs(log_dir, days=30)

    logger = logging.getLogger(__name__)
    logger.info(f"Logger initialized. Log file: {log_file}")


def _cleanup_old_logs(log_dir: Path, days: int = 30):
    """Remove log files older than specified days."""
    import time

    cutoff_time = time.time() - (days * 24 * 60 * 60)

    try:
        for log_file in log_dir.glob("*.log*"):
            if log_file.stat().st_mtime < cutoff_time:
                log_file.unlink()
    except Exception:
        pass  # Silently ignore cleanup errors
