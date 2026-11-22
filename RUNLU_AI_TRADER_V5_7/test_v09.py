import unittest
from datetime import date
from decimal import Decimal
from corporate_actions import Split, Dividend, FxRate, convert, apply_split, cash_dividend, validate_ledger

D = date(2025, 1, 2)

class TestActions(unittest.TestCase):
    def test_split(self):
        self.assertEqual(apply_split('3', Split(D, 'CSU', 3, 1)), Decimal('9'))
    def test_reverse_split_fraction(self):
        self.assertEqual(apply_split('3', Split(D, 'CSU', 1, 2)), Decimal('1.5'))
    def test_invalid_split(self):
        with self.assertRaises(ValueError): Split(D, 'CSU', 0, 1)
    def test_dividend(self):
        d = Dividend(D, date(2025, 1, 10), 'VFV', Decimal('0.25'), 'CAD')
        self.assertEqual(cash_dividend('12', d), Decimal('3.00'))
    def test_invalid_dividend_date(self):
        with self.assertRaises(ValueError): Dividend(D, date(2025, 1, 1), 'VFV', '0.2', 'CAD')
    def test_fx_forward(self):
        r = FxRate(D, 'USD', 'CAD', '1.4')
        self.assertEqual(convert('100', 'USD', 'CAD', r), Decimal('140.0'))
    def test_fx_reverse(self):
        r = FxRate(D, 'USD', 'CAD', '1.25')
        self.assertEqual(convert('125', 'CAD', 'USD', r), Decimal('100'))
    def test_invalid_fx(self):
        with self.assertRaises(ValueError): FxRate(D, 'USD', 'CAD', 'NaN')
    def test_ledger_duplicate(self):
        s = Split(D, 'CSU', 2, 1)
        with self.assertRaises(ValueError): validate_ledger([s, s], 'CSU')
    def test_ledger_symbol(self):
        with self.assertRaises(ValueError): validate_ledger([Split(D, 'CSU', 2, 1)], 'VFV')
    def test_ledger_sorted(self):
        a = Split(D, 'CSU', 2, 1)
        b = Dividend(date(2025, 2, 1), date(2025, 2, 15), 'CSU', '1', 'CAD')
        self.assertEqual(len(validate_ledger([a, b], 'CSU')), 2)
    def test_negative_shares(self):
        with self.assertRaises(ValueError): apply_split('-1', Split(D, 'CSU', 2, 1))

if __name__ == '__main__': unittest.main()
