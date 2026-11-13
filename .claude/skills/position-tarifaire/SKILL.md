---
name: position-tarifaire
description: Recherche et vérification d'une position tarifaire dans les sources officielles du dépôt (tarif DGD, notes, RGI, décisions de classement 2020/2025, loi de finances 2026, code des douanes). À utiliser pour toute question de classement, de code SH, de droit de douane, ou pour vérifier la position déclarée d'un dossier.
---

# Position tarifaire — toujours depuis les sources fournies

Toute réponse sur un code SH s'appuie sur `knowledge-base/`, jamais sur la mémoire seule. On cite la source de chaque affirmation (document, section, note, article).

## 0. Le moteur d'abord
Le hook injecte déjà les sources pertinentes à chaque message. Pour aller plus loin : `python -m visite demande "<code ou désignation>"`. Il consulte toutes les sources en une fois et propose des positions candidates pour une désignation.

## 1. Ouvrir la fiche de la position
```bash
python -m visite tarif 3506.99.90.00            # fiche complète
python -m visite tarif 3506.99.90.00 --notes    # + texte intégral des notes de section et de chapitre
python -m visite tarif dossiers/<id>/dossier.json   # chaque article d'un dossier + famille du code d'origine
```
La fiche donne :
- la **section** (titre, chapitres, notes qui citent la position) ;
- le **chapitre** (titre, notes qui citent la position) ;
- la **position** à 4 chiffres et son libellé ;
- la **sous-position** SH6 et la **ligne nationale** à 10 chiffres (hiérarchie des tirets, unité) ;
- le **droit de douane**, après les mesures inconditionnelles de la loi de finances 2026 ;
- toutes les lignes nationales de la position ;
- les **mesures de la loi de finances 2026** qui touchent le code ;
- les **décisions de classement** (RTC) des recueils 2020 et 2025 sur la même position.

Recherche par mots-clés, quand on part d'une désignation :
```bash
cd knowledge-base && python tools/kb.py search "adhésif polyuréthane"
python tools/kb.py code 3506.91
python tools/kb.py article "16"      # article du code des douanes (loi 17-04) ou du décret 18-165
```

## 2. Réponse à une question « quelle position pour… »
Répondre dans cet ordre, en citant le tarif :
1. Section (numéro romain + titre).
2. Chapitre (numéro + titre).
3. Position (4 chiffres + libellé exact).
4. Sous-position et ligne nationale (10 chiffres + libellé, unité, DD %).
5. Définition : ce que couvre la position, avec les notes de section et de chapitre applicables (citées).
6. RGI appliquées (1, 3 a, 3 b, 6…). Le texte est dans `knowledge-base/data/tarif_2016_sections.json` → `rgi`.
7. Décisions de classement liées (référence RTC, désignation, validité).
8. Mesures de la loi de finances 2026, s'il y en a.
9. Réserve : le tarif fourni est l'édition DGD 2016 (SH 2012). Un code SH 2017/2022 est donné avec sa ligne correspondante 2016.

L'utilisateur écrit en arabe : expliquer en arabe et garder les libellés officiels en français.

## 3. Vérifier la position déclarée d'un dossier
Les contrôles `TAR`, `DD` et `FAM` de `python -m visite controler` le font automatiquement :

| Contrôle | Question | Statut si écart |
|---|---|---|
| TAR-n | Le code existe-t-il au tarif ? | alerte si correspondance SH 2017, erreur si la position est absente |
| DD-n | La quotité DD déclarée est-elle égale au tarif ? | erreur sur une ligne exacte, alerte sur une correspondance |
| FAM-n | Le code du pays d'origine est-il de la même famille (même SH6) ? | alerte, avec le libellé des deux sous-positions |

Pour chaque alerte, ouvrir les deux fiches. Exemple : D10 en 3506.99 et export en 3506.91. On compare alors :
- la désignation, la FDS et la composition ;
- le libellé de chaque sous-position ;
- les notes de chapitre et la RGI 6 (comparaison au même niveau).

Puis on conclut quelle sous-position est la plus spécifique (RGI 3 a).

**Où va le résultat.** Les risques de classement (sous-position contestable, assortiment selon la note 3 de la section VI, etc.) se donnent **à l'utilisateur seul**, jamais dans la fiche destinée à l'inspecteur. La fiche n'affiche que la ligne « Classement (tarif douanier) » : section, chapitre, position.

## 4. Taux en vigueur et veille
- Le tarif de la base date de 2016. Quand le taux compte, chercher le code sur le web (`conformepro.dz <code>`), lire la page de la ligne (DD, TVA, TCS, PRCT) et comparer ; signaler tout écart comme « tarif 2016 ≠ taux publié (source tierce) ».
- `knowledge-base/data/veille_secondaire.json` : DAPS, contribution de solidarité, domiciliation, exonérations LF 2025, chaque fait avec sa source et le texte officiel à confirmer.
- Source officielle manquante : la nommer à l'utilisateur avec son lien (`knowledge-base/REFERENTIEL.md`) ; une fois téléchargée, `python knowledge-base/tools/ingest.py <fichier>`.

## 5. Toujours utiliser toutes les sources fournies
| Source (`knowledge-base/sources/`) | Données | Quand l'utiliser |
|---|---|---|
| Tarif douanier DGD 2016 | `tarif_2016.json`, `tarif_2016_notes.json`, `tarif_2016_sections.json` | tout code, DD, notes, RGI |
| Recueils des décisions de classement 2020 et 2025 | `decisions_classement_2020.json`, `decisions_classement_2025.json` | précédents de classement |
| Loi 25-17, loi de finances 2026 | `loi_finances_2026.json`, `mesures_tarifaires_lf2026.json` | taux modifiés, exonérations, conditions |
| Loi 17-04 (code des douanes) | `loi_17-04_code_douanes.json` | régime, procédure, valeur, origine, infractions |
| Décret exécutif 18-165 | `decret_18-165.json` | décisions anticipées (RTC, origine, valeur) |
| Guide EBTI (UE) | `text/ebti_general_information_en.txt` | méthode de description de la marchandise (case 9) |
| Rapport OMD « douanes intelligentes » | `text/smart-customs_public_report_fr_1.txt` | méthodes, gestion des risques |
