# Fonctionnel — Kubernetes avancé et mapping cloud-native

Ce document décline le volume V23 dans la vue fonctionnelle du dossier OpenInfra SFG/STG v4.

## Capacités utilisateur

| Fonctionnalité |
|---|
| inventaire clusters, namespaces, nodes, workloads, pods, services, ingress, network policies et volumes |
| mapping pod → node → VM → hyperviseur → serveur → rack → salle |
| corrélation images, SBOM, certificats, secrets référencés et expositions externes |
| multi-cluster et clusters managés cloud |
| conformité labels, annotations, propriétaires et environnements |
| dépendances service mesh, ingress, load balancer et DNS |
| analyse capacité CPU/mémoire/stockage par cluster et namespace |
| détection dérives entre état attendu GitOps et état découvert |

## Parcours métier principal

1. L’utilisateur authentifié ouvre le périmètre `K8S`.
2. Le système applique tenant, RBAC, ABAC et filtres de confidentialité.
3. L’utilisateur consulte ou déclenche une opération contrôlée.
4. L’opération produit audit, métriques, événements et éventuels résultats asynchrones.
5. Les résultats sont consultables par API, UI, export asynchrone et matrice de traçabilité.

## Critères d’acceptation fonctionnels

| Critère |
|---|
| un workload est rattachable à son service métier, son image, ses flux et son infrastructure sous-jacente |
| les secrets Kubernetes sont référencés sans exposition de valeur |
| les clusters managés conservent compte, région et fournisseur |
| les données volumineuses de pods et événements sont bornées et partitionnées |

## Interfaces minimales

- Vue liste avec filtres sélectifs et pagination.
- Fiche détail avec historique et audit.
- Vue qualité/conformité lorsque applicable.
- Action de job asynchrone lorsque le traitement peut être long.
- Exports filtrés et exports massifs asynchrones.
- Webhooks configurables.
