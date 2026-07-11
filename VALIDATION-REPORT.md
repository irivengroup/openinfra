# OpenInfra v0.30.5 — rapport de validation

Date : 2026-07-11

## Périmètre

Cette livraison regroupe trois corrections cohérentes :

1. durcissement des dépendances détectées par `pip-audit` ;
2. optimisation de la charte graphique React/runtime packagé ;
3. regroupement Swagger/ReDoc par composant puis contexte métier.

## Sécurité des dépendances

- `cryptography>=48.0.1,<50.0` afin d'exclure les wheels antérieurs à la correction OpenSSL publiée en juin 2026 ;
- `urllib3>=2.7.0,<3.0` afin d'exclure les vulnérabilités corrigées en 2.7.0 ;
- `pip>=26.0` avant installation dans la CI et dans l'image Docker ;
- `pip-audit --strict` reste un gate bloquant sur `requirements/security-audit.txt`.

L'environnement local ne peut pas résoudre `pypi.org`. Le gate `pip-audit` complet n'a donc pas pu être rejoué localement ; les planchers corrigés sont vérifiés par tests de contrat et le contrôle réseau reste bloquant en CI.

## Documentation API

- 331 opérations OpenAPI classifiées ;
- 69 contextes métier ;
- 16 composants ;
- un tag unique par opération ;
- groupes ReDoc via `x-tagGroups` ;
- tri Swagger déterministe par composant puis contexte ;
- deux documents OpenAPI synchronisés et valides ;
- 319 paths OpenAPI.

## Charte graphique

- design system commun aux deux portails ;
- identité bleu nuit/IONOS conservée ;
- surfaces, cartes, formulaires, tableaux, navigation et états interactifs harmonisés ;
- parité exacte des fichiers CSS React/runtime packagé ;
- modes `prefers-contrast` et `prefers-reduced-motion` conservés ;
- aucune nouvelle dépendance frontend ni ressource média ;
- audit npm : 0 vulnérabilité.

## Tests et qualité

- 990 tests Python réussis en 163,18 s ;
- couverture globale : 98,01 % ;
- seuil contractuel de 98 % : PASS ;
- 51 tests frontend réussis ;
- Ruff format : 289 fichiers conformes ;
- Ruff lint : PASS ;
- mypy strict : 93 modules, PASS ;
- `compileall` : PASS ;
- Bandit : PASS ;
- security gate : PASS ;
- quality gate : PASS ;
- ESLint JSX : PASS ;
- WCAG 2.2 AA : PASS ;
- build Vite : PASS ;
- validation frontend statique : PASS ;
- six profils installateurs : PASS ;
- CDC 4.9.0 : 840 exigences / 529 entités, PASS ;
- roadmap 2.1.0 : 21 phases / 125 epics / 10 gates / 106 tests, PASS ;
- runtime natif : PASS.

## Régression de performance ASGI

Profil local : 200 requêtes par scénario, concurrence 25, 10 warmups.

| Scénario | p95 | p99 | Seuil p95/p99 |
|---|---:|---:|---:|
| API `/health` | 10,977 ms | 12,653 ms | 150 / 300 ms |
| Web `/bootstrap.json` | 0,258 ms | 0,412 ms | 150 / 300 ms |
| Proxy BFF | 0,498 ms | 0,953 ms | 200 / 400 ms |

Le benchmark valide le transport ASGI et non une certification de capacité PostgreSQL réelle.

## Limites d'environnement

- résolution DNS de `pypi.org` indisponible pour `pip-audit` ;
- Docker/Podman et PostgreSQL réel non disponibles ;
- capture Chromium headless non exploitable dans cet environnement.

Ces validations restent bloquantes dans la CI ou sur une plateforme Pro/Enterprise représentative.
