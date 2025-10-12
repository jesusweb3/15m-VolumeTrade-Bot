# signals/parser/signal_parser.py
import re
from typing import Optional
from signals.models import Signal


class SignalParser:
    """Парсер торговых сигналов"""

    @staticmethod
    def parse(text: str) -> Optional[Signal]:
        """
        Парсинг торгового сигнала из текста

        Args:
            text: Текст сообщения

        Returns:
            Signal или None если парсинг не удался
        """
        try:
            lines = text.strip().split('\n')

            asset = SignalParser._parse_asset(lines[0])
            direction = SignalParser._parse_direction(lines[0])
            leverage = SignalParser._parse_leverage(text)
            entry = SignalParser._parse_entry(text)
            take_profits = SignalParser._parse_take_profits(text)
            stop_loss = SignalParser._parse_stop_loss(text)

            if not all([asset, direction, leverage, entry, take_profits, stop_loss]):
                return None

            return Signal(
                asset=asset,
                direction=direction,
                leverage=leverage,
                entry=entry,
                take_profits=take_profits,
                stop_loss=stop_loss
            )

        except (IndexError, ValueError, AttributeError):
            return None

    @staticmethod
    def _parse_asset(first_line: str) -> Optional[str]:
        """Извлечение актива из первой строки"""
        match = re.search(r'([A-Z]+/USDT)', first_line)
        return match.group(1) if match else None

    @staticmethod
    def _parse_direction(first_line: str) -> Optional[str]:
        """Определение направления сделки"""
        first_line_lower = first_line.lower()
        if 'short' in first_line_lower or '🟥' in first_line:
            return 'Short'
        elif 'long' in first_line_lower or '🟩' in first_line:
            return 'Long'
        return None

    @staticmethod
    def _parse_leverage(text: str) -> Optional[int]:
        """Извлечение кредитного плеча"""
        match = re.search(r'Leverage:.*?\((\d+)X\)', text, re.IGNORECASE)
        return int(match.group(1)) if match else None

    @staticmethod
    def _parse_entry(text: str) -> Optional[float]:
        """Извлечение цены входа"""
        match = re.search(r'Entry Targets:\s*(\d+\.?\d*)', text, re.IGNORECASE)
        return float(match.group(1)) if match else None

    @staticmethod
    def _parse_take_profits(text: str) -> Optional[list]:
        """Извлечение всех take-profit уровней"""
        tp_section = re.search(r'Take-Profit Targets:(.*?)Stop Targets:', text, re.IGNORECASE | re.DOTALL)
        if not tp_section:
            return None

        tp_text = tp_section.group(1)
        matches = re.findall(r'\d+\)\s*(\d+\.?\d*)', tp_text)

        if not matches:
            return None

        return [float(tp) for tp in matches]

    @staticmethod
    def _parse_stop_loss(text: str) -> Optional[float]:
        """Извлечение stop-loss уровня"""
        match = re.search(r'Stop Targets:\s*(\d+\.?\d*)', text, re.IGNORECASE)
        return float(match.group(1)) if match else None