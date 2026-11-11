"""Точка входа: python main.py (Сеточный бот)"""
import asyncio
import logging
import config
from bybit_trader import BybitTrader
from grid_engine import GridBot
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

async def monitor_grids(bot: Bot, trader: BybitTrader, grids: dict):
    """Следит за исполнением ордеров и ставит новые."""
    while True:
        try:
            for symbol, grid in grids.items():
                trade_symbol = f"{symbol}:USDT" if ":" not in symbol else symbol
                
                # 1. Получаем текущую цену напрямую с Bybit
                ticker = await trader.exchange.fetch_ticker(trade_symbol)
                current_price = ticker['last']
                
                # 2. Проверяем, не вышли ли за пределы сетки
                lower_bound = grid.levels[0] * (1 - config.STOP_LOSS_PCT)
                upper_bound = grid.levels[-1] * (1 + config.STOP_LOSS_PCT)
                
                if current_price < lower_bound or current_price > upper_bound:
                    await bot.send_message(
                        config.CHAT_ID, 
                        f"⚠️ <b>{symbol}</b>: Цена вышла за пределы сетки ({current_price:.4f})! Требуется перестройка."
                    )
                    continue
                
                # 3. Проверяем открытые ордера
                open_orders = await trader.exchange.fetch_open_orders(trade_symbol)
                
                # 4. Проверяем историю закрытых ордеров (на предмет исполнения)
                # Берем последние 20 закрытых ордеров, чтобы понять, что сработало
                closed_orders = await trader.exchange.fetch_closed_orders(trade_symbol, limit=20)
                
                for order in closed_orders:
                    # Если ордер уже обработан нашим ботом, пропускаем
                    if order['id'] in grid.processed_orders:
                        continue
                    
                    if order['status'] == 'closed':
                        # Если это была покупка — ставим продажу на уровень выше
                        if order['side'] == 'buy':
                            sell_level = grid.on_buy_filled(order['price'])
                            if sell_level:
                                amount = order['amount']
                                await trader.place_limit_order(symbol, 'sell', amount, sell_level)
                                await bot.send_message(
                                    config.CHAT_ID, 
                                    f"✅ {symbol}: Куплено на {order['price']:.4f} → Продажа на {sell_level:.4f}"
                                )
                        
                        # Если это была продажа — ставим покупку на уровень ниже
                        elif order['side'] == 'sell':
                            buy_level = grid.on_sell_filled(order['price'])
                            if buy_level:
                                amount = order['amount']
                                await trader.place_limit_order(symbol, 'buy', amount, buy_level)
                                await bot.send_message(
                                    config.CHAT_ID, 
                                    f"✅ {symbol}: Продано на {order['price']:.4f} → Покупка на {buy_level:.4f}"
                                )
                        
                        # Помечаем ордер как обработанный
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
                    f"🟢 <b>{symbol}</b>: Сетка создана. Диапазон: {grid.levels[0]:.4f} - {grid.levels[-1]:.4f}"
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
