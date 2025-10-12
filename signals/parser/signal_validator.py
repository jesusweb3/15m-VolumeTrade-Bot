# signals/parser/signal_validator.py


class SignalValidator:
    """Валидация сообщений на предмет торговых сигналов"""

    REQUIRED_KEYWORDS = [
        "Leverage:",
        "Entry Targets:",
        "Take-Profit Targets:",
        "Stop Targets:"
    ]

    @staticmethod
    def is_signal(text: str) -> bool:
        """
        Проверка является ли сообщение торговым сигналом

        Args:
            text: Текст сообщения

        Returns:
            True если это сигнал, False иначе
        """
        if not text:
            return False

        text_lower = text.lower()

        for keyword in SignalValidator.REQUIRED_KEYWORDS:
            if keyword.lower() not in text_lower:
                return False

        return True