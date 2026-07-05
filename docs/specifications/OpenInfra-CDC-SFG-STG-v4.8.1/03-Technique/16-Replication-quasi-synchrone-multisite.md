# Réplication quasi synchrone et multisite

## Cluster automatique

En mode cluster, l'installateur backend doit configurer automatiquement la réplication PostgreSQL, la sélection des standbys, la synchronisation, la supervision et la bascule.

L'opérateur fournit uniquement les paramètres réseau minimaux déjà prévus : FQDN, IP, masque, VIP, passerelle et DNS.

## Mode quasi synchrone

Le mode quasi synchrone doit garantir qu'une transaction critique n'est confirmée que lorsque le WAL correspondant a été transmis à au moins un standby éligible dans le groupe de synchronisation.

Le mode recommandé par défaut est local-site quorum. Pour les déploiements multisites, la synchronisation stricte inter-sites n'est pas activée par défaut afin d'éviter les effets de latence WAN. Les réplicas distants peuvent être asynchrones, différés ou dédiés PRA selon la politique de l'entreprise.

## Modes supportés

| Mode | Usage | Cible |
|---|---|---|
| standalone | Lite ou Pro non cluster | simplicité |
| local_quasi_sync | Pro/Entreprise cluster local | RPO local quasi nul |
| strict_sync | Entreprise critique | cohérence maximale |
| multisite_dr_async | Entreprise DR | PRA inter-site |
| reporting_replica | Pro/Entreprise | reporting isolé |

## Multisite

Pro et Entreprise doivent supporter plusieurs sites. L'écart se situe sur le niveau de distribution :

- Pro : multisite centralisé sans clustering d'agents obligatoire.
- Entreprise : multisite distribué avec agents régionaux, clustering d'agents et planification régionale.
