# trading/symbols_cache.py
import asyncio
from typing import Dict
import requests
from utils.logger import get_logger


class SymbolsCache:
    """Кеш информации об активах XT с API"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.host = "https://fapi.xt.com"
        self._cache: Dict[str, Dict] = {}

    async def load(self) -> None:
        """
        Загрузка списка активов с XT API и кеширование

        Raises:
            RuntimeError: Если запрос не удался
        """
        def _fetch():
            url = f"{self.host}/future/market/v1/public/symbol/list"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            return resp.json()

        try:
            data = await asyncio.to_thread(_fetch)

            if data.get("returnCode") != 0 or not isinstance(data.get("result"), list):
                raise RuntimeError(f"Ошибка получения списка активов: {data}")

            symbols = data["result"]

            for symbol_data in symbols:
                if not symbol_data.get("isOpenApi"):
                    continue

                symbol = symbol_data.get("symbol", "").lower()
                contract_size_str = symbol_data.get("contractSize", "0")

                try:
                    contract_size = float(contract_size_str)
                except (ValueError, TypeError):
                    self.logger.warning(f"Некорректный contractSize для {symbol}: {contract_size_str}")
                    continue

                self._cache[symbol] = {
                    "symbol": symbol,
                    "contractSize": contract_size,
                    "isOpenApi": True
                }

            total_symbols = len(symbols)
            cached_symbols = len(self._cache)
            self.logger.info(f"Загружено {cached_symbols} активов в кеш (всего на бирже: {total_symbols})")

        except requests.RequestException as e:
            self.logger.error(f"Ошибка подключения при загрузке активов: {e}")
            raise RuntimeError(f"API недоступен: {e}")
        except Exception as e:
            self.logger.error(f"Ошибка загрузки активов: {e}")
            raise RuntimeError(f"Ошибка при загрузке активов: {e}")

    def is_tradeable(self, symbol: str) -> bool:
        """
        Проверка можно ли торговать активом через API

        Args:
            symbol: Символ (нормализованный, например aero_usdt)

        Returns:
            True если активом можно торговать, False иначе
        """
        normalized = self.normalize_symbol(symbol)
        return normalized in self._cache

    def get_contract_size(self, symbol: str) -> float:
        """
        Получение размера контракта

        Args:
            symbol: Символ (нормализованный, например aero_usdt)

        Returns:
            Размер контракта (float)

        Raises:
            KeyError: Если актив не найден в кеше
        """
        normalized = self.normalize_symbol(symbol)

        if normalized not in self._cache:
            raise KeyError(f"Актив не найден в кеше: {normalized}")

        return self._cache[normalized]["contractSize"]

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        """Нормализация символа: BTC/USDT -> btc_usdt"""
        s = symbol.replace("/", "_").replace("-", "_")
        if s.isupper() and s.endswith("USDT"):
            s = s[:-4] + "_USDT"
        s = s.lower()
        if "_" not in s and s.endswith("usdt"):
            s = s[:-4] + "_usdt"
        return s

    def get_all_symbols(self) -> list:
        """
        Получение списка всех кешированных символов

        Returns:
            Список символов
        """
        return list(self._cache.keys())