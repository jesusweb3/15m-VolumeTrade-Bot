# utils/logger.py
import logging
import sys
import http.client
from datetime import datetime
from pathlib import Path


class MillisecondFormatter(logging.Formatter):
    """Форматтер с миллисекундами (3 цифры)"""

    def formatTime(self, record, datefmt=None):
        if datefmt:
            s = datetime.fromtimestamp(record.created).strftime(datefmt)
            s = f"{s}.{int(record.msecs):03d}"
        else:
            s = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
            s = f"{s}.{int(record.msecs):03d}"
        return s


class FilteredStdout:
    """Обёртка для stdout, фильтрующая шумные выводы"""

    FILTER_PATTERNS = [
        'method:',
        'headers:',
        'params:',
        'body:',
        'data:',
        'code:',
    ]

    def __init__(self, original_stdout):
        self.original_stdout = original_stdout
        self._buffer = ""

    def write(self, text: str) -> int:
        """Фильтрует и пишет в stdout"""
        if text is None:
            return 0

        self._buffer += text

        if '\n' in self._buffer or len(self._buffer) > 1000:
            lines = self._buffer.split('\n')
            for line in lines[:-1]:
                if not self._should_filter(line):
                    self.original_stdout.write(line + '\n')
            self._buffer = lines[-1]

        return len(text)

    def flush(self):
        if self._buffer and not self._should_filter(self._buffer):
            self.original_stdout.write(self._buffer)
            self._buffer = ""
        if hasattr(self.original_stdout, 'flush'):
            self.original_stdout.flush()

    @staticmethod
    def _should_filter(line: str) -> bool:
        """Проверяет, нужно ли фильтровать строку"""
        if not line.strip():
            return False
        return any(pattern in line for pattern in FilteredStdout.FILTER_PATTERNS)

    def __getattr__(self, name):
        return getattr(self.original_stdout, name)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Создает логгер с консольным и файловым выводом

    Args:
        name: Имя логгера
        level: Уровень логирования

    Returns:
        Настроенный логгер
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(level)

    formatter = MillisecondFormatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)-37s | %(message)s',
        datefmt='%d-%m-%y %H:%M:%S'
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    project_root = Path(__file__).resolve().parent.parent
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)

    log_file_path = logs_dir / "logs.txt"

    file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.propagate = False

    return logger


def initialize_logging() -> None:
    """
    Инициализация логирования приложения.
    Отключает verbose логи внешних библиотек и перехватывает print() statements.
    """
    http.client.HTTPConnection.debuglevel = 0

    logging.getLogger('pyxt').setLevel(logging.CRITICAL)
    logging.getLogger('pyxt.http').setLevel(logging.CRITICAL)
    logging.getLogger('requests').setLevel(logging.CRITICAL)
    logging.getLogger('urllib3').setLevel(logging.CRITICAL)
    logging.getLogger('urllib3.connectionpool').setLevel(logging.CRITICAL)
    logging.getLogger('telethon').setLevel(logging.WARNING)
    logging.getLogger('telethon.client').setLevel(logging.WARNING)
    logging.getLogger('http.client').setLevel(logging.CRITICAL)

    sys.stdout = FilteredStdout(sys.stdout)
    sys.stderr = FilteredStdout(sys.stderr)


def set_log_level(level: int) -> None:
    """
    Устанавливает уровень логирования для всех логгеров

    Args:
        level: Уровень логирования
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    for handler in root_logger.handlers:
        handler.setLevel(level)