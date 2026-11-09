import copy
import json
import unittest
from pathlib import Path

import jsonschema

from visite import app, calc, data, mobile, moteur, registry, render, tarif

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

    def test_partage_sans_donnees_privees(self):
        d = copy.deepcopy(self.d)
        d["risques_declarant"] = [{"titre": "SECRET-RISQUE", "detail": "SECRET-DETAIL"}]
        autre = {"dossier": "AUTRE-CLIENT-XYZ"}
        html = app.construire(d, registre=[app.ligne(d)], partage=True)
        self.assertNotIn("SECRET-RISQUE", html)
        self.assertNotIn("SECRET-DETAIL", html)
        complet = app.construire(d, partage=False)
        self.assertIn("SECRET-RISQUE", complet)

    def test_fiche_visite_plan_d10(self):
        html = render.html(self.d)
        for t in ("Identification de la déclaration", "Espèce tarifaire", "Valeur en douane", "Constatations de la visite"):
            self.assertIn(t, html)
        self.assertNotIn("DOSSIER CONFORME", html)

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

    def test_sources_recentes(self):
        f = tarif.fiche("2404.12.90.00")            # ligne créée en 2022
        self.assertEqual(f["statut"], "exact")
        self.assertIn("SH 2022", f["droit_douane_source"])
        f = tarif.fiche("8424.10.10.00")            # mise à jour 2020 : DD, TVA, FAP
        self.assertEqual((f["droit_douane"], f["tva"]), (30, 19))
        self.assertIn("C.C", f["fap"])
        self.assertEqual(tarif.daps("9403.70.10.00")["taux"], 60)
        self.assertIsNone(tarif.daps("3506.99.90.00"))

    def test_controle_daps(self):
        d = copy.deepcopy(self.d)
        d["articles"][0]["code_sh"] = "9403701000"
        ids = {c["id"]: c["statut"] for c in calc.controles(d)}
        self.assertEqual(ids["DAPS-1"], "alerte")

    def test_moteur_lecture(self):
        L = moteur.lire("DAPS sur 8415.10 ? facture de 1500 DA en 2025, article 16 bis")
        self.assertEqual(L["codes"], ["841510"])
        self.assertIn("daps", L["themes"])
        self.assertEqual(L["articles"][0][0], "16 bis")
        self.assertIn("admission temporaire", moteur.traduire("شروط القبول المؤقت"))

    def test_moteur_toutes_sources(self):
        r = moteur.analyser("herbicide glyphosate", preparation=False)
        self.assertEqual(r["candidats"][0]["position"], "38.08")
        r = moteur.analyser("8415.10 DAPS", preparation=False)
        self.assertTrue(r["positions"][0]["daps_sous_code"])
        self.assertTrue(any("18-13" in s for s in r["sources"]))
        r = moteur.analyser("article 16 du code des douanes", preparation=False)
        self.assertIn("valeur", r["articles"][0]["texte"].lower())
        self.assertFalse(moteur.utile("bonjour, ça va ?"))

    def test_note_risques(self):
        n = moteur.note_risques(self.d, calc.controles(self.d))
        self.assertIn("FAM-1", n)
        self.assertIn("RGI 6", n)
        self.assertIn("ne pas joindre", n)


if __name__ == "__main__":
    unittest.main()
