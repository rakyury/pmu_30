"""
Logging configuration for PMU-30 Configurator

Owner: R2 m-sport
© 2025 R2 m-sport. All rights reserved.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(log_level=logging.INFO):
    """
    Setup application logger.

    Args:
        log_level: Logging level (default: INFO)
    """

    # Create logs directory
    log_dir = Path.home() / ".pmu30" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Log file name with timestamp
    log_file = log_dir / f"pmu30_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Set specific module log levels
    logging.getLogger("PyQt6").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"Logger initialized. Log file: {log_file}")
