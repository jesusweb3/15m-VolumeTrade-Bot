# signals/config.py
import os
from dotenv import load_dotenv
from utils.logger import get_logger

logger = get_logger(__name__)

load_dotenv()


class SignalsConfig:
    API_ID: str = os.getenv("API_ID", "")
    API_HASH: str = os.getenv("API_HASH", "")
    PHONE_NUMBER: str = os.getenv("PHONE_NUMBER", "")
    SESSION_NAME: str = os.getenv("SESSION_NAME", "")
    DEVICE_MODEL: str = os.getenv("DEVICE_MODEL", "")
    SYSTEM_VERSION: str = os.getenv("SYSTEM_VERSION", "")
    APP_VERSION: str = os.getenv("APP_VERSION", "")
    LANG_CODE: str = os.getenv("LANG_CODE", "")

    @classmethod
    def validate(cls) -> None:
        """Валидация обязательных параметров"""
        required_fields = {
            "API_ID": cls.API_ID,
            "API_HASH": cls.API_HASH,
            "PHONE_NUMBER": cls.PHONE_NUMBER,
            "SESSION_NAME": cls.SESSION_NAME,
            "DEVICE_MODEL": cls.DEVICE_MODEL,
            "SYSTEM_VERSION": cls.SYSTEM_VERSION,
            "APP_VERSION": cls.APP_VERSION,
            "LANG_CODE": cls.LANG_CODE
        }

        missing_fields = [field for field, value in required_fields.items() if not value]

        if missing_fields:
            logger.error(f"Отсутствуют обязательные параметры: {', '.join(missing_fields)}")
            raise ValueError(f"Отсутствуют обязательные параметры в .env: {', '.join(missing_fields)}")


SignalsConfig.validate()