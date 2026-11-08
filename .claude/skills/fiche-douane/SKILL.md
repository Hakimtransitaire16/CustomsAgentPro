---
name: fiche-douane
description: Flux complet d'un dossier de visite douane, du scan à la fiche technique et à l'application unique. À utiliser à « شغل التحليل الجمركي », « analyse ce dossier », ou dès qu'un dossier scanné (D10, facture, B/L, BAD, certificat d'origine) est fourni.
argument-hint: "[chemin du PDF scanné]"
---

# Fiche douane — du scan à la livraison

On lance immédiatement, sans poser de questions. Si une information manque, on annonce en une ligne l'hypothèse retenue. Documents en **français**. Explications à l'utilisateur en **arabe** s'il écrit en arabe.

## 0. Préparer
- Id du dossier : `AAAA-MM-PRODUIT-D10` (année-mois de la D10, produit principal, 6 derniers caractères de la D10).
- `mkdir -p dossiers/<id>` puis y copier le PDF scanné. Le scan n'est **jamais modifié**.
- Partir de `visite/exemples/dossier_exemple.json` (fictif) et vider les valeurs.

## 1. Lire le scan
- `python -m visite extraire dossiers/<id>/dossier.json` donne les suggestions OCR (sortie : `sortie/suggestions.json`).
- Ouvrir chaque page à **300 dpi minimum**, puis zoomer à 600 dpi sur chaque référence.
- Transcrire **caractère par caractère** :
  - D10 : N°, date-heure, bureau, **MRN (case 29)**, cases 20, 21, 25, 32, 36, 37·38, 39, 40, 41, 42, 43, 44, 45, 55–58 ;
  - BAD : N° Gros (avec suffixe « CS »), localisation, escale ;
  - B/L : conteneur, scellé, navire, voyage ;
  - importateur : NIF, RC, code fiscal, agrément ;
  - domiciliation, facture, montants, taux ;
  - certificat d'origine, déclaration d'export, code du pays d'origine.
- Pièges : I / 1, O / 0, nombre de zéros, suffixes. Le conteneur n'est **jamais** le numéro du dossier.
- Remplir `references_scan` avec `zone` (page, x, y, l, h en fraction de page) pour chaque référence.

## 2. Classer et vérifier la position — skill `position-tarifaire`
- `python -m visite tarif dossiers/<id>/dossier.json` : section, chapitre, position, ligne, DD, notes, LF 2026 et décisions pour chaque article.
- La position déclarée doit exister au tarif, avoir la bonne quotité DD et être de la même famille que le code du pays d'origine (contrôles TAR, DD, FAM).
- Toute divergence est expliquée **à l'utilisateur seul** ; elle ne va pas dans la fiche.

## 3. Décrire la marchandise (modèle européen, EBTI case 9)
Pour chaque article, `description` contient :
- `definition`, `nature`, `presentation`, `fonction` ;
- `usages`, `n_est_pas`, `identification` (listes).

On remplit aussi `technique` et `visite` (lieu, inspecteur, agent).
- Une valeur qui ne vient pas du dossier porte **« † indicatif »** (la FDS du fabricant fait foi).
- Une référence externe est citée.
- Un dessin porte **« ILLUSTRATION »**.

## 4. Produire
```bash
python -m visite tout dossiers/<id>/dossier.json
```
Critères de sortie :
- **0 erreur** aux contrôles, et chaque alerte expliquée ;
- fidélité ≥ 95 % pour chaque référence, sinon contrôle visuel de l'extrait (`sortie/extraits/`) ;
- relecture : toutes les références présentes et **aucun nombre inconnu** ;
- mise en page sans débordement.

## 5. Vérification indépendante
Lancer le sous-agent **`verificateur`** sur `dossiers/<id>/`. Corriger chaque écart qu'il signale, puis relancer l'étape 4 jusqu'au verdict `CONFORME`.

## 6. Livrer
- `sortie/Dossier_<id>.html` (application unique : fiche, visite, contrôles, registre, données) ;
- `sortie/Fiche_technique_<id>.pdf` ;
- registre mis à jour (`dossiers/registre/`) ;
- `sortie/Note_risques_<id>.md` (produite par `tout`) : base de la note de risques donnée à l'utilisateur seul.

Ajouter une ligne à `dossiers/INDEX.md` : date, dossier, fichiers produits. Envoyer les fichiers à l'utilisateur.

Séparément, **à l'utilisateur seul**, une note de risques : classement, assurance, délais, origine, pièces manquantes.

## Interdits
- Pas d'amendes, de scénarios de redressement ni de points faibles dans la fiche de l'inspecteur.
- Rien de `dossiers/` dans git. Le hook `.claude/hooks/garde_donnees_clients.py` bloque `git add`, `commit` et `push` ; ne jamais le contourner.
