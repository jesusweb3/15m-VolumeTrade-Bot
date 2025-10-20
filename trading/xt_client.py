# trading/xt_client.py
import asyncio
from typing import Dict, List
import requests
from pyxt.perp import Perp
from trading.config import TradingConfig
from utils.logger import get_logger


class XTClient:
    """Асинхронная обертка над XT Perpetual API"""

    def __init__(self, config: TradingConfig):
        self.logger = get_logger(__name__)
        self.config = config
        self.host = "https://fapi.xt.com"
        self.perp = Perp(
            host=self.host,
            access_key=config.api_key,
            secret_key=config.api_secret,
            timeout=10_000,
        )

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        """Нормализация символа: BTC/USDT -> btc_usdt"""
        s = symbol.replace("/", "_").replace("-", "_")
        if s.isupper() and s.endswith("USDT"):
            s = s[:-4] + "_USDT"
        s = s.lower()
        if "_" not in s and s.endswith("usdt"):
            s = s[:-4] + "_usdt"
        return s

    @staticmethod
    def _extract_response(resp) -> dict:
        """Извлечение данных из ответа pyxt (кортеж или dict)"""
        if isinstance(resp, tuple):
            _, resp_data, _ = resp
            return resp_data
        return resp

    async def set_leverage(self, symbol: str, leverage: int) -> None:
        """Установка кредитного плеча для обеих сторон (Long/Short)"""
        self.logger.info(f"Установка плеча {leverage}x для {symbol}")

        def _set():
            return self.perp.set_account_leverage(
                symbol=self._normalize_symbol(symbol),
                leverage=leverage,
                position_side="BOTH",
            )

        try:
            resp = await asyncio.to_thread(_set)
            resp = self._extract_response(resp)

            if not isinstance(resp, dict):
                raise RuntimeError(f"Неожиданный ответ: {resp}")

            rc = resp.get("rc", resp.get("returnCode"))
            if rc == 0:
                self.logger.info(f"Плечо {leverage}x установлено для {symbol}")
            else:
                error_msg = resp.get("mc") or resp.get("msgInfo") or resp.get("msg")
                raise RuntimeError(f"Ошибка установки плеча: {error_msg}")

        except Exception as e:
            error_msg = str(e)
            if "leverage not modified" in error_msg.lower():
                self.logger.info(f"Плечо {leverage}x уже установлено для {symbol}")
            else:
                raise

    async def get_contract_size(self, symbol: str) -> float:
        """Получение размера контракта (минимальный increment)"""
        normalized = self._normalize_symbol(symbol)

        def _get():
            url = f"{self.host}/future/market/v1/public/symbol/detail"
            resp = requests.get(url, params={"symbol": normalized}, timeout=10)
            resp.raise_for_status()
            return resp.json()

        try:
            data = await asyncio.to_thread(_get)

            if data.get("returnCode") != 0 or not data.get("result"):
                raise RuntimeError(f"Ошибка получения контракта: {data}")

            result = data["result"]
            contract_size = float(result.get("contractSize", 0))

            if contract_size <= 0:
                raise RuntimeError(f"Некорректный contractSize: {contract_size}")

            self.logger.info(f"Contract size для {symbol}: {contract_size}")
            return contract_size

        except Exception as e:
            self.logger.error(f"Ошибка получения contract size: {e}")
            raise

    async def place_market_order(
            self,
            symbol: str,
            side: str,
            qty: float,
            sl_price: float,
            position_side: str,
    ) -> str:
        """
        Открытие рыночного ордера с stop loss

        Args:
            symbol: Торговая пара (BTC/USDT)
            side: BUY или SELL
            qty: Количество (целое число)
            sl_price: Цена stop loss
            position_side: LONG или SHORT

        Returns:
            Order ID
        """
        self.logger.info(f"Открытие {side} {position_side} позиции по {symbol}: qty={qty}, SL={sl_price}")

        def _place():
            return self.perp.send_order(
                symbol=self._normalize_symbol(symbol),
                amount=int(qty),
                order_side=side,
                order_type="MARKET",
                position_side=position_side,
                trigger_stop_price=sl_price,
            )

        resp = await asyncio.to_thread(_place)
        resp = self._extract_response(resp)

        if not isinstance(resp, dict):
            raise RuntimeError(f"Неожиданный ответ при открытии ордера: {resp}")

        rc = resp.get("rc", resp.get("returnCode"))
        if rc != 0:
            error_msg = resp.get("mc") or resp.get("msgInfo") or resp.get("msg")
            raise RuntimeError(f"Ошибка открытия позиции: {error_msg}")

        result = resp.get("result", {})
        order_id = result.get("orderId") if isinstance(result, dict) else result

        self.logger.info(f"Позиция открыта: orderId={order_id}, {position_side}")

        return str(order_id)

    async def place_reduce_limit_orders(
            self,
            symbol: str,
            orders: List[Dict[str, float]],
            position_side: str,
    ) -> List[str]:
        """
        Выставление лимитных reduce-only ордеров (TP)

        Args:
            symbol: Торговая пара (BTC/USDT)
            orders: Список [{"price": ..., "qty": ...}, ...]
            position_side: LONG или SHORT

        Returns:
            Список order IDs
        """
        self.logger.info(f"Выставление {len(orders)} TP ордеров для {symbol}")

        side = "SELL" if position_side == "LONG" else "BUY"
        normalized = self._normalize_symbol(symbol)
        order_ids = []

        for i, order in enumerate(orders, start=1):
            price = float(order["price"])
            qty = int(order["qty"])

            def _place():
                return self.perp.send_order(
                    symbol=normalized,
                    amount=qty,
                    order_side=side,
                    order_type="LIMIT",
                    position_side=position_side,
                    price=price,
                )

            try:
                resp = await asyncio.to_thread(_place)
                resp = self._extract_response(resp)

                if not isinstance(resp, dict):
                    self.logger.error(f"TP [{i}] неожиданный ответ: {resp}")
                    continue

                rc = resp.get("rc", resp.get("returnCode"))
                if rc != 0:
                    error_msg = resp.get("mc") or resp.get("msgInfo") or resp.get("msg")
                    self.logger.error(f"TP [{i}] ошибка: {error_msg}")
                    continue

                result = resp.get("result", {})
                order_id = result.get("orderId") if isinstance(result, dict) else result
                order_ids.append(str(order_id))

                self.logger.info(f"TP [{i}/{len(orders)}] выставлен: price={price}, qty={qty}, orderId={order_id}")

            except Exception as e:
                self.logger.error(f"TP [{i}] исключение: {e}", exc_info=True)

        return order_ids