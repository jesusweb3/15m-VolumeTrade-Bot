# main.py
import asyncio
from signals.auth.telegram_auth import TelegramAuth
from utils.logger import get_logger

logger = get_logger(__name__)


async def main():
    """Точка входа приложения"""
    auth = None

    try:
        logger.info("Запуск торгового бота")

        auth = TelegramAuth.from_config()
        await auth.connect()

        logger.info("Бот успешно запущен и авторизован")

        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            logger.info("Получен сигнал остановки")

    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки (Ctrl+C)")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
    finally:
        if auth:
            await auth.disconnect()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())