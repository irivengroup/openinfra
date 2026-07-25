# OpenInfra 0.34.26 — rapport de qualification

## Décision

- correction Ruff format et Bandit SAST : **GO local** ;
- régression Python et frontend : **GO** ;
- promotion GitHub/production : **NO-GO** jusqu’à la réexécution réussie des binaires hébergés Ruff et Bandit.

## Objet de l’incrément

OpenInfra 0.34.26 corrige les annotations Ruff format et Bandit SAST observées après la livraison 0.34.25, sans désactiver ni exclure aucune règle.

- suppression de la commande factice contenant `admin_token="unused"` ;
- valeurs métier par défaut centralisées dans des constantes immuables ;
- Bandit figé à `1.9.4` et intégré au validateur déterministe du toolchain ;
- test AST bloquant sur les littéraux transmis aux arguments sensibles ;
- normalisation Ruff des nouveaux fichiers et de l’ordre des imports ;
- aucun `# nosec`, aucune migration, aucune modification du thème, aucune rupture API/CLI/RBAC.

## Résultats

| Contrôle | Résultat |
|---|---:|
| Fichiers de tests Python | 304/304 |
| Tests Python | 1 724/1 724 |
| Échecs | 0 |
| Instructions | 50 622 |
| Couvertes | 49 626 |
| Non couvertes | 996 |
| Couverture exacte | 98,0324759985777 % |
| Tests frontend | 103/103 |
| Migrations PostgreSQL | 60/60 |
| Migrations Oracle | 60/60 |
| Préflight Docker | 30/30 ressources |

## Limites de l’environnement

Les exécutables Ruff, Bandit et mypy ne sont pas disponibles dans le miroir Python local. Les corrections sont couvertes par compilation, tests contractuels, analyse AST et régression complète. La réexécution GitHub Actions reste la preuve finale des trois commandes hébergées.
