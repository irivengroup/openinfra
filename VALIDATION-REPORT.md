# OpenInfra 0.34.25 — rapport de qualification

## Décision

- correction de la CI qualité et de l’upload GATE-14 : **GO local** ;
- régression Python et frontend : **GO** ;
- checkpoint local reproductible : **GO** ;
- promotion GitHub/production : **NO-GO** jusqu’à la réexécution réussie des jobs hébergés.

## Objet de l’incrément

OpenInfra 0.34.25 corrige deux défauts de pipeline observés sur le checkpoint 0.34.24 :

1. le job `Format, lint and strict typing` pouvait absorber une nouvelle version de Ruff ou mypy sans modification du dépôt et ne conservait pas de diagnostic séparé par outil ;
2. l’étape `Upload immutable GATE-14 evidence`, exécutée avec `if: always()`, exigeait `report.json`, `dist/*` et `web/dist/**` même lorsque le job avait été interrompu avant leur génération, produisant une seconde erreur sans rapport avec la cause initiale.

Le correctif verrouille le toolchain de qualité, vérifie les versions réellement installées, sépare formatage, lint, typage et compilation, puis distingue les artefacts de diagnostic sur échec des preuves immuables sur succès.

## Changements structurants

- Ruff `0.15.22` et mypy `2.2.0` figés dans `requirements/dev.txt` et `pyproject.toml` ;
- `scripts/validate_quality_toolchain.py` bloque toute absence ou dérive de version ;
- `scripts/prepare_ci_evidence.py` matérialise atomiquement le contexte d’exécution dès le début du job ;
- sorties Ruff format, Ruff lint et mypy écrites séparément sous `artifacts/quality/` avec `set -o pipefail` ;
- upload de diagnostic sous `if: failure()` avec `if-no-files-found: warn` ;
- upload immuable sous `if: success()` avec `if-no-files-found: error` ;
- stratégie appliquée aux GATE-12, GATE-13 et GATE-14 ;
- validation du même toolchain ajoutée à la CI principale, au packaging et à l’identité avancée ;
- tests de contrat mis à jour pour la commande mypy renforcée ;
- aucune migration, aucune modification fonctionnelle, aucune rupture API/CLI/RBAC et aucune modification du thème approuvé.

## Résultats ciblés acquis

- 16/16 workflows GitHub Actions analysables en YAML ;
- 32/32 tests de workflows et de contrats CI ;
- 26/26 tests ciblés finaux du toolchain, GATE-12, GATE-13 et GATE-14 ;
- qualité documentaire, sécurité interne, OpenAPI, CDC 4.12, roadmap 2.5 et préflight Docker : PASS ;
- frontend autonome : 103/103 ;
- migrations PostgreSQL et Oracle inchangées : 60/60 pour chaque catalogue.

## Résultats de qualification complète

| Contrôle | Résultat |
|---|---:|
| Fichiers de tests Python | 303/303 |
| Tests Python | 1 723/1 723 |
| Échecs | 0 |
| Instructions | 50 621 |
| Instructions couvertes | 49 625 |
| Instructions non couvertes | 996 |
| Couverture exacte | 98,03243713083504 % |
| Seuil obligatoire | >= 98 % — PASS |
| Tests frontend autonomes | 103/103 |
| Migrations PostgreSQL | 60/60 |
| Migrations Oracle | 60/60 |
| Catalogue autonome des migrations | 123/123 membres |
| Préflight Docker | 30/30 ressources |
| Quality gate global | code 0 |
| Wheel reproductible | PASS |
| Sdist reproductible | PASS |
| Wheel reconstruit depuis le sdist | identique |
| Smoke du wheel hors arbre source | PASS |

## Métriques GATE-14

- 667 tests contractuels ;
- 35 preuves automatisées ;
- 584 preuves partielles ;
- 48 preuves externes ;
- 48 sélecteurs pytest résolus ;
- 83 fichiers d’évidence ;
- zéro preuve manquante ;
- zéro exigence N1 non classifiée.

## Limites de l’environnement de qualification

Ruff et mypy n’étaient pas installables depuis le miroir Python disponible dans l’environnement local. Leur exécution réelle reste donc à confirmer par GitHub Actions avec les versions désormais verrouillées. Les tests contractuels vérifient que ces commandes sont bloquantes, séparées et que leurs journaux sont conservés.

Restent également externes : Bandit, Twine, pip-audit, Vite/ESLint/npm audit selon disponibilité des registres, Docker Compose réel, PostgreSQL live, Oracle 19c Enterprise, fournisseurs DDI, systemd, identité fédérée, charge et reprise.

Aucune promotion production ne doit contourner ces preuves externes.
