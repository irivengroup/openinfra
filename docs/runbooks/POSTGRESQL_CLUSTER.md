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
openinfra database status --root installers/migrations/postgresql
openinfra database apply-migrations --root installers/migrations/postgresql --dry-run
openinfra database apply-migrations --root installers/migrations/postgresql
```

Le moteur applique les migrations versionnées `0001_bootstrap.sql` à `0006_audit_trail_integrity.sql`. Il maintient `openinfra_schema_migrations` avec :

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
openinfra database status --root installers/migrations/postgresql
openinfra database apply-migrations --root installers/migrations/postgresql --dry-run
openinfra database apply-migrations --root installers/migrations/postgresql
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
openinfra database render-migration --name 0005_access_policy_abac --root installers/migrations/postgresql
openinfra database apply-migrations --root installers/migrations/postgresql --dry-run
openinfra database apply-migrations --root installers/migrations/postgresql
openinfra database status --root installers/migrations/postgresql
```

Les index GIN accélèrent la recherche par sujets, rôles, sites et environnements. L’index `idx_audit_events_access_policy` facilite l’audit des actions `access.policy.%`.


## Audit Trail v0.9.0

La migration `0006_audit_trail_integrity.sql` ajoute `previous_hash` et `record_hash` à `audit_events`. Chaque événement applicatif est chaîné au précédent par tenant avec un hash SHA-256 canonique. Les index `idx_audit_events_actor_action`, `idx_audit_events_severity_time` et `idx_audit_events_integrity_chain` accélèrent respectivement les recherches d’exploitation, les filtres de conformité et les vérifications d’intégrité.

Commandes de validation :

```bash
openinfra database render-migration --name 0006_audit_trail_integrity --root installers/migrations/postgresql
openinfra audit list --backend postgresql --tenant default --admin-token "$ADMIN_TOKEN"
openinfra audit export --backend postgresql --tenant default --admin-token "$ADMIN_TOKEN" --format jsonl
openinfra audit verify-integrity --backend postgresql --tenant default --admin-token "$ADMIN_TOKEN"
```

## Migration 0007 IT Ressources Management

La migration `0007_source_of_truth_core.sql` ajoute les tables partitionnées `source_objects`, `source_object_snapshots` et `source_relations`. Elle doit être appliquée avec le moteur de migrations OpenInfra afin de conserver l'historique `openinfra_schema_migrations` et les checksums SHA-256. La migration `0026_itrm_as_of_audit_indexes.sql` ajoute les index non destructifs nécessaires à la restitution `as-of`, au filtrage temporel des relations et à l’audit par objet ITRM.

Validation :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration \
  --name 0007_source_of_truth_core \
  --root installers/migrations/postgresql
PYTHONPATH=src python -m openinfra.interfaces.cli database apply-migrations \
  --postgres-dsn "$OPENINFRA_DATABASE_DSN"
```

Les index principaux couvrent la recherche par type, tags, attributs JSONB, versions historiques et relations entrantes/sortantes. Les opérations applicatives doivent utiliser la pagination pour éviter toute lecture non bornée.

## Migration 0008 Gouvernance des sources ITRM

La migration `0008_source_governance.sql` ajoute la table partitionnée `source_governance_rules`. Elle stocke les règles de source autoritative par tenant, type d'objet optionnel, chemin d'attribut, priorité, fraîcheur optionnelle et stratégie de conflit.

Validation :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration \
  --name 0008_source_governance \
  --root installers/migrations/postgresql
PYTHONPATH=src python -m openinfra.interfaces.cli database apply-migrations \
  --postgres-dsn "$OPENINFRA_DATABASE_DSN"
```

Les index couvrent la recherche par type d'objet, chemin d'attribut, source autoritative et audit `itrm.governance.%`. Les opérations applicatives doivent rester transactionnelles avec la mise à jour ITRM afin d'éviter toute divergence entre décision de gouvernance, versionnement et audit.


## Migration 0009 Modèle physique DCIM

La migration `0009_dcim_physical_model.sql` ajoute la fondation P04 / EPIC-0401 : région de site, étages, zones de salle, rattachement des salles à un étage, coordonnées X/Y/Z et rattachement étage/zone pour racks et équipements.

Validation :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration \
  --name 0009_dcim_physical_model \
  --root installers/migrations/postgresql
PYTHONPATH=src python -m openinfra.interfaces.cli database apply-migrations \
  --postgres-dsn "$OPENINFRA_DATABASE_DSN"
```

Les index couvrent la recherche par site/région/ville, étage, salle, zone, grille et localisation équipement. Les écritures DCIM restent transactionnelles via le `UnitOfWork` applicatif.

## Migration 0010 Capacité rack DCIM

La migration `0010_dcim_rack_capacity.sql` ajoute le support P04 / EPIC-0402 : faces utilisables, capacité poids, capacité électrique, face de montage équipement, hauteur U et index d'occupation.

Validation SQL :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli database render-migration \
  --name 0010_dcim_rack_capacity \
  --root installers/migrations/postgresql >/tmp/openinfra-0010.sql
```

Après application, les appels applicatifs doivent continuer à passer par l'API ou la CLI afin de bénéficier du contrôle de chevauchement des intervalles U.

## v0.29.10 — Plan HA/PITR généré par les installateurs

Le plan HA/PITR est généré par les scopes backend/all-in-one. En Pro/Enterprise server, `identity.peer_nodes` déclenche la topologie `near-real-time-streaming-cluster`. Le plan ne lit aucun port ni paramètre PostgreSQL dans `install.ini`; les valeurs internes restent gérées par l'installateur pour éviter les contournements et les divergences.

Commande d'audit :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli database ha-plan \
  --path installers/setup/enterprise/server/install.ini \
  --edition enterprise \
  --scope server
```

Paramètres rendus :

- `wal_level=replica` ;
- `archive_mode=on` ;
- `archive_command` vers `/data/openinfra/pitr` ;
- `hot_standby=on` ;
- `max_wal_senders=16` ;
- `max_replication_slots=16` ;
- `synchronous_commit='local'` pour un commit local non bloquant ;
- aucun `synchronous_standby_names` par défaut, même lorsque des peers existent ;

Le failover reste manuel : OpenInfra prépare le socle technique et l'audit, mais ne promeut jamais automatiquement un standby.
