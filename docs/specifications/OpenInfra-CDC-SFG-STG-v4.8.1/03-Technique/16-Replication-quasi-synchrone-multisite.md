# Synchronisation quasi temps réel et multisite

## Cluster automatique

En mode cluster, l'installateur backend doit configurer automatiquement la réplication PostgreSQL, la sélection des standbys, la synchronisation, la supervision et la bascule.

L'opérateur fournit uniquement les paramètres réseau minimaux déjà prévus : FQDN, IP, masque, VIP, passerelle et DNS.

## Mode quasi temps réel

Le mode quasi temps réel doit garantir une transmission continue du WAL vers au moins un standby éligible, avec surveillance du lag et alerte en cas de dépassement de seuil. La confirmation applicative reste locale par défaut afin de ne pas bloquer les écritures sur l'attente d'un rejeu distant.

Le mode recommandé par défaut est le streaming PostgreSQL faible latence avec commit local non bloquant. Pour les déploiements multisites, la synchronisation stricte inter-sites n'est pas activée par défaut afin d'éviter les effets de latence WAN. Les réplicas distants peuvent être asynchrones, différés ou dédiés PRA selon la politique de l'entreprise.

## Modes supportés

| Mode | Usage | Cible |
|---|---|---|
| standalone | Lite ou Pro non cluster | simplicité |
| near_real_time_streaming | Pro/Entreprise cluster local | RPO local très faible, mesuré par lag WAL |
| strict_sync | Option future Entreprise critique après validation architecture | cohérence maximale au prix de la latence |
| multisite_dr_async | Entreprise DR | PRA inter-site |
| reporting_replica | Pro/Entreprise | reporting isolé |

## Multisite

Pro et Entreprise doivent supporter plusieurs sites. L'écart se situe sur le niveau de distribution :

- Pro : multisite centralisé sans agents/proxy collectors distribués ; les backends servers collectent directement.
- Entreprise : multisite distribué avec agents proxy collectors régionaux Enterprise, clustering de collectors et planification régionale.

## Complément v0.29.10 — Déduction depuis les scopes installateur

La synchronisation quasi temps réel PostgreSQL est déduite du scope `server` et de `identity.peer_nodes`. Le fichier `install.ini` ne doit pas exposer les ports de réplication ni les paramètres `wal_level`, `archive_mode`, `synchronous_commit` ou `paramètres de standby bloquant`. L'installateur les rend en configuration interne contrôlée.
