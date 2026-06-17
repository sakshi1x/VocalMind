import logging
from pathlib import Path
from typing import Any, Dict, Optional

ROOT_DIR = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
QUEUE_LOG_FILE = LOG_DIR / "queue.log"

# Reserved LogRecord attributes that cannot be overridden via extra dict
RESERVED_LOG_ATTRIBUTES = {
    'name', 'msg', 'args', 'created', 'audio_filename', 'funcName', 'levelname', 'levelno',
    'lineno', 'module', 'msecs', 'message', 'pathname', 'process', 'processName',
    'relativeCreated', 'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info',
    'asctime'
}

# Set the logger class BEFORE any loggers are created
logging.setLoggerClass(logging.Logger)  # Reset first


class SafeQueueLogger(logging.Logger):
    """Custom logger that safely handles extra dict by filtering reserved attributes."""
    
    def makeRecord(self, name, level, fn, lno, msg, args, exc_info,
                   func=None, extra=None, sinfo=None):
        """Override makeRecord to filter reserved attributes from extra dict."""
        if extra:
            # Filter out reserved LogRecord attributes
            filtered_extra = {}
            for key, value in extra.items():
                if key not in RESERVED_LOG_ATTRIBUTES:
                    filtered_extra[key] = value
                else:
                    # Rename reserved attributes to avoid conflict
                    filtered_extra[f"log_{key}"] = value
            extra = filtered_extra
        
        return super().makeRecord(name, level, fn, lno, msg, args, exc_info,
                                 func=func, extra=extra, sinfo=sinfo)


# Set the custom logger class globally
logging.setLoggerClass(SafeQueueLogger)


def get_queue_logger(name: str = "queue_logger") -> SafeQueueLogger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers to prevent duplicates
    logger.handlers.clear()
    
    handler = logging.FileHandler(QUEUE_LOG_FILE, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    logger.addHandler(handler)
    logger.propagate = False
    
    return logger
