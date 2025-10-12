# signals/models.py
from dataclasses import dataclass
from typing import List


@dataclass
class Signal:
    """Модель торгового сигнала"""

    asset: str
    direction: str
    leverage: int
    entry: float
    take_profits: List[float]
    stop_loss: float

    def __str__(self) -> str:
        tps = ", ".join([f"{tp:.4f}" for tp in self.take_profits])
        return (
            f"Signal({self.asset} {self.direction} {self.leverage}x | "
            f"TPs: [{tps}] | SL: {self.stop_loss:.4f})"
        )