# Veille d'innovation — modèles étrangers étudiés, adoptés ou proposés

Chaque mois, on cherche ce que font de mieux les douanes et les déclarants des pays avancés (UE, Allemagne, Royaume-Uni, États-Unis, Chine, OMD). Ce qui sert notre travail est intégré au moteur `visite/` et noté ici.

Statuts : **adopté** (dans le moteur) · **proposé** (à décider) · **à surveiller**.

| Date | Modèle | Pays / organisme | Ce qu'il apporte | Statut | Où dans le moteur |
|---|---|---|---|---|---|
| 2026-11-09 | Liste des termes génériques refusés dans la désignation des marchandises (« Guidance on acceptable goods description », v4.10, 2021) | Commission européenne (DG TAXUD) | Une désignation doit dire nature, forme et usage : « pièces », « verre », « produits chimiques », « machines » seuls sont refusés | **adopté** | contrôle `DES-n` (`calc.designation_generique`) |
| 2026-11-09 | Structure des décisions de classement (Faits → Question → Textes et analyse → Décision) | Douane américaine (CBP, rulings CROSS) ; RTC de l'UE (EBTI) | Classement lisible et vérifiable par l'inspecteur | **adopté** | fiche, § 6 : « Question » et « Classement retenu » (`classement.question`, `classement.decision`) |
| 2026-11-09 | Empreinte numérique des documents (intégrité) | Pratique des documents électroniques européens | Toute modification des données change l'empreinte SHA-256 imprimée au pied de chaque page | **adopté** | `render.empreinte` |
| 2026-11-09 | SH 2028 : 299 séries d'amendements, en vigueur le 01/01/2028 | OMD | Vaccins 30.02 → 30.07 / 30.08 ; compléments alimentaires 21.07 ; déchets plastiques ; fournitures d'urgence sanitaire | **à surveiller** | veille C9 du dossier complet : dit si les chapitres du dossier sont cités |
| 2026-11-09 | Guichet unique électronique ALCES (autorisations et certificats) | Douane algérienne, avis du 18/08/2026 | Dépôt électronique des autorisations du ministère du Commerce par les commissionnaires | **à surveiller** | veille C9 ; à relier aux pièces `AUT` |
| 2026-11-09 | Passeport numérique des produits (DPP, règlement ESPR) — registre ouvert le 19/07/2026 | Union européenne | Identifiant unique par produit, consultable par les douanes ; utile pour les exportateurs algériens vers l'UE | **à surveiller** | — (piste de marché) |
| 2026-11-09 | Code QR sur la fiche (références D10, MRN, conteneur, empreinte) | Pratique des documents de transport européens | L'inspecteur lit les références au téléphone | **proposé** | nécessite le paquet `segno` (installation bloquée tant que l'accès réseau est coupé) |

## Sources
- Commission européenne, Guidance on acceptable goods description, v4.10, mars 2021 — https://info-aduaneiro.portaldasfinancas.gov.pt/pt/informacao_aduaneira/ICS2/Documents/guidance_acceptable_goods_description_V4.10_MAR2021_EN.pdf
- OMD, HS 2028 Amendments, janvier 2026 — https://www.wcoomd.org/en/media/newsroom/2026/january/hs-2028-amendments-adapting-the-harmonized-system-to-global-priorities-and-trade-evolution.aspx
- Algérie Eco, guichet unique électronique ALCES, 20/08/2026 — https://algerie-eco.com/2026/08/20/douanes-mis-en-service-dun-guichet-unique-electronique/
- CBP, Rulings (CROSS) — https://www.cbp.gov/trade/rulings
- Tilkal, registre DPP au 19/07/2026 — https://www.tilkal.com/post/the-eu-digital-product-passport-registry-is-coming-why-july-19th-2026-is-the-deadline-few-are-prep
