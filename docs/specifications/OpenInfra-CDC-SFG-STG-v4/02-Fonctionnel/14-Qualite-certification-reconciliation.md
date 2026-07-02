# Fonctionnel — Qualité, certification et réconciliation des données

Ce document décline le volume V14 dans la vue fonctionnelle du dossier OpenInfra SFG/STG v4.

## Capacités utilisateur

| Fonctionnalité |
|---|
| détection des doublons, orphelins, valeurs manquantes et incohérences inter-domaines |
| moteur de règles de qualité configurable par domaine et criticité |
| score qualité global et score qualité par objet |
| réconciliation multi-sources avec seuils de confiance |
| gestion des exceptions justifiées avec expiration |
| rapports de qualité par tenant, site, application et propriétaire |
| correction en lot avec prévisualisation et rollback |
| historique time travel des campagnes qualité |

## Parcours métier principal

1. L’utilisateur authentifié ouvre le périmètre `DQ`.
2. Le système applique tenant, RBAC, ABAC et filtres de confidentialité.
3. L’utilisateur consulte ou déclenche une opération contrôlée.
4. L’opération produit audit, métriques, événements et éventuels résultats asynchrones.
5. Les résultats sont consultables par API, UI, export asynchrone et matrice de traçabilité.

## Critères d’acceptation fonctionnels

| Critère |
|---|
| chaque finding possède une preuve, une criticité, une règle source et un statut |
| la correction de masse exige un dry-run et un rapport avant application |
| une exception qualité a une justification, une portée et une date d’expiration |
| les écarts IPAM/DNS/DHCP sont visibles dans un tableau de bord dédié |

## Interfaces minimales

- Vue liste avec filtres sélectifs et pagination.
- Fiche détail avec historique et audit.
- Vue qualité/conformité lorsque applicable.
- Action de job asynchrone lorsque le traitement peut être long.
- Exports filtrés et exports massifs asynchrones.
- Webhooks configurables.
