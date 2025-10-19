# trading/config.py
import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class TradingConfig:
    """Конфигурация для торговли"""

    balance: float
    amount: float
    api_key: str
    api_secret: str

    @classmethod
    def from_env(cls) -> "TradingConfig":
        """
        Загрузка конфигурации из .env файла

        Returns:
            TradingConfig экземпляр

        Raises:
            ValueError: Если обязательные параметры отсутствуют или некорректны
        """
        load_dotenv()

        balance_str = os.getenv('BALANCE')
        amount_str = os.getenv('AMOUNT')
        api_key = os.getenv('BYBIT_API_KEY')
        api_secret = os.getenv('BYBIT_API_SECRET')

        if not balance_str:
            raise ValueError("BALANCE должен быть указан в .env")
        if not amount_str:
            raise ValueError("AMOUNT должен быть указан в .env")
        if not api_key:
            raise ValueError("BYBIT_API_KEY должен быть указан в .env")
        if not api_secret:
            raise ValueError("BYBIT_API_SECRET должен быть указан в .env")

        try:
            balance = float(balance_str)
        except ValueError:
            raise ValueError("BALANCE должен быть числом")

        try:
            amount = float(amount_str)
        except ValueError:
            raise ValueError("AMOUNT должен быть числом")

        if balance <= 0:
            raise ValueError("BALANCE должен быть положительным числом")
        if amount <= 0 or amount > 100:
            raise ValueError("AMOUNT должен быть в диапазоне (0, 100]")

        return cls(
            balance=balance,
            amount=amount,
            api_key=api_key,
            api_secret=api_secret
        )