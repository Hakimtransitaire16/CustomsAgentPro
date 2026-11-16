# Référentiel de classement — méthode et journal des cas

Ce fichier est utilisé à chaque question de classement et à chaque dossier (skill `position-tarifaire`, contrôle `RTC-n` du moteur).
Version de lecture en arabe pour le déclarant : doc « مرجع التصنيف التعريفي — حالات عملية » (https://claude.ai/artifact/LP9XfKNmqp2p5aQLYydprQ).
Aucune donnée client ici : produit, codes et sources seulement.

## 1. Hiérarchie des sources

| Rang | Source | Rôle | Fichier |
|---|---|---|---|
| 1 | Libellés des positions + notes de section et de chapitre | le droit | `data/tarif_2016.json`, `data/tarif_2016_notes.json` |
| 2 | RGI 1 à 6 | lecture des positions et des notes | `data/tarif_2016_sections.json` → `rgi` |
| 3 | Décisions RTC (recueils 2020, 2024, 2025) | application par la DGD à un produit donné | `data/decisions_classement_*.json` |
| 4 | Code des douanes (art. 50 ter, 89) et décret 18-165 | procédure : décisions anticipées, rectification | `data/textes/code-douanes-consolide.json`, `data/decret_18-165.json` |
| — | Code SH du fournisseur (facture, B/L) | avis commercial | n'engage pas la douane |

RGI = règles d'interprétation (méthode, valables pour tout produit). RTC = décision de renseignement tarifaire contraignant (un produit, un titulaire).

## 2. Méthode en 6 étapes

1. Identifier la marchandise par les pièces : nature, matière, fonction, appareil auquel elle est destinée.
2. Lister les positions candidates : position de la matière et position de la fonction. Une position « Autres … » est résiduelle.
3. RGI 1 : lire les notes de section et de chapitre de chaque candidate (« ne comprend pas », règles des parties et accessoires).
4. RGI 2 puis 3 si plusieurs positions restent : article incomplet ou non monté, position la plus spécifique, caractère essentiel.
5. RGI 6 : descendre niveau par niveau jusqu'à la ligne nationale ; DD du tarif.
6. Rechercher dans les recueils RTC une marchandise de même désignation, y compris dans d'autres chapitres (contrôle `RTC-n` du moteur).

Le classement se tranche **avant** l'exonération ou le régime fiscal, jamais l'inverse.

## 3. Décisions anticipées (décret 18-165)

| Texte | Contenu |
|---|---|
| Code des douanes, art. 50 ter | décisions anticipées sur le classement, l'origine et l'éligibilité à l'exonération, à la demande des tiers, avant l'opération |
| Décret 18-165, art. 2 | trois types : RTC (classement), RCO (origine), RCDT (éligibilité à l'exonération des droits et taxes) |
| art. 3 | contraignante pour la douane envers le **titulaire** seulement |
| art. 4 | valable 6 mois à compter de la notification, prorogée tacitement sauf dénonciation écrite |
| art. 5 | la marchandise déclarée doit correspondre « à tous égards » à celle de la décision |
| art. 14 | la décision est annexée au dossier de dédouanement à chaque opération |
| art. 15 | refus si la marchandise fait l'objet d'une vérification ou d'un recours |
| Code des douanes, art. 89 | une déclaration enregistrée ne peut plus être modifiée, sauf cas fixés par arrêté du ministre des finances (arrêté absent de la base) |

## 4. Règles à retenir

1. Les notes passent avant les libellés ; les titres n'ont qu'une valeur indicative (RGI 1).
2. « Autres ouvrages » est résiduel : il ne prend la marchandise que si aucune position plus spécifique ne la vise (RGI 3 a).
3. La fonction l'emporte sur la matière quand une note le dit (ch. 39, note 2 u).
4. La partie reconnaissable comme destinée à un instrument suit l'instrument (ch. 90, note 2 b).
5. Le code du fournisseur ne fait pas foi.
6. Les recueils RTC se consultent avant la déclaration.
7. Classement d'abord, exonération ensuite.

## 5. Journal des cas (le plus récent en premier)

| Date | Marchandise | Position déclarée | Position la plus probable | Sources décisives | Enjeu |
|---|---|---|---|---|---|
| 2026-11-14 | Mécanisme de dosage pour stylo injecteur d'insuline, présenté seul | 3926.90.99.90 (DD 30 %, exonéré régime 401) | 9018.39.99.00 (DD 5 %) | ch. 39 note 2 u) ; ch. 90 note 2 b) ; RGI 1, 2 a), 6 ; RTC 062/DGD du 10.12.2025 (stylo doseur non monté) | perte de l'exonération art. 39 LF 2001 (ch. 90 non cité) : DD + TVA exigibles |
