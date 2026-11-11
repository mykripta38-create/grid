"""Движок для сеточной торговли."""
import logging

class GridBot:
    def __init__(self, symbol: str, current_price: float):
        self.symbol = symbol
        self.center_price = current_price
        self.levels = []
        self.active_buys = {}   # Уровень: Order ID
        self.active_sells = {}  # Уровень: Order ID
        self.total_profit = 0.0
        
    def calculate_levels(self, range_pct: float, num_levels: int):
        """Рассчитывает цены для уровней сетки."""
        lower = self.center_price * (1 - range_pct / 2)
        upper = self.center_price * (1 + range_pct / 2)
        step = (upper - lower) / num_levels
        
        self.levels = [lower + i * step for i in range(num_levels + 1)]
        logging.info(f"Сетка для {self.symbol} от {lower:.4f} до {upper:.4f}, шаг: {step:.4f}")
        return self.levels

    def get_buy_levels(self):
        """Возвращает уровни ниже текущей цены (для покупки)."""
        return [lvl for lvl in self.levels if lvl < self.center_price]

    def get_sell_levels(self):
        """Возвращает уровни выше текущей цены (для продажи)."""
        return [lvl for lvl in self.levels if lvl > self.center_price]

    def on_buy_filled(self, level: float):
        """Вызывается, когда лимитка на покупку исполнена."""
        logging.info(f"🟢 {self.symbol}: Куплено на уровне {level:.4f}")
        # Находим следующий уровень вверх для продажи
        sell_level = next((lvl for lvl in self.levels if lvl > level), None)
        if sell_level:
            return sell_level
        return None

    def on_sell_filled(self, level: float):
        """Вызывается, когда лимитка на продажу исполнена."""
        logging.info(f"🔴 {self.symbol}: Продано на уровне {level:.4f}")
        # Находим следующий уровень вниз для покупки
        buy_level = next((lvl for lvl in reversed(self.levels) if lvl < level), None)
        if buy_level:
            return buy_level
        return None