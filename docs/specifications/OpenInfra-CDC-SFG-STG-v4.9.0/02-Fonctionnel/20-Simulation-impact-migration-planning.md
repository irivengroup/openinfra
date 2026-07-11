# Fonctionnel — Simulation, analyse d’impact et migration planning

Ce document décline le volume V20 dans la vue fonctionnelle du dossier OpenInfra SFG/STG v4.

## Capacités utilisateur

| Fonctionnalité |
|---|
| simulation déplacement, ajout, retrait ou coupure d’équipement |
| simulation changement VLAN, VRF, subnet, DNS, firewall ou PDU |
| analyse d’impact sur dépendances, flux, IPAM, énergie, refroidissement, coût et service métier |
| création de groupes de migration par affinité technique et métier |
| readiness score par application, actif, subnet ou site |
| planning de vagues de migration avec contraintes et dépendances bloquantes |
| rapport avant/après et comparaison de scénarios |
| aucune exécution de changement sans intégration externe explicitement configurée |

## Parcours métier principal

1. L’utilisateur authentifié ouvre le périmètre `SIM`.
2. Le système applique tenant, RBAC, ABAC et filtres de confidentialité.
3. L’utilisateur consulte ou déclenche une opération contrôlée.
4. L’opération produit audit, métriques, événements et éventuels résultats asynchrones.
5. Les résultats sont consultables par API, UI, export asynchrone et matrice de traçabilité.

## Critères d’acceptation fonctionnels

| Critère |
|---|
| un scénario de simulation ne modifie jamais les données de production |
| un rapport d’impact référence les objets, relations et hypothèses utilisés |
| les vagues de migration respectent dépendances et contraintes déclarées |
| les résultats sont versionnés et comparables dans le temps |

## Interfaces minimales

- Vue liste avec filtres sélectifs et pagination.
- Fiche détail avec historique et audit.
- Vue qualité/conformité lorsque applicable.
- Action de job asynchrone lorsque le traitement peut être long.
- Exports filtrés et exports massifs asynchrones.
- Webhooks configurables.
