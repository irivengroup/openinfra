# Fonctionnel — GreenOps et capacité énergétique

Ce document décline le volume V21 dans la vue fonctionnelle du dossier OpenInfra SFG/STG v4.

## Capacités utilisateur

| Fonctionnalité |
|---|
| suivi consommation par site, salle, rack, PDU, équipement et application |
| modélisation PUE, coût énergétique et estimation carbone selon facteurs configurables |
| détection équipements zombies ou sous-utilisés |
| corrélation énergie ↔ coût ↔ capacité ↔ refroidissement ↔ criticité métier |
| prévision saturation énergie/refroidissement/espace/poids |
| suggestions de consolidation ou déplacement avec validation humaine |
| rapports GreenOps par tenant, site, application et période |
| traçabilité des hypothèses de calcul |

## Parcours métier principal

1. L’utilisateur authentifié ouvre le périmètre `GREEN`.
2. Le système applique tenant, RBAC, ABAC et filtres de confidentialité.
3. L’utilisateur consulte ou déclenche une opération contrôlée.
4. L’opération produit audit, métriques, événements et éventuels résultats asynchrones.
5. Les résultats sont consultables par API, UI, export asynchrone et matrice de traçabilité.

## Critères d’acceptation fonctionnels

| Critère |
|---|
| chaque estimation carbone indique facteur, source, période et périmètre |
| les mesures massives sont partitionnées et agrégées |
| les suggestions GreenOps ne déclenchent pas automatiquement de changement |
| les prévisions de capacité utilisent des données historisées traçables |

## Interfaces minimales

- Vue liste avec filtres sélectifs et pagination.
- Fiche détail avec historique et audit.
- Vue qualité/conformité lorsque applicable.
- Action de job asynchrone lorsque le traitement peut être long.
- Exports filtrés et exports massifs asynchrones.
- Webhooks configurables.
