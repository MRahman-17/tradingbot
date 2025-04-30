import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Any
from datetime import datetime


def setup_logging(config: Dict[str, Any]) -> None:
    """Set up logging for the trading system

    Args:
        config: Logging configuration
    """
    log_level_str = config.get('level', 'INFO')
    log_level = getattr(logging, log_level_str.upper())
    log_to_file = config.get('log_to_file', True)
    log_dir = Path(config.get('log_dir', 'logs'))

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Always add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add file handler if enabled
    if log_to_file:
        log_dir.mkdir(exist_ok=True, parents=True)
        log_file = log_dir / f"trading_system_{datetime.now().strftime('%Y%m%d')}.log"

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=10
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Log startup
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized at level {log_level_str}")
    logger.info(f"Log file: {log_file if log_to_file else 'disabled'}")