# OpenInfra v0.29.103 — Rapport de validation

Date : `2026-07-11`  
Release : `0.29.103`  
Jalon : `P17 / EPIC-1702 — multisite Enterprise distribué`

## Périmètre livré

- Route Discovery régionale immuable et tenant-aware pour le triplet région/site/VRF.
- Affectation à un collector `network-proxy` ou `datacenter-proxy` actif.
- Validation du site DCIM, de l’endpoint HTTPS et de la portée autorisée.
- Revalidation du collector lors de chaque soumission de job.
- Routage vers le moteur Discovery existant : idempotence, retries, baux, fencing et DLQ préservés.
- Garde d’édition : fonctionnalité disponible uniquement en Enterprise.
- Persistance JSON et PostgreSQL.
- Migration `0051_enterprise_regional_discovery_routing.sql`.
- Cinq commandes CLI et cinq routes REST/OpenAPI.
- Parité React/runtime statique, traductions FR/EN et formulaires typés.
- Audit de configuration, désactivation et routage.
- Documentation d’exploitation et de rollback.

## Résultats automatisés

### Python

- Tests fonctionnels sans couverture : **936 réussis** en **106,59 s**.
- Suite finale avec couverture : **937 réussis** en **140,30 s**.
- Couverture globale : **98,01 %**.
- Seuil contractuel : **98 % — PASS**.
- Ruff format : **273 fichiers conformes**.
- Ruff lint strict : **PASS**.
- mypy strict : **94 modules — PASS**.
- `compileall` : **PASS**.

### Frontend

- Tests Node.js : **43 réussis**.
- Contrat des assets statiques : **PASS**.
- ESLint/JSX accessibilité : **PASS**.
- Contrat WCAG 2.2 AA : **PASS**.
- Build Vite : **PASS**.
- Parité i18n React/runtime statique : **PASS**.

### Sécurité

- Bandit SAST : **PASS**.
- Security gate secrets/CI/dépendances : **PASS**.
- Aucun secret, placeholder, `TODO`, `FIXME` ou `NotImplementedError` ajouté.
- `pip-audit` : **non exécutable localement**, car la résolution DNS de `pypi.org` échoue dans l’environnement. Le gate CI strict reste configuré.

### API et documentation

- OpenAPI principal : **PASS**.
- OpenAPI embarqué dans le CDC : **PASS**.
- Version OpenAPI : `0.29.103`.
- Nombre de paths OpenAPI : **311**.
- Cinq routes régionales présentes dans l’index API et le wheel.
- CDC v4.8.1 : **828 exigences / 628 tests — PASS**.
- Roadmap v2 : **19 phases / 115 epics / 8 gates / 97 tests — PASS**.
- CDC et roadmap inchangés : EPIC-1702 était déjà planifié et aucune nouvelle recommandation ne modifie l’existant.

### Base de données et migrations

- Total : **51 migrations PostgreSQL**.
- Dernière migration : `0051_enterprise_regional_discovery_routing.sql`.
- Les 51 migrations ont été rendues par la CLI et comparées octet pour octet à leur source : **PASS**.
- Migration `0051` : transactionnelle, additive, partitionnée, indexée, contrainte et non destructive : **PASS**.
- Adaptateur PostgreSQL testé avec doubles transactionnels : **PASS**.
- PostgreSQL réel non disponible dans l’environnement courant ; la validation réelle reste exécutée par la CI.

### Installateurs et runtime

- Six profils `install.ini` : **PASS**.
- Alignement Enterprise/CDC/roadmap : **PASS**.
- Validation et dry-run installateur : **PASS**.
- Smoke runtime natif : **PASS**.
- Docker et Podman absents de l’environnement ; les smokes conteneurisés restent des gates CI.

### Packaging

- Wheel : `openinfra-0.29.103-py3-none-any.whl`.
- sdist : `openinfra-0.29.103.tar.gz`.
- Vérification du contenu wheel : **PASS**.
- Installation du wheel dans un répertoire vierge : **PASS**.
- Smoke installé : version `0.29.103`, **12 routes multisites**, **51 migrations**, dernière migration `0051`, quatre assets runtime et trois points d’entrée publics : **PASS**.

## Empreintes des packages Python

```text
openinfra-0.29.103-py3-none-any.whl
SHA-256: cf3b44fa23931bb83526d2c687ca949f1075e5fe2cb604652cb01e3c7c2755fc
Taille: 749149 octets

openinfra-0.29.103.tar.gz
SHA-256: 427a2544d3d8b77627f9a25076fdc119a0af84dbdca9b3c0df9e2826ccef2bff
Taille: 1539314 octets
```

## Risques résiduels

- Aucun test PostgreSQL réel n’a pu être exécuté localement.
- Aucun smoke Docker/Podman n’a pu être exécuté localement.
- L’audit CVE distant dépend de la connectivité PyPI et doit être confirmé par la CI.
- Le routage soumet des jobs ; l’exécution effective du scan reste de la responsabilité de l’agent Discovery et de son workflow existant.
