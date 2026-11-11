"""Точка входа: python main.py (Сеточный бот)"""
import asyncio
import logging
import time
import config
from bybit_trader import BybitTrader
from grid_engine import GridBot
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

async def monitor_grids(bot: Bot, trader: BybitTrader, grids: dict):
    """Следит за исполнением ордеров и ставит новые."""
    start_time = int(time.time() * 1000)  # Время старта бота
    
    while True:
        try:
            for symbol, grid in grids.items():
                trade_symbol = f"{symbol}:USDT" if ":" not in symbol else symbol
                
                # 1. Получаем текущую цену
                ticker = await trader.exchange.fetch_ticker(trade_symbol)
                current_price = ticker['last']
                
                # 2. Проверяем границы
                lower_bound = grid.levels[0] * (1 - config.STOP_LOSS_PCT)
                upper_bound = grid.levels[-1] * (1 + config.STOP_LOSS_PCT)
                
                if current_price < lower_bound or current_price > upper_bound:
                    await bot.send_message(config.CHAT_ID, f"⚠️ <b>{symbol}</b>: Цена вышла за пределы сетки! ({current_price:.6f})")
                    continue
                
                # 3. Берем закрытые ордера ТОЛЬКО после старта бота
                try:
                    closed_orders = await trader.exchange.fetch_closed_orders(trade_symbol, limit=50, since=start_time)
                except Exception as e:
                    logging.error(f"Ошибка получения закрытых ордеров для {symbol}: {e}")
                    continue
                
                for order in closed_orders:
                    if order['id'] in grid.processed_orders:
                        continue
                    
                    if order['status'] == 'closed':
                        if order['side'] == 'buy':
                            sell_level = grid.on_buy_filled(order['price'])
                            if sell_level:
                                amount = order['amount']
                                await trader.place_limit_order(symbol, 'sell', amount, sell_level)
                                await bot.send_message(config.CHAT_ID, f"✅ {symbol}: Куплено на {order['price']:.6f} → Продажа на {sell_level:.6f}")
                        
                        elif order['side'] == 'sell':
                            buy_level = grid.on_sell_filled(order['price'])
                            if buy_level:
                                amount = order['amount']
                                await trader.place_limit_order(symbol, 'buy', amount, buy_level)
                                await bot.send_message(config.CHAT_ID, f"✅ {symbol}: Продано на {order['price']:.6f} → Покупка на {buy_level:.6f}")
                        
                        grid.processed_orders.add(order['id'])
                            
        except Exception as e:
            logging.error(f"Ошибка в мониторинге сетки: {e}")
        
        await asyncio.sleep(config.CHECK_INTERVAL)

async def main():
    logging.info("🚀 Запуск сеточного бота...")
    
    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    trader = BybitTrader()
    
    grids = {}
    
    try:
        # 1. Инициализация сеток для всех пар
        for symbol in config.SYMBOLS:
            try:
                trade_symbol = f"{symbol}:USDT" if ":" not in symbol else symbol
                ticker = await trader.exchange.fetch_ticker(trade_symbol)
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
                    
                await bot.send_message(
                    config.CHAT_ID, 
                    f"🟢 <b>{symbol}</b>: Сетка создана. Диапазон: {grid.levels[0]:.6f} - {grid.levels[-1]:.6f}"
                )
                
            except Exception as e:
                logging.error(f"Ошибка инициализации {symbol}: {e}")
        
        # 3. Запускаем мониторинг
        await bot.send_message(config.CHAT_ID, "🚀 <b>Сеточный бот запущен!</b> Начинаю мониторинг.")
        await monitor_grids(bot, trader, grids)
        
    finally:
        await trader.close()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
