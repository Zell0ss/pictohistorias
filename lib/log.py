try:
    from logcentral_client import get_logger
except ImportError:
    from loguru import logger as _logger

    def get_logger(name: str):
        return _logger.bind(source=name)
