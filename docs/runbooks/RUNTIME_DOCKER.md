# Environnement d'exécution Docker OpenInfra

Ce runbook décrit un lab facultatif. La production OpenInfra s’exécute directement sur serveurs Linux via le runbook `RUNTIME_NATIVE.md`; Docker n’est pas requis pour le runtime de production.

Ce runbook décrit le lab Docker livré avec OpenInfra pour valider le fonctionnement réel de la solution développée : PostgreSQL, moteur de migrations applicatif, API, frontend `openinfra-web`, proxy HTTP same-origin, readiness backend, statut de schéma, sécurité API, allocation IPAM transactionnelle par API et allocation IPAM par CLI.

## Objectif

L'environnement n'est pas un simple conteneur de tests unitaires. Il exécute la solution comme un service :

- `postgres` : instance PostgreSQL 16 persistante avec healthcheck ;
- `migrate` : conteneur applicatif OpenInfra exécutant `openinfra database apply-migrations` ;
- `runtime-secrets` : service one-shot générant ou réutilisant le jeton bootstrap dans un volume séparé ;
- `auth-bootstrap` : enregistrement haché du jeton runtime dans PostgreSQL via `--token-file` ;
- `api` : API OpenInfra construite depuis le Dockerfile applicatif, lancée avec backend PostgreSQL ;
- `web` : service `openinfra-web` servant le frontend et proxyfiant `/api/*` vers `api:8080`, sans DSN ni secret exposé au navigateur ;
- `pgadmin` : console PostgreSQL de lab liée uniquement au réseau Compose ;
- `smoke` : scénario fonctionnel exécuté dans le même runtime applicatif que l'API et le frontend.

## Sécurité locale

Le fichier `.env` n'est pas versionné. Il est créé ou mis à niveau localement avec des secrets cryptographiquement aléatoires et des permissions `0600` par le script d'orchestration.

```bash
python scripts/docker_environment.py init
```

Le script conserve les valeurs non vides déjà présentes et complète atomiquement les clés absentes ou les secrets obligatoires vides, notamment la réplication PostgreSQL, la cohérence de lecture et l'administration Grafana. Le fichier `.env.example` documente les variables attendues sans contenir de secret exploitable.

Les valeurs suivantes sont gérées exclusivement par OpenInfra et ne font plus partie du contrat `.env` :

- `OPENINFRA_IMAGE_TAG` : remplacé par un override Compose temporaire calculé depuis `VERSION`, sans variable d’environnement ;
- `OPENINFRA_WEB_EDITION` : remplacé par la découverte de l’édition effective publiée par l’API active ;
- `OPENINFRA_WEB_PUBLIC_API_BASE_URL` : dérivé du proxy BFF same-origin `/api` ;
- `OPENINFRA_BOOTSTRAP_TOKEN` : remplacé par un jeton généré dans le volume Docker `openinfra-runtime-secrets`, jamais écrit dans `.env`.

Lors d’un nouvel `init`, toute occurrence héritée de ces quatre clés est supprimée atomiquement du `.env`. Les commandes recommandées du lab passent par `scripts/docker_environment.py`, qui génère un override Compose temporaire depuis la version lue dans `VERSION` puis le supprime après exécution. Les appels Docker Compose directs restent compatibles grâce au tag figé de la release et au service interne `runtime-secrets`, mais ne doivent jamais réintroduire ces clés dans `.env`.


## Intégrité du contexte de build — v0.34.19

Avant l’installation du paquet, le Dockerfile exécute :

```bash
python scripts/validate_docker_build_context.py --project-root . --json
```

Le validateur croise les sources déclarées dans `[tool.hatch.build.targets.wheel.force-include]` avec l’arbre local et les instructions `COPY` exécutées avant le packaging. Le build est bloqué si une ressource est absente ou non copiée dans l’image.

L’erreur suivante indique un arbre local incomplet, et non une dépendance PyPI défaillante :

```text
OpenInfra packaging sources are missing: docs/runbooks/RSOT_QUALITY_NON_AUTHORITATIVE_SOURCE.md
```

Restaurer la source qualifiée complète, puis vérifier avant Compose :

```bash
python scripts/validate_docker_build_context.py --project-root . --json
python -m pip wheel . --no-deps --no-build-isolation --wheel-dir dist
```

Ne pas supprimer la ressource de `pyproject.toml` et ne pas désactiver le backend de build : ce runbook fait partie du contrat runtime distribué. Le staging valide désormais toutes les sources avant la première copie, de sorte qu’un échec ne laisse aucun contenu partiel sous `src/openinfra`.

## Démarrage du runtime

```bash
python scripts/docker_environment.py up
```

Cette commande construit l'image OpenInfra, démarre PostgreSQL, applique les migrations, génère ou réutilise le jeton bootstrap dans le volume secret, l'enregistre sous forme hachée en base, démarre l'API puis `openinfra-web` uniquement lorsque les dépendances sont saines.

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

Cette commande supprime les volumes PostgreSQL et `openinfra-runtime-secrets`. Le prochain démarrage repart donc d'une base vierge et génère automatiquement un nouveau jeton bootstrap.

## Contraintes respectées

- image applicative non-root ;
- aucun secret en clair dans le code ;
- migrations versionnées, idempotentes et vérifiées par checksum ;
- healthcheck applicatif connecté à `/ready` ;
- PostgreSQL comme socle de persistance runtime ;
- API, CLI et frontend `openinfra-web` validés dans l'environnement d'exécution ;
- réseau Docker isolé ;
- données PostgreSQL stockées dans un volume nommé ;
- jeton bootstrap stocké dans un volume distinct, fichier `0400`, monté en lecture seule dans ses consommateurs.

## Authentification du runtime

Le runtime Docker active l’authentification API sans dépendre de `OPENINFRA_BOOTSTRAP_TOKEN` dans `.env`.

Le service one-shot `runtime-secrets` :

1. crée le volume `openinfra-runtime-secrets` si nécessaire ;
2. génère un jeton préfixé `oi_` à partir d’un générateur cryptographique ;
3. conserve le même jeton lors des redémarrages non destructifs ;
4. impose un répertoire `0700` et un fichier `0400` appartenant au compte runtime UID/GID `10001` ;
5. ne journalise jamais la valeur du jeton.

`auth-bootstrap` lit ce fichier avec `--token-file`, `openinfra-web` avec `--backend-bearer-token-file`, et le smoke test depuis le même montage en lecture seule. Seul le hash SHA-256 et un préfixe d’identification sont persistés en base.

La consultation explicite du jeton pour une opération d’administration s’effectue via le programme interne :

```bash
OPENINFRA_TOKEN="$(python scripts/docker_environment.py bootstrap-token)"
openinfra security whoami --backend postgresql --tenant default --token "$OPENINFRA_TOKEN"
unset OPENINFRA_TOKEN
```

Sous PowerShell :

```powershell
$OpenInfraToken = python scripts/docker_environment.py bootstrap-token
openinfra security whoami --backend postgresql --tenant default --token $OpenInfraToken
Remove-Variable OpenInfraToken
```

La commande `down` conserve le volume et donc le jeton. La commande `reset` supprime le volume et provoque une rotation automatique au prochain `up`.

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

## Validation runtime RSOT (Ressource Source of Truth)

Le smoke test Docker v0.10.0 vérifie également le module RSOT (Ressource Source of Truth) : création d'un objet device, création d'une application, relation `runs_on`, lecture paginée, récupération de la version 1 et appel CLI `openinfra rsot list-relations` contre le backend PostgreSQL du lab.

```bash
python scripts/docker_environment.py init
python scripts/docker_environment.py validate
python scripts/docker_environment.py reset
```

## Validation runtime Gouvernance des sources RSOT

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
