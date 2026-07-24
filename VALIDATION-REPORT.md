# OpenInfra 0.34.24 — rapport de qualification

## Décision

- cohérence contractuelle du header réintégré : **GO** ;
- incrément `TST-WEB-052` : **GO** ;
- checkpoint local reproductible : **GO** ;
- promotion production : **NO-GO** tant que les qualifications externes restent ouvertes.

## Objet de l’incrément

La suppression du second bandeau, encore présente dans `REQ-00748/TST-WEB-051`, contredisait la réintégration explicitement approuvée et l’exigence `REQ-00777/TST-WEB-080`. OpenInfra 0.34.24 réaligne les spécifications actives sans modifier l’interface : la double barre existante devient le comportement protégé.

Le même incrément automatise `TST-WEB-052` : les deux portails doivent afficher une carte de statistiques par composant métier, avec métriques opérationnelles et camembert lecture/mutation accessible et responsive.

## Traçabilité

- tests Python : `tests/integration/test_contract_web_header_and_statistics.py` ;
- test frontend : `web/tests/component-statistics.test.mjs` ;
- registre : `docs/release/contract-proof-registry-v4.12.csv` ;
- politique : `docs/release/contract-completeness-promotion-policy.json` ;
- CI : `.github/workflows/contract-completeness.yml` ;
- CDC actif : `REQ-00748`, `TST-WEB-051`, `REQ-00749`, `TST-WEB-052` ;
- référence détaillée de la double barre : `REQ-00777/TST-WEB-080`.

## Résultats ciblés acquis

- 2/2 tests Python contractuels ;
- 3/3 tests Node du composant statistiques ;
- double barre, recherche globale, Swagger et ReDoc présents ;
- Login/Sign-up absents ;
- cartes, métriques et camemberts présents dans les deux portails ;
- aucune modification des migrations ni du thème.


## Résultats de qualification complète

| Contrôle | Résultat |
|---|---:|
| Fichiers de tests Python | 301/301 |
| Tests Python | 1 715/1 715 |
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
| Préflight Docker source et sdist | 30/30 ressources |
| Quality gate global | code 0 |
| Wheel reproductible | PASS |
| Sdist reproductible | PASS |
| Wheel reconstruit depuis le sdist | identique |
| Smoke du wheel hors source avec runtime local | PASS |

## Métriques GATE-14

- 667 tests contractuels ;
- 35 preuves automatisées ;
- 584 preuves partielles ;
- 48 preuves externes ;
- 48 sélecteurs pytest résolus ;
- 83 fichiers d’évidence ;
- zéro preuve manquante ;
- zéro exigence N1 non classifiée.


Le smoke strict dans un environnement Python vierge est bloqué avant l’exécution d’OpenInfra : le registre configuré ne fournit pas `defusedxml>=0.7.1`. Le même wheel installé hors de l’arbre source avec le runtime local disponible passe intégralement.

## Qualifications externes restantes

- Ruff, mypy, Bandit, Twine et pip-audit selon disponibilité de l’environnement ;
- build Vite, ESLint JSX et npm audit selon disponibilité du registre Node ;
- Docker Compose réel et scans d’images ;
- PostgreSQL live et Oracle 19c Enterprise ;
- fournisseurs DDI réels, systemd, fédération d’identité, charge et reprise.

Aucune promotion production ne doit contourner ces preuves externes.
