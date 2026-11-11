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

# 7 лучших пар по результатам теста (GALA и DOGE убраны)
SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", 
    "SUI/USDT", "LINK/USDT", "LTC/USDT"
]

# Настройки сетки
GRID_RANGE_PCT = 0.20      # Общий диапазон сетки (20%)
GRID_LEVELS = 10           # Количество уровней (шагов) в сетке
POSITION_SIZE_USDT = 100   # Размер одной позиции (в USDT) на один уровень

# Мягкий стоп (аварийная перестройка)
SOFT_STOP_PCT = 0.20       # Если цена уходит на 20% ниже сетки — перестраиваем

# Интервал проверки (в секундах)
CHECK_INTERVAL = 60 
