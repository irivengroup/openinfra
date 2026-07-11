# Reprise après sinistre multisite

## Objet

OpenInfra `0.29.104` réalise P17 / EPIC-1703 en ajoutant un registre de plans de reprise intersite et des preuves immuables d’exercices de perte du site primaire. La capacité est disponible en éditions **Pro** et **Enterprise**.

Un plan associe exactement deux sites DCIM distincts :

- un site primaire ;
- un site de secours ;
- un mode de réplication `asynchronous` ou `synchronous` ;
- un RPO (Recovery Point Objective, perte de données maximale admissible) ;
- un RTO (Recovery Time Objective, durée maximale de reprise) ;
- un âge maximal admissible pour la sauvegarde utilisée lors d’une restauration.

OpenInfra ne promeut jamais automatiquement PostgreSQL, ne déclenche aucun fencing, ne modifie aucun DNS/VIP et n’exécute aucune restauration. Il enregistre la politique, contrôle les sites, évalue les preuves fournies par l’opérateur et conserve l’audit. Les opérations destructives restent soumises aux procédures PostgreSQL et réseau de l’organisation.

## Permissions et prérequis

- Permission requise : `multisite.admin`.
- Éditions : Pro ou Enterprise. Lite est refusée par le feature gate `multisite_disaster_recovery`.
- Les deux codes de site doivent exister dans le DCIM du tenant.
- Les identités, tokens et journaux d’audit suivent les règles de sécurité OpenInfra existantes.
- Le cluster PostgreSQL, les sauvegardes et le PITR doivent être préparés conformément à `docs/runbooks/POSTGRESQL_CLUSTER.md` et `docs/runbooks/INSTALLERS.md`.

## Configuration d’un plan

```bash
openinfra multisite dr-plan-configure \
  --backend postgresql \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN" \
  --name "Reprise PAR1 vers LON1" \
  --primary-site-code PAR1 \
  --recovery-site-code LON1 \
  --replication-mode asynchronous \
  --rpo-seconds 300 \
  --rto-seconds 1800 \
  --max-backup-age-seconds 86400 \
  --actor dr-operator
```

La même paire primaire/secours est révisée de manière idempotente : l’identifiant et la date de création sont conservés, les objectifs et l’opérateur sont actualisés et un plan précédemment désactivé est réactivé.

```bash
openinfra multisite dr-plans \
  --backend postgresql \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN"

openinfra multisite dr-plan-get \
  --backend postgresql \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN" \
  --plan-id "$PLAN_ID"
```

## Préparation obligatoire d’un exercice

Avant de simuler la perte du site primaire, l’opérateur doit disposer d’un ticket ou changement approuvé et vérifier :

1. l’identité des sites et le plan actif ;
2. l’état de la réplication et le retard mesuré ;
3. l’existence d’une sauvegarde restaurable et son âge ;
4. la disponibilité du site de secours ;
5. l’isolation/fencing du primaire simulé afin d’éviter un split-brain ;
6. le plan de bascule DNS/VIP et son TTL ;
7. les contrôles applicatifs, réseau et sécurité à exécuter ;
8. le plan de retour arrière et les propriétaires de décision.

L’exercice doit être réalisé sur une fenêtre contrôlée. Les valeurs transmises à OpenInfra constituent des preuves opérateur ; elles ne sont pas déduites automatiquement d’une action de promotion.

## Enregistrement et évaluation d’un exercice

```bash
openinfra multisite dr-drill-execute \
  --backend postgresql \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN" \
  --plan-id "$PLAN_ID" \
  --replication-lag-seconds 90 \
  --backup-age-seconds 7200 \
  --measured-rto-seconds 1200 \
  --restore-verified \
  --recovery-available \
  --vip-reachable \
  --operator-confirmed \
  --actor dr-operator
```

Le résultat est `passed` uniquement lorsque toutes les conditions suivantes sont réunies :

- confirmation explicite de l’opérateur ;
- disponibilité du site de secours ;
- restauration vérifiée ;
- endpoint DNS/VIP joignable ;
- retard de réplication inférieur ou égal au RPO ;
- âge de sauvegarde inférieur ou égal au seuil du plan ;
- durée de reprise mesurée inférieure ou égale au RTO.

Les motifs d’échec possibles sont stables et auditables :

- `operator-confirmation-missing` ;
- `recovery-site-unavailable` ;
- `restore-not-verified` ;
- `service-endpoint-unreachable` ;
- `rpo-exceeded` ;
- `backup-too-old` ;
- `rto-exceeded`.

```bash
openinfra multisite dr-drills \
  --backend postgresql \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN" \
  --plan-id "$PLAN_ID" \
  --status failed

openinfra multisite dr-drill-get \
  --backend postgresql \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN" \
  --drill-id "$DRILL_ID"
```

## Procédure de perte réelle d’un site

OpenInfra sert de registre de décision et de preuve. La séquence technique reste volontairement externe :

1. déclarer l’incident et geler les changements concurrents ;
2. confirmer l’indisponibilité du primaire par au moins deux sources indépendantes ;
3. exécuter le fencing selon la plateforme afin d’interdire toute écriture résiduelle ;
4. mesurer le dernier point de réplication et la fraîcheur de la sauvegarde/PITR ;
5. faire approuver la décision de bascule par les propriétaires désignés ;
6. promouvoir ou restaurer le secours avec les outils PostgreSQL approuvés ;
7. appliquer la bascule DNS/VIP/load-balancer selon la procédure réseau ;
8. valider l’intégrité PostgreSQL, les migrations, l’API, le Web, l’authentification et les parcours métier ;
9. enregistrer les mesures et preuves dans un exercice OpenInfra ;
10. conserver les journaux, identifiants de changement et résultats de validation dans le système d’audit de l’organisation.

Aucune étape ne doit être sautée parce qu’un exercice antérieur était réussi.

## Retour au site primaire

Le failback est un changement distinct :

1. reconstruire le primaire depuis une source approuvée ;
2. vérifier l’intégrité, la version, les migrations et la réplication inverse ;
3. attendre la convergence et mesurer le lag ;
4. obtenir l’approbation formelle ;
5. clôturer les écritures sur le secours, effectuer le fencing nécessaire puis rebasculer DNS/VIP ;
6. valider les parcours métier et la cohérence de l’audit ;
7. rétablir la topologie nominale et documenter les écarts RPO/RTO.

Ne jamais réintroduire un ancien primaire sans reconstruction ou resynchronisation complète : cela créerait un risque de split-brain et de divergence irréconciliable.

## Désactivation et rollback fonctionnel

```bash
openinfra multisite dr-plan-disable \
  --backend postgresql \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN" \
  --plan-id "$PLAN_ID" \
  --actor dr-operator
```

La désactivation est idempotente et conserve l’historique. Elle interdit de nouveaux exercices mais ne supprime ni le plan, ni les preuves, ni les audits. Le rollback de la release est donc non destructif : conserver les tables `multisite_dr_plans` et `multisite_dr_drills`, désactiver les plans actifs si nécessaire, puis revenir au binaire précédent. La migration `0052` est additive et ne doit pas être supprimée en production.

## API

Les sept routes sont documentées dans `docs/api/openapi.yaml` :

- `GET /api/v1/multisite/disaster-recovery/plans` ;
- `GET /api/v1/multisite/disaster-recovery/plans/get` ;
- `POST /api/v1/multisite/disaster-recovery/plans/configure` ;
- `POST /api/v1/multisite/disaster-recovery/plans/disable` ;
- `GET /api/v1/multisite/disaster-recovery/drills` ;
- `GET /api/v1/multisite/disaster-recovery/drills/get` ;
- `POST /api/v1/multisite/disaster-recovery/drills/execute`.

## Persistance, volumétrie et audit

La migration `0052_multisite_disaster_recovery.sql` ajoute deux tables hash-partitionnées par tenant, huit partitions chacune, des contraintes d’intégrité, des index de consultation et les payloads JSONB. Les opérations de configuration, désactivation et exercice sont transactionnelles avec l’audit :

- `multisite.dr_plan.configured` ;
- `multisite.dr_plan.disabled` ;
- `multisite.dr_drill.executed`.

L’audit d’exercice contient toujours `automatic_promotion=false`. Les listes sont paginées et bornées à 500 éléments par page.

## Validation de la capacité

```bash
PYTHONPATH=src python -m pytest -q --no-cov \
  tests/unit/test_multisite_disaster_recovery_domain.py \
  tests/integration/test_multisite_disaster_recovery.py \
  tests/integration/test_multisite_disaster_recovery_cli.py \
  tests/integration/test_multisite_disaster_recovery_http_api.py \
  tests/integration/test_multisite_migration.py \
  tests/integration/test_multisite_postgresql_repository.py \
  tests/integration/test_multisite_web_contract.py
```
