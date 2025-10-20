# trading/position_manager.py
from typing import List, Dict
from decimal import Decimal, ROUND_DOWN
from signals.models import Signal
from trading.xt_client import XTClient
from trading.config import TradingConfig
from utils.logger import get_logger


class PositionManager:
    """Управление торговыми позициями на XT"""

    def __init__(self, xt_client: XTClient, config: TradingConfig):
        self.logger = get_logger(__name__)
        self.xt_client = xt_client
        self.config = config

    def calculate_position_size(
            self,
            entry_price: float,
            leverage: int,
            contract_size: float
    ) -> int:
        """
        Расчет размера позиции

        Args:
            entry_price: Цена входа
            leverage: Кредитное плечо
            contract_size: Размер контракта (минимальный increment)

        Returns:
            Размер позиции в контрактах (целое число)
        """
        margin = self.config.balance * (self.config.amount / 100)
        volume = margin * leverage
        qty_decimal = volume / entry_price

        contract_size_decimal = Decimal(str(contract_size))
        qty_decimal_obj = Decimal(str(qty_decimal))
        rounded_qty = qty_decimal_obj.quantize(contract_size_decimal, rounding=ROUND_DOWN)

        result = int(rounded_qty)

        self.logger.info(
            f"Расчет позиции: margin={margin:.2f} USDT, volume={volume:.2f} USDT, "
            f"qty={qty_decimal:.4f} -> rounded={result} (contract_size={contract_size})"
        )

        return result

    def split_tp_orders(
            self,
            total_qty: int,
            tp_prices: List[float],
            contract_size: float
    ) -> List[Dict[str, float]]:
        """
        Распределение объема по TP ордерам

        Args:
            total_qty: Общий объем позиции (целое число контрактов)
            tp_prices: Список цен TP
            contract_size: Размер контракта

        Returns:
            Список [{"price": ..., "qty": ...}, ...]
        """
        num_tps = len(tp_prices)
        contract_size_decimal = Decimal(str(contract_size))

        qty_per_tp_decimal = Decimal(str(total_qty)) / Decimal(str(num_tps))
        rounded_qty_per_tp = qty_per_tp_decimal.quantize(contract_size_decimal, rounding=ROUND_DOWN)

        orders = []
        total_allocated = Decimal('0')

        for i, price in enumerate(tp_prices):
            if i == 0:
                first_qty = Decimal(str(total_qty)) - (rounded_qty_per_tp * Decimal(str(num_tps - 1)))
                qty = int(first_qty)
            else:
                qty = int(rounded_qty_per_tp)

            orders.append({"price": price, "qty": qty})
            total_allocated += Decimal(str(qty))

        self.logger.info(
            f"Распределение TP: total={total_qty}, per_tp={int(rounded_qty_per_tp)}, "
            f"first_tp={orders[0]['qty']}, allocated={int(total_allocated)}"
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

            symbol = signal.asset.replace('/', '')

            await self.xt_client.set_leverage(symbol, signal.leverage)

            contract_size = await self.xt_client.get_contract_size(symbol)

            position_size = self.calculate_position_size(
                signal.entry,
                signal.leverage,
                contract_size
            )

            if signal.direction == 'Long':
                side = 'BUY'
                position_side = 'LONG'
            else:
                side = 'SELL'
                position_side = 'SHORT'

            await self.xt_client.place_market_order(
                symbol=symbol,
                side=side,
                qty=position_size,
                sl_price=signal.stop_loss,
                position_side=position_side
            )

            tp_orders = self.split_tp_orders(
                position_size,
                signal.take_profits,
                contract_size
            )

            tp_order_ids = await self.xt_client.place_reduce_limit_orders(
                symbol=symbol,
                orders=tp_orders,
                position_side=position_side
            )

            self.logger.info(f"Выставлено {len(tp_order_ids)} TP ордеров")
            self.logger.info(f"Сигнал успешно обработан: {signal.asset} {signal.direction}")

        except Exception as e:
            self.logger.error(f"Ошибка обработки сигнала: {e}", exc_info=True)