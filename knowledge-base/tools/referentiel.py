"""Catalogue des sources de référence du déclarant en douane (Algérie).

Chaque entrée : où se trouve le texte officiel, ce qu'il apporte au moteur, et s'il est déjà dans la base.
Le statut est recalculé à partir de sources/ (fichier présent = « base »).

    python tools/referentiel.py          # écrit data/referentiel_sources.json et REFERENTIEL.md

Types → traitement par tools/build_kb.py :
    tarif        tableau tarifaire (codes à 10 chiffres)        → lignes, taux
    correlation  table de correspondance de nomenclature        → codes anciens ↔ nouveaux
    recueil      recueil de décisions de classement (RTC)        → décisions
    texte        loi, décret, arrêté (Journal officiel)          → articles
    guide        guide, manuel, circulaire, bulletin             → index de recherche
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DGD = "https://www.douane.gov.dz/IMG/pdf/"

# id, domaine, titre, type, priorité (1 = indispensable), fichier officiel, url, usage
SOURCES = [
    # ---------------------------------------------------------------- nomenclature et tarif
    ("tarif-2016", "Tarif", "Tarif douanier DGD, édition 2016 (SH 2012)", "tarif", 1,
     "tarif-douanier-2016-10-chiffres-pour-telechargement.pdf", None,
     "Lignes à 10 chiffres, DD, notes de chapitres et de sections, RGI"),
    ("correlation-sh2022", "Tarif", "Amendements du Système harmonisé 2022 — table de corrélation nationale "
     "(structure du tarif applicable au 01/01/2024)", "correlation", 1,
     "amendements_systeme_harmonise_2022_table_de_correlation_nationale_.pdf", None,
     "Passer des codes 2016 aux codes en vigueur ; détecter les lignes supprimées ou éclatées"),
    ("tarif-maj-2020", "Tarif", "Mise à jour du tarif douanier et de ses annexes (loi de finances 2020) — "
     "dispositions préliminaires", "tarif", 1, "mise_a_jour_du_tarif_2020.pdf", None,
     "Taux DD modifiés depuis 2016, dispositions préliminaires du tarif"),
    ("tarif-annexes-2020", "Tarif", "Annexes du tarif d'usage 2020", "guide", 1,
     "annexes_tarif_d_usague_2020.pdf", None, "Annexes : TVA réduite, DAPS, mesures particulières par code"),
    ("tarif-eclatements", "Tarif", "Amendements de la structure du tarif : éclatements de sous-positions « Autres »",
     "tarif", 2, "eclatements_tarifaires_de_certaines_sous_postions_denommees_autres.pdf", None,
     "Nouvelles lignes nationales créées depuis 2016"),
    ("tarif-maj-2018", "Tarif", "Mise à jour du tarif 2018", "tarif", 2, "mise_a_jours_tarif_2018_.pdf", None,
     "Historique des taux"),
    ("tarif-usage-2018", "Tarif", "Mise à jour du tarif d'usage et de ses annexes, août 2018", "tarif", 3,
     "mise_a_jour_du_tarif_d_usage_et_ses_annexe_aout_2018.pdf", None, "Historique des taux"),
    ("omd-correlation-2017-2022", "Tarif", "OMD — tables de corrélation SH 2017 ↔ SH 2022 (tables I et II)",
     "correlation", 2, "table-i_en.pdf",
     "https://www.wcoomd.org/en/topics/nomenclature/instrument-and-tools/hs-nomenclature-2022-edition/"
     "correlation-tables-hs-2017-2022.aspx", "Correspondances internationales SH6"),

    # ---------------------------------------------------------------- décisions de classement
    ("rtc-2025", "Classement", "Recueil des décisions de classement tarifaire 2025 (publié janvier 2026)", "recueil", 1,
     "recueil_des_decisions_de_classement_tarifaire_2026.pdf", None, "Précédents RTC"),
    ("rtc-2024", "Classement", "Recueil des décisions de classement tarifaire établies durant 2024 (édition 2025)",
     "recueil", 1, "recueil_des_decisions_de_classement_tarifaire_2024-.pdf", None, "Précédents RTC"),
    ("rtc-2022", "Classement", "Recueil des décisions de classement tarifaire (édition 2023)", "recueil", 1,
     "recueil_des_decisions_de_classement_traifaire_2023.pdf", None, "Précédents RTC"),
    ("rtc-2020", "Classement", "Recueil des décisions de classement tarifaire 2020 (publié janvier 2021)", "recueil", 1,
     "recueil_des_decisions_de_classement_tarifaire_2021.pdf", None, "Précédents RTC"),
    ("rtc-2017-2018", "Classement", "Recueil de décisions de classement tarifaire 2017-2018", "recueil", 2,
     "recueil_decision_ct_2017-2018.pdf", None, "Précédents anciens"),
    ("rtc-2015", "Classement", "Recueil des décisions de classement tarifaire 2015", "recueil", 2,
     "recueil_decisions_de_classement_2015.pdf", None, "Précédents anciens"),
    ("rtc-2008", "Classement", "Recueil des décisions de classement 2008", "recueil", 3, "class2008.pdf", None,
     "Précédents anciens"),

    # ---------------------------------------------------------------- codes et lois
    ("code-douanes-consolide", "Législation", "Code des douanes — loi n° 79-07 du 21/07/1979 modifiée et complétée "
     "(texte consolidé)", "texte", 1, "loi_no79-07_du_21_juillet_1979.pdf", None,
     "Tous les articles en vigueur (la loi 17-04 seule ne donne que les articles modifiés)"),
    ("loi-17-04", "Législation", "Loi n° 17-04 du 16/02/2017 modifiant le code des douanes", "texte", 1,
     "loi_no_17-04_du_16_fevrier_2017_code_des_douanes.pdf", None, "Articles modifiés en 2017"),
    ("code-tca", "Fiscalité", "Code des taxes sur le chiffre d'affaires (TVA)", "texte", 1,
     "code_des_taxes_sur_le_chiffre_d_affaire.pdf", None,
     "Taux de TVA 19 % / 9 %, listes du taux réduit et exonérations à l'importation (vérifier l'édition)"),
    ("code-impots-indirects", "Fiscalité", "Code des impôts indirects (art. 73, édition 2012)", "texte", 3,
     "code_des_impots_indirect_art_73._annee_2012.pdf", None, "Droits indirects (alcools, tabacs…)"),
    ("lf-2026", "Fiscalité", "Loi n° 25-17 du 14/12/2025 portant loi de finances pour 2026", "texte", 1,
     "loi_de_finances_2026.pdf", None, "Taux modifiés, exonérations, conditions 2026"),
    ("lf-2025", "Fiscalité", "Loi de finances pour 2025 (JORADP)", "texte", 1, None, "https://www.joradp.dz",
     "Contribution de solidarité 3 %, taxe de domiciliation 5 %, exonérations 2025-2027"),
    ("lfc-2018", "Fiscalité", "Loi n° 18-13 du 11/07/2018 — loi de finances complémentaire 2018 (création du DAPS)",
     "texte", 1, "loi_no_18-13_du_11_juillet_2018.pdf", None, "Base légale du DAPS (30 % à 200 %)"),
    ("daps-arrete-2019", "Fiscalité", "Arrêté du 26/01/2019 fixant la liste des marchandises soumises au DAPS",
     "texte", 1, "arreteedu_26_janvier_2019_fr.pdf", None, "Liste DAPS par code et taux"),
    ("daps-arrete-2019-mod", "Fiscalité", "Arrêté du 8/04/2019 modifiant l'arrêté du 26/01/2019 (DAPS)", "texte", 1,
     "arrete_du_2_chaabane_1440_correspondant_au_8_avril_2019_modifiant_l_arrete_26_janvier_2019.pdf", None,
     "Modifications de la liste DAPS"),
    ("lfc-2015", "Fiscalité", "Loi de finances complémentaire 2015", "texte", 3, "lfc_2015.pdf", None, "Historique"),

    # ---------------------------------------------------------------- réglementation
    ("decret-10-288", "Profession", "Décret exécutif n° 10-288 du 14/11/2010 — personnes habilitées à déclarer "
     "en détail (commissionnaires en douane)", "texte", 1, "decret_executif_no_10-288_du_14_novembre_2010.pdf", None,
     "Agrément, obligations et responsabilité du commissionnaire et du déclarant"),
    ("decret-10-286", "Profession", "Décret exécutif n° 10-286 (JO n° 71 de 2010)", "texte", 2,
     "decret_executif_n10_286.pdf", None, "À identifier à la lecture"),
    ("decret-18-165", "Classement", "Décret exécutif n° 18-165 du 14/06/2018 — décisions anticipées (RTC, origine, "
     "valeur)", "texte", 1, "decret_executif_no_18-165_du_14_juin2018.pdf", None, "Demande de RTC"),
    ("decret-17-353", "Réglementation", "Décret exécutif n° 17-353 (JO n° 72 de 2017)", "texte", 2,
     "decret_executif_no_17-353.pdf", None, "À identifier à la lecture"),
    ("decret-18-63", "Réglementation", "Décret exécutif n° 18-63 du 13/02/2018", "texte", 3,
     "decret_executif_no_18-63_du_26_joumada_el_oula_1439_correspondant_au_13_fevrier_2018.pdf", None,
     "À identifier à la lecture"),
    ("decret-05-467", "Conformité", "Décret exécutif n° 05-467 du 10/12/2005 — contrôle de la conformité des "
     "produits importés aux frontières", "texte", 1, None, "https://commerce.gov.dz/fr/1-ancrage-juridique",
     "Visa de contrôle aux frontières, documents exigés"),
    ("guide-controle-frontieres", "Conformité", "Ministère du Commerce — guide du contrôle aux frontières", "guide", 1,
     "04-contr-front-fran.pdf", "https://www.commerce.gov.dz/events/claff/guides/04-contr-front-fran.pdf",
     "Procédure, délais et pièces du contrôle de conformité"),
    ("circulaire-419", "Réglementation", "Circulaire n° 419 DGD/SPD", "guide", 3, "circulaire_419.pdf", None,
     "À identifier à la lecture"),

    # ---------------------------------------------------------------- valeur, origine, régimes
    ("guide-valeur", "Valeur", "Guide sur la valeur en douane", "guide", 1, "guide_sur_la_valeur_en_douane.pdf",
     None, "Méthodes de valeur, éléments à ajouter (fret, assurance), contrôle de la valeur"),
    ("manuel-origine", "Origine", "Manuel sur les règles d'origine appliquées en Algérie", "guide", 1,
     "manuel_sur_les_regles_d_origine_applicables_en_algerie.pdf", None, "Origine non préférentielle et preuves"),
    ("manuel-origine-ue", "Origine", "Manuel sur les règles de l'origine — accord d'association Algérie-UE", "guide", 1,
     "manuel_sur_les_regles_de_lorigine_des_marchandisses_dans_le_cadre_de_laccord_dassociation_algerie_ue.pdf",
     None, "EUR.1, déclaration d'origine, cumul, ouvraisons suffisantes"),
    ("rco", "Origine", "Dépliant — renseignement contraignant sur l'origine (RCO)", "guide", 2, "depliant_rco.pdf",
     None, "Décision anticipée d'origine"),
    ("guide-regimes", "Régimes", "Guide de l'opérateur — régimes douaniers économiques à caractère commercial", "guide",
     1, "guideoperateur.pdf", None, "Entrepôt, admission temporaire, transit, perfectionnement"),
    ("circulaire-157", "Régimes", "Circulaire n° 157 — schéma d'opération d'admission temporaire", "guide", 2,
     "circulaire_157.pdf", None, "Admission temporaire"),
    ("entrepot-129-164", "Régimes", "Code des douanes, articles 129 à 164 — entrepôt de douane", "texte", 2,
     "article_129_164.pdf", None, "Entrepôt"),
    ("guide-exportateur-2024", "Export", "Guide de l'exportateur 2024", "guide", 2,
     "fr_guide_de_l_exportateur_2024_fr-2.pdf", None, "Procédures export"),

    # ---------------------------------------------------------------- bulletins et méthodes
    ("boda-2022-t3", "Bulletin", "Bulletin officiel des douanes (BODA), 3e trimestre 2022", "guide", 3,
     "boda_n3_2022_francais.pdf", None, "Circulaires et décisions publiées"),
    ("boda-2022-t4", "Bulletin", "Bulletin officiel des douanes (BODA), 4e trimestre 2022", "guide", 3,
     "boda_n4_2022_francais.pdf", None, "Circulaires et décisions publiées"),
    ("boda-2018-t2", "Bulletin", "Bulletin officiel des douanes (BODA), 2e trimestre 2018", "guide", 3,
     "boda_2_2018_fr.pdf", None, "Circulaires et décisions publiées"),
    ("boda-2018-t4", "Bulletin", "Bulletin officiel des douanes (BODA), 4e trimestre 2018", "guide", 3,
     "boda_num_04_2018.pdf", None, "Circulaires et décisions publiées"),
    # ---------------------------------------------------------------- banque et change
    ("ba-instruction-01-2026", "Banque et change", "Banque d'Algérie — instruction n° 01/2026 du 14/05/2026 : "
     "domiciliation des importations avant l'expédition", "texte", 1, "note-01-DGC-2026.pdf",
     "https://www.bank-of-algeria.dz/stoodroa/2026/05/note-01-DGC-2026.pdf",
     "Domiciliation avant le B/L, délai de 45 jours (lien relevé par la recherche : vérifier à l'ouverture)"),
    ("ba-reglement-07-01", "Banque et change", "Banque d'Algérie — règlement n° 07-01 du 03/02/2007 modifié "
     "(domiciliation, rapatriement, comptes devises)", "texte", 1, "reglement-07-01.pdf",
     "https://www.bank-of-algeria.dz/importations-exportations-instruction/",
     "Art. 29 : domiciliation préalable au transfert et au dédouanement"),
    ("ba-reglement-26-02", "Banque et change", "Banque d'Algérie — règlement n° 26-02 du 23/07/2026 "
     "(JO n° 58 du 12/08/2026) : rapatriement des recettes d'exportation en 120 jours", "texte", 2,
     "reglement-26-02.pdf", "https://www.joradp.dz", "Exportation : délai de rapatriement"),
    ("plf-2027", "Fiscalité", "Projet de loi de finances 2027 — dispositions douanières (articles 153 à 176)",
     "texte", 1, "plf-2027.pdf", "https://www.mfdgi.gov.dz", "Mesures douanières à venir (projet, non adopté)"),
    ("ebti", "Méthode", "Commission européenne — informations générales sur les RTC (EBTI)", "guide", 2,
     "ebti_general_information_en.pdf", None, "Méthode de description (case 9)"),
    ("omd-smart-customs", "Méthode", "OMD — rapport « douanes intelligentes » (2024)", "guide", 3,
     "smart-customs_public_report_fr_1.pdf", None, "Gestion des risques, numérique"),
]


def catalogue() -> list[dict]:
    present = {p.name for p in (ROOT / "sources").glob("*.pdf")}
    out = []
    for sid, dom, titre, typ, prio, fichier, url, usage in SOURCES:
        url = url or (DGD + fichier if fichier else None)
        out.append({"id": sid, "domaine": dom, "titre": titre, "type": typ, "priorite": prio,
                    "fichier": fichier, "url": url, "usage": usage,
                    "statut": "base" if fichier in present else "a_telecharger"})
    return out


def par_fichier() -> dict:
    return {s["fichier"]: s for s in catalogue() if s["fichier"]}


def main() -> None:
    cat = catalogue()
    (ROOT / "data" / "referentiel_sources.json").write_text(
        json.dumps({"count": len(cat), "sources": cat}, ensure_ascii=False, indent=1), encoding="utf-8")
    base = sum(1 for s in cat if s["statut"] == "base")
    L = ["# Référentiel des sources du déclarant", "",
         f"{len(cat)} sources de référence · **{base} dans la base** · {len(cat) - base} à télécharger.", "",
         "Les sites officiels (douane.gov.dz, commerce.gov.dz, mfdgi.gov.dz, OMD) refusent la lecture "
         "automatique : ces fichiers se téléchargent à la main, puis `python tools/ingest.py <dossier>` les "
         "intègre (texte, données, index) et met ce tableau à jour.", "",
         "Priorité : 1 = indispensable au travail quotidien · 2 = utile · 3 = historique.", ""]
    for dom in dict.fromkeys(s["domaine"] for s in cat):
        L += [f"## {dom}", "", "| | Prio. | Source | Apport | Lien |", "|---|---|---|---|---|"]
        for s in sorted((x for x in cat if x["domaine"] == dom), key=lambda x: (x["statut"] != "base", x["priorite"])):
            etat = "✅" if s["statut"] == "base" else "⬇"
            lien = f"[{s['fichier'] or 'site'}]({s['url']})" if s["url"] else "—"
            L.append(f"| {etat} | {s['priorite']} | {s['titre']} | {s['usage']} | {lien} |")
        L.append("")
    (ROOT / "REFERENTIEL.md").write_text("\n".join(L), encoding="utf-8")
    print(f"{len(cat)} sources · {base} dans la base · {len(cat) - base} à télécharger")


if __name__ == "__main__":
    main()
