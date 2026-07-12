# OpenInfra v0.32.0 — rapport de validation

Date : 2026-07-12

## Objet

Cette livraison implémente **P18 / EPIC-1802 — audit sécurité bloquant de release**. Elle transforme les contrôles de sécurité auparavant dispersés en une certification versionnée, probatoire et non contournable avant promotion d'une image OpenInfra.

Elle corrige également l'initialisation de l'environnement Docker : `scripts/docker_environment.py init` génère et met à niveau tous les secrets obligatoires, y compris la réplication PostgreSQL et la cohérence de lecture.

## Contrôles de release

Le catalogue fermé exige huit résultats :

1. détection de secrets et validation des workflows ;
2. SAST Bandit ;
3. non-régression RBAC et authentification ;
4. audit des dépendances Python ;
5. audit des dépendances Node ;
6. scan Trivy du dépôt ;
7. scan Trivy de l'image réellement construite ;
8. sonde DAST HTTP sur l'API et le BFF web.

Une certification n'est délivrée que lorsque les huit contrôles sont présents et réussis. Le mode hors ligne est explicitement non certifiant. Les preuves stdout/stderr sont expurgées, écrites atomiquement et liées au rapport par SHA-256.

Trivy est épinglé par tag et digest OCI :

```text
aquasec/trivy:0.72.0@sha256:cffe3f5161a47a6823fbd23d985795b3ed72a4c806da4c4df16266c02accdd6f
```

## Environnement Docker

`python scripts/docker_environment.py init` :

- crée un `.env` en mode `0600` ;
- génère des secrets cryptographiquement aléatoires ;
- ajoute les clés obligatoires absentes ;
- remplace uniquement les secrets obligatoires laissés vides ;
- conserve les valeurs non vides existantes ;
- effectue les mises à niveau par remplacement atomique ;
- reste idempotent.

## Compatibilité

- aucune migration PostgreSQL supplémentaire ;
- aucune suppression ou modification incompatible d'API/CLI métier ;
- aucune dépendance runtime de production ajoutée ;
- outils d'audit maintenus dans les dépendances de développement/sécurité ;
- aucune modification des feuilles CSS.

Les deux feuilles de style sont identiques octet par octet à la version 0.31.4 :

```text
SHA-256 : 1df955fd51fdd253590c391a3ee9430c9ca9db88b76819f4482007a5cf567dad
```

## Validations exécutées

### Python et qualité

- collection complète : **1 132 tests sur 196 fichiers** ;
- exécution complète par partitions isolées : **1 132 tests réussis** ;
- couverture exacte : **98,00081495441349 %** ;
- lignes couvertes : **38 481 / 39 266** ;
- lignes non couvertes : **785** ;
- Ruff format : **PASS**, 321 fichiers conformes ;
- Ruff lint : **PASS** ;
- mypy strict : **PASS**, 103 modules ;
- `compileall` : **PASS** ;
- Bandit : **PASS** ;
- gate de sécurité interne : **PASS** ;
- quality gate global : **PASS** ;
- OpenAPI runtime et miroir CDC : **PASS** ;
- workflows GitHub Actions : **PASS** ;
- six profils installateur : **PASS**.

Les suites réseau ont été exécutées dans des processus isolés afin d'éviter qu'un serveur de test déjà terminé bloque la fermeture d'un lot. La collection complète a été conservée ; aucun test n'a été désactivé ou exclu.

### Frontend

- `npm ci` : **PASS** ;
- tests Node : **60 réussis** ;
- validation statique : **PASS** ;
- ESLint JSX/accessibilité : **PASS** ;
- contrat WCAG 2.2 AA : **PASS** ;
- build Vite : **PASS** ;
- chunks dynamiques : **11** ;
- `npm audit --audit-level=moderate` : **PASS**, aucune vulnérabilité.

### Packaging

- build isolé wheel/sdist : **PASS** ;
- vérification du contenu obligatoire : **PASS** ;
- installation du wheel dans un environnement Python vierge : **PASS** ;
- `pip check` : **PASS** ;
- smoke installé : version, scripts console, OpenAPI, assets, migrations et huit contrôles de sécurité **PASS**.

## Limites de validation

Docker n'est pas disponible dans le sandbox. Les scans Trivy réels de l'image et le DAST contre la stack Compose n'ont donc pas été exécutés localement. Ils sont obligatoires dans `.github/workflows/release-security.yml` et toute absence de Docker, de Trivy, de service HTTP ou de preuve rend la certification non complète et bloquante.

`pip-audit` n'a pas pu interroger `pypi.org` en raison d'un échec de résolution DNS. Le contrôle réseau demeure obligatoire et bloquant dans le workflow de release ; il n'a pas été converti en avertissement.
