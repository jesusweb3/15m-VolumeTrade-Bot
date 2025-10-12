# main.py
import asyncio
from signals.auth.telegram_auth import TelegramAuth
from signals.parser.channel_parser import ChannelParser
from utils.logger import get_logger


class BotApplication:
    """Главное приложение бота"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.telegram_auth = TelegramAuth()
        self.channel_parser = None
        self.running = False
        self.shutdown_event = asyncio.Event()

    async def start(self):
        """Запуск бота"""
        self.logger.info("Запуск торгового бота")

        try:
            client = await self.telegram_auth.connect()

            self.channel_parser = ChannelParser(client)
            await self.channel_parser.start()

            self.running = True
            self.logger.info("Бот активен и готов к работе")

            await self.shutdown_event.wait()

        except Exception as e:
            self.logger.error(f"Критическая ошибка: {e}", exc_info=True)
        finally:
            await self.stop()

    async def stop(self):
        """Остановка бота"""
        if not self.running:
            return

        self.running = False
        self.logger.info("Остановка бота...")
        await self.telegram_auth.disconnect()
        self.logger.info("Бот остановлен")
        self.shutdown_event.set()


async def main():
    """Точка входа"""
    bot = BotApplication()

    try:
        await bot.start()
    except KeyboardInterrupt:
        bot.logger.info("Получен сигнал остановки")
        if bot.running:
            await bot.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass