# Changelog

## 0.9.0 - 2026-07-03

- Ajout du domaine d’audit exploitable : filtres sûrs, export JSON/JSONL, page d’événements et rapport d’intégrité.
- Ajout du chaînage d’intégrité `previous_hash` / `record_hash` calculé en SHA-256 sur les événements d’audit.
- Ajout du service applicatif `AuditTrailService` : liste, export et vérification d’intégrité avec contrôle `audit.read`.
- Ajout du rôle intégré `audit:reader` et extension de `security:admin` avec la permission `audit.read`.
- Ajout de la migration PostgreSQL `0006_audit_trail_integrity.sql` avec colonnes, contraintes et index d’intégrité.
- Ajout des commandes `openinfra audit list`, `openinfra audit export` et `openinfra audit verify-integrity`.
- Ajout des endpoints `/api/v1/audit/events`, `/api/v1/audit/export` et `/api/v1/audit/integrity`.
- Extension des smoke tests Docker et CI pour couvrir l’audit trail.
- Mise à jour README, OpenAPI, runbooks, architecture, CI et tests de non-régression.

## 0.8.0 - 2026-07-02

- Ajout du socle ABAC contextuel tenant/site/environnement comme contrôle complémentaire à RBAC.
- Ajout du domaine `AccessPolicyRule`, `AccessRequestContext` et des effets `allow` / `deny` avec priorité explicite aux règles de refus.
- Ajout du service applicatif `AccessPolicyService` : création, inventaire paginé, désactivation et évaluation des règles.
- Ajout des référentiels JSON et PostgreSQL `AccessPolicyRepository`.
- Ajout de la migration PostgreSQL `0005_access_policy_abac.sql` avec table partitionnée, index GIN sujets/rôles/sites/environnements et index d’audit `access.policy.%`.
- Ajout des commandes `openinfra access create-rule`, `list-rules`, `evaluate` et `deactivate-rule`.
- Extension de `openinfra ipam allocate` avec `--auth-token`, `--site-code` et `--environment` pour valider RBAC + ABAC côté CLI.
- Ajout des endpoints `/api/v1/access/rules`, `/api/v1/access/evaluate`, `/api/v1/access/deactivate-rule` et enforcement ABAC sur `/api/v1/ipam/allocate` lorsque l’API authentifiée est activée.
- Extension des smoke tests Docker et CI pour couvrir la migration `0005` et le scénario ABAC runtime.
- Mise à jour README, OpenAPI, runbooks, architecture, CI et tests de non-régression.

## 0.6.0 - 2026-07-02

- Ajout du cycle de vie complet des jetons API : expiration optionnelle, révocation, rotation, compteur d’usage et inventaire paginé sans exposition des hashes.
- Ajout de la migration PostgreSQL `0003_security_token_lifecycle.sql` avec colonnes de cycle de vie et index opérationnels.
- Ajout des commandes `openinfra security list-tokens`, `openinfra security revoke-token` et `openinfra security rotate-token`.
- Ajout des endpoints `/api/v1/security/tokens`, `/api/v1/security/revoke-token` et `/api/v1/security/rotate-token`.
- Extension des smoke tests Docker et CI pour couvrir la migration `0003` et le cycle de vie sécurité.
- Mise à jour README, OpenAPI, runbooks, architecture, CI et tests de non-régression.

## 0.5.0 - 2026-07-02

- Ajout du moteur applicatif de migrations PostgreSQL avec historique `openinfra_schema_migrations`, checksum SHA-256, dry-run, statut et application idempotente.
- Ajout des commandes `openinfra database status` et `openinfra database apply-migrations`.
- Renforcement de `/ready` en backend PostgreSQL avec contrôle du schéma appliqué.
- Ajout de l'endpoint `/api/v1/database/schema` pour exposer le statut opérationnel du schéma.
- Mise à jour du runtime Docker : le service `migrate` utilise désormais l'image applicative OpenInfra et non un appel direct `psql`.
- Extension des smoke tests Docker pour vérifier le statut de schéma.
- Suppression des marqueurs de code incomplet dans `src`, `tests`, `scripts`, `docker` et runbooks.
- Mise à jour README, OpenAPI, runbooks PostgreSQL/Docker/validation, architecture, CI et tests.

## 0.3.0 - 2026-07-02

- Ajout d’un environnement d’exécution Docker complet pour valider OpenInfra avec PostgreSQL réel, migration, API et CLI.
- Ajout du `Dockerfile` applicatif non-root et du `compose.yaml` avec services `postgres`, `migrate`, `api` et `smoke`.
- Ajout du script `scripts/docker_environment.py` pour générer un `.env` local sécurisé, démarrer, valider, superviser et réinitialiser le runtime.
- Ajout du scénario `docker/openinfra-runtime-smoke.py` validant `/ready`, `/health`, `/api/v1/version`, allocation IPAM API idempotente et allocation IPAM CLI en backend PostgreSQL.
- Ajout de la sonde applicative `/ready` connectée au backend de persistance via `ReadinessProbe`.
- Mise à jour OpenAPI, README, runbook Docker, CI GitHub Actions et tests d’intégration.

## 0.2.0 - 2026-07-02

- Ajout de la persistance PostgreSQL runtime via adaptateur optionnel `psycopg`.
- Ajout des référentiels PostgreSQL DCIM, IPAM et audit alignés sur la migration partitionnée `0001_bootstrap.sql`.
- Ajout d’un gestionnaire transactionnel PostgreSQL avec registre de session par thread et fermeture systématique des connexions.
- Extension CLI/API pour sélectionner le backend `json` ou `postgresql` avec DSN explicite ou variable `OPENINFRA_DATABASE_DSN`.
- Correction transactionnelle IPAM : création de préfixe, idempotence, allocation, réservation et audit sont exécutés dans la même unité de travail.
- Ajout de tests d’intégration PostgreSQL sans base externe via connecteur simulé et vérification des erreurs opérationnelles.
- Mise à jour documentation, CI smoke tests et rapport de validation.

## 0.1.0 - 2026-07-02

- Création du socle Python POO OpenInfra.
- Ajout des domaines DCIM, IPAM, ITAM, Discovery et Dependency Mapping.
- Ajout des services applicatifs pour localisation DCIM et allocation IPAM idempotente.
- Ajout de la persistance JSON atomique pour développement et tests.
- Ajout de la migration PostgreSQL initiale partitionnée et indexée.
- Ajout de la CLI, de l'API HTTP, de la documentation, des tests et de la CI GitHub Actions.
- Intégration documentaire du CDC/SFG/STG v4 et de la roadmap v1 comme sources contractuelles.
