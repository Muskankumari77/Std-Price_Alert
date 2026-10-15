import unittest
from app import make_token, verify_token, parse_csv_prices, suggest_rules

class AppFeatureTests(unittest.TestCase):
    def test_jwt_token_verifies(self):
        token=make_token("admin")
        payload=verify_token(token)
        self.assertEqual(payload["sub"], "admin")
        self.assertEqual(payload["role"], "admin")

    def test_jwt_tampering_is_rejected(self):
        token=make_token("admin")
        parts=token.split(".")
        parts[1]=parts[1][:-1] + ("A" if parts[1][-1] != "A" else "B")
        self.assertIsNone(verify_token(".".join(parts)))

    def test_amazon_csv_maps_to_daily_average(self):
        raw="OrderDate,ProductID,UnitPrice\n2023-01-01,P1,10\n2023-01-01,P1,20\n2023-01-02,P1,30\n"
        normalized,meta=parse_csv_prices(raw)
        self.assertIn("2023-01-01,AMZ-P1,15", normalized)
        self.assertEqual(meta["instruments"],1)

    def test_standard_csv_is_preserved(self):
        raw="date,instrument,close\n2026-01-01,X,10\n"
        normalized,meta=parse_csv_prices(raw)
        self.assertEqual(normalized,raw)
        self.assertEqual(meta["rows"],1)


    def test_suggest_rules_uses_instruments_in_uploaded_data(self):
        raw="date,instrument,close\n" + "\n".join(f"2026-01-{i:02d},AMZ-P1,{100+i}" for i in range(1, 22)) + "\n"
        rules=suggest_rules(raw)
        self.assertTrue(any(rule['instrument']=='AMZ-P1' for rule in rules))
        self.assertTrue(any(rule['type']=='ma_cross' for rule in rules))

    def test_unknown_csv_schema_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"columns not recognized"):
            parse_csv_prices("foo,bar\na,b\n")

if __name__ == "__main__": unittest.main()
