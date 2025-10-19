# trading/signal_processor.py
import asyncio
from trading.position_manager import PositionManager
from utils.logger import get_logger


async def process_signals_queue(signal_queue: asyncio.Queue, position_manager: PositionManager) -> None:
    """
    Обработка очереди сигналов

    Args:
        signal_queue: Очередь с сигналами
        position_manager: Менеджер позиций
    """
    logger = get_logger(__name__)
    logger.info("Процессор сигналов запущен")

    while True:
        try:
            signal = await signal_queue.get()

            logger.info(f"Получен сигнал из очереди: {signal}")

            await position_manager.open_position_with_signal(signal)

            signal_queue.task_done()

        except asyncio.CancelledError:
            logger.info("Процессор сигналов остановлен")
            break
        except Exception as e:
            logger.error(f"Ошибка обработки сигнала из очереди: {e}", exc_info=True)