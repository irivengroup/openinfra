# Changelog

## 0.12.0 - 2026-07-03

- Réalignement maintenu sur la roadmap avec P04 / EPIC-0401 Modèle physique DCIM.
- Ajout du modèle pays, région, ville, site, bâtiment, étage, salle et zone de salle.
- Extension de la localisation équipement avec étage, zone et coordonnées X/Y/Z.
- Ajout de validations de grille ligne/colonne, zone incluse dans salle, conflits rack/U, cohérence étage et zone.
- Ajout du service `DcimTopologyService` pour définir une salle physique idempotente et auditée.
- Ajout de la commande `openinfra dcim define-room` et extension de `openinfra dcim locate` avec `--floor` et `--zone`.
- Ajout de l’endpoint `POST /api/v1/dcim/rooms` avec contrôle `dcim.write` en mode API authentifié.
- Ajout de la migration PostgreSQL `0009_dcim_physical_model.sql` avec tables et index DCIM physiques.
- Extension du runtime Docker smoke, OpenAPI, README, architecture, runbooks, CI et tests.

## 0.11.0 - 2026-07-03

- Réalignement maintenu sur REL-01/P03 avec EPIC-0306 Gouvernance minimale des sources.
- Ajout du domaine `SourceGovernanceRule`, `SourceGovernanceEvaluation` et `SourceGovernanceEvaluator`.
- Ajout du service applicatif `SourceGovernanceService` : création, inventaire paginé, évaluation et désactivation des règles.
- Intégration de la gouvernance dans `SourceOfTruthService` pour refuser les écrasements non autoritatifs selon la stratégie `reject`.
- Ajout du rôle `sot:governance-admin` et des permissions `sot.governance.read` / `sot.governance.write`.
- Ajout des référentiels JSON et PostgreSQL `SourceGovernanceRepository`.
- Ajout de la migration PostgreSQL `0008_source_governance.sql` avec table partitionnée, contraintes et index métier.
- Ajout des commandes `openinfra sot create-governance-rule`, `list-governance-rules`, `evaluate-governance` et `deactivate-governance-rule`.
- Ajout des endpoints `/api/v1/sot/governance-rules`, `/api/v1/sot/governance/evaluate` et `/api/v1/sot/governance/deactivate-rule`.
- Extension du runtime Docker smoke, OpenAPI, README, architecture, runbooks, CI et tests de non-régression.

## 0.10.0 - 2026-07-03

- Réalignement roadmap sur REL-01/P03 Source of Truth avant poursuite des briques P14.
- Ajout du domaine SOT : objets typés, clés sûres, tags, attributs JSON contrôlés, source déclarée, version et statut.
- Ajout des relations typées transactionnelles entre objets SOT avec provenance et validité temporelle.
- Ajout des snapshots `SourceObjectSnapshot` pour restitution time-travel initiale par version.
- Ajout du service applicatif `SourceOfTruthService` avec contrôle `sot.read` / `sot.write` et audit.
- Ajout des référentiels JSON et PostgreSQL `SourceOfTruthRepository`.
- Ajout de la migration PostgreSQL `0007_source_of_truth_core.sql` avec tables partitionnées et index type/tags/JSONB/relations.
- Ajout des commandes `openinfra sot upsert-object`, `get-object`, `list-objects`, `get-object-version`, `create-relation`, `list-relations`.
- Ajout des endpoints `/api/v1/sot/objects`, `/api/v1/sot/object-versions` et `/api/v1/sot/relations`.
- Extension du runtime Docker smoke, OpenAPI, README, architecture, runbooks, CI et tests de non-régression.

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
