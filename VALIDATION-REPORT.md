# Rapport de validation — OpenInfra Python POO v0.34.1

## Objet

La version **0.34.1** corrige la migration PostgreSQL `0057_federated_identity_team_sync.sql` qui échouait avec un identifiant tel que `identity_team_sync_sources_p 0`.

PostgreSQL `format()` n’effectue pas de zéro-padding avec `%1$02s` : la largeur est complétée par un espace. La migration utilise désormais :

- `lpad(partition_index::text, 2, '0')` pour produire `00` à `31` ;
- `%I` pour encoder les identifiants SQL ;
- `%s` uniquement pour la valeur entière bornée du remainder.

Les **96 partitions** des trois tables sont ainsi nommées de manière déterministe :

- `identity_team_sync_sources_p00` à `identity_team_sync_sources_p31` ;
- `identity_team_sync_runs_p00` à `identity_team_sync_runs_p31` ;
- `federated_identity_links_p00` à `federated_identity_links_p31`.

## Prévention de régression

Le validateur de migrations PostgreSQL refuse désormais les directives `format()` de type `%02s` ou `%1$02s`, car elles peuvent introduire des espaces dans les identifiants dynamiques. Le message impose `lpad()` pour les suffixes numériques et `%I` pour les identifiants.

La migration conserve son numéro `0057` : elle avait échoué avant l’insertion dans `openinfra_schema_migrations` et l’exécuteur annule la transaction. Après mise à niveau, elle peut donc être relancée sans migration de réparation ni nettoyage manuel.

## Validations exécutées

| Contrôle | Résultat |
|---|---:|
| Tests unitaires, architecture et performance | **714/714 PASS** |
| Tests d’intégration — 169 fichiers | **724/724 PASS** |
| Total Python | **1 438/1 438 PASS** |
| Tests migration 0057/catalogue/politique | **17/17 PASS** |
| Couverture globale | **46 348 lignes, 1 140 non couvertes, 98 % PASS** |
| `coverage report --fail-under=98` | **PASS** |
| Ruff format | **442 fichiers PASS** |
| Ruff lint | **PASS** |
| mypy strict | **135 modules PASS** |
| Bandit | **PASS** |
| Tests frontend | **79/79 PASS** |
| Contrat statique frontend | **PASS** |
| WCAG 2.2 AA / ESLint JSX | **PASS** |
| Build Vite et budget initial | **PASS** |
| Audit npm | **0 vulnérabilité** |
| OpenAPI, documentation GA et workflows | **PASS via matrice d’intégration** |
| Build wheel et sdist | **PASS** |
| `twine check` | **PASS** |
| Vérification du contenu wheel/sdist | **PASS** |
| Installation du wheel hors dépôt | **PASS** |
| Smoke du wheel installé | **PASS** |
| Contrat migration 0057 dans le wheel | **PASS** |

## Non-régression

- PostgreSQL reste le backend par défaut.
- Oracle reste optionnel pour les éditions compatibles.
- SAML, LDAP avancé, Team Sync, API, CLI et unités systemd sont inchangés fonctionnellement.
- La chaîne reste à **57 migrations** ; la dernière reste `0057_federated_identity_team_sync.sql`.
- Aucun endpoint, aucune commande CLI métier et aucune permission RBAC ne sont supprimés.
- Le CSS source et runtime conserve le SHA-256 `fb7feabe378613ac41efb18db94b0d95a8faa916b6f782c9fd0ea2b0d8e9fcf4`.
- Le CDC et la roadmap ne sont pas modifiés : il s’agit d’un correctif d’implémentation d’une exigence existante.

## Limites de l’environnement

Aucun serveur PostgreSQL ni moteur Docker n’est installé dans l’environnement de construction. L’application de la migration sur une instance PostgreSQL réelle n’est donc pas revendiquée localement. La validation couvre le catalogue, le découpage transactionnel, l’exécuteur simulé, le rendu déterministe des 96 noms de partitions, les politiques de migration et la non-régression complète.
