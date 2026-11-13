# Programme du commissionnaire en douane — 14 modules

Source : Chambre de Commerce et d'Industrie IGILGILI (Jijel), ministère du Commerce — dépliant « Commissionnaire en douane, modules de formation » (`sources/programme_formation_commissionnaire_cci_igilgili.pdf`). Durée : 12 mois, jeudi et samedi.

**Cadre légal** : Décret exécutif n° 10-288 du 14/11/2010 : l'agrément exige un diplôme universitaire (spécialités juridiques, économiques, commerciales et financières), une formation de commissionnaire en douane réussie dans une école publique ou privée agréée par l'État (programmes certifiés par arrêté conjoint des ministres des finances et de la formation professionnelle) et la réussite au concours d'accès organisé par la DGD (texte de la base, data/textes/decret-10-288.json).

Chaque question est rattachée à son module par le moteur (`moteur.modules`), qui dit ce qui est en base et ce qui manque.

| N° | Module | En base | À télécharger | Dans le moteur |
|---|---|---|---|---|
| 1 | Organisation et fonctionnement de l'administration des douanes ; activité du commissionnaire en douane (droits et obligations) | ◐ decret-10-288; code-douanes-consolide (art. 78 : qui déclare); loi-17-04 | Texte d'organisation de l'administration centrale et des services extérieurs de la DGD (à identifier) | pieces_dossier.json (mandat, agrément) ; règles de CLAUDE.md |
| 2 | Procédures de dédouanement | ◐ code-douanes-consolide (art. 54 manifeste, 71 et 76 délais, 75 et 82 déclaration en détail, 83 articles, 92 mainlevée et vérification); guide-regimes; guide-controle-frontieres | circulaire-419 | flux complet du dossier, contrôles DAT, pièces manquantes, fiche de visite |
| 3 | Régimes douaniers | ◐ guide-regimes; code-douanes-consolide | circulaire-157 (admission temporaire); entrepot-129-164 | régime de la case 1 et régime fiscal (case 38) lus sur le D10 |
| 4 | Contentieux douanier | ◐ code-douanes-consolide (constatation des infractions art. 241 et 250 ; titre du contentieux) | Texte fixant les modalités de la transaction douanière (à identifier) | note de risques (déclarant seul) ; jamais d'amende dans la fiche du service |
| 5 | Système harmonisé de codification et de désignation des marchandises | ◐ tarif-2016; correlation-sh2022; tarif-maj-2020; rtc-2025; rtc-2024; rtc-2020; decret-18-165; ebti | Notes explicatives du SH (OMD); Tables de corrélation SH 2022 → SH 2028 (à paraître); omd-correlation-2017-2022 | python -m visite tarif ; contrôles TAR, DD, FAM, DES ; classement au format décision |
| 6 | Les assurances | ◐ code-douanes-consolide (art. 16 octies § 1 e : assurance dans la valeur) | Ordonnance n° 95-07 du 25/01/1995 relative aux assurances, modifiée | contrôle VAL-4 (assurance déclarée) ; pièce ASS |
| 7 | Fiscalité douanière ; origine des marchandises ; valeur en douane | ◐ code-tca; lf-2026; lfc-2018; daps-arrete-2019; guide-valeur; manuel-origine; manuel-origine-ue | lf-2025; code-impots-indirects; daps-arrete-2019-mod; rco | liquidation (CS, DD, TVA, RPS, DAPS), exonérations, contrôles VAL et ORI, analyse 360° |
| 8 | Commerce international | ◐ veille_secondaire.json (PPI, domiciliation, MACF) | Incoterms® 2020 (Chambre de commerce internationale, publication payante); Textes du ministère du Commerce extérieur sur le programme prévisionnel d'importation | incoterm et ajustements de la valeur ; rôle des parties ; analyse de marché mensuelle |
| 9 | Techniques bancaires | ✗ — | ba-reglement-07-01; ba-instruction-01-2026; ba-reglement-26-02; RUU 600 — crédit documentaire (Chambre de commerce internationale, publication payante) | domiciliation (contrôle DAT-1), change et sensibilité (analyse 360°) |
| 10 | Droit maritime | ✗ — | Ordonnance n° 76-80 du 23/10/1976 portant code maritime, modifiée | B/L, avis d'arrivée, surestaries selon le barème de l'armateur |
| 11 | Droit civil | ✗ — | Ordonnance n° 75-58 du 26/09/1975 portant code civil, modifiée | — |
| 12 | Droit commercial | ✗ — | Ordonnance n° 75-59 du 26/09/1975 portant code de commerce, modifiée | RC des parties, commissionnaire personne morale |
| 13 | Droit pénal | ✗ — | Ordonnance n° 66-156 du 08/06/1966 portant code pénal, modifiée | — |
| 14 | Anglais technique | ✅ ebti (anglais); glossaire_douane.json | — | lecture des factures, B/L et certificats en anglais ; glossaire FR / EN / AR |

✅ couvert · ◐ partiel · ✗ aucun texte en base : réponse limitée aux principes, sans citer d'article.
