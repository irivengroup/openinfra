# Fonctionnel — Gouvernance de la donnée et sources autoritatives

Ce document décline le volume V13 dans la vue fonctionnelle du dossier OpenInfra SFG/STG v4.

## Capacités utilisateur

| Fonctionnalité |
|---|
| définition des propriétaires fonctionnels et techniques par domaine de données |
| déclaration des sources autoritatives par objet, attribut, tenant, site et environnement |
| priorisation des sources avec score de confiance, score de fraîcheur et score de complétude |
| certification périodique des données critiques |
| gel contrôlé des objets critiques pendant opérations sensibles |
| règles de fusion, déduplication et résolution de conflit |
| journalisation des décisions de gouvernance et des exceptions |
| tableaux de bord de gouvernance par domaine, site, tenant et criticité |

## Parcours métier principal

1. L’utilisateur authentifié ouvre le périmètre `GOV`.
2. Le système applique tenant, RBAC, ABAC et filtres de confidentialité.
3. L’utilisateur consulte ou déclenche une opération contrôlée.
4. L’opération produit audit, métriques, événements et éventuels résultats asynchrones.
5. Les résultats sont consultables par API, UI, export asynchrone et matrice de traçabilité.

## Critères d’acceptation fonctionnels

| Critère |
|---|
| un attribut critique ne peut pas être déclaré sans règle de source autoritative |
| toute résolution de conflit est historisée avec acteur, preuve et justification |
| les campagnes de certification produisent un rapport exploitable par API et export |
| les scores de confiance et de fraîcheur sont calculés de manière déterministe |

## Interfaces minimales

- Vue liste avec filtres sélectifs et pagination.
- Fiche détail avec historique et audit.
- Vue qualité/conformité lorsque applicable.
- Action de job asynchrone lorsque le traitement peut être long.
- Exports filtrés et exports massifs asynchrones.
- Webhooks configurables.
