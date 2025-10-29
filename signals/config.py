# signals/config.py
import os
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv


@dataclass
class AuthConfig:
    """Конфигурация для авторизации в Telegram"""

    api_id: int
    api_hash: str
    phone: str
    session_name: str

    @classmethod
    def from_env(cls) -> "AuthConfig":
        """
        Загрузка конфигурации из .env файла

        Returns:
            AuthConfig экземпляр

        Raises:
            ValueError: Если обязательные параметры отсутствуют или некорректны
        """
        load_dotenv()

        api_id_str = os.getenv('API_ID')
        api_hash = os.getenv('API_HASH')
        phone = os.getenv('PHONE_NUMBER')
        session_name = os.getenv('SESSION_NAME', 'trading_bot_session')

        if not api_id_str:
            raise ValueError("API_ID должен быть указан в .env")
        if not api_hash:
            raise ValueError("API_HASH должен быть указан в .env")
        if not phone:
            raise ValueError("PHONE_NUMBER должен быть указан в .env")

        try:
            api_id = int(api_id_str)
        except ValueError:
            raise ValueError("API_ID должен быть числом")

        return cls(
            api_id=api_id,
            api_hash=api_hash,
            phone=phone,
            session_name=session_name
        )


@dataclass
class Channel:
    """Конфигурация канала для парсинга"""

    chat_id: int
    enabled: bool


@dataclass
class ChannelsConfig:
    """Конфигурация всех каналов"""

    channels: List[Channel]

    @classmethod
    def from_env(cls) -> "ChannelsConfig":
        """
        Загрузка конфигурации каналов из .env файла

        Returns:
            ChannelsConfig экземпляр
        """
        load_dotenv()

        channels = []

        for i in range(1, 5):
            channel_key = f"CHANNEL{i}"
            enabled_key = f"CHANNEL{i}_ENABLED"

            chat_id_str = os.getenv(channel_key)
            enabled_str = os.getenv(enabled_key, "false")

            if not chat_id_str:
                continue

            try:
                chat_id = int(chat_id_str)
            except ValueError:
                continue

            enabled = enabled_str.lower() in ('true', '1', 'yes')

            channels.append(Channel(
                chat_id=chat_id,
                enabled=enabled
            ))

        return cls(channels=channels)

    def get_active_channels(self) -> List[Channel]:
        """
        Получение списка активных каналов

        Returns:
            Список активных каналов
        """
        return [ch for ch in self.channels if ch.enabled]

    def get_active_chat_ids(self) -> List[int]:
        """
        Получение списка ID активных каналов

        Returns:
            Список chat_id активных каналов
        """
        return [ch.chat_id for ch in self.channels if ch.enabled]