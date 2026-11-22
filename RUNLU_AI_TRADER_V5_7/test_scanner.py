import unittest
from datetime import datetime, timezone
from scanner import Bar, scan, scan_universe
from trader import PaperTrader

NOW = datetime(2026, 11, 3, 20, 0, tzinfo=timezone.utc)

def trending():
    return [Bar(80 + i * 0.65, 200_000 if i < 29 else 340_000) for i in range(30)]

class ScannerTests(unittest.TestCase):
    def test_trending_candidate(self):
        result = scan('DEMO', trending(), NOW)
        self.assertEqual(result.status, 'CANDIDATE')
        self.assertEqual(result.score, 100)
        self.assertIsNotNone(result.signal)
    def test_trading_pipeline(self):
        result = scan('DEMO', trending(), NOW)
        trader = PaperTrader()
        self.assertEqual(trader.buy(result.signal, {'DEMO': result.signal.price}, NOW), 'FILLED')
    def test_short_history(self):
        self.assertIn('INSUFFICIENT_HISTORY', scan('X', trending()[:20], NOW).reasons)
    def test_bad_price(self):
        bars = trending(); bars[-1] = Bar(float('nan'), 200000)
        self.assertIn('INVALID_BAR', scan('X', bars, NOW).reasons)
    def test_low_liquidity(self):
        bars = [Bar(b.close, 100) for b in trending()]
        self.assertIn('LOW_LIQUIDITY', scan('X', bars, NOW).reasons)
    def test_low_price(self):
        bars = [Bar(b.close / 100, b.volume) for b in trending()]
        self.assertIn('PRICE_TOO_LOW', scan('X', bars, NOW).reasons)
    def test_extreme_jump(self):
        bars = trending(); bars[-1] = Bar(180, 340000)
        self.assertIn('EXTREME_DAILY_MOVE', scan('X', bars, NOW).reasons)
    def test_flat_watch(self):
        bars = [Bar(100, 200000) for _ in range(30)]
        self.assertEqual(scan('X', bars, NOW).status, 'WATCH')
    def test_invalid_symbol(self):
        self.assertIn('INVALID_SYMBOL', scan('A/B', trending(), NOW).reasons)
    def test_naive_timestamp(self):
        self.assertIn('NAIVE_TIMESTAMP', scan('X', trending(), datetime(2026,11,3)).reasons)
    def test_universe_order(self):
        results = scan_universe({'Z': trending(), 'A': [Bar(100, 200000)]*30}, NOW)
        self.assertEqual([r.symbol for r in results], ['Z', 'A'])
    def test_negative_volume(self):
        bars = trending(); bars[2] = Bar(90, -1)
        self.assertIn('INVALID_BAR', scan('X', bars, NOW).reasons)

if __name__ == '__main__': unittest.main()
