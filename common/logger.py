import logging
import threading
from datetime import datetime
from typing import Optional

from .config import Config

_RUN_ID = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
_CONFIGURED = False


class _RunContextFilter(logging.Filter):
    """Attach a stable run identifier and thread name to every record."""

    def __init__(self, run_id: str):
        super().__init__()
        self.run_id = run_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = self.run_id
        record.thread_name = threading.current_thread().name
        return True


def _resolve_log_level(default: str = 'INFO') -> str:
    try:
        return Config().log_level
    except Exception:
        # Fallback when config.yml is absent during setup or tests.
        return default


def _configure_logging():
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_level = _resolve_log_level()
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(run_id)s | %(thread_name)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    handler.addFilter(_RunContextFilter(_RUN_ID))
    root_logger.addHandler(handler)

    logging.captureWarnings(True)
    _CONFIGURED = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    _configure_logging()
    return logging.getLogger(name or 'miniflux_ai')


logger = get_logger('miniflux_ai')
