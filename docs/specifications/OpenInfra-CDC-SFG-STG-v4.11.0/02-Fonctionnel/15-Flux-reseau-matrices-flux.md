# Fonctionnel — Flux réseau, matrices de flux et segmentation

Ce document décline le volume V15 dans la vue fonctionnelle du dossier OpenInfra SFG/STG v4.

## Capacités utilisateur

| Fonctionnalité |
|---|
| modélisation source, destination, protocole, port, environnement, justification et durée de validité |
| comparaison flux déclarés et flux observés par NetFlow, sFlow, IPFIX, firewall logs et discovery applicative |
| détection des flux non autorisés, orphelins, expirés ou déclarés mais non observés |
| visualisation des flux par application, service, tenant, VRF, site et environnement |
| export contrôlé vers équipes firewall ou outils de sécurité externes |
| simulation d’impact avant modification firewall, segmentation ou migration |
| gestion des flux temporaires avec expiration et audit |
| corrélation flux ↔ dépendances applicatives ↔ IPAM ↔ certificats |

## Parcours métier principal

1. L’utilisateur authentifié ouvre le périmètre `FLOW`.
2. Le système applique tenant, RBAC, ABAC et filtres de confidentialité.
3. L’utilisateur consulte ou déclenche une opération contrôlée.
4. L’opération produit audit, métriques, événements et éventuels résultats asynchrones.
5. Les résultats sont consultables par API, UI, export asynchrone et matrice de traçabilité.

## Critères d’acceptation fonctionnels

| Critère |
|---|
| un flux déclaré contient source, destination, protocole, port, propriétaire et justification |
| les flux observés massifs sont stockés en tables partitionnées et agrégés |
| un export firewall volumineux est toujours asynchrone |
| un flux temporaire expiré devient non conforme sans suppression de l’historique |

## Interfaces minimales

- Vue liste avec filtres sélectifs et pagination.
- Fiche détail avec historique et audit.
- Vue qualité/conformité lorsque applicable.
- Action de job asynchrone lorsque le traitement peut être long.
- Exports filtrés et exports massifs asynchrones.
- Webhooks configurables.
