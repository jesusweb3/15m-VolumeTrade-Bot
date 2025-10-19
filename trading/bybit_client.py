# trading/bybit_client.py
import asyncio
from typing import Dict, List
from pybit.unified_trading import HTTP
from trading.config import TradingConfig
from utils.logger import get_logger


class BybitClient:
    """Асинхронная обертка над Bybit API"""

    def __init__(self, config: TradingConfig):
        self.logger = get_logger(__name__)
        self.config = config
        self.http = HTTP(
            api_key=config.api_key,
            api_secret=config.api_secret,
            testnet=False,
            timeout=10_000,
            recv_window=5_000
        )
        self.hedge_mode_enabled = False

    async def enable_hedge_mode(self) -> None:
        """Включение hedge mode для USDT perpetual"""
        if self.hedge_mode_enabled:
            self.logger.info("Hedge mode уже включен")
            return

        self.logger.info("Включение hedge mode...")

        def _enable():
            return self.http.switch_position_mode(
                category="linear",
                coin="USDT",
                mode=3
            )

        resp = await asyncio.to_thread(_enable)

        if not isinstance(resp, dict) or resp.get("retCode") != 0:
            raise RuntimeError(f"Ошибка включения hedge mode: {resp}")

        self.hedge_mode_enabled = True
        self.logger.info("Hedge mode успешно включен")

    async def set_leverage(self, symbol: str, leverage: int) -> None:
        """Установка кредитного плеча"""
        self.logger.info(f"Установка плеча {leverage}x для {symbol}")

        def _set():
            return self.http.set_leverage(
                category="linear",
                symbol=symbol,
                buyLeverage=str(leverage),
                sellLeverage=str(leverage)
            )

        try:
            resp = await asyncio.to_thread(_set)

            if not isinstance(resp, dict) or resp.get("retCode") != 0:
                raise RuntimeError(f"Ошибка установки плеча: {resp}")

            self.logger.info(f"Плечо {leverage}x установлено для {symbol}")
        except Exception as e:
            error_msg = str(e)
            if "110043" in error_msg or "leverage not modified" in error_msg:
                self.logger.info(f"Плечо {leverage}x уже установлено для {symbol}")
            else:
                raise

    async def get_min_order_qty(self, symbol: str) -> str:
        """Получение минимального размера ордера"""

        def _get():
            return self.http.get_instruments_info(
                category="linear",
                symbol=symbol
            )

        resp = await asyncio.to_thread(_get)

        if not isinstance(resp, dict) or resp.get("retCode") != 0:
            raise RuntimeError(f"Ошибка получения информации о символе: {resp}")

        instruments = resp.get("result", {}).get("list", [])
        if not instruments:
            raise RuntimeError(f"Символ {symbol} не найден")

        lot_filter = instruments[0].get("lotSizeFilter", {})
        min_qty = lot_filter.get("minOrderQty")

        if min_qty is None:
            raise RuntimeError(f"minOrderQty не найден для {symbol}")

        return str(min_qty)

    async def place_market_order(
            self,
            symbol: str,
            side: str,
            qty: float,
            sl_price: float,
            position_idx: int
    ) -> str:
        """
        Открытие рыночного ордера с stop loss

        Args:
            symbol: Торговая пара
            side: Buy или Sell
            qty: Количество
            sl_price: Цена stop loss
            position_idx: 1 для Long, 2 для Short

        Returns:
            Order ID
        """
        self.logger.info(f"Открытие {side} позиции по {symbol}: qty={qty}, SL={sl_price}")

        def _place():
            return self.http.place_order(
                category="linear",
                symbol=symbol,
                side=side,
                orderType="Market",
                qty=str(qty),
                stopLoss=str(sl_price),
                slTriggerBy="MarkPrice",
                tpslMode="Full",
                slOrderType="Market",
                positionIdx=str(position_idx)
            )

        resp = await asyncio.to_thread(_place)

        if not isinstance(resp, dict) or resp.get("retCode") != 0:
            raise RuntimeError(f"Ошибка открытия позиции: {resp}")

        order_id = resp.get("result", {}).get("orderId", "<unknown>")
        self.logger.info(f"Позиция открыта: orderId={order_id}")

        return order_id

    async def place_reduce_limit_orders(
            self,
            symbol: str,
            side: str,
            orders: List[Dict[str, float]],
            position_idx: int
    ) -> List[str]:
        """
        Выставление лимитных reduce-only ордеров (TP)

        Args:
            symbol: Торговая пара
            side: Sell для Long, Buy для Short
            orders: Список [{"price": ..., "qty": ...}, ...]
            position_idx: 1 для Long, 2 для Short

        Returns:
            Список order IDs
        """
        self.logger.info(f"Выставление {len(orders)} TP ордеров для {symbol}")

        order_ids = []

        for i, order in enumerate(orders, start=1):
            price = order["price"]
            qty = order["qty"]

            def _place():
                return self.http.place_order(
                    category="linear",
                    symbol=symbol,
                    side=side,
                    orderType="Limit",
                    price=str(price),
                    qty=str(qty),
                    timeInForce="GTC",
                    reduceOnly=True,
                    positionIdx=str(position_idx)
                )

            resp = await asyncio.to_thread(_place)

            if not isinstance(resp, dict) or resp.get("retCode") != 0:
                self.logger.error(f"Ошибка TP ордера [{i}]: {resp}")
                continue

            order_id = resp.get("result", {}).get("orderId", "<unknown>")
            order_ids.append(order_id)
            self.logger.info(f"TP [{i}/{len(orders)}] выставлен: price={price}, qty={qty}, orderId={order_id}")

        return order_ids