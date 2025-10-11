# signals/auth/config.py
import os
from dataclasses import dataclass
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