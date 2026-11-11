"""Точка входа: python main.py (Сеточный бот)"""
import asyncio
import logging
import config
from binance_data import BinanceData
from bybit_trader import BybitTrader
from grid_engine import GridBot
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

async def monitor_grids(bot: Bot, trader: BybitTrader, data: BinanceData, grids: dict):
    while True:
        try:
            for symbol, grid in grids.items():
                # 1. Получаем текущую цену
                ticker = await data.exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                
                # 2. Проверяем, не вышли ли за пределы сетки
                lower_bound = grid.levels[0] * (1 - config.STOP_LOSS_PCT)
                upper_bound = grid.levels[-1] * (1 + config.STOP_LOSS_PCT)
                
                if current_price < lower_bound or current_price > upper_bound:
                    await bot.send_message(config.CHAT_ID, f"⚠️ {symbol}: Цена вышла за пределы сетки! Требуется перестройка.")
                    # Здесь можно добавить логику перестройки (отмена всех ордеров и создание новых)
                    continue
                
                # 3. Проверяем открытые ордера
                open_orders = await trader.exchange.fetch_open_orders(f"{symbol}:USDT")
                
                # 4. Если ордера на покупку исполнились — ставим на продажу
                for order in open_orders:
                    if order['side'] == 'buy' and order['status'] == 'closed': # Исполнился
                        sell_level = grid.on_buy_filled(order['price'])
                        if sell_level:
                            # Ставим ордер на продажу на следующем уровне
                            await trader.place_limit_order(symbol, 'sell', order['amount'], sell_level)
                            # Уведомляем
                            await bot.send_message(config.CHAT_ID, f"✅ {symbol}: Цикл завершен! Куплено на {order['price']:.4f}, продажа на {sell_level:.4f}")
                            
                    elif order['side'] == 'sell' and order['status'] == 'closed':
                        buy_level = grid.on_sell_filled(order['price'])
                        if buy_level:
                            await trader.place_limit_order(symbol, 'buy', order['amount'], buy_level)
                            await bot.send_message(config.CHAT_ID, f"✅ {symbol}: Цикл завершен! Продано на {order['price']:.4f}, покупка на {buy_level:.4f}")
                            
        except Exception as e:
            logging.error(f"Ошибка в мониторинге сетки: {e}")
        
        await asyncio.sleep(config.CHECK_INTERVAL)

async def main():
    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    trader = BybitTrader()
    data = BinanceData()
    
    grids = {}
    
    # 1. Инициализация сеток для всех пар
    for symbol in config.SYMBOLS:
        try:
            ticker = await data.exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            
            grid = GridBot(symbol, current_price)
            grid.calculate_levels(config.GRID_RANGE_PCT, config.GRID_LEVELS)
            grids[symbol] = grid
            
            # 2. Ставим начальные ордера
            buy_levels = grid.get_buy_levels()
            sell_levels = grid.get_sell_levels()
            
            for level in buy_levels:
                amount = config.POSITION_SIZE_USDT / level
                await trader.place_limit_order(symbol, 'buy', amount, level)
                
            for level in sell_levels:
                amount = config.POSITION_SIZE_USDT / level
                await trader.place_limit_order(symbol, 'sell', amount, level)
                
            await bot.send_message(config.CHAT_ID, f"🟢 {symbol}: Сетка создана. Диапазон: {grid.levels[0]:.4f} - {grid.levels[-1]:.4f}")
            
        except Exception as e:
            logging.error(f"Ошибка инициализации {symbol}: {e}")
    
    # 3. Запускаем мониторинг
    await bot.send_message(config.CHAT_ID, "🚀 Сеточный бот запущен! Начинаю мониторинг.")
    await monitor_grids(bot, trader, data, grids)
    
    await data.close()
    await trader.close()
    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())