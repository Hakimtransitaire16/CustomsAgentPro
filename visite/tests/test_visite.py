import copy
import json
import unittest
from pathlib import Path

import jsonschema

from visite import app, calc, data, mobile, moteur, registry, render, tarif

EX = Path(__file__).resolve().parents[1] / "exemples" / "dossier_exemple.json"


def moteur_kb_tools():
    from visite import moteur
    return moteur.KB / "tools"


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

    def test_partage_sans_note_interne_ni_hypotheses(self):
        d = copy.deepcopy(self.d)
        d["note_interne"] = {"synthese": "SECRET-NOTE", "enjeux": "SECRET-ENJEUX"}
        d["meta"]["hypotheses"] = ["SECRET-HYPOTHESE"]
        d["frais_locaux"] = [{"libelle": "SECRET-FRAIS", "ht": 1}]
        d["transport"]["surestaries"] = {"source": "SECRET-BAREME", "paliers": []}
        html = app.construire(d, registre=[app.ligne(d)], partage=True)
        for s in ("SECRET-NOTE", "SECRET-ENJEUX", "SECRET-HYPOTHESE", "SECRET-FRAIS", "SECRET-BAREME"):
            self.assertNotIn(s, html)

    def _plusieurs_conteneurs(self):
        """Dossier d'exemple (fictif) réparti sur deux conteneurs fictifs."""
        brut = json.loads(EX.read_text(encoding="utf-8"))
        t, dec = brut["transport"], brut["declaration"]
        c1 = t.pop("conteneur")
        t.pop("scelle", None)
        t.pop("type_conteneur", None)
        c2 = next(c for c in (f"TSTU{i:07d}" for i in range(1000000, 1000040)) if calc.iso6346_ok(c))
        a, b = dec["nb_colis"] // 2, dec["nb_colis"] - dec["nb_colis"] // 2
        t["conteneurs"] = [{"numero": c1, "scelle": "SC-A1", "type": "40' HC", "palettes": a, "brut": dec["poids_brut"] / 2},
                           {"numero": c2, "scelle": "SC-B2", "type": "40' HC", "palettes": b, "brut": dec["poids_brut"] / 2}]
        jsonschema.validate(brut, json.loads(data.SCHEMA.read_text(encoding="utf-8")))
        return data.normaliser(brut), c1, c2

    def test_plusieurs_conteneurs(self):
        d, c1, c2 = self._plusieurs_conteneurs()
        self.assertEqual(d["transport"]["conteneur"], f"{c1} · {c2}")
        self.assertEqual(d["transport"]["scelle"], "SC-A1 · SC-B2")
        self.assertEqual(d["transport"]["type_conteneur"], "2 × 40' HC")
        self.assertEqual([c["numero"] for c in data.conteneurs(d)], [c1, c2])
        ctrl = {c["id"]: c for c in calc.controles(d)}
        for k in ("ISO-1", "ISO-2", "TC-1", "TC-2"):
            self.assertEqual(ctrl[k]["statut"], "ok", k)
        d["transport"]["_conteneurs"][1]["palettes"] += 1          # une palette de trop : le contrôle le voit
        self.assertEqual({c["id"]: c for c in calc.controles(d)}["TC-1"]["statut"], "alerte")
        lignes = render.checklist(d)
        self.assertTrue(any(c1 in x and "SC-A1" in x for x in lignes) and any(c2 in x and "SC-B2" in x for x in lignes))

    def test_surestaries_par_conteneur(self):
        from visite import expertise
        un = expertise.surestaries(self.d)
        d, _, _ = self._plusieurs_conteneurs()
        deux = expertise.surestaries(d)
        if un:
            self.assertEqual(deux["nb"], 2)
            self.assertAlmostEqual(deux["total"], 2 * un["total"])

    def test_dossier_sans_bad_ni_accostage(self):
        d = json.loads(EX.read_text(encoding="utf-8"))
        d["transport"].pop("bad", None)
        d.pop("arrivee", None)
        d["visite"] = {}
        html = render.html(data.normaliser(d))
        self.assertNotIn("N° Gros", html)
        self.assertIn("Localisation (case 35)", html)

    def test_sources_presentes_seulement(self):
        f = render.filtre_pieces({"documents": [{"code": "D10"}, {"code": "BL"}, {"code": "DOC"}]})
        self.assertEqual(f("Facture · colisage · B/L"), "B/L · document du fournisseur")
        self.assertEqual(f("D10 · avis d'arrivée"), "D10")
        self.assertEqual(f("Avis d'arrivée"), "D10")
        g = render.filtre_pieces({"documents": [{"code": "FAC"}, {"code": "PL"}, {"code": "BL"}, {"code": "AA"}]})
        self.assertEqual(g("Facture · colisage · B/L"), "Facture · colisage · B/L")

    def test_fds_seulement_pour_les_produits_chimiques(self):
        from visite import exigences
        d = copy.deepcopy(self.d)
        d["articles"] = d["articles"][:1]
        d["articles"][0]["code_sh"] = "3926909990"      # ouvrage en plastique : pas de FDS
        self.assertNotIn("FDS", {c for c, _, _ in exigences.requises(d)})
        d["articles"][0]["code_sh"] = "3907300000"      # résine sous forme primaire : FDS
        self.assertIn("FDS", {c for c, _, _ in exigences.requises(d)})

    def test_tarif_ligne_subdivisee_depuis_2016(self):
        if not tarif.disponible():
            self.skipTest("base tarifaire absente")
        f = tarif.fiche("3926909990")
        self.assertEqual(f["ligne"]["code"], "3926.90.99.00")
        self.assertEqual(f["ligne"]["libelle"], "Autres")          # sans le numéro de page du PDF

    def test_fiche_visite_plan_d10(self):
        html = render.html(self.d)
        for t in ("Identification de la déclaration", "Espèce tarifaire", "Valeur en douane", "Constatations de la visite"):
            self.assertIn(t, html)
        self.assertNotIn("DOSSIER CONFORME", html)

    def test_manquants_signale_visite_et_pieces(self):
        from visite import exigences
        d = copy.deepcopy(self.d)
        d["visite"] = {"lieu": "Port sec X", "inspecteur": "", "agent": "", "date": ""}
        d.setdefault("meta", {})["hypotheses"] = ["visite.lieu"]
        m = exigences.manquants(d)
        codes = {x["code"] for x in m}
        self.assertIn("visite.inspecteur", codes)
        self.assertIn("visite.lieu", codes)  # hypothèse à confirmer
        for x in m:
            if x["type"] == "pièce":
                self.assertTrue(x["emetteur"] and x["base"])

    def test_designation_generique(self):
        from visite.calc import designation_generique as g
        self.assertTrue(g("PIECES DE RECHANGE"))
        self.assertTrue(g("Verre"))
        self.assertFalse(g("AMP 10 ML VERRE TRANSPARENTE"))
        self.assertFalse(g("Colle polyuréthane bicomposant"))

    def test_empreinte_change_si_donnees_changent(self):
        d = copy.deepcopy(self.d)
        e1 = render.empreinte(d)
        d["declaration"]["valeur_da"] += 1
        self.assertNotEqual(e1, render.empreinte(d))

    def test_expertise_surestaries_et_analyse(self):
        from visite import expertise
        d = copy.deepcopy(self.d)
        self.assertIn("Coût de revient", expertise.analyse(d)["sections"])  # sans barème : pas d'erreur
        d["transport"]["date_accostage"] = "01/01/2026"
        d["declaration"]["date_heure"] = "11/04/2026 10:00:00"  # 100 jours
        d["transport"]["surestaries"] = {"franchise_jours": 15, "paliers": [[16, 40, 52], [41, 60, 96], [61, 90, 124]],
                                         "devise": "USD", "taux_da": 100.0, "frais_gestion_da": 40000, "seuil_gestion_jours": 90}
        s = expertise.surestaries(d)
        self.assertEqual(s["jours"], 100)
        self.assertEqual(s["total"], 25 * 52 + 20 * 96 + 30 * 124)
        self.assertEqual(s["total_da"], 694000.0)
        self.assertEqual(s["au_dela"], 10)
        self.assertEqual(s["gestion_da"], 40000)
        d["declaration"]["date_heure"] = "21/01/2026 10:00:00"  # 20 jours : 5 jours au premier palier
        self.assertEqual(expertise.surestaries(d)["total"], 5 * 52)
        self.assertIn("Surestaries", expertise.texte(d))

    def test_registre_indicateurs(self):
        from visite import registry
        l = registry.ligne(self.d)
        for k in ("bureau", "incoterm", "transit_jours", "surestaries_da", "cout_connu_da", "alertes", "pieces_manquantes"):
            self.assertIn(k, l)
        self.assertEqual(set(l), set(registry.CHAMPS))

    def test_programme_commissionnaire(self):
        import json
        from visite import moteur
        prog = json.loads((moteur.KB / "data" / "programme_commissionnaire.json").read_text(encoding="utf-8"))
        self.assertEqual([m["n"] for m in prog["modules"]], list(range(1, 15)))
        nums = [m["n"] for m in moteur.modules(["surestaries", "connaissement", "armateur"])]
        self.assertEqual(nums[0], 10)
        self.assertIn(9, [m["n"] for m in moteur.modules(["domiciliation", "banque"])])

    def test_recherche_arabe(self):
        from visite import moteur
        self.assertEqual(moteur.mots_arabes("ما هي مسؤولية الناقل البحري"), ["مسؤولي", "ناقل", "بحري"])
        q = moteur._fts(["ناقل"])
        self.assertIn('"الناقل"*', q)

    def test_articles_arabes(self):
        import sys
        sys.path.insert(0, str(moteur_kb_tools()))
        import build_kb
        arts = build_kb.parse_articles_ar("المادة 43 : نص أ\nالمادة 60 مكرر 1 : نص ب\nالمادة ٦١ : نص ج", "T")
        self.assertEqual([a["article"] for a in arts], ["43", "60 مكرر 1", "61"])

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
