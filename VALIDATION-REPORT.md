# OpenInfra 0.34.27 — rapport de qualification

## Décision

- correction de la recherche globale : **GO** ;
- stabilisation de la topologie DAST primaire : **GO contractuel local** ;
- régression Python, frontend, packaging et quality gate : **GO** ;
- promotion GitHub/production : **NO-GO** jusqu’à la réexécution réussie des jobs hébergés Ruff, mypy, Bandit, Python 3.12/3.13 et du DAST Docker réel.

## Objet de l’incrément

OpenInfra 0.34.27 corrige cinq régressions observées dans GitHub Actions et dans le portail Web :

- la recherche globale demandait `limit=80`, alors que le contrat backend accepte au maximum 25 résultats ;
- les deux portails normalisent maintenant la limite entre 1 et 25 et utilisent 25 pour la requête globale ;
- la topologie DAST démarre explicitement PostgreSQL, les secrets runtime, les migrations, PgBouncer primaire, le bootstrap d’identité, l’API et le Web avec le routage de lecture désactivé ;
- l’API ne dépend plus de la santé de PgBouncer replica lorsque le routage de lecture est désactivé ; la topologie HA complète reste disponible pour les déploiements normaux ;
- les fichiers ciblés par Ruff dans les jobs Python 3.12/3.13 et packaging reproductible ont été normalisés sans réduire la portée des contrôles ;
- les tests de contrat vérifient la limite backend, l’absence de `limit=80`, la topologie DAST primaire et la conservation indépendante des services replica.

Aucune migration, règle métier, rupture API/CLI/RBAC ou modification du thème approuvé n’a été introduite.

## Résultats

| Contrôle | Résultat |
|---|---:|
| Fichiers de tests Python | **305/305** |
| Tests Python | **1 725/1 725** |
| Échecs | **0** |
| Instructions | **50 623** |
| Couvertes | **49 627** |
| Non couvertes | **996** |
| Couverture exacte | **98,032514864785 %** |
| Tests frontend | **104/104** |
| Tests ciblés de régression | **28/28** |
| Quality gate global | **code 0** |
| Préflight Docker | **30/30 ressources** |
| Migrations PostgreSQL | **60/60** |
| Migrations Oracle | **60/60** |
| Archive migrations | **123/123 membres** |
| GATE-14 automatisées/partielles/externes | **35 / 584 / 48** |
| Sélecteurs pytest GATE-14 | **48** |
| Fichiers d’évidence GATE-14 | **83** |

## Validations exécutées

- compilation Python de `src`, `tests`, `scripts` et du backend de build ;
- security gate interne ;
- contrats statiques frontend et WCAG 2.2 AA ;
- 104 tests Node autonomes ;
- OpenAPI principal et CDC 4.12 ;
- CDC 4.12, roadmap 2.5 et alignement Enterprise ;
- catalogue Oracle 60/60 ;
- préflight du contexte Docker 30/30 ;
- campagne Python isolée par fichier avec 305 fragments Coverage combinés uniquement après code retour 0 ;
- quality gate global avec code retour 0 ;
- construction reproductible du wheel, du sdist et du catalogue migrations sous `SOURCE_DATE_EPOCH`.

## Limites de l’environnement

- le miroir Python local retourne HTTP 503 pour Ruff ; Ruff `0.15.22` n’a donc pas pu être exécuté localement ;
- mypy `2.2.0`, Bandit `1.9.4`, Twine et pip-audit ne sont pas disponibles localement ;
- Docker Engine, PostgreSQL live, Oracle 19c, fournisseurs DDI, systemd et fédération d’identité ne sont pas disponibles dans l’environnement de qualification ;
- la topologie DAST réelle doit être rejouée dans GitHub Actions avant promotion ;
- les matrices hébergées Python 3.12 et 3.13 doivent repasser avec les outils verrouillés.
