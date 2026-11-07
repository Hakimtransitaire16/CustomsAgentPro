"""Checks on the official DGD data parsed into knowledge-base/data."""
import unittest

from customsagent.engine import Engine
from customsagent.knowledge import KB_DATA


@unittest.skipUnless((KB_DATA / "tarif_2016.json").exists(), "knowledge-base not built")
class OfficialDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = Engine.official()

    def test_tariff_size_and_rates(self):
        lines = self.engine.tariff.lines
        self.assertEqual(len(lines), 15946)
        # rates printed in the 2016 edition: exemption, 5 %, 15 %, 30 %
        self.assertEqual({l.duty_rate for l in lines.values()}, {0.0, 0.05, 0.15, 0.30})
        self.assertEqual(lines["0101.21.11.00"].duty_rate, 0.05)  # pur-sang arabe, reproducteur
        self.assertEqual(lines["8415.90.19.00"].duty_rate, 0.30)

    def test_rtc_used_as_precedent(self):
        top = self.engine.classify("Boitier de l'unité extérieure de climatiseur split")[0]
        self.assertEqual(top["hs_code"], "8415.90.19.00")
        self.assertIn("RTC 001/DGD du 06.03.2025", top["precedents"])

    def test_decisions_loaded_with_validity(self):
        rtc = self.engine.rulings.get("RTC 001/DGD du 06.03.2025")
        self.assertEqual(str(rtc.valid_from), "2025-03-06")
        self.assertEqual(str(rtc.valid_to), "2028-03-05")

    def test_precedent_contradiction_warns(self):
        res = self.engine.analyze_dict({
            "direction": "import", "origin_country": "CN", "destination_country": "DZ", "exchange_rate": 150,
            "items": [{"description": "Boitier de l'unité extérieure de climatiseur", "hs_code": "8415.90.11.00", "value": 1000}],
            "documents": [{"type": "invoice", "number": "F"}, {"type": "transport", "number": "B"}],
        })
        pre = [f for f in res["findings"] if f["rule"] == "R-PRE-01"]
        self.assertTrue(pre and "RTC 001/DGD du 06.03.2025" in pre[0]["message"], res["findings"])

    def test_precedent_agreement_is_silent(self):
        res = self.engine.analyze_dict({
            "direction": "import", "origin_country": "CN", "destination_country": "DZ",
            "items": [{"description": "Boitier de l'unité extérieure de climatiseur", "hs_code": "8415.90.19.00", "value": 1000}],
        })
        self.assertFalse([f for f in res["findings"] if f["rule"] == "R-PRE-01"])

    def test_cost_flags_assumed_vat(self):
        res = self.engine.analyze_dict({
            "direction": "import", "origin_country": "FR", "destination_country": "DZ", "exchange_rate": 150,
            "items": [{"description": "herbicide", "hs_code": "3808.93.99.19", "value": 1000}],
        })
        line = res["cost"]["lines"][0]
        self.assertEqual(line["duty"], 22500.0)  # 150 000 DZD x 15 %
        self.assertTrue(line["vat_assumed"])
        self.assertFalse(res["cost"]["illustrative_rates"])


if __name__ == "__main__":
    unittest.main()
