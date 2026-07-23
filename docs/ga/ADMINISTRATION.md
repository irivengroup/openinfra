# Guide administrateur

Version cible : `0.34.19`

## Authentification et jetons

Le backend applique les jetons applicatifs. Le BFF web porte le jeton serveur et ne demande pas à l’opérateur de le saisir dans les formulaires métier. Dans le lab Docker, le jeton bootstrap est généré dans un volume interne et non dans `.env`.

```bash
OPENINFRA_TOKEN="$(python scripts/docker_environment.py bootstrap-token)"
```

Afficher la version et vérifier le jeton :

```bash
openinfra version
openinfra security whoami --backend postgresql --tenant default --token "$OPENINFRA_TOKEN"
```

Créer ou remplacer un jeton applicatif à durée et rôle contrôlés :

```bash
export OPENINFRA_INTEGRATION_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
openinfra security bootstrap-token \
  --backend postgresql \
  --tenant default \
  --subject integration-ci \
  --role reader \
  --token "$OPENINFRA_INTEGRATION_TOKEN" \
  --ttl-seconds 86400
```

Les secrets ne doivent être ni passés dans l’historique shell partagé, ni stockés dans le dépôt, ni journalisés.

## RBAC et périmètres

Le RBAC combine rôles, permissions et périmètres tenant/site. L’annuaire LDAP/IPA authentifie l’identité ; il n’accorde jamais directement une permission OpenInfra.

Principes :

- moindre privilège ;
- séparation lecture, écriture, worker et administration ;
- refus par défaut ;
- périmètres tenant et site explicites ;
- audit de toute élévation ou modification de mapping.

Consulter l’aide canonique :

```bash
openinfra identity --help
openinfra access --help
openinfra security --help
```

## Éditions et quotas

```bash
openinfra edition list --edition pro
openinfra edition feature-check --tenant default --feature discovery
openinfra edition quota-check --tenant default --resource users --requested 1
```

Les quotas sont vérifiés avant la mutation. Une réponse de refus doit être traitée comme une décision métier, pas comme une erreur transitoire à rejouer sans borne.

## Audit et traçabilité

```bash
openinfra audit list \
  --backend postgresql \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN"

openinfra audit verify-integrity \
  --backend postgresql \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN"
```

Exporter les événements pour archivage :

```bash
openinfra audit export \
  --backend postgresql \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN" \
  --format jsonl
```

## Administration PostgreSQL

```bash
openinfra database status --root installers/migrations/postgresql
openinfra database apply-migrations --root installers/migrations/postgresql --dry-run
openinfra database apply-migrations --root installers/migrations/postgresql
```

Règles obligatoires :

- sauvegarde vérifiée avant toute mise à niveau ;
- migrations appliquées par le moteur OpenInfra ;
- aucun fichier SQL déjà appliqué ne doit être modifié ;
- checksum divergent = arrêt de la procédure ;
- les écritures visent le primaire ;
- les lectures sur réplica restent soumises au seuil de lag et à la cohérence read-after-write.

## Administration des workers

```bash
openinfra async metrics --backend postgresql --tenant default --token "$OPENINFRA_TOKEN"
openinfra async jobs --backend postgresql --tenant default --admin-token "$OPENINFRA_TOKEN"
openinfra async outbox-events --backend postgresql --tenant default --admin-token "$OPENINFRA_TOKEN"
```

Une DLQ non vide, des leases expirés ou un âge de file croissant doivent déclencher une investigation avant tout rejeu administratif.
