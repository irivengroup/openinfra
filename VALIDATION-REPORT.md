# OpenInfra v0.29.104 — Rapport de validation

Date : `2026-07-11`  
Release : `0.29.104`  
Jalon : `P17 / EPIC-1703 — reprise d’activité multisite`

## Périmètre livré

- Plans de reprise primaire/secours tenant-aware pour les éditions Pro et Enterprise.
- Objectifs RPO/RTO, mode de réplication et seuil maximal d’ancienneté de sauvegarde.
- Vérification des deux sites dans le référentiel DCIM avant configuration et avant exercice.
- Exercices immuables de perte du site primaire avec sept contrôles explicites et motifs d’échec stables.
- Preuves d’exercice horodatées, audit transactionnel et absence de modification rétroactive.
- Garantie de sécurité : aucune promotion PostgreSQL, opération de fencing, restauration ou mutation DNS/VIP automatique.
- Persistances JSON et PostgreSQL.
- Migration `0052_multisite_disaster_recovery.sql` additive, partitionnée et non destructive.
- Sept commandes CLI, sept routes REST/OpenAPI et parité React/runtime statique FR/EN.
- Runbook complet de préparation, exercice, bascule contrôlée, failback et rollback.
- Gate GitHub Actions bloquant dédié au DR multisite.

## Résultats automatisés

### Python

- Suite exhaustive : **947 tests réussis** en **163,79 s**.
- Couverture globale : **98,0025 %** (`34 393 / 35 094` instructions).
- Seuil contractuel : **98 % — PASS**.
- Ruff format : **277 fichiers conformes**.
- Ruff lint strict : **PASS**.
- mypy strict : **88 modules — PASS**.
- `compileall` : **PASS**.

### Frontend

- Tests Node.js : **44 réussis**.
- Contrat des assets statiques : **PASS**.
- ESLint/JSX accessibilité : **PASS**.
- Contrat WCAG 2.2 AA : **PASS**.
- Build Vite de production : **PASS**.
- Parité des opérations DR et des traductions React/runtime statique : **PASS**.

### Sécurité

- Bandit SAST : **PASS**.
- Security gate secrets/CI/dépendances : **PASS**.
- Aucun secret, placeholder, `TODO`, `FIXME` ou `NotImplementedError` ajouté.
- Les preuves d’exercice sont immuables côté JSON et PostgreSQL.
- Les plans conservent leur identité PostgreSQL lors d’une révision afin de préserver les clés étrangères des exercices.
- `pip-audit` a été installé et lancé avec la commande CI officielle, mais n’a pas pu résoudre `pypi.org` dans l’environnement courant. Le gate CI strict reste configuré.

### API, CDC et roadmap

- OpenAPI principal : **PASS**.
- OpenAPI embarqué dans le CDC : **PASS**.
- Version OpenAPI : `0.29.104`.
- Nombre de paths OpenAPI : **318**.
- Sept routes DR présentes dans l’index API, les deux contrats et le wheel.
- CDC v4.8.1 : **828 exigences / 628 tests — PASS**.
- Roadmap v2 : **19 phases / 115 epics / 8 gates / 97 tests — PASS**.
- CDC et roadmap non réémis : EPIC-1703 était déjà planifié et aucune nouvelle recommandation ne modifie leur contenu contractuel.

### Base de données et migrations

- Total : **52 migrations PostgreSQL**.
- Dernière migration : `0052_multisite_disaster_recovery.sql`.
- Catalogue complet des 52 migrations chargé, validé et comparé à ses sources : **PASS**.
- Migration `0052` : transactionnelle, additive, deux tables partitionnées par tenant, contraintes d’intégrité, index d’exploitation et audit : **PASS**.
- Adaptateur PostgreSQL testé avec doubles transactionnels, y compris l’immuabilité des preuves et la stabilité des identifiants de plan : **PASS**.
- PostgreSQL réel et `psql` indisponibles localement ; l’application réelle des migrations reste un gate CI/environnement PostgreSQL.

### Installateurs et runtime

- Six profils `install.ini` : **PASS**.
- Alignement Enterprise/CDC/roadmap : **PASS**.
- Validation et dry-run des six installateurs : **PASS**.
- Smoke runtime natif et unités systemd rendues : **PASS**.
- Docker et Podman absents de l’environnement ; les smokes conteneurisés restent des gates CI.

### Performance

Benchmark du graphe RSOT sur **5 000 nœuds** et **100 hubs SPOF** : **PASS**.

| Scénario | p95 mesuré | Seuil | Résultat |
|---|---:|---:|---|
| Parcours un niveau | 255,864 ms | 1 500 ms | PASS |
| Parcours filtré | 130,200 ms | 1 500 ms | PASS |
| Analyse SPOF | 250,820 ms | 5 000 ms | PASS |
| Pagination SPOF complète | 607,122 ms | 15 000 ms | PASS |

### Packaging

- Wheel : `openinfra-0.29.104-py3-none-any.whl`.
- sdist : `openinfra-0.29.104.tar.gz`.
- Vérification du contenu wheel : **PASS**.
- Installation du wheel dans un répertoire vierge : **PASS**.
- Smoke installé : version `0.29.104`, **19 routes multisites**, **52 migrations**, dernière migration `0052`, quatre assets runtime et trois points d’entrée publics : **PASS**.

## Empreintes des packages Python

```text
openinfra-0.29.104-py3-none-any.whl
SHA-256: 3dc0cc3ac0af563266ce9abe1fa5a2a72cc63004ed53c209e8ce24a89f150c60
Taille: 758865 octets

openinfra-0.29.104.tar.gz
SHA-256: ff1a1909095eac0fb9cbe8298d94c7cbe664ad573054dd121960958111cce169
Taille: 1557906 octets
```

## Risques résiduels

- Aucun test PostgreSQL réel n’a pu être exécuté localement.
- Aucun smoke Docker/Podman n’a pu être exécuté localement.
- L’audit CVE distant dépend de la résolution DNS de PyPI et doit être confirmé par la CI.
- La bascule réelle reste volontairement opérateur-contrôlée : promotion PostgreSQL, fencing, restauration et DNS/VIP relèvent des runbooks et outils d’infrastructure externes.
