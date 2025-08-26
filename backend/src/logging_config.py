import logging
import sys
import logging
import sys


def setup_logging(level=None):
    """
    Configure the root logger for the application.

    Args:
        level: logging level as a string (e.g. 'INFO') or numeric level. If None,
               defaults to logging.INFO.

    Notes:
        This function deliberately does NOT import application config. The
        entrypoint should call this after configuration is loaded and pass the
        desired level.
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    elif isinstance(level, int):
        # numeric level provided
        pass
    else:
        level = logging.INFO

    # Create stream handler and formatter
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    root = logging.getLogger()
    # Avoid adding duplicate handlers when called multiple times
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(handler)

    root.setLevel(level)

    logger = logging.getLogger("projeto_zero")
    # Ensure the returned logger has the effective level set explicitly so
    # tests and callers inspecting logger.level get a numeric level instead
    # of 0 (NOTSET).
    logger.setLevel(level)
    logger.info("Logging configured with level: %s", logging.getLevelName(level))
    return logger
