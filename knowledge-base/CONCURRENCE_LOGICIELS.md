# Logiciels de transit et plateformes portuaires — analyse comparative

Mise à jour : 2026-11-13. Sources secondaires (sites des éditeurs, presse) : chiffres des éditeurs non vérifiés.
Pour le déclarant seul. Sert à positionner nos outils (fiche de suivi véhicules, copie électronique par QR, moteur `visite/`).

## Trois familles (à ne pas confondre)

| Famille | Exemples | Client | Rôle |
|---|---|---|---|
| Logiciel de transitaire (SaaS) | GoFreight, Logitude World, CargoWise, Magaya | le transitaire | dossiers, cotations, facturation, portail client |
| Port Community System (PCS) | Portbase (Pays-Bas), APCS (Algérie) | toute la place portuaire | échange de messages entre armateurs, terminaux, douane, transitaires |
| Système douanier | ALCES (Algérie), ACE (États-Unis) | l'État | déclaration, liquidation, mainlevée |

## Fiches

| Produit | Structure | Prix | Forces | Faiblesses |
|---|---|---|---|---|
| GoFreight | SaaS navigateur, API REST, EDI armateurs, IA de lecture de documents incluse ; douane US (ABI : AES, ISF, AMS) et Japon | par utilisateur, non publié ; mise en place 4 à 8 semaines (éditeur) | rapide à déployer, comptabilité intégrée, IA, plus de 1 000 transitaires (éditeur) | douane limitée à l'Amérique du Nord et à l'Asie-Pacifique ; pas d'Algérie |
| Logitude World | SaaS, portail et appli mobile client, API à partir de 10 utilisateurs | 39 à 90 USD par utilisateur et par mois (3 formules) | prix publié et bas, suivi client inclus dès la formule Business | pas de module douane national ; API réservée aux grandes équipes |
| CargoWise (WiseTech) | suite mondiale tout-en-un, modules douane de nombreux pays | à la transaction depuis 12/2025 (selon GoFreight, source partiale) | couverture mondiale, profondeur fonctionnelle | 6 à 12 mois de mise en place, complexe, coût variable (selon GoFreight) |
| Portbase | PCS : écrans web + système à système, compte unique avec MFA, services par métier (Cargo Declaration Import, Notification Import Documentation, Cargo Controller, Secure Chain) | par service, non publié sur la page lue | une seule saisie réutilisée par tous les acteurs du port | ne couvre que les ports néerlandais ; ce n'est pas un outil de gestion du transitaire |

## Marché algérien

| Acteur | Ce que c'est | Limite |
|---|---|---|
| APCS (Serport, lancé le 14/06/2021) | PCS national ; circulaire Serport du 12/10/2025 : déclarations de chargement vers ALCES exclusivement par APCS | outil de place, pas de suivi par client final |
| ALCES (DGD) | système douanier | pas d'API ouverte aux transitaires connue |
| BlenyAI | logiciel de transitaire algérien avec IA : lecture des B/L (VIN, marque, conteneur), facturation, House B/L, suivi conteneurs ; sous-domaine par agence, 2FA | pas de D10 ni de portail client annoncés ; prix sur démonstration |
| ITHRYTEC (Alger) | TMS sur Odoo 17 : dossiers, B/L, CMR, marges, NIF/NIS/RC, FR/AR | orienté transport, pas dédouanement |
| Guefaifia Transit (Tébessa) | simulateur public de droits et taxes véhicules (moins de 3 ans, CCR, neuf), devis par WhatsApp | aucun suivi de dossier |

## Manques communs (notre place)
- aucun produit étranger ne connaît le D10, ALCES, les codes EPC/APC, le 846 ;
- le client final est une entreprise avec un compte : rien pour le particulier sans compte ;
- tout suppose la saisie à l'écran : rien pour le bureau qui travaille au papier ;
- en Algérie, personne n'annonce un suivi du véhicule par le client (du D10 au 846).

## Sources
- https://gofreight.com/blog/gofreight-platform-overview · https://gofreight.com/blog/cargowise-vs-gofreight
- https://logitudeworld.com/our-pricing
- https://support.portbase.com/en/starten-met-port-community-system-en
- https://www.nticweb.com/web/10055-serport-lance-une-plateforme-d-echanges-de-donnees-numeriques.html
- https://www.algerie360.com/les-ports-algeriens-passent-au-numerique-voici-ce-qui-change-pour-la-declaration-de-marchandises/
- https://blenyai.com/ · https://ithrytec.com/blog/tms-sur-odoo-la-solution-pour-digitaliser-le-transport-maritime-et-routier-en-algerie · https://guefaifia-transit.pages.dev/
