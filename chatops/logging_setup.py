import logging
import os
from typing import Optional, cast


def setup_logging(level: Optional[str] = None) -> None:
    """Configure logging to JSON if available, else fallback to simple format.

    Respects LOG_LEVEL env (defaults INFO). Uses python-json-logger if installed.
    """
    env_level = cast(str, os.getenv("LOG_LEVEL", "INFO"))
    log_level = (level or env_level).upper()
    try:
        from pythonjsonlogger import jsonlogger

        handler = logging.StreamHandler()
        fmt = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={
                "asctime": "ts",
                "levelname": "level",
                "message": "msg",
            },
        )
        handler.setFormatter(fmt)
        root = logging.getLogger()
        root.handlers.clear()
        root.addHandler(handler)
        root.setLevel(log_level)
    except ModuleNotFoundError:
        # python-json-logger not installed, use basic logging
        logging.basicConfig(level=log_level, format="%(asctime)s %(levelname)s %(message)s")
    except Exception as e:
        # Catch any other JSON formatter setup errors
        logging.basicConfig(level=log_level, format="%(asctime)s %(levelname)s %(message)s")
        logging.warning("Failed to setup JSON logging: %s", e)
