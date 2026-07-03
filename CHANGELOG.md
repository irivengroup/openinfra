## 0.21.0 - 2026-07-03

- Ajout du jalon P05 / EPIC-0504 : moteur de détection conflits IPAM.
- Détection des overlaps de préfixes, overlaps de ranges, doublons d'adresses, leases DHCP conflictuels, adresses observées hors préfixe et divergences DNS/PTR.
- Ajout des observations DNS/DHCP dans les backends JSON et PostgreSQL.
- Ajout de la migration PostgreSQL `0018_ipam_conflict_detection.sql`.
- Ajout des commandes `observe-dns`, `observe-dhcp-lease` et `detect-conflicts`.
- Ajout des endpoints API `/api/v1/ipam/dns-observations`, `/api/v1/ipam/dhcp-leases` et `/api/v1/ipam/conflicts`.
- CI mise à jour avec rendu migration `0018`, smoke IPAM conflits et correction d'une étape security smoke dupliquée.

## 0.20.0 - 2026-07-03

- Roadmap : P05 / EPIC-0503 — VLAN/VXLAN/ASN/BGP fondation.
- Ajout du domaine IPAM réseau : `VlanGroup`, `Vlan`, `VxlanVni`, `AutonomousSystem`, `BgpPeer` et politique de validation `NetworkIdentifierPolicy`.
- Ajout du service applicatif `IpamModelService` pour définir VLAN groups, VNI/VXLAN, VLAN attachés à VRF/VNI, ASN et pairs BGP.
- Cohérence métier : VLAN attaché à un VNI doit référencer le même VRF ; VNI unique par tenant ; ASN local et distant distincts ; route targets validées au format `ASN:NUMBER`.
- Ajout des commandes `openinfra ipam define-vlan-group`, `define-vxlan-vni`, `define-vlan`, `define-asn`, `define-bgp-peer` et `network-bindings`.
- Ajout des endpoints `POST /api/v1/ipam/vlan-groups`, `POST /api/v1/ipam/vxlan-vnis`, `POST /api/v1/ipam/vlans`, `POST /api/v1/ipam/asns`, `POST /api/v1/ipam/bgp-peers` et `GET /api/v1/ipam/network-bindings`.
- Ajout de la migration PostgreSQL `0017_ipam_networking_foundation.sql` avec contraintes VRF/VLAN/VNI/ASN et index d’audit opérationnel.
- CI, OpenAPI, README, runbooks, traçabilité et tests mis à jour avec couverture globale `>= 98 %`.

## 0.19.0 - 2026-07-03

- Roadmap : P05 / EPIC-0502 — Allocation IP transactionnelle.
- Allocation `openinfra ipam allocate` durcie : sélection next-available tenant/VRF/prefixe, idempotence par clé métier, prise en compte des adresses suivies, plages d’allocation, réservations et exclusions.
- Verrou fin côté PostgreSQL via `pg_advisory_xact_lock` par tenant/VRF/prefixe afin d’éviter les collisions inter-processus pendant le calcul + insertion.
- Backend JSON protégé par transaction atomique et test de concurrence 100 allocations sans collision.
- Migration PostgreSQL `0016_ipam_transactional_allocation.sql` ajoutant les index transactionnels de scan allocation/ranges/adresses.
- CI, OpenAPI, documentation, runbooks et validation mis à jour.

## 0.18.0 - 2026-07-03

- Roadmap : P05 / EPIC-0501 — Modèle IPAM IPv4/IPv6/VRF.
- Ajout du domaine `IpAggregate`, `IpRange`, `IpAddressRecord`, `IpRangePurpose` et `IpAddressStatus`.
- Ajout du service applicatif `IpamModelService` pour définir VRF, agrégats, préfixes, plages IP, adresses suivies et capacité de préfixe.
- Ajout des commandes `openinfra ipam define-vrf`, `define-aggregate`, `define-prefix`, `define-range`, `register-address`, `list-prefixes` et `capacity`.
- Ajout des endpoints `POST /api/v1/ipam/vrfs`, `POST /api/v1/ipam/aggregates`, `POST /api/v1/ipam/prefixes`, `POST /api/v1/ipam/ranges`, `POST /api/v1/ipam/addresses`, `GET /api/v1/ipam/prefixes` et `GET /api/v1/ipam/capacity`.
- Ajout de la migration PostgreSQL `0015_ipam_enterprise_foundation.sql` avec tables partitionnées pour agrégats, ranges et adresses suivies, index par tenant/VRF/prefixe/adresse et contraintes IPv4/IPv6.
- Règle métier EPIC-0501 : les chevauchements de préfixes et agrégats sont refusés dans un même VRF et autorisés entre VRF distincts.
- CI, OpenAPI, README, architecture, runbook et tests mis à jour avec couverture globale `>= 98 %`.

## 0.17.6 - 2026-07-03

- Correctif CI Python 3.13 : les jetons générés dans les smoke tests GitHub Actions sont désormais préfixés par `ci_` afin qu'aucune valeur aléatoire commençant par `-` ne soit interprétée par `argparse` comme une option au lieu d'un argument de `--token`.
- Durcissement de la génération applicative des jetons API : `TokenGenerator` produit désormais des jetons préfixés par `oi_`, sans casser la validation ni l'authentification des jetons existants.
- Alignement des scripts optionnels Docker/lab : `docker/openinfra-runtime-smoke.py` et `scripts/docker_environment.py` génèrent aussi des jetons préfixés sûrs.
- Ajout d'un garde-fou dans `scripts/security_gate.py` contre le retour de `print(secrets.token_urlsafe(48))` dans le workflow CI.
- Ajout de tests de non-régression sur le gate CI et la génération de jetons applicatifs.
- Aucun changement fonctionnel métier ; P04 / EPIC-0406 reste le jalon fonctionnel actif.

## 0.17.5 - 2026-07-03

- Correctif GitHub Actions : suppression du job PR-only `dependency-review` du workflow de push pour éviter le statut `Skipped` après `push`.
- Ajout du workflow séparé `.github/workflows/dependency-review.yml`, déclenché uniquement par `pull_request`.
- Renommage explicite du job sécurité en `Blocking push vulnerability gate / Python ...` pour matérialiser le blocage vulnérabilités sur `push`.
- Renforcement de `scripts/security_gate.py` : rejet de `actions/dependency-review-action` et de `if: github.event_name == 'pull_request'` dans le workflow de push, et vérification du workflow PR dédié.
- Ajout de tests de non-régression sur la séparation workflow push / workflow PR.
- Aucun changement fonctionnel métier ; P04 / EPIC-0406 reste le jalon fonctionnel actif.

## 0.17.4 - 2026-07-03

- Correctif CI sécurité : remplacement de l'audit d'environnement par un audit explicite du fichier `requirements/security-audit.txt`.
- Ajout d'un garde-fou bloquant dans `scripts/security_gate.py` contre le retour d'un audit `pip-audit` de l'environnement editable.
- Ajout du fichier `requirements/security-audit.txt` pour auditer uniquement les dépendances tierces.
- Aucun changement fonctionnel métier ; P04 / EPIC-0406 reste le jalon fonctionnel actif.

## 0.17.3 - 2026-07-03

- Correctif CI sécurité initial sur l'audit du package projet installé en editable ; correction finalisée en v0.17.4 avec une entrée d'audit dédiée aux dépendances tierces.
- Correction PostgreSQL runtime : `PostgreSQLDriver.connect()` encapsule les erreurs de connexion `psycopg` en `OpenInfraError`, afin que les erreurs DNS/réseau/serveur manquant soient reportées proprement par OpenInfra au lieu de faire échouer les tests avec une exception tierce.
- Mise à jour tests de sécurité CI pour valider la présence de `requirements/security-audit.txt`.
- Aucun changement fonctionnel métier ; P04 / EPIC-0406 reste le jalon fonctionnel actif livré en v0.17.0.
- Couverture globale conservée au-dessus du seuil obligatoire `>= 98 %`.

## 0.17.2 - 2026-07-03

- Correctif CI bloquant : ajout d'un job `blocking-security` exécuté sur `push`, pull request et lancement manuel.
- Prise en charge CI de Python `3.13` et `3.14`, en plus de `3.11` et `3.12`.
- Ajout de contrôles sécurité bloquants : `bandit` SAST, `pip-audit` pour vulnérabilités de dépendances, `scripts/security_gate.py` pour secrets committés et durcissement workflow.
- Ajout de CodeQL avec suites `security-extended` et `security-and-quality`.
- Ajout du `dependency-review-action` sur pull requests et d'une politique Dependabot pour `pip` et `github-actions`.
- Correction du smoke CI `security list-tokens` / `security revoke-token` : les opérations d'administration des tokens utilisent désormais un jeton `security:admin`, et non un jeton `ipam:operator`.
- Aucun changement fonctionnel métier ; P04 / EPIC-0406 reste le jalon fonctionnel actif livré en v0.17.0.
- Couverture globale conservée au-dessus du seuil obligatoire `>= 98 %`.

## 0.17.0 - 2026-07-03

- Roadmap : P04 / EPIC-0406 — Énergie et refroidissement fondation.
- Ajout du domaine `PowerDevice`, `PowerCircuit`, `CoolingZone`, `RackPowerReservation` et `RackEnergyCoolingReport`.
- Ajout du service applicatif `DcimEnvironmentService` avec contrôle des capacités source, circuit, rack et zone de refroidissement.
- Ajout des commandes `openinfra dcim define-power-device`, `define-power-circuit`, `define-cooling-zone`, `reserve-power` et `energy-cooling-capacity`.
- Ajout des endpoints `POST /api/v1/dcim/power-devices`, `POST /api/v1/dcim/power-circuits`, `POST /api/v1/dcim/cooling-zones`, `POST /api/v1/dcim/power-reservations` et `GET /api/v1/dcim/energy-cooling-capacity`.
- Ajout de la migration PostgreSQL `0014_dcim_energy_cooling_foundation.sql` avec tables partitionnées et index par source, rack, circuit et zone.
- Correction du déclenchement GitHub Actions : le workflow n’est plus limité à `main`, il se lance sur tous les `push`, toutes les pull requests et peut être lancé manuellement via `workflow_dispatch`.
- Confirmation production : OpenInfra reste indépendant de Docker en production ; Docker demeure un lab facultatif de test/smoke.
- CI, OpenAPI, runbooks, architecture, tests et quality gate mis à jour avec couverture globale `>= 98 %`.

## 0.16.0 - 2026-07-03

- Roadmap : P04 / EPIC-0405 — Câblage DCIM fondation.
- Ajout du domaine `PatchPanel`, `DcimPortEndpoint`, `DcimPort`, `DcimCablePathSegment` et `DcimCable`.
- Ajout du service applicatif `DcimCablingService` avec génération de ports, connexion de câbles, prévention des conflits d’endpoint actif et trace humaine.
- Ajout des commandes `openinfra dcim define-patch-panel`, `define-port`, `connect-cable` et `cable-trace`.
- Ajout des endpoints `POST /api/v1/dcim/patch-panels`, `POST /api/v1/dcim/ports`, `POST /api/v1/dcim/cables` et `GET /api/v1/dcim/cable-trace`.
- Ajout de la migration PostgreSQL `0013_dcim_cabling_foundation.sql` avec tables partitionnées et index par endpoint.
- Production clarifiée : runtime serveur natif `systemd` + virtualenv + PostgreSQL ; Docker reste uniquement un lab optionnel.
- CI, OpenAPI, runbooks, architecture, tests et quality gate mis à jour avec couverture globale `>= 98 %`.

## 0.15.0 - 2026-07-03

- Roadmap : P04 / EPIC-0404 — Plans 2D salle et rack elevation.
- Ajout des objets domaine `RoomPlan2D`, `RoomPlanCell`, `RackElevation` et `RackElevationUnit`.
- Ajout du service applicatif `DcimVisualizationService` et des lectures repository `list_racks_in_room` / `list_equipment_in_room`.
- Ajout des commandes `openinfra dcim room-plan` et `openinfra dcim rack-elevation` avec sorties JSON, SVG et HTML.
- Ajout des endpoints `GET /api/v1/dcim/room-plan` et `GET /api/v1/dcim/rack-elevation`.
- Ajout de la migration PostgreSQL `0012_dcim_visualization_indexes.sql` pour les chemins de lecture visualisation.
- Extension de l’OpenAPI, de la CI, du smoke Docker, de la documentation et des tests pour conserver une couverture globale `>= 98 %`.

## 0.14.0 - 2026-07-03

- Roadmap : P04 / EPIC-0403 — QR codes, fiches de localisation et chemins d’intervention terrain.
- Ajout du domaine `EquipmentLocatorPayload`, `QrCodeSvgDocument`, `EquipmentLocatorSheet`, `EquipmentScanProof` et `InterventionRouteStep`.
- Ajout du service `DcimFieldOperationService` pour générer une fiche terrain JSON/HTML et vérifier une preuve de scan QR.
- Ajout de la permission `dcim.identify` au rôle `dcim:operator`.
- Ajout des commandes `openinfra dcim locator-sheet` et `openinfra dcim verify-scan`.
- Ajout des endpoints `GET /api/v1/dcim/locator-sheet` et `POST /api/v1/dcim/verify-scan`.
- Ajout de la migration PostgreSQL `0011_dcim_field_operations.sql` préparant l’historique partitionné des preuves terrain.
- Extension du runtime Docker smoke avec génération de fiche, QR compact et validation de scan.
- Relèvement du seuil de couverture globale à `>= 98 %` avec tests unitaires, intégration, CLI et API supplémentaires.

# Changelog

## 0.13.0 - 2026-07-03

- Roadmap : P04 / EPIC-0402 — Racks, unités U, faces, capacité et occupation.
- Ajout du domaine `RackFace` et `RackCapacityReport`.
- Extension de `Rack` avec faces utilisables, capacité U, poids maximal et capacité électrique.
- Extension de `EquipmentLocation` avec `rack_face`, `u_height`, calcul des unités U occupées et contrôle de chevauchement.
- Ajout du service `DcimRackService` et extension de `DcimLocationService`.
- Ajout de la commande `openinfra dcim define-rack` et `openinfra dcim rack-capacity`.
- Extension de `openinfra dcim locate` avec `--rack-face` et `--u-height`.
- Ajout des endpoints `POST /api/v1/dcim/racks` et `GET /api/v1/dcim/rack-capacity`.
- Ajout de la migration PostgreSQL `0010_dcim_rack_capacity.sql`.
- Extension du runtime Docker smoke avec scénario rack complet.

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
