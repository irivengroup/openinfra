# Installateur OpenInfra Entreprise — serveur

Ce scope installe un nœud backend Entreprise, PostgreSQL géré et toutes les migrations backend. Il active exclusivement `openinfra.service` et prend en charge le multisite et la réplication quasi temps réel.

## Préconditions

- inventaire FQDN, IP, masque, VIP, passerelle, DNS et nœuds pairs validé ;
- volume group `datavg` disponible pour `openinfradata_lv` de 1TB ;
- certificats TLS 1.3/mTLS, CA et clés privées disponibles par référence ;
- secrets PostgreSQL injectés par variables d'environnement ;
- quorum et prérequis de réplication vérifiés.

## Résultat attendu

L'installateur prépare `/opt/openinfra/`, `/data/openinfra/`, `/opt/openinfra/data -> /data/openinfra/`, initialise `PGDATA`, applique toutes les migrations backend, configure les pairs et active `openinfra.service` derrière la VIP.

## Validation et rollback

Le dry-run contrôle le stockage, le réseau, la sécurité, le quorum et le plan de migrations. Une défaillance bloque l'activation et déclenche la restauration de configuration ; les données PostgreSQL et sauvegardes ne sont jamais supprimées automatiquement.
