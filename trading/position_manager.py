# trading/position_manager.py
from typing import List, Dict
from decimal import Decimal, ROUND_DOWN
from signals.models import Signal
from trading.bybit_client import BybitClient
from trading.config import TradingConfig
from utils.logger import get_logger


class PositionManager:
    """Управление торговыми позициями"""

    def __init__(self, bybit_client: BybitClient, config: TradingConfig):
        self.logger = get_logger(__name__)
        self.bybit_client = bybit_client
        self.config = config

    def calculate_position_size(
            self,
            entry_price: float,
            leverage: int,
            min_qty_str: str
    ) -> float:
        """
        Расчет размера позиции

        Args:
            entry_price: Цена входа
            leverage: Кредитное плечо
            min_qty_str: Минимальный размер ордера (например "0.1")

        Returns:
            Размер позиции в монетах
        """
        margin = self.config.balance * (self.config.amount / 100)
        volume = margin * leverage
        qty = volume / entry_price

        min_qty = Decimal(min_qty_str)

        qty_decimal = Decimal(str(qty))
        rounded_qty = qty_decimal.quantize(min_qty, rounding=ROUND_DOWN)

        result = float(rounded_qty)

        self.logger.info(
            f"Расчет позиции: margin={margin:.2f} USDT, volume={volume:.2f} USDT, "
            f"qty={qty:.4f} -> rounded={result}"
        )

        return result

    def split_tp_orders(
            self,
            total_qty: float,
            tp_prices: List[float],
            min_qty_str: str
    ) -> List[Dict[str, float]]:
        """
        Распределение объема по TP ордерам

        Args:
            total_qty: Общий объем позиции
            tp_prices: Список цен TP
            min_qty_str: Минимальный размер ордера

        Returns:
            Список [{"price": ..., "qty": ...}, ...]
        """
        num_tps = len(tp_prices)
        min_qty = Decimal(min_qty_str)

        qty_per_tp = Decimal(str(total_qty)) / Decimal(str(num_tps))
        rounded_qty_per_tp = qty_per_tp.quantize(min_qty, rounding=ROUND_DOWN)

        orders = []
        total_allocated = Decimal('0')

        for i, price in enumerate(tp_prices):
            if i == 0:
                first_qty = Decimal(str(total_qty)) - (rounded_qty_per_tp * Decimal(str(num_tps - 1)))
                qty = float(first_qty)
            else:
                qty = float(rounded_qty_per_tp)

            orders.append({"price": price, "qty": qty})
            total_allocated += Decimal(str(qty))

        self.logger.info(
            f"Распределение TP: total={total_qty}, per_tp={float(rounded_qty_per_tp)}, "
            f"first_tp={orders[0]['qty']}, allocated={float(total_allocated)}"
        )

        return orders

    async def open_position_with_signal(self, signal: Signal) -> None:
        """
        Открытие позиции по сигналу

        Args:
            signal: Торговый сигнал
        """
        try:
            self.logger.info(f"Обработка сигнала: {signal}")

            await self.bybit_client.enable_hedge_mode()

            symbol = signal.asset.replace('/', '')

            await self.bybit_client.set_leverage(symbol, signal.leverage)

            min_qty_str = await self.bybit_client.get_min_order_qty(symbol)

            position_size = self.calculate_position_size(
                signal.entry,
                signal.leverage,
                min_qty_str
            )

            if signal.direction == 'Long':
                side = 'Buy'
                position_idx = 1
                tp_side = 'Sell'
            else:
                side = 'Sell'
                position_idx = 2
                tp_side = 'Buy'

            await self.bybit_client.place_market_order(
                symbol=symbol,
                side=side,
                qty=position_size,
                sl_price=signal.stop_loss,
                position_idx=position_idx
            )

            tp_orders = self.split_tp_orders(
                position_size,
                signal.take_profits,
                min_qty_str
            )

            tp_order_ids = await self.bybit_client.place_reduce_limit_orders(
                symbol=symbol,
                side=tp_side,
                orders=tp_orders,
                position_idx=position_idx
            )

            self.logger.info(f"Выставлено {len(tp_order_ids)} TP ордеров")
            self.logger.info(f"Сигнал успешно обработан: {signal.asset} {signal.direction}")

        except Exception as e:
            self.logger.error(f"Ошибка обработки сигнала: {e}", exc_info=True)