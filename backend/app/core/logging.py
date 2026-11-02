import logging
import sys
from rich.logging import RichHandler


def setup_logger(name: str = "ai_video_studio", level: str = "INFO") -> logging.Logger:
    """Configure structured logging with rich handler and UTF-8 console output."""
    # Ensure Windows console supports UTF-8
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        console_handler = RichHandler(
            rich_tracebacks=True,
            show_time=True,
            show_level=True,
            show_path=False
        )
        formatter = logging.Formatter("%(message)s", datefmt="[%X]")
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


logger = setup_logger()
