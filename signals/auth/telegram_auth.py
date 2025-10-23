# signals/auth/telegram_auth.py
from pathlib import Path
from typing import Optional
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from signals.config import AuthConfig
from utils.logger import get_logger


class TelegramAuth:
    """Управление авторизацией в Telegram аккаунте"""

    def __init__(self, config: Optional[AuthConfig] = None):
        self.logger = get_logger(__name__)

        self.config = config if config else AuthConfig.from_env()

        project_root = Path(__file__).resolve().parent.parent.parent
        self.sessions_dir = project_root / 'signals' / 'auth' / 'sessions'
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        self.session_path = self.sessions_dir / f"{self.config.session_name}.session"

        self.client: Optional[TelegramClient] = None

    async def connect(self) -> TelegramClient:
        """
        Подключение к Telegram аккаунту

        Returns:
            Активный TelegramClient
        """
        if self.client and self.client.is_connected():
            self.logger.info("Клиент уже подключен")
            return self.client

        self.logger.info(
            "Инициализация TelegramClient с параметрами: "
            "auto_reconnect=True, connection_retries=5, retry_delay=5s, timeout=10s"
        )

        self.client = TelegramClient(
            str(self.session_path),
            self.config.api_id,
            self.config.api_hash,
            auto_reconnect=True,
            connection_retries=5,
            retry_delay=5,
            timeout=10,
            device_model="Trading Bot Server",
            system_version="1.0",
            app_version="1.0.0",
            lang_code="en",
            system_lang_code="en"
        )

        await self.client.connect()

        if not await self.client.is_user_authorized():
            self.logger.info("Требуется авторизация")
            await self._authorize()
        else:
            self.logger.info("Сессия активна, авторизация не требуется")

        me = await self.client.get_me()
        self.logger.info(f"Подключен как: {me.first_name} (@{me.username if me.username else 'no username'})")

        return self.client

    async def _authorize(self) -> None:
        """Процесс авторизации с обработкой кода и 2FA"""
        await self.client.send_code_request(self.config.phone)
        self.logger.info(f"Код отправлен на {self.config.phone}")

        code = input("Введите код из Telegram: ").strip()

        try:
            await self.client.sign_in(self.config.phone, code)
            self.logger.info("Авторизация успешна")
        except SessionPasswordNeededError:
            self.logger.info("Требуется 2FA пароль")
            password = input("Введите 2FA пароль: ").strip()
            await self.client.sign_in(password=password)
            self.logger.info("Авторизация с 2FA успешна")

    async def disconnect(self) -> None:
        """Корректное отключение клиента"""
        if self.client and self.client.is_connected():
            await self.client.disconnect()
            self.logger.info("Клиент отключен")

    async def is_authorized(self) -> bool:
        """
        Проверка статуса авторизации

        Returns:
            True если авторизован, False иначе
        """
        if not self.client:
            return False

        try:
            return await self.client.is_user_authorized()
        except Exception as e:
            self.logger.error(f"Ошибка проверки авторизации: {e}")
            return False

    def get_client(self) -> Optional[TelegramClient]:
        """
        Получение текущего клиента

        Returns:
            TelegramClient или None
        """
        return self.client