# Environnement d'exécution Docker OpenInfra

Ce runbook décrit un lab facultatif. La production OpenInfra s’exécute directement sur serveurs Linux via le runbook `RUNTIME_NATIVE.md`; Docker n’est pas requis pour le runtime de production.

Ce runbook décrit le lab Docker livré avec OpenInfra pour valider le fonctionnement réel de la solution développée : PostgreSQL, moteur de migrations applicatif, API, frontend `openinfra-web`, proxy HTTP same-origin, readiness backend, statut de schéma, sécurité API, allocation IPAM transactionnelle par API et allocation IPAM par CLI.

## Objectif

L'environnement n'est pas un simple conteneur de tests unitaires. Il exécute la solution comme un service :

- `postgres` : instance PostgreSQL 16 persistante avec healthcheck ;
- `migrate` : conteneur applicatif OpenInfra exécutant `openinfra database apply-migrations` ;
- `api` : API OpenInfra construite depuis le Dockerfile applicatif, lancée avec backend PostgreSQL ;
- `web` : service `openinfra-web` servant le frontend et proxyfiant `/api/*` vers `api:8080`, sans DSN ni secret exposé au navigateur ;
- `pgadmin` : console PostgreSQL de lab liée uniquement au réseau Compose ;
- `smoke` : scénario fonctionnel exécuté dans le même runtime applicatif que l'API et le frontend.

## Sécurité locale

Le fichier `.env` n'est pas versionné. Il est généré localement avec un secret aléatoire et des permissions `0600` par le script d'orchestration.

```bash
python scripts/docker_environment.py init
```

Le fichier `.env.example` documente les variables attendues sans contenir de secret exploitable.

## Démarrage du runtime

```bash
python scripts/docker_environment.py up
```

Cette commande construit l'image OpenInfra, démarre PostgreSQL, applique les migrations via la CLI OpenInfra, démarre l'API uniquement après succès du conteneur `migrate`, puis démarre `openinfra-web` uniquement quand l'API est saine.

## Validation fonctionnelle runtime

```bash
python scripts/docker_environment.py validate
```

Le scénario de validation vérifie :

1. `/ready` retourne un état prêt après connexion PostgreSQL réelle et contrôle du schéma ;
2. `/health` retourne l'état de vie du processus API ;
3. `/api/v1/version` retourne la version attendue ;
4. `/api/v1/database/schema` confirme que le schéma PostgreSQL est à jour ;
5. `/api/v1/ipam/allocate` crée une réservation IPAM ;
6. un second appel API avec la même clé confirme l'idempotence ;
7. le cycle de vie sécurité crée, liste et révoque un jeton de test sans exposer de hash ;
8. la commande `openinfra ipam allocate --backend postgresql` fonctionne dans le conteneur applicatif ;
9. `openinfra-web` répond sur `/health`, sert `/config.json`, sert l'interface HTML et proxyfie `/api/v1/version` vers le backend sans exposer `OPENINFRA_DATABASE_DSN`.

## Commandes de migration PostgreSQL

```bash
openinfra database status --postgres-dsn "$OPENINFRA_DATABASE_DSN" --root installers/migrations/postgresql
openinfra database apply-migrations --postgres-dsn "$OPENINFRA_DATABASE_DSN" --root installers/migrations/postgresql
openinfra database apply-migrations --postgres-dsn "$OPENINFRA_DATABASE_DSN" --root installers/migrations/postgresql --dry-run
```

Le moteur maintient `openinfra_schema_migrations`, enregistre le checksum SHA-256 de chaque migration et bloque l'exécution si une migration déjà appliquée diverge du fichier source.

## Supervision locale

```bash
python scripts/docker_environment.py status
```

## Arrêt sans suppression des données

```bash
python scripts/docker_environment.py down
```

## Réinitialisation complète

```bash
python scripts/docker_environment.py reset
```

Cette commande supprime aussi le volume PostgreSQL Docker afin de repartir d'un état vierge.

## Contraintes respectées

- image applicative non-root ;
- aucun secret en clair dans le code ;
- migrations versionnées, idempotentes et vérifiées par checksum ;
- healthcheck applicatif connecté à `/ready` ;
- PostgreSQL comme socle de persistance runtime ;
- API, CLI et frontend `openinfra-web` validés dans l'environnement d'exécution ;
- réseau Docker isolé ;
- données PostgreSQL stockées dans un volume nommé.

## Authentification du runtime v0.7.0

Le runtime Docker exécute la solution avec l’authentification API activée. Le script `python scripts/docker_environment.py init` génère deux valeurs locales non versionnées dans `.env` :

- `OPENINFRA_POSTGRES_PASSWORD` pour PostgreSQL ;
- `OPENINFRA_BOOTSTRAP_TOKEN` pour amorcer un client API `docker-runtime`.

La chaîne Compose suit l’ordre suivant : PostgreSQL sain, migrations appliquées, jeton API haché en base, API démarrée avec `OPENINFRA_AUTH_REQUIRED=true`, smoke tests API/CLI. Les smoke tests appellent `/api/v1/ipam/allocate` avec l’en-tête `Authorization: Bearer ...` et valident l’idempotence IPAM sur le backend PostgreSQL.

Le jeton n’est pas stocké en clair en base. Seul le hash SHA-256 et un préfixe d’identification opérationnelle sont persistés. La validation runtime vérifie aussi la création d’un jeton temporaire, l’inventaire paginé des métadonnées et la révocation auditée.

## Validation runtime IAM v0.7.0

Le scénario `docker/openinfra-runtime-smoke.py` crée un utilisateur IAM, un groupe, une appartenance et vérifie les rôles effectifs via l’API authentifiée. Cette étape s’exécute après migration PostgreSQL et bootstrap du jeton administrateur, afin de valider le fonctionnement réel de la solution avec le backend PostgreSQL du lab.

## Validation runtime ABAC v0.8.0

Le smoke test Docker crée une règle ABAC `runtime-docker-par1-prod` autorisant `docker-runtime` à exécuter `ipam.allocate` uniquement pour le site `PAR1` et l’environnement `prod`. Il vérifie ensuite :

- création de règle via `/api/v1/access/rules` ;
- inventaire paginé des règles ;
- évaluation via `/api/v1/access/evaluate` ;
- allocation IPAM API authentifiée avec contexte autorisé ;
- allocation IPAM CLI en backend PostgreSQL avec `--auth-token`, `--site-code` et `--environment`.

L’objectif est de valider que l’environnement d’exécution contrôle réellement RBAC + ABAC sur la solution démarrée, et pas seulement les tests unitaires.

## Validation runtime Audit Trail v0.9.0

Le smoke test Docker vérifie désormais le journal d’audit dans l’environnement d’exécution réel :

- `GET /api/v1/audit/events` retourne des événements avec `record_hash` ;
- `GET /api/v1/audit/integrity` valide le chaînage SHA-256 ;
- `POST /api/v1/audit/export` produit un export JSONL sans secret applicatif.

Ces contrôles s’exécutent après les scénarios sécurité, IAM, ABAC, IPAM API et IPAM CLI afin de vérifier que les événements issus des flux réels sont consultables et intègres en backend PostgreSQL.

## Validation runtime Source of Truth

Le smoke test Docker v0.10.0 vérifie également le module Source of Truth : création d'un objet device, création d'une application, relation `runs_on`, lecture paginée, récupération de la version 1 et appel CLI `openinfra sot list-relations` contre le backend PostgreSQL du lab.

```bash
python scripts/docker_environment.py init
python scripts/docker_environment.py validate
python scripts/docker_environment.py reset
```

## Validation runtime Gouvernance des sources SOT

Le smoke test Docker v0.11.0 vérifie que l'environnement d'exécution applique la gouvernance des sources : création d'une règle autoritative sur l'attribut `serial`, évaluation d'une mise à jour non autoritative, refus attendu avec stratégie `reject`, et vérification que les endpoints authentifiés restent protégés par RBAC.

```bash
python scripts/docker_environment.py init
python scripts/docker_environment.py validate
python scripts/docker_environment.py reset
```


## Validation runtime DCIM physique P04

Le smoke test Docker v0.12.0 vérifie le modèle physique DCIM contre l’API authentifiée et le backend PostgreSQL : création d’une salle avec étage, grille, zone et coordonnées, puis localisation CLI d’un équipement dans cette salle avec étage, zone, ligne, colonne et coordonnées X/Y/Z.

```bash
python scripts/docker_environment.py init
python scripts/docker_environment.py validate
python scripts/docker_environment.py reset
```

## Smoke runtime v0.13.0 — capacité rack

Le smoke test Docker v0.13.0 vérifie le scénario rack complet contre l'API authentifiée et le backend PostgreSQL : création d'une salle physique, définition d'un rack double face, localisation CLI d'un équipement en face avant avec hauteur U, puis consultation de l'occupation du rack via `GET /api/v1/dcim/rack-capacity`.

## Smoke runtime v0.14.0 — QR terrain et preuve de scan

Le smoke test Docker v0.14.0 vérifie le scénario terrain complet dans l’environnement d’exécution OpenInfra : équipement localisé en rack, génération de fiche de localisation via l’API authentifiée, extraction du payload QR compact, vérification du scan via `POST /api/v1/dcim/verify-scan`, puis contrôle CLI `openinfra dcim verify-scan` contre le backend PostgreSQL.

```bash
python scripts/docker_environment.py init
python scripts/docker_environment.py validate
python scripts/docker_environment.py reset
```


## Smoke runtime v0.15.0 — plans 2D salle et rack elevation

Le smoke test Docker v0.15.0 prolonge le scénario DCIM P04 contre l’API authentifiée et le backend PostgreSQL : après création de la salle, définition du rack et localisation en rack, il appelle `GET /api/v1/dcim/room-plan` en JSON/SVG puis `GET /api/v1/dcim/rack-elevation` en JSON/HTML. Le contrôle vérifie que le plan contient le rack attendu, que le SVG est rendu, que l’occupation U correspond à la localisation et que la fiche HTML est produite.

```bash
python scripts/docker_environment.py init
python scripts/docker_environment.py validate
python scripts/docker_environment.py reset
```


## Correctif v0.22.2

Le healthcheck `/ready` est défini uniquement sur le service `api`. Les services one-shot `migrate`, `auth-bootstrap` et `smoke` ne doivent pas hériter d’un healthcheck API depuis le `Dockerfile`. Si `openinfra-migrate` sort avec le code `1`, consulter d’abord `docker logs openinfra-migrate` : le statut healthcheck n’est plus utilisé comme diagnostic pour les migrations.

## Administration PostgreSQL avec pgAdmin4 — v0.22.2

Le lab Docker Compose inclut le service `pgadmin` pour administrer la base PostgreSQL de test. Après `python scripts/docker_environment.py init`, les variables suivantes sont générées dans `.env` :

```env
OPENINFRA_PGADMIN_EMAIL=admin@openinfra.tld
OPENINFRA_PGADMIN_PASSWORD=<valeur generee localement>
OPENINFRA_PGADMIN_BIND=127.0.0.1
OPENINFRA_PGADMIN_PORT=5050
OPENINFRA_PGADMIN_IMAGE=dpage/pgadmin4:latest
```

Démarrage recommandé :

```bash
python scripts/docker_environment.py up
```

Accès local :

```text
http://127.0.0.1:5050
```

Le serveur PostgreSQL Compose est préenregistré sous le nom `OpenInfra PostgreSQL` avec l’hôte interne `postgres`, le port `5432`, la base `openinfra` et l’utilisateur `openinfra`. Lors de la première connexion au serveur depuis pgAdmin4, saisir la valeur `OPENINFRA_POSTGRES_PASSWORD` présente dans `.env`. Le volume `openinfra-pgadmin-data` conserve la configuration pgAdmin4 entre deux démarrages.

Pour exposer pgAdmin4 uniquement sur un autre port local :

```env
OPENINFRA_PGADMIN_BIND=127.0.0.1
OPENINFRA_PGADMIN_PORT=5051
```

Ne pas exposer `OPENINFRA_PGADMIN_BIND` sur `0.0.0.0` dans un poste non isolé : ce service est prévu pour l’administration locale du lab.

## Correctif v0.22.3

La migration IPAM enterprise `0015` est compatible avec une base PostgreSQL fraîche créée depuis `0001_bootstrap.sql`. Elle ajoute et renseigne `prefixes.family` avant de créer l’index `idx_prefixes_vrf_family`, ce qui corrige l’erreur `column "family" does not exist` observée dans `openinfra-migrate`.

## Correctif v0.23.1 — racine API et logs Docker

`GET /` et `GET /api/v1` retournent un document JSON de découverte du service. L’ouverture de `http://127.0.0.1:8080/` dans un navigateur ne doit donc plus retourner `{"error": "not_found"}`.

Contrôles manuels recommandés après démarrage Compose :

```bash
curl http://127.0.0.1:8080/
curl http://127.0.0.1:8080/api/v1
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/ready
curl http://127.0.0.1:8080/api/v1/version
docker logs openinfra-api
```

Au démarrage, `openinfra-api` écrit un événement JSON `openinfra_api_started` sur stdout afin que `docker logs openinfra-api` confirme le backend, le port et les URLs opérationnelles exposées par le conteneur.


## Documentation API runtime v0.25.2

Le point d’entrée `GET /` et `GET /api/v1` publie les liens de documentation `Swagger UI` (`/docs` et `/swagger`), `ReDoc` (`/redoc`) et le contrat OpenAPI YAML (`/openapi.yaml` et `/api/v1/openapi.yaml`). Les smoke tests HTTP vérifient ces routes afin d’éviter une régression de découvrabilité API.
