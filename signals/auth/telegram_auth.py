# signals/auth/telegram_auth.py
import asyncio
from pathlib import Path
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded, PhoneNumberInvalid, BadRequest, Unauthorized
from utils.logger import get_logger
from signals.config import SignalsConfig

logger = get_logger(__name__)


async def ainput(prompt: str) -> str:
    """Асинхронный ввод с поддержкой UTF-8"""
    return await asyncio.to_thread(input, prompt)


class TelegramAuth:
    def __init__(self, api_id: str, api_hash: str, phone_number: str, session_name: str,
                 device_model: str, system_version: str, app_version: str, lang_code: str):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.session_name = session_name
        self.device_model = device_model
        self.system_version = system_version
        self.app_version = app_version
        self.lang_code = lang_code

        self.sessions_dir = Path(__file__).parent / "sessions"
        self.sessions_dir.mkdir(exist_ok=True)

        self.session_path = self.sessions_dir / f"{self.session_name}.session"
        self.client: Client | None = None
        self.is_connected: bool = False

    @classmethod
    def from_config(cls) -> "TelegramAuth":
        """Создание экземпляра из конфигурации"""
        return cls(
            api_id=SignalsConfig.API_ID,
            api_hash=SignalsConfig.API_HASH,
            phone_number=SignalsConfig.PHONE_NUMBER,
            session_name=SignalsConfig.SESSION_NAME,
            device_model=SignalsConfig.DEVICE_MODEL,
            system_version=SignalsConfig.SYSTEM_VERSION,
            app_version=SignalsConfig.APP_VERSION,
            lang_code=SignalsConfig.LANG_CODE
        )

    async def connect(self) -> Client:
        """Основной метод подключения к Telegram"""
        logger.info("Начало подключения к Telegram")

        self.client = Client(
            name=str(self.session_path),
            api_id=self.api_id,
            api_hash=self.api_hash,
            device_model=self.device_model,
            system_version=self.system_version,
            app_version=self.app_version,
            lang_code=self.lang_code,
            no_updates=True
        )

        await self.client.connect()
        self.is_connected = True

        try:
            user = await self.client.get_me()
            logger.info(f"Успешное подключение как {user.first_name} (ID: {user.id})")
        except (BadRequest, Unauthorized):
            logger.info("Требуется авторизация")
            await self._authorize()
            user = await self.client.get_me()
            logger.info(f"Успешное подключение как {user.first_name} (ID: {user.id})")

        return self.client

    async def _authorize(self) -> None:
        """Авторизация пользователя"""
        try:
            sent_code = await self.client.send_code(self.phone_number)

            try:
                code = await ainput(f"Введите код отправленный на {self.phone_number}: ")
            except asyncio.CancelledError:
                logger.info("Авторизация прервана пользователем")
                raise KeyboardInterrupt

            await self.client.sign_in(self.phone_number, sent_code.phone_code_hash, code)

        except SessionPasswordNeeded:
            try:
                password = await ainput("Введите пароль двухфакторной аутентификации: ")
            except asyncio.CancelledError:
                logger.info("Авторизация прервана пользователем")
                raise KeyboardInterrupt

            await self.client.check_password(password)

        except PhoneNumberInvalid:
            logger.error(f"Неверный номер телефона: {self.phone_number}")
            raise ValueError(f"Неверный номер телефона: {self.phone_number}")

    async def disconnect(self) -> None:
        """Отключение от Telegram"""
        if self.client and self.is_connected:
            try:
                await self.client.disconnect()
                self.is_connected = False
            except Exception as e:
                logger.warning(f"Ошибка при отключении: {e}")