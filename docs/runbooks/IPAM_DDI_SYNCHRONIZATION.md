# Synchronisation transactionnelle IPAM vers DNS/DHCP — OpenInfra 0.34.24

## Objet

La commande `ipam ddi-sync` applique une réservation IPAM existante aux fournisseurs DNS/DHCP configurés. Elle exécute une saga durable et idempotente : chaque état fournisseur est lu avant mutation, chaque effet est journalisé, et une défaillance déclenche les compensations exactes dans l’ordre inverse.

## Garanties

- aucune exécution sans permission `ipam.ddi.sync` ;
- clé d’idempotence d’exécution unique par tenant ;
- verrou transactionnel et journal persistant ;
- capture de l’état BIND, PowerDNS ou Kea avant écriture ;
- compensation exacte des effets confirmés ;
- résultat réseau ambigu classé `compensation_failed` avec `reconciliation_required=true` ;
- aucune commande shell, exécutables BIND absolus et délais bornés ;
- TLS vérifié pour PowerDNS et Kea ;
- secrets exclusivement fournis par l’environnement protégé.

## Configuration

Les variables `OPENINFRA_DDI_*` sont documentées dans `.env.example`. N’activez un fournisseur que lorsque son URL, son jeton ou ses exécutables sont complètement configurés. PowerDNS et Kea exigent une URL HTTPS sans identifiants embarqués.

## Exécution

```bash
openinfra ipam ddi-sync \
  --tenant default \
  --actor admin@openinfra \
  --auth-token "$OPENINFRA_AUTH_TOKEN" \
  --vrf global \
  --reservation-idempotency-key ipam-alloc-srv-app-01 \
  --execution-idempotency-key ddi-sync-srv-app-01 \
  --provider bind --provider kea \
  --dns-zone example.net \
  --reverse-dns-zone 2.0.192.in-addr.arpa \
  --mac-address 00:11:22:33:44:55
```

L’API équivalente est `POST /api/v1/ipam/ddi-sync`.

## Reprise et réconciliation

Une exécution interrompue peut être reprise avec `--resume`, en conservant la même clé d’exécution et exactement la même requête. Une clé réutilisée pour une requête différente est refusée.

Lorsque `reconciliation_required=true`, comparez le journal OpenInfra à l’état réel du fournisseur avant toute nouvelle mutation. Corrigez l’écart fournisseur, documentez l’intervention dans l’outil d’exploitation, puis relancez avec une nouvelle clé d’exécution. OpenInfra ne transforme jamais une réponse ambiguë en succès.

## Rollback opérationnel

La migration `0060_ipam_ddi_execution_journal.sql` est additive. Le rollback applicatif consiste à arrêter les synchronisations, sauvegarder les journaux et restaurer la version précédente. Ne supprimez la table qu’après conservation des preuves d’audit et validation explicite du responsable de production.
