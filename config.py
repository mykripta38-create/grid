"""Конфигурация сеточного бота."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Переменная {name} не задана в окружении")
    return value

BOT_TOKEN: str = _require("BOT_TOKEN")
CHAT_ID: int = int(_require("CHAT_ID"))

BYBIT_API_KEY: str = os.getenv("BYBIT_API_KEY", "").strip()
BYBIT_API_SECRET: str = os.getenv("BYBIT_API_SECRET", "").strip()

# Пары для сетки (лучше брать волатильные, где есть движение)
SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT", "GALA/USDT", "SUI/USDT"
]

# Настройки сетки
GRID_RANGE_PCT = 0.10      # Общий диапазон сетки (10% = от -5% до +5% от текущей цены)
GRID_LEVELS = 10           # Количество уровней (шагов) в сетке
POSITION_SIZE_USDT = 100   # Размер одной позиции (в USDT) на один уровень
STOP_LOSS_PCT = 0.15       # Если цена уходит за границу сетки на 15% — закрываем всё

# Таймфрейм для проверки (сетка работает всегда, но проверяем раз в минуту)
CHECK_INTERVAL = 60 