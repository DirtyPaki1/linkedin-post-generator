from loguru import logger
import sys
from pathlib import Path
from config import get_settings

settings = get_settings()

# Remove default handler
logger.remove()

# Add console handler
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.log_level,
    colorize=True
)

# Add file handler
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logger.add(
    log_dir / "app_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level=settings.log_level
)

# Add error file handler
logger.add(
    log_dir / "errors_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR"
)

# Add performance logging
logger.add(
    log_dir / "performance_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {message}",
    filter=lambda record: record["extra"].get("type") == "performance"
)

def log_performance(operation: str, duration: float, metadata: dict = None):
    """Log performance metrics."""
    extra = {"type": "performance"}
    logger.bind(**extra).info(f"PERF: {operation} took {duration:.3f}s | {metadata or {}}")

def get_logger(name: str):
    """Get a logger instance with context."""
    return logger.bind(name=name)