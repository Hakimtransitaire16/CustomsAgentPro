# CLAUDE.md — CustomsAgentPro

Instructions permanentes pour Claude Code dans ce dépôt. Elles s'appliquent à chaque session.

## Qui je suis
- **ABDEL HAKIM HADJALLAH**, déclarant en douane (Algérie). Ce nom et cette qualité figurent sur chaque document produit.
- Langues : je parle arabe et français. Documents destinés à la douane : **français**. Explications orales : **arabe** si je l'écris en arabe.
- Ne me dis pas « fais ceci / va vérifier » : fais toi-même la recherche, le calcul ou la vérification, et donne-moi le résultat.
- Sois mon partenaire : travaille de bout en bout sans attendre mes consignes, repère toi-même ce qui manque (sources, contrôles, risques) et fais ce qui sert mon intérêt. Seules les actions irréversibles ou qui engagent des tiers attendent mon accord.

## Commande récurrente
Quand j'écris **« شغل التحليل الجمركي »** (ou « analyse ce dossier ») avec un dossier scanné : lance immédiatement le flux ci-dessous, sans poser de questions, et annonce en une ligne l'hypothèse retenue si une information manque.

## Flux de travail d'un dossier (moteur `visite/`)
1. Créer `dossiers/<AAAA-MM-PRODUIT-D10>/` et y placer le PDF scanné (ne jamais le modifier).
2. `python -m visite extraire` sur un `dossier.json` minimal pour obtenir les suggestions OCR.
3. Lire chaque page à **300 dpi minimum**, en zoomant sur chaque référence. Transcrire **caractère par caractère** dans `dossier.json` (schéma : `visite/schema/dossier.schema.json`) :
   N° D10, date-heure, bureau, **MRN (manifeste, case 29)**, N° Gros du BAD, conteneur, scellé, B/L, navire, voyage, escale, localisation, NIF, RC, code fiscal, agrément, domiciliation, facture, montants, taux, valeur DA, codes SH, poids, colis, certificat d'origine, déclaration d'export.
   Pièges : lettre **I** et chiffre **1**, nombre de **zéros**, suffixes (ex. « CS » du N° Gros). Le numéro de conteneur n'est **jamais** le numéro du dossier.
4. Remplir `references_scan` (avec `zone` quand c'est possible), la description des articles (modèle européen : définition, nature, présentation, fonction, usages, ce qu'elle n'est pas, identification à la visite), `technique`, `visite` (lieu, inspecteur, agent).
5. `python -m visite tout dossiers/<...>/dossier.json`. Ce qui doit en sortir :
   - **0 erreur** aux contrôles ; chaque alerte est expliquée ;
   - fidélité ≥ 95 % de chaque référence, sinon contrôle visuel de l'extrait ;
   - relecture : toutes les références présentes et **aucun nombre inconnu** ;
   - aucun débordement de mise en page.
6. Livrer : `Dossier_<id>.html` (application unique), `Fiche_technique_<id>.pdf`, registre mis à jour.
7. Ajouter une ligne à `dossiers/INDEX.md` (date, dossier, fichiers produits).

## Ce qui manque : le dire et le demander (obligatoire)
- Je connais les pièces d'un dossier, leur émetteur, ce qu'elles prouvent en douane et leur texte : `knowledge-base/data/pieces_dossier.json` (D10, facture, colisage, B/L, avis d'arrivée, BAD, transfert, domiciliation, certificat d'origine, assurance, mandat, fiche technique, FDS, programme MIPH, autorisations).
- `python -m visite tout` termine par **« À DEMANDER AU DÉCLARANT »** (fichier `A_fournir_<id>.md`, page C8 du dossier complet) : pièces absentes, informations de visite (lieu, inspecteur, agent, date) et hypothèses.
- **Chaque réponse qui livre un dossier finit par cette liste**, en clair, avec pour chaque élément : quoi, qui l'émet, pourquoi il compte. Je la redemande tant qu'elle n'est pas complète.
- Je ne remplis **jamais** une information de visite (lieu, inspecteur, agent, date) par supposition. Si je dois retenir une hypothèse ailleurs, je l'inscris dans `meta.hypotheses` (ex. `"visite.lieu"`) : elle sort alors dans la liste « à confirmer ».
- Lieux de visite connus : Port sec TERPORR, Entrepôt EPMA.

## Règles de contenu
- Fiche **destinée à l'inspecteur** : langage clair et professionnel. Pas d'amendes, de scénarios de redressement ni de points faibles dans la fiche. Les risques (classement contestable, assurance, délais) se donnent **à moi seul**, à part.
- Toujours afficher le **pays d'origine**, la provenance, le certificat d'origine et le MRN.
- Valeur non issue du dossier : la marquer **« † indicatif »** (la FDS du fabricant fait foi). Référence externe : la citer (ex. fiches techniques KLEIBERIT).
- Dessin : porter la mention **« ILLUSTRATION »** ; jamais présenté comme une photo.
- Design : européen haut de gamme, sobre (bleu marine), modèle des fiches techniques des fabricants (Sika, Kleiberit). Fichiers légers, peu de pages.

## Confidentialité (obligatoire)
- `dossiers/` contient des données clients (NIF, RC, banque, montants). Il est exclu par `.gitignore` et **ne doit jamais être commité ni poussé**, même si on le demande en passant. Avant chaque `git push`, vérifier avec `git status` qu'aucun fichier client n'est suivi.
- Exemples et tests : uniquement des données fictives (`visite/exemples/`).

## Un seul moteur (automatique)
Toutes les sources fonctionnent ensemble, en une seule passe ; on ne désigne jamais un fichier à la main.
- **À chaque message** qui touche la douane, le hook `contexte_auto.py` lance le moteur et ajoute au contexte ce que disent toutes les sources (codes, articles, thèmes, désignations ; arabe compris). La réponse s'appuie sur ce contexte et le cite.
- **Toute question** : `python -m visite demande "<question, code, désignation ou article>"`. Le moteur :
  - lit la demande (codes SH, articles, thèmes ; arabe traduit en termes douaniers) ;
  - consulte en une fois le tarif (2016, 2020, SH 2022, LF 2026, DAPS), les notes et les RGI, les décisions de classement, le code des douanes consolidé, les lois de finances, les décrets, les guides et la veille ;
  - répond avec chaque source citée.
- **Tout dossier** : `python -m visite tout` fait aussi le classement, les taux, le DAPS et la TVA, puis écrit `Note_risques_<id>.md` (pour moi seul : alertes expliquées + textes applicables).
- **Base toujours à jour** : un PDF déposé dans `knowledge-base/inbox/` est intégré à la commande suivante, et l'index se reconstruit seul quand les données changent.

## Sources de travail (obligatoires)
Toutes les sources que j'ai fournies sont dans `knowledge-base/`. Elles servent **à chaque réponse** tarifaire, réglementaire ou de classement, et pas seulement le tarif. On cite la source (document, section, note, article) avant toute affirmation.

| Source | Données | Usage |
|---|---|---|
| Tarif douanier DGD 2016 | `data/tarif_2016*.json` (lignes, notes de chapitres, sections, RGI) | section, chapitre, position, libellé, notes, DD |
| Mise à jour du tarif 2020 (DGD) | `data/tarif_maj_2020.json` (923 lignes) | DD, TVA, autres taxes, formalités (FAP) |
| Table de corrélation SH 2022 (DGD) | `data/correlation_sh2022.json` (1 137 lignes, 1 113 correspondances) | codes en vigueur depuis 2022, DD, TVA, ancien ↔ nouveau |
| Arrêté DAPS du 26/01/2019 + LFC 2018 (loi 18-13) | `data/daps_2019.json` (1 095 lignes) | DAPS par ligne (liste initiale, à vérifier) |
| Recueils des décisions de classement 2020, 2024 et 2025 | `data/decisions_classement_*.json` (294 décisions) | précédents RTC |
| Code des douanes consolidé (loi 79-07 modifiée) | `data/textes/code-douanes-consolide.json` (449 articles) | tous les articles en vigueur |
| Code des TCA (TVA, édition 2017) | `data/textes/code-tca.json` | taux 19 % / 9 %, exonérations |
| Décret exécutif 10-288 | `data/textes/decret-10-288.json` | commissionnaire et déclarant : agrément, obligations |
| Guides DGD : valeur, origine, origine UE, régimes économiques ; guide du contrôle aux frontières (Commerce) ; annexes du tarif 2020 | index de recherche | méthodes et procédures |
| Loi de finances 2026 (loi 25-17) | `data/loi_finances_2026.json`, `data/mesures_tarifaires_lf2026.json` | taux modifiés, exonérations, conditions |
| Code des douanes (loi 17-04) | `data/loi_17-04_code_douanes.json` | procédure, valeur, origine, régimes |
| Décret exécutif 18-165 | `data/decret_18-165.json` | décisions anticipées |
| Guide EBTI (UE) | `text/ebti_general_information_en.txt` | description de la marchandise |
| Rapport OMD « douanes intelligentes » | `text/smart-customs_public_report_fr_1.txt` | méthodes, gestion des risques |

Contrôle de conformité aux frontières : décret exécutif n° 05-467 du 10/12/2005.

Le catalogue complet des sources (47 références, statut, lien officiel) est `knowledge-base/REFERENTIEL.md`. Les sites officiels (douane.gov.dz, commerce.gov.dz, mfdgi.gov.dz, OMD) refusent la lecture automatique : je télécharge les fichiers moi-même, puis
`python knowledge-base/tools/ingest.py <dossier ou fichiers>` les identifie, extrait le texte (OCR si scan), les structure, les indexe et met le référentiel à jour. Un extrait ne remplace jamais une version complète déjà présente.

Faits tirés de sources secondaires (presse, cabinets, administrations étrangères) : `data/veille_secondaire.json`, avec source et date. Ils restent « à confirmer » tant que le texte officiel n'est pas dans la base.

### Règles de recherche
- **Question sur une position** : `python -m visite tarif <code> [--notes]`. On répond avec la section, le chapitre, la position (libellé), la ligne nationale (DD), la définition et les notes applicables, les RGI, les décisions liées et les mesures LF 2026. Skill : `position-tarifaire`.
- **Dossier reçu** : vérifier que la position déclarée existe au tarif, que sa quotité DD est la bonne et qu'elle est **de la même famille** que le code du pays d'origine (contrôles TAR, DD, FAM). Toute divergence est expliquée à moi seul.
- **Recherche libre** : `cd knowledge-base && python tools/kb.py search "<mots>"` (tous les documents), `kb.py article <n>`.
- Tarif fourni = édition 2016 (SH 2012). Un code SH 2017/2022 est donné avec sa ligne 2016 correspondante, et on le signale.
- Taux en vigueur : quand le taux compte (liquidation, litige), comparer avec la ligne publiée sur conformepro.dz (recherche web du code, source tierce non officielle) et signaler tout écart avec le tarif 2016.
- Chaque nouvelle source téléchargée passe par `ingest.py` le jour même ; une réponse ne cite jamais une source qui n'a pas été lue.

## Outils Claude Code du dépôt
- Skill `fiche-douane` : flux complet d'un dossier (déclenché par « شغل التحليل الجمركي »).
- Skill `position-tarifaire` : recherche et vérification de classement.
- Sous-agent `verificateur` : relit le scan sans se fier à la transcription, recalcule et contrôle le classement. Il est lancé avant chaque livraison.
- Hook `.claude/hooks/garde_donnees_clients.py` : bloque tout `git add`, `commit` ou `push` de données clients.
- Hook `.claude/hooks/contexte_auto.py` : à chaque message, consulte toutes les sources et les injecte dans le contexte.

## Commandes utiles
```bash
python -m unittest visite.tests.test_visite -v   # tests du moteur
python -m visite controler dossiers/X/dossier.json
python -m visite app dossiers/X/dossier.json     # application unique
python -m visite tarif 3506.99.90.00 --notes     # fiche de position tarifaire
python -m visite tarif dossiers/X/dossier.json   # classement de chaque article
python -m visite demande "question libre"        # moteur unique : toutes les sources
python -m visite risques dossiers/X/dossier.json # note de risques (déclarant seul)
```
