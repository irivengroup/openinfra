# Runbook PostgreSQL Cluster

## Objectif

OpenInfra utilise PostgreSQL comme socle transactionnel principal pour la cible production. Le schéma initial est conçu pour de très grands volumes : partitionnement par tenant, partitions spécialisées pour les réservations IPAM, partitions temporelles pour l'audit, index composés et contraintes d'intégrité explicites.

## DSN runtime

La CLI et l'API utilisent `--postgres-dsn` ou `OPENINFRA_DATABASE_DSN`.

```bash
export OPENINFRA_DATABASE_DSN='postgresql://openinfra:secret@postgres:5432/openinfra'
```

Aucun secret ne doit être stocké dans le code, les migrations ou les fichiers versionnés.

## Migrations applicatives

Les migrations sont appliquées par OpenInfra et non par un appel manuel `psql` dans le runtime Docker.

```bash
openinfra database status --root migrations/postgresql
openinfra database apply-migrations --root migrations/postgresql --dry-run
openinfra database apply-migrations --root migrations/postgresql
```

Le moteur applique les migrations `0001_bootstrap.sql`, `0002_security_rbac.sql` et `0003_security_token_lifecycle.sql`. Il maintient `openinfra_schema_migrations` avec :

- `version` : nom du fichier SQL ;
- `checksum` : SHA-256 du contenu source ;
- `applied_at` : date d'application.

Une divergence de checksum sur une migration déjà appliquée bloque l'exécution afin d'éviter une dérive silencieuse du schéma.

## Disponibilité et scalabilité

Pour un cluster HA, déployer PostgreSQL avec une solution de réplication et de bascule supervisée, par exemple Patroni ou une offre managée équivalente. Les écritures OpenInfra doivent cibler le primaire. Les lectures lourdes futures devront être routées vers des réplicas lorsque l'invariant métier le permet.

## Paramètres runtime

`PostgreSQLClusterProfile.production_default()` configure :

- `application_name=openinfra-api` ;
- `statement_timeout=30000 ms` ;
- `lock_timeout=5000 ms`.

Ces limites évitent les requêtes bloquées durablement et facilitent l'observabilité côté PostgreSQL.

## Validation

```bash
openinfra database status --root migrations/postgresql
openinfra database apply-migrations --root migrations/postgresql --dry-run
openinfra database apply-migrations --root migrations/postgresql
openinfra ipam allocate --backend postgresql --tenant default --vrf default --prefix 10.10.0.0/29 --hostname srv --idempotency-key validation-1
```

## Rollback

La version actuelle applique des migrations avant uniquement. Pour une opération critique, effectuer un snapshot PostgreSQL ou une sauvegarde logique avant `apply-migrations`. Les migrations destructives futures devront être livrées avec stratégie de rollback documentée, tests de non-régression et fenêtre d'exploitation validée. La migration `0003_security_token_lifecycle.sql` est additive et conserve la compatibilité ascendante des jetons existants.

## Tables IAM v0.7.0

La migration `0004_identity_users_groups.sql` ajoute `identity_users`, `identity_groups` et `identity_group_memberships`. Les tables sont partitionnées par `tenant_id`, avec index GIN sur les tableaux de rôles et index d’appartenance pour accélérer le calcul des rôles effectifs. Les écritures IAM restent transactionnelles et auditées.

## Tables ABAC v0.8.0

La migration `0005_access_policy_abac.sql` ajoute `access_policy_rules`, partitionnée par `tenant_id`. Les règles stockent la permission, l’effet `allow` ou `deny`, les sélecteurs de sujets/rôles et les attributs contextuels `site_codes` / `environments`.

Commandes de validation :

```bash
openinfra database render-migration --name 0005_access_policy_abac --root migrations/postgresql
openinfra database apply-migrations --root migrations/postgresql --dry-run
openinfra database apply-migrations --root migrations/postgresql
openinfra database status --root migrations/postgresql
```

Les index GIN accélèrent la recherche par sujets, rôles, sites et environnements. L’index `idx_audit_events_access_policy` facilite l’audit des actions `access.policy.%`.
