import json
import tempfile
import unittest
from pathlib import Path

from alerts import Alert, InputError, Price, find_alerts, read_prices, read_rules
from datetime import date


class PriceAlertTests(unittest.TestCase):
    def p(self, day, instrument, close):
        return Price(date.fromisoformat(day), instrument, close)

    def test_level_below_crosses_once_and_dates_are_sorted(self):
        prices = [self.p('2026-09-03', 'INFY', 1498), self.p('2026-09-01', 'INFY', 1520.5), self.p('2026-09-02', 'INFY', 1490), self.p('2026-09-04', 'INFY', 1480)]
        rules = [{'id':'r1','instrument':'INFY','type':'level','direction':'below','level':1500}]
        alerts = find_alerts(prices, rules)
        self.assertEqual([a.day.isoformat() for a in alerts], ['2026-09-02'])

    def test_level_above_crosses_only_from_other_side(self):
        prices = [self.p('2026-01-01','TCS',99), self.p('2026-01-02','TCS',100), self.p('2026-01-03','TCS',101), self.p('2026-01-04','TCS',102)]
        rule = [{'id':'a','instrument':'TCS','type':'level','direction':'above','level':100}]
        self.assertEqual([a.day.isoformat() for a in find_alerts(prices, rule)], ['2026-01-03'])

    def test_no_alert_when_already_below_level(self):
        prices = [self.p('2026-01-01','INFY',10), self.p('2026-01-02','INFY',9)]
        rules = [{'id':'r','instrument':'INFY','type':'level','direction':'below','level':20}]
        self.assertEqual(find_alerts(prices, rules), [])

    def test_ma_cross_needs_full_windows_and_detects_cross_above(self):
        closes = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 2, 3]
        prices = [self.p(f'2026-01-{i:02d}', 'X', close) for i, close in enumerate(closes, 1)]
        rule = [{'id':'ma','instrument':'X','type':'ma_cross','short':2,'long':3,'direction':'above'}]
        alerts = find_alerts(prices, rule)
        self.assertEqual([a.day.isoformat() for a in alerts], ['2026-01-12'])

    def test_alerts_sorted_by_date_then_rule_id(self):
        prices = [self.p('2026-01-01','X',12), self.p('2026-01-02','X',8)]
        rules = [
            {'id':'z','instrument':'X','type':'level','direction':'below','level':10},
            {'id':'a','instrument':'X','type':'level','direction':'below','level':11},
        ]
        self.assertEqual([a.rule_id for a in find_alerts(prices, rules)], ['a','z'])

    def test_unknown_instrument_produces_no_alert(self):
        rules = [{'id':'r','instrument':'MISSING','type':'level','direction':'below','level':1}]
        self.assertEqual(find_alerts([], rules), [])

    def test_csv_rejects_duplicate_instrument_day(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'prices.csv'
            path.write_text('date,instrument,close\n2026-01-01,X,10\n2026-01-01,X,11\n', encoding='utf-8')
            with self.assertRaisesRegex(InputError, 'duplicate price'):
                read_prices(path)

    def test_csv_rejects_bad_date_and_nan(self):
        for row in ['not-a-date,X,10', '2026-01-01,X,nan']:
            with self.subTest(row=row), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'prices.csv'
                path.write_text('date,instrument,close\n' + row + '\n', encoding='utf-8')
                with self.assertRaises(InputError):
                    read_prices(path)

    def test_rules_reject_short_window_not_less_than_long(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'rules.json'
            path.write_text(json.dumps([{'id':'r','instrument':'X','type':'ma_cross','short':5,'long':5,'direction':'above'}]), encoding='utf-8')
            with self.assertRaisesRegex(InputError, 'short must be smaller'):
                read_rules(path)

    def test_rules_reject_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'rules.json'
            rule = {'id':'same','instrument':'X','type':'level','direction':'below','level':1}
            path.write_text(json.dumps([rule, rule]), encoding='utf-8')
            with self.assertRaisesRegex(InputError, 'duplicate rule id'):
                read_rules(path)


if __name__ == '__main__':
    unittest.main()
