import copy
import json
import unittest
from pathlib import Path

import jsonschema

from visite import app, calc, data, mobile, registry, render, tarif

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

    def test_application_unique(self):
        h = app.construire(self.d)
        for v in ('id="t-fiche"', 'id="t-visite"', 'id="t-controles"', 'id="t-registre"', 'id="t-donnees"', 'data-pv="observations"', "srcdoc="):
            self.assertIn(v, h)
        self.assertIn(self.d["declaration"]["mrn"], h)
        self.assertNotIn("</script><", h.split('id="dossier">')[1].split("</script>")[0])

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

    def test_tarif_position_exacte(self):
        f = tarif.fiche("3506.99.90.00")
        self.assertEqual(f["statut"], "exact")
        self.assertEqual(f["section"]["numero"], "VI")
        self.assertEqual(f["chapitre"]["numero"], 35)
        self.assertEqual(f["position"]["code"], "35.06")
        self.assertEqual(f["droit_douane"], 30)
        self.assertTrue(any("35.06" in x for x in f["section"]["notes_citant_position"]))

    def test_tarif_correspondance_sh2017(self):
        f = tarif.fiche("3824999999")
        self.assertEqual(f["statut"], "correspondance")
        self.assertEqual(f["ligne"]["code"], "3824.90.99.99")
        self.assertEqual(f["droit_douane"], 15)

    def test_controle_quotite_dd(self):
        d = copy.deepcopy(self.d)
        next(t for t in d["articles"][0]["taxes"] if t["code"] == "DD")["quotite"] = 15
        ids = {c["id"]: c["statut"] for c in calc.controles(d)}
        self.assertEqual(ids["DD-1"], "erreur")

    def test_controle_famille(self):
        ids = {c["id"]: c["statut"] for c in calc.controles(self.d)}
        self.assertEqual(ids["FAM-1"], "alerte")   # 3506.99 déclaré, 3506.91 au pays d'origine
        self.assertEqual(ids["FAM-2"], "ok")
        d = copy.deepcopy(self.d)
        d["articles"][0]["code_origine"] = "3920.10"
        det = next(c for c in calc.controles(d) if c["id"] == "FAM-1")["detail"]
        self.assertIn("chapitres différents", det)


if __name__ == "__main__":
    unittest.main()
