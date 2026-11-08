# CLAUDE.md — CustomsAgentPro

Instructions permanentes pour Claude Code dans ce dépôt. Elles s'appliquent à chaque session.

## Qui je suis
- **ABDEL HAKIM HADJALLAH**, déclarant en douane (Algérie). Ce nom et cette qualité figurent sur chaque document produit.
- Langues : je parle arabe et français. Documents destinés à la douane : **français**. Explications orales : **arabe** si je l'écris en arabe.
- Ne me dis pas « fais ceci / va vérifier » : fais toi-même la recherche, le calcul ou la vérification, et donne-moi le résultat.

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

## Règles de contenu
- Fiche **destinée à l'inspecteur** : langage clair et professionnel. Pas d'amendes, de scénarios de redressement ni de points faibles dans la fiche. Les risques (classement contestable, assurance, délais) se donnent **à moi seul**, à part.
- Toujours afficher le **pays d'origine**, la provenance, le certificat d'origine et le MRN.
- Valeur non issue du dossier : la marquer **« † indicatif »** (la FDS du fabricant fait foi). Référence externe : la citer (ex. fiches techniques KLEIBERIT).
- Dessin : porter la mention **« ILLUSTRATION »** ; jamais présenté comme une photo.
- Design : européen haut de gamme, sobre (bleu marine), modèle des fiches techniques des fabricants (Sika, Kleiberit). Fichiers légers, peu de pages.

## Confidentialité (obligatoire)
- `dossiers/` contient des données clients (NIF, RC, banque, montants). Il est exclu par `.gitignore` et **ne doit jamais être commité ni poussé**, même si on le demande en passant. Avant chaque `git push`, vérifier avec `git status` qu'aucun fichier client n'est suivi.
- Exemples et tests : uniquement des données fictives (`visite/exemples/`).

## Références officielles
`knowledge-base/` : tarif douanier, décisions de classement 2020 et 2025, loi 17-04 (code des douanes), décret 18-165, loi de finances 2026 (loi 25-17), guide EBTI. Les citer avant toute affirmation tarifaire ou réglementaire. Contrôle de conformité aux frontières : décret exécutif n° 05-467 du 10/12/2005.

## Commandes utiles
```bash
python -m unittest visite.tests.test_visite -v   # tests du moteur
python -m visite controler dossiers/X/dossier.json
python -m visite app dossiers/X/dossier.json     # application unique
```
