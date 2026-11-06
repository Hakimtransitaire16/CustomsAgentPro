import unittest
from datetime import date

from customsagent import Engine

TODAY = date(2026, 11, 6)
HOLDER = "000016001234567"  # holder of DEMO-RTC-2026-0001 (brake pads, 8708.30)


def dossier(**kw):
    base = {
        "reference": "T", "direction": "import", "holder_nif": None,
        "origin_country": "CN", "destination_country": "DZ",
        "exchange_rate": 100, "freight": 0, "insurance": 0,
        "items": [], "documents": [{"type": "invoice", "number": "F1"}, {"type": "transport", "number": "BL1"}],
    }
    base.update(kw)
    return base


def rules(result):
    return {f["rule"] for f in result["findings"]}


class ClassifierTest(unittest.TestCase):
    def setUp(self):
        self.e = Engine()

    def test_french_description(self):
        self.assertEqual(self.e.classify("Plaquettes de frein céramique")[0]["hs_code"], "8708.30")

    def test_arabic_description_with_article(self):
        self.assertEqual(self.e.classify("قضبان الحديد للخرسانة")[0]["hs_code"], "7214.20")

    def test_precedent_is_reported(self):
        self.assertIn("DEMO-RTC-2026-0002", self.e.classify("boîtes carton ondulé dattes")[0]["precedents"])

    def test_unknown_goods(self):
        self.assertEqual(self.e.classify("xyz qwerty"), [])


class RulingRulesTest(unittest.TestCase):
    def setUp(self):
        self.e = Engine()

    def test_code_contradicting_held_ruling_is_blocking(self):
        r = self.e.analyze_dict(dossier(holder_nif=HOLDER, items=[
            {"description": "Plaquettes de frein céramique", "hs_code": "8708.99", "value": 100}]), TODAY)
        self.assertIn("R-RTC-01", rules(r))
        self.assertEqual(r["status"], "blocked")

    def test_matching_code_with_ruling_is_ready(self):
        r = self.e.analyze_dict(dossier(items=[
            {"description": "Plaquettes de frein", "hs_code": "8708.30", "value": 100,
             "ruling_ref": "DEMO-RTC-2026-0001"}]), TODAY)
        self.assertEqual(r["status"], "ready", r["findings"])

    def test_expired_ruling(self):
        r = self.e.analyze_dict(dossier(items=[
            {"description": "Plaquettes de frein", "hs_code": "8708.30", "value": 100,
             "ruling_ref": "DEMO-RTC-2026-0001"}]), date(2027, 1, 1))
        self.assertIn("R-RTC-02", rules(r))

    def test_expiring_ruling_warning(self):
        r = self.e.analyze_dict(dossier(holder_nif="000016009876543", items=[
            {"description": "Boîtes en carton ondulé", "hs_code": "4819.10", "value": 100}]), TODAY)
        self.assertIn("R-RTC-03", rules(r))


class EuMarketTest(unittest.TestCase):
    def setUp(self):
        self.e = Engine()

    def export(self, items, docs=()):
        return dossier(direction="export", origin_country="DZ", destination_country="FR", items=items,
                       documents=[{"type": "invoice", "number": "F"}] + [{"type": d, "number": "X"} for d in docs])

    def test_leather_needs_eudr(self):
        r = self.e.analyze_dict(self.export([{"description": "cuir", "hs_code": "4107.12", "value": 1}]), TODAY)
        self.assertIn("R-EUDR-01", rules(r))

    def test_eudr_satisfied_by_dds(self):
        r = self.e.analyze_dict(self.export([{"description": "cuir", "hs_code": "4107.12", "value": 1}], ["dds"]), TODAY)
        self.assertNotIn("R-EUDR-01", rules(r))

    def test_cement_needs_cbam(self):
        r = self.e.analyze_dict(self.export([{"description": "ciment", "hs_code": "2523.29", "value": 1}]), TODAY)
        self.assertIn("R-CBAM-01", rules(r))

    def test_dates_are_out_of_scope(self):
        r = self.e.analyze_dict(self.export([{"description": "dattes", "hs_code": "0804.10", "value": 1}]), TODAY)
        self.assertFalse(rules(r) & {"R-EUDR-01", "R-CBAM-01"})

    def test_non_eu_destination_ignores_eudr(self):
        d = self.export([{"description": "cuir", "hs_code": "4107.12", "value": 1}])
        d["destination_country"] = "TN"
        self.assertNotIn("R-EUDR-01", rules(self.e.analyze_dict(d, TODAY)))


class CostAndDataTest(unittest.TestCase):
    def setUp(self):
        self.e = Engine()

    def test_landed_cost_formula(self):
        # 8708.30 sample: DD 30%, VAT 19%, no DAPS. FOB 1000 + freight 100, rate 100.
        r = self.e.analyze_dict(dossier(freight=100, items=[
            {"description": "Plaquettes de frein", "hs_code": "8708.30", "value": 1000}]), TODAY)
        t = r["cost"]["totals"]
        self.assertEqual(t["customs_value"], 110000)
        self.assertEqual(t["duty"], 33000)
        self.assertEqual(t["vat"], round((110000 + 33000) * 0.19, 2))

    def test_freight_ignored_for_cif(self):
        r = self.e.analyze_dict(dossier(incoterm="CIF", freight=100, items=[
            {"description": "x", "hs_code": "8708.30", "value": 1000}]), TODAY)
        self.assertEqual(r["cost"]["totals"]["customs_value"], 100000)

    def test_missing_transport_document(self):
        d = dossier(items=[{"description": "pneu", "hs_code": "4011.10", "value": 1}])
        d["documents"] = [{"type": "invoice", "number": "F"}]
        self.assertIn("R-DOC-01", rules(self.e.analyze_dict(d, TODAY)))

    def test_net_weight_above_gross(self):
        r = self.e.analyze_dict(dossier(items=[
            {"description": "pneu", "hs_code": "4011.10", "value": 1, "net_kg": 10, "gross_kg": 5}]), TODAY)
        self.assertIn("R-VAL-01", rules(r))

    def test_missing_code_is_filled(self):
        r = self.e.analyze_dict(dossier(items=[{"description": "Pneumatiques neufs voiture", "value": 1}]), TODAY)
        self.assertEqual(r["items"][0]["hs_code"], "4011.10")


if __name__ == "__main__":
    unittest.main()
