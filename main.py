"""Точка входа: python main.py (Сеточный бот с мягким стопом)"""
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
    start_time = int(time.time() * 1000)
    
    while True:
        try:
            for symbol, grid in grids.items():
                trade_symbol = f"{symbol}:USDT" if ":" not in symbol else symbol
                
                # 1. Получаем текущую цену
                ticker = await trader.exchange.fetch_ticker(trade_symbol)
                current_price = ticker['last']
                
                # 2. ЛОГИКА МЯГКОГО СТОПА
                soft_sl_trigger = grid.levels[0] * (1 - config.SOFT_STOP_PCT)
                
                # Если цена упала НИЖЕ нижней границы, но НЕ ДОШЛА до мягкого стопа — ставим на паузу
                if current_price < grid.levels[0] and current_price > soft_sl_trigger:
                    if not grid.is_paused:
                        grid.is_paused = True
                        await bot.send_message(
                            config.CHAT_ID, 
                            f"⚠️ <b>{symbol}</b>: Цена ниже сетки ({current_price:.6f}). Пауза на покупки."
                        )
                elif current_price >= grid.levels[0]:
                    if grid.is_paused:
                        grid.is_paused = False
                        await bot.send_message(
                            config.CHAT_ID, 
                            f"✅ <b>{symbol}</b>: Цена вернулась в сетку. Возобновляем работу."
                        )
                
                # 3. АВАРИЙНАЯ ПЕРЕСТРОЙКА (если упали ниже мягкого стопа)
                if current_price < soft_sl_trigger:
                    await bot.send_message(
                        config.CHAT_ID, 
                        f"🚨 <b>{symbol}</b>: КРИТИЧЕСКОЕ ПАДЕНИЕ! Цена ушла за мягкий стоп ({current_price:.6f}). Перестройка сетки."
                    )
                    # Отменяем все открытые ордера
                    try:
                        open_orders = await trader.exchange.fetch_open_orders(trade_symbol)
                        for o in open_orders:
                            try: await trader.exchange.cancel_order(o['id'], trade_symbol)
                            except: pass
                    except: pass
                    
                    # Перестраиваем сетку
                    grid.center_price = current_price
                    grid.calculate_levels(config.GRID_RANGE_PCT, config.GRID_LEVELS)
                    
                    # Ставим новые ордера
                    for level in grid.get_buy_levels():
                        amount = config.POSITION_SIZE_USDT / level
                        await trader.place_limit_order(symbol, 'buy', amount, level)
                    for level in grid.get_sell_levels():
                        amount = config.POSITION_SIZE_USDT / level
                        await trader.place_limit_order(symbol, 'sell', amount, level)
                    
                    continue
                
                # 4. ОБЫЧНАЯ РАБОТА СЕТКИ
                try:
                    closed_orders = await trader.exchange.fetch_closed_orders(trade_symbol, limit=50, since=start_time)
                except Exception as e:
                    logging.error(f"Ошибка получения закрытых ордеров: {e}")
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
                            if buy_level and not grid.is_paused:  # Не покупаем, если на паузе
                                amount = order['amount']
                                await trader.place_limit_order(symbol, 'buy', amount, buy_level)
                                await bot.send_message(config.CHAT_ID, f"✅ {symbol}: Продано на {order['price']:.6f} → Покупка на {buy_level:.6f}")
                        
                        grid.processed_orders.add(order['id'])
                            
        except Exception as e:
            logging.error(f"Ошибка в мониторинге сетки: {e}")
        
        await asyncio.sleep(config.CHECK_INTERVAL)

async def main():
    logging.info("🚀 Запуск сеточного бота (с мягким стопом)...")
    
    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    trader = BybitTrader()
    
    grids = {}
    
    try:
        for symbol in config.SYMBOLS:
            try:
                trade_symbol = f"{symbol}:USDT" if ":" not in symbol else symbol
                ticker = await trader.exchange.fetch_ticker(trade_symbol)
                current_price = ticker['last']
                
                grid = GridBot(symbol, current_price)
                grid.calculate_levels(config.GRID_RANGE_PCT, config.GRID_LEVELS)
                grids[symbol] = grid
                
                for level in grid.get_buy_levels():
                    amount = config.POSITION_SIZE_USDT / level
                    await trader.place_limit_order(symbol, 'buy', amount, level)
                    
                for level in grid.get_sell_levels():
                    amount = config.POSITION_SIZE_USDT / level
                    await trader.place_limit_order(symbol, 'sell', amount, level)
                    
                await bot.send_message(
                    config.CHAT_ID, 
                    f"🟢 <b>{symbol}</b>: Сетка создана. Диапазон: {grid.levels[0]:.6f} - {grid.levels[-1]:.6f}"
                )
                
            except Exception as e:
                logging.error(f"Ошибка инициализации {symbol}: {e}")
        
        await bot.send_message(config.CHAT_ID, "🚀 <b>Сеточный бот запущен (с мягким стопом)!</b>")
        await monitor_grids(bot, trader, grids)
        
    finally:
        await trader.close()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
