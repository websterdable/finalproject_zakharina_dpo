"""
Настройка логирования для приложения.
"""
import logging
import logging.handlers
from pathlib import Path


def setup_logging(
    log_file: str = "logs/valutatrade.log",
    level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5
) -> None:
    """
    Настраивает логирование.

    Args:
        log_file: Путь к файлу логов
        level: Уровень логирования
        max_bytes: Максимальный размер файла перед ротацией
        backup_count: Количество файлов бэкапа
    """
    # Создаем директорию для логов, если её нет
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Форматтер
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Файловый обработчик с ротацией
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)

    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Удаляем существующие обработчики
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Добавляем наши обработчики
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Логируем начало работы
    logging.info("Логирование настроено")
