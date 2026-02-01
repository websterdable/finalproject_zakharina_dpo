# valutatrade_hub/parser_service/__init__.py
"""
Parser Service для обновления курсов валют.
"""

from .config import ParserConfig, config
from .scheduler import Scheduler, scheduler
from .storage import ParserStorage
from .updater import RatesUpdater

__all__ = [
    'config', 'ParserConfig',
    'RatesUpdater', 'ParserStorage',
    'scheduler', 'Scheduler'
]
