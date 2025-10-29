# main.py
import asyncio
from signals.auth.telegram_auth import TelegramAuth
from signals.parser.channel_parser import ChannelParser
from trading.config import TradingConfig
from trading.xt_client import XTClient
from trading.symbols_cache import SymbolsCache
from trading.position_manager import PositionManager
from trading.signal_processor import process_signals_queue
from utils.logger import get_logger, initialize_logging


class BotApplication:
    """Главное приложение бота"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.telegram_auth = TelegramAuth()
        self.signal_queue = asyncio.Queue()
        self.channel_parser = None
        self.position_manager = None
        self.running = False
        self.shutdown_event = asyncio.Event()

    async def start(self):
        """Запуск бота"""
        self.logger.info("Запуск торгового бота (XT)")

        try:
            client = await self.telegram_auth.connect()

            trading_config = TradingConfig.from_env()
            xt_client = XTClient(trading_config)

            symbols_cache = SymbolsCache()
            await symbols_cache.load()

            self.position_manager = PositionManager(xt_client, trading_config, symbols_cache)

            self.channel_parser = ChannelParser(client, self.signal_queue)

            self.running = True

            parser_task = asyncio.create_task(self.channel_parser.start())
            processor_task = asyncio.create_task(process_signals_queue(self.signal_queue, self.position_manager))

            await self.channel_parser.wait_ready()

            self.logger.info("Бот активен и готов к работе")

            try:
                await asyncio.gather(
                    parser_task,
                    processor_task,
                    self.shutdown_event.wait()
                )
            except asyncio.CancelledError:
                self.logger.info("Получен сигнал об остановке от пользователя")
                raise

        except Exception as e:
            self.logger.error(f"Критическая ошибка: {e}", exc_info=True)
        finally:
            await self.stop()

    async def stop(self):
        """Остановка бота"""
        if not self.running:
            return

        self.running = False

        if self.channel_parser:
            self.channel_parser.stop()

        await self.telegram_auth.disconnect()
        self.logger.info("Бот успешно остановлен")
        self.shutdown_event.set()


async def main():
    """Точка входа"""
    initialize_logging()

    bot = BotApplication()

    try:
        await bot.start()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass