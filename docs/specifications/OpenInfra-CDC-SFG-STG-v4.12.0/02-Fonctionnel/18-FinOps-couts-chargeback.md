# Fonctionnel — FinOps, coûts, showback et chargeback

Ce document décline le volume V18 dans la vue fonctionnelle du dossier OpenInfra SFG/STG v4.

## Capacités utilisateur

| Fonctionnalité |
|---|
| import des coûts cloud, SaaS, datacenter, énergie, licences, support et contrats |
| allocation par actif, application, service métier, tenant, propriétaire, tag et centre de coût |
| showback et chargeback configurable |
| budgets, prévisions, anomalies et tendances |
| coût par environnement et coût par dépendance applicative |
| corrélation coût ↔ capacité ↔ consommation ↔ criticité |
| rapports exécutifs et exports financiers contrôlés |
| gestion des règles d’allocation et des exceptions |

## Parcours métier principal

1. L’utilisateur authentifié ouvre le périmètre `FINOPS`.
2. Le système applique tenant, RBAC, ABAC et filtres de confidentialité.
3. L’utilisateur consulte ou déclenche une opération contrôlée.
4. L’opération produit audit, métriques, événements et éventuels résultats asynchrones.
5. Les résultats sont consultables par API, UI, export asynchrone et matrice de traçabilité.

## Critères d’acceptation fonctionnels

| Critère |
|---|
| chaque coût importé conserve source, période, devise, propriétaire et méthode d’allocation |
| les rapports financiers sont reproductibles pour une période clôturée |
| les coûts non attribuables sont isolés dans un bucket de qualité financière |
| les imports de coûts volumineux sont asynchrones et traçables |

## Interfaces minimales

- Vue liste avec filtres sélectifs et pagination.
- Fiche détail avec historique et audit.
- Vue qualité/conformité lorsque applicable.
- Action de job asynchrone lorsque le traitement peut être long.
- Exports filtrés et exports massifs asynchrones.
- Webhooks configurables.
