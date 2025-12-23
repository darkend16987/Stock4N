"""
Logging Module - Centralized logging configuration
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path


class StockLogger:
    """
    Centralized logger for Stock4N application
    """
    _loggers = {}

    @staticmethod
    def get_logger(name, log_dir=None, log_level=logging.INFO):
        """
        Get or create a logger instance

        Args:
            name: Logger name (usually module name)
            log_dir: Directory to store log files (default: project_root/logs)
            log_level: Logging level (default: INFO)

        Returns:
            logging.Logger instance
        """
        # Return existing logger if already created
        if name in StockLogger._loggers:
            return StockLogger._loggers[name]

        # Create new logger
        logger = logging.getLogger(name)
        logger.setLevel(log_level)
        logger.propagate = False  # Prevent duplicate logs

        # Create log directory if not specified
        if log_dir is None:
            # Get project root (3 levels up from this file)
            project_root = Path(__file__).parent.parent.parent.parent
            log_dir = project_root / "logs"

        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Console Handler (INFO and above)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File Handler - Daily rotating (all levels)
        today = datetime.now().strftime('%Y%m%d')
        log_file = log_dir / f"stock4n_{today}.log"

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Error File Handler (ERROR and above only)
        error_log_file = log_dir / f"stock4n_error_{today}.log"
        error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)

        # Store logger
        StockLogger._loggers[name] = logger

        return logger

    @staticmethod
    def cleanup_old_logs(log_dir=None, days_to_keep=7):
        """
        Remove log files older than specified days

        Args:
            log_dir: Directory containing log files
            days_to_keep: Number of days to keep (default: 7)
        """
        if log_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent
            log_dir = project_root / "logs"

        log_dir = Path(log_dir)
        if not log_dir.exists():
            return

        cutoff_time = datetime.now().timestamp() - (days_to_keep * 86400)

        for log_file in log_dir.glob("*.log"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                except Exception:
                    pass


# Convenience function
def get_logger(name):
    """Get logger instance - shorthand function"""
    return StockLogger.get_logger(name)
