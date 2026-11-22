from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from math import isfinite, floor
import json

@dataclass(frozen=True)
class Config:
    initial_cash: float = 2000.0
    max_position_fraction: float = .10
    max_daily_loss_fraction: float = .02
    max_total_drawdown_fraction: float = .08
    min_score: int = 75
    fee_per_order: float = 1.0
    slippage_fraction: float = .001
    max_signal_age_minutes: int = 15

@dataclass(frozen=True)
class Signal:
    symbol: str
    score: int
    price: float
    timestamp: str
    reason: str

class PaperTrader:
    """Educational simulation only. No broker connections or real orders."""
    def __init__(self, config=Config()):
        self.config = config
        self.cash = config.initial_cash
        self.positions = {}  # symbol -> {qty, cost_basis}
        self.day_start_equity = config.initial_cash
        self.peak_equity = config.initial_cash
        self.last_day = None
        self.halted = False
        self.log = []

    def _prices(self, prices):
        if not isinstance(prices, dict): raise ValueError('Market prices must be a dictionary')
        for symbol in self.positions:
            if symbol not in prices: raise ValueError(f'Missing current price for {symbol}')
        for symbol, price in prices.items():
            if not isinstance(price, (int, float)) or not isfinite(price) or price <= 0:
                raise ValueError(f'Invalid price for {symbol}')

    def equity(self, prices):
        self._prices(prices)
        return self.cash + sum(p['qty'] * prices[s] for s,p in self.positions.items())

    def mark_to_market(self, prices, now=None):
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None: raise ValueError('Timezone required')
        value = self.equity(prices)
        day = now.astimezone(timezone.utc).date()
        if self.last_day != day:
            self.day_start_equity = value
            self.last_day = day
        self.peak_equity = max(self.peak_equity, value)
        return value

    def _risk(self, equity):
        if self.halted: return 'HALTED'
        if equity <= self.day_start_equity * (1-self.config.max_daily_loss_fraction): return 'DAILY_LOSS_LIMIT'
        if equity <= self.peak_equity * (1-self.config.max_total_drawdown_fraction): return 'DRAWDOWN_LIMIT'
        return 'APPROVED'

    def _signal_valid(self, signal, now):
        if not signal.symbol or not signal.symbol.isascii() or not signal.symbol.replace('.', '').replace('-', '').isalnum(): return False
        if not isinstance(signal.score, int) or not 0 <= signal.score <= 100: return False
        if not isinstance(signal.price, (int,float)) or not isfinite(signal.price) or signal.price <= 0: return False
        try:
            ts = datetime.fromisoformat(signal.timestamp.replace('Z','+00:00'))
            if ts.tzinfo is None: return False
            age = now - ts.astimezone(timezone.utc)
            return timedelta(0) <= age <= timedelta(minutes=self.config.max_signal_age_minutes)
        except (ValueError, TypeError): return False

    def _record(self, action, symbol, verdict, **details):
        entry = {'time': datetime.now(timezone.utc).isoformat(), 'action': action, 'symbol': symbol,
                 'decision': verdict, 'mode': 'PAPER_ONLY', **details}
        self.log.append(entry)
        return verdict

    def buy(self, signal, prices, now=None):
        now = now or datetime.now(timezone.utc)
        if not self._signal_valid(signal, now): return self._record('BUY', signal.symbol, 'INVALID_OR_STALE_SIGNAL')
        try:
            equity = self.mark_to_market(prices, now)
        except ValueError:
            return self._record('BUY', signal.symbol, 'INVALID_MARKET_DATA')
        if signal.symbol not in prices or abs(prices[signal.symbol]-signal.price)/signal.price > .02:
            return self._record('BUY', signal.symbol, 'PRICE_MISMATCH')
        verdict = self._risk(equity)
        if verdict != 'APPROVED': return self._record('BUY', signal.symbol, verdict)
        if signal.score < self.config.min_score: return self._record('BUY', signal.symbol, 'SCORE_TOO_LOW')
        if signal.symbol in self.positions: return self._record('BUY', signal.symbol, 'ALREADY_HELD')
        fill = prices[signal.symbol]*(1+self.config.slippage_fraction)
        budget = min(self.cash, equity*self.config.max_position_fraction)
        qty = floor((budget-self.config.fee_per_order)/fill)
        if qty < 1: return self._record('BUY', signal.symbol, 'POSITION_LIMIT')
        cost = qty*fill + self.config.fee_per_order
        self.cash -= cost
        self.positions[signal.symbol] = {'qty': qty, 'cost_basis': cost}
        return self._record('BUY', signal.symbol, 'FILLED', qty=qty, fill_price=fill, fee=self.config.fee_per_order)

    def sell(self, symbol, prices, now=None):
        now = now or datetime.now(timezone.utc)
        try: equity = self.mark_to_market(prices, now)
        except ValueError: return self._record('SELL', symbol, 'INVALID_MARKET_DATA')
        if symbol not in self.positions: return self._record('SELL', symbol, 'NOT_HELD')
        if self.halted: return self._record('SELL', symbol, 'HALTED')
        p = self.positions.pop(symbol)
        fill = prices[symbol]*(1-self.config.slippage_fraction)
        proceeds = p['qty']*fill-self.config.fee_per_order
        self.cash += proceeds
        return self._record('SELL', symbol, 'FILLED', qty=p['qty'], fill_price=fill,
                            fee=self.config.fee_per_order, realized_pnl=proceeds-p['cost_basis'])

    def stop(self): self.halted = True

    def export_log(self): return json.dumps(self.log, indent=2)

if __name__ == '__main__':
    p = PaperTrader()
    now = datetime.now(timezone.utc)
    s = Signal('DEMO', 82, 100., now.isoformat(), 'Synthetic example')
    print(p.buy(s, {'DEMO': 100.}, now))
    print(p.sell('DEMO', {'DEMO': 102.}, now))
    print(p.export_log())
