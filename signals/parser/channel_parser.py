# signals/parser/channel_parser.py
import asyncio
from typing import Optional, Set, Dict, Tuple
from telethon import TelegramClient, events
from signals.config import ChannelsConfig
from signals.parser.signal_validator import SignalValidator
from signals.parser.signal_parser import SignalParser
from utils.logger import get_logger


class ChannelParser:
    """Парсер сообщений из Telegram каналов"""

    def __init__(
            self,
            client: TelegramClient,
            signal_queue: asyncio.Queue,
            channels_config: Optional[ChannelsConfig] = None
    ):
        self.logger = get_logger(__name__)
        self.client = client
        self.signal_queue = signal_queue
        self.channels_config = channels_config if channels_config else ChannelsConfig.from_env()
        self.active_channels = self.channels_config.get_active_channels()
        self.active_chat_ids = self.channels_config.get_active_chat_ids()
        self._chat_id_to_title: Dict[int, str] = {}
        self._running = False
        self._processed_signals: Set[Tuple[str, str, float]] = set()
        self._lock = asyncio.Lock()
        self._handler_registered = False
        self._stop_event = asyncio.Event()
        self._ready_event = asyncio.Event()

    async def _load_channel_titles(self) -> None:
        """Загрузка названий каналов из Telegram API"""
        for chat_id in self.active_chat_ids:
            try:
                entity = await self.client.get_entity(chat_id)
                title = entity.title if hasattr(entity, 'title') else f"ID: {chat_id}"
                self._chat_id_to_title[chat_id] = title
                self.logger.debug(f"Загружено название канала: {title} (ID: {chat_id})")
            except ValueError as e:
                if "Cannot find any entity" in str(e):
                    self.logger.warning(f"Канал не найден: ID: {chat_id}")
                else:
                    self.logger.warning(f"Ошибка загрузки названия канала {chat_id}: {e}")
                self._chat_id_to_title[chat_id] = f"ID: {chat_id}"
            except Exception as e:
                self.logger.warning(f"Ошибка загрузки названия канала {chat_id}: {e}")
                self._chat_id_to_title[chat_id] = f"ID: {chat_id}"

    async def start(self):
        """Запуск прослушивания каналов"""
        if self._running:
            self.logger.warning("Парсер уже запущен")
            return

        if not self.active_chat_ids:
            self.logger.warning("Нет активных каналов для прослушивания")
            return

        self._running = True

        await self._load_channel_titles()

        channel_word = self._get_channel_word(len(self.active_channels))
        self.logger.info(f"Запущен парсер для {len(self.active_channels)} {channel_word}:")
        for chat_id in self.active_chat_ids:
            title = self._chat_id_to_title.get(chat_id, f"ID: {chat_id}")
            self.logger.info(f"  - {title} (ID: {chat_id})")

        if not self._handler_registered:
            @self.client.on(events.NewMessage(chats=self.active_chat_ids))
            async def handler(event):
                await self._handle_new_message(event)

            self._handler_registered = True

        self._ready_event.set()

        try:
            await self._stop_event.wait()
        except asyncio.CancelledError:
            pass
        finally:
            self._running = False

    def stop(self):
        """Остановка парсера"""
        self._stop_event.set()

    async def wait_ready(self):
        """Ожидание готовности парсера"""
        await self._ready_event.wait()

    async def _handle_new_message(self, event):
        """
        Обработка нового сообщения

        Args:
            event: Событие NewMessage от Telethon
        """
        try:
            chat_id = event.chat_id
            message_text = event.message.text or ""

            if not SignalValidator.is_signal(message_text):
                return

            channel_title = self._get_channel_title(chat_id)

            signal = SignalParser.parse(message_text)

            if not signal:
                self.logger.warning(f"[{channel_title}] Не удалось распарсить сигнал")
                return

            signal_key = (signal.asset, signal.direction, signal.entry)

            async with self._lock:
                if signal_key in self._processed_signals:
                    self.logger.debug(f"[{channel_title}] Сигнал уже обработан: {signal_key}")
                    return

                self._processed_signals.add(signal_key)

            await self.signal_queue.put(signal)
            self.logger.info(f"[{channel_title}] Сигнал добавлен в очередь: {signal}")

        except Exception as e:
            self.logger.error(f"Ошибка обработки сообщения: {e}", exc_info=True)

    @staticmethod
    def _get_channel_word(count: int) -> str:
        """
        Правильное склонение слова 'канал' для родительного падежа (для X)

        Args:
            count: Количество каналов

        Returns:
            Правильно склоненное слово
        """
        if count % 10 == 1 and count % 100 != 11:
            return "канала"
        else:
            return "каналов"

    def _get_channel_title(self, chat_id: int) -> str:
        """
        Получение названия канала по chat_id

        Args:
            chat_id: ID чата

        Returns:
            Название канала или 'ID: {chat_id}'
        """
        return self._chat_id_to_title.get(chat_id, f"ID: {chat_id}")