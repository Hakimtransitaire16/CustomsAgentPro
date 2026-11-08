import copy
import json
import unittest
from pathlib import Path

import jsonschema

from visite import calc, data, mobile, registry, render

EX = Path(__file__).resolve().parents[1] / "exemples" / "dossier_exemple.json"


class TestVisite(unittest.TestCase):
    def setUp(self):
        self.d = data.load(EX)

    def test_schema_refuse_conteneur_invalide(self):
        d = copy.deepcopy(self.d)
        d["transport"]["conteneur"] = "ABC123"
        schema = json.loads(data.SCHEMA.read_text(encoding="utf-8"))
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate({k: v for k, v in d.items() if not k.startswith("_")}, schema)

    def test_controles_exemple(self):
        r = calc.resume(calc.controles(self.d))
        self.assertEqual(r["erreur"], 0)
        self.assertGreaterEqual(r["ok"], 12)

    def test_detecte_erreur_liquidation(self):
        d = copy.deepcopy(self.d)
        d["articles"][0]["taxes"][1]["montant"] += 1000
        ids = {c["id"]: c["statut"] for c in calc.controles(d)}
        self.assertEqual(ids["LIQ-1"], "erreur")

    def test_detecte_erreur_poids(self):
        d = copy.deepcopy(self.d)
        d["declaration"]["poids_brut"] += 50
        ids = {c["id"]: c["statut"] for c in calc.controles(d)}
        self.assertEqual(ids["PDS-2"], "erreur")

    def test_iso6346(self):
        self.assertTrue(calc.iso6346_ok("CSQU3054383"))
        self.assertFalse(calc.iso6346_ok("CSQU3054384"))

    def test_formats(self):
        self.assertEqual(data.n(8451938), "8 451 938")
        self.assertEqual(data.n(236313.9, 2), "236 313,90")
        self.assertEqual(data.sh("3506999000"), "3506.99.90.00")

    def test_rendu_html(self):
        h = render.html(self.d)
        for v in (self.d["declaration"]["numero"], self.d["declaration"]["mrn"], self.d["transport"]["conteneur"], "3506.99.90.00"):
            self.assertIn(v, h)
        self.assertNotIn("{PAGE}", h)

    def test_page_mobile(self):
        h = mobile.page(self.d)
        self.assertIn("Exporter la visite", h)
        self.assertIn(self.d["transport"]["scelle"], h)

    def test_registre(self):
        tmp = Path(__file__).parent / "_tmp_registre"
        try:
            rows = registry.enregistrer(self.d, tmp)
            self.assertEqual(len(rows), 1)
            rows = registry.enregistrer(self.d, tmp)  # idempotent
            self.assertEqual(len(rows), 1)
            kpi = registry.tableau_de_bord(tmp, tmp / "tb.html")
            self.assertEqual(kpi["dossiers"], 1)
        finally:
            for f in tmp.glob("*"):
                f.unlink()
            tmp.rmdir()


if __name__ == "__main__":
    unittest.main()
