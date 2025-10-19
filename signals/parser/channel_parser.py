# signals/parser/channel_parser.py
import asyncio
from typing import Optional
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

    async def start(self):
        """Запуск прослушивания каналов"""
        if not self.active_chat_ids:
            self.logger.warning("Нет активных каналов для прослушивания")
            return

        self.logger.info(f"Запуск парсера для {len(self.active_channels)} каналов:")
        for channel in self.active_channels:
            self.logger.info(f"  - {channel.name} (ID: {channel.chat_id})")

        @self.client.on(events.NewMessage(chats=self.active_chat_ids))
        async def handler(event):
            await self._handle_new_message(event)

        self.logger.info("Парсер активен, ожидание новых сообщений...")

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

            channel_name = self._get_channel_name(chat_id)

            signal = SignalParser.parse(message_text)

            if signal:
                await self.signal_queue.put(signal)
                self.logger.info(f"[{channel_name}] Сигнал добавлен в очередь: {signal}")
            else:
                self.logger.warning(f"[{channel_name}] Не удалось распарсить сигнал")

        except Exception as e:
            self.logger.error(f"Ошибка обработки сообщения: {e}", exc_info=True)

    def _get_channel_name(self, chat_id: int) -> str:
        """
        Получение имени канала по chat_id

        Args:
            chat_id: ID чата

        Returns:
            Имя канала или 'unknown'
        """
        for channel in self.active_channels:
            if channel.chat_id == chat_id:
                return channel.name
        return "unknown"