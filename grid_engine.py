"""Движок для сеточной торговли с мягким стопом."""
import logging

class GridBot:
    def __init__(self, symbol: str, current_price: float):
        self.symbol = symbol
        self.center_price = current_price
        self.levels = []
        self.active_buys = {}      
        self.active_sells = {}     
        self.total_profit = 0.0
        self.processed_orders = set()  
        self.is_paused = False  # Флаг: цена ушла ниже сетки (пауза на покупки)

    def calculate_levels(self, range_pct: float, num_levels: int):
        lower = self.center_price * (1 - range_pct / 2)
        upper = self.center_price * (1 + range_pct / 2)
        step = (upper - lower) / num_levels
        
        self.levels = [lower + i * step for i in range(num_levels + 1)]
        self.is_paused = False
        logging.info(f"Сетка для {self.symbol} от {lower:.6f} до {upper:.6f}, шаг: {step:.6f}")
        return self.levels

    def get_buy_levels(self):
        """Возвращает уровни ниже текущей цены (для покупки)."""
        return [lvl for lvl in self.levels if lvl < self.center_price]

    def get_sell_levels(self):
        """Возвращает уровни выше текущей цены (для продажи)."""
        return [lvl for lvl in self.levels if lvl > self.center_price]

    def on_buy_filled(self, level: float):
        logging.info(f"🟢 {self.symbol}: Куплено на уровне {level:.6f}")
        sell_level = next((lvl for lvl in self.levels if lvl > level), None)
        return sell_level

    def on_sell_filled(self, level: float):
        logging.info(f"🔴 {self.symbol}: Продано на уровне {level:.6f}")
        buy_level = next((lvl for lvl in reversed(self.levels) if lvl < level), None)
        return buy_level
