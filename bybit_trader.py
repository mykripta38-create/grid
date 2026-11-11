"""Модуль для исполнения ордеров на Demo-счете Bybit."""
import ccxt.async_support as ccxt
import logging
import config

class BybitTrader:
    def __init__(self):
        self.exchange = ccxt.bybit({
            'apiKey': config.BYBIT_API_KEY,
            'secret': config.BYBIT_API_SECRET,
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'}
        })
        self.exchange.enableDemoTrading(True)
        logging.info("Bybit Trader инициализирован (Сеточный режим).")

    async def get_balance(self) -> float:
        try:
            balance = await self.exchange.fetch_balance({'type': 'swap'})
            return float(balance['free'].get('USDT', 0.0))
        except Exception as e:
            logging.error(f"❌ Ошибка получения баланса: {e}")
            return 0.0

    async def place_limit_order(self, symbol: str, side: str, amount: float, price: float):
        """Ставит лимитный ордер (buy/sell) с округлением цены."""
        trade_symbol = f"{symbol}:USDT" if ":" not in symbol else symbol
        try:
            # Округляем цену до шага биржи (критично для GALA и других дешевых монет)
            price = float(self.exchange.price_to_precision(trade_symbol, price))
            amount = float(self.exchange.amount_to_precision(trade_symbol, amount))

            order = await self.exchange.create_order(
                symbol=trade_symbol,
                type='limit',
                side=side,
                amount=amount,
                price=price,
                params={'positionIdx': 0}
            )
            logging.info(f"✅ Лимит {side} {symbol} {amount:.4f} @ {price}")
            return order
        except Exception as e:
            logging.error(f"❌ Ошибка лимитки для {symbol}: {e}")
            return None

    async def cancel_order(self, symbol: str, order_id: str):
        """Отменяет ордер по ID."""
        trade_symbol = f"{symbol}:USDT" if ":" not in symbol else symbol
        try:
            await self.exchange.cancel_order(order_id, trade_symbol)
            logging.info(f"🧹 Отменен ордер {order_id} для {symbol}")
        except Exception as e:
            logging.warning(f"⚠️ Не удалось отменить ордер {order_id}: {e}")

    async def close(self):
        await self.exchange.close()
