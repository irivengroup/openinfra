# Architecture OpenInfra Python

## Décision de conception

Le socle est un modular monolith Python strictement orienté objet. Il applique une architecture hexagonale : le domaine ne dépend d'aucune technologie d'interface ou de persistance, les services applicatifs orchestrent les cas d'usage, l'infrastructure implémente les ports, et les interfaces exposent CLI/API.

## Couches

- `openinfra.domain` : entités, value objects, politiques métier, erreurs contrôlées.
- `openinfra.application` : commandes, services applicatifs, ports, transaction manager, readiness et statut de schéma.
- `openinfra.infrastructure` : persistance JSON atomique, adaptateur PostgreSQL runtime, moteur de migrations PostgreSQL, readiness backend, validation contractuelle.
- `openinfra.interfaces` : CLI et API HTTP.
- `Dockerfile`, `compose.yaml`, `docker/openinfra-runtime-smoke.py` : environnement d’exécution validant PostgreSQL, migrations, API et CLI.

## Contraintes respectées

- Pas d'ITSM intégré ; l'intégration ITSM restera externe par connecteurs.
- Les opérations DCIM imposent ligne et colonne pour toute localisation en salle.
- Les opérations IPAM passent par un service transactionnel et une clé d'idempotence.
- Toute écriture importante produit un audit event.
- La migration PostgreSQL utilise partitionnement, contraintes, index et tables d'audit.
- Les migrations runtime sont exécutées par l'application, suivies dans `openinfra_schema_migrations` et contrôlées par checksum SHA-256.
- Les adaptateurs runtime sont sélectionnables sans changer le domaine ni les services applicatifs.
- La sonde `/ready` valide le backend de persistance configuré et, en PostgreSQL, l'état du schéma.

## Persistance

Deux adaptateurs sont disponibles :

1. JSON atomique pour développement, démonstration et tests reproductibles.
2. PostgreSQL runtime pour production, via `psycopg` optionnel et DSN explicite.

L'adaptateur PostgreSQL implémente les référentiels DCIM, IPAM et audit sur le schéma `0001_bootstrap.sql`. Les transactions sont courtes et bornées par un `UnitOfWork` applicatif. Le registre de session est local au thread afin de supporter l'API HTTP multithreadée sans partager une connexion entre requêtes.

## Migrations PostgreSQL

Le moteur `PostgreSQLMigrationExecutor` charge les fichiers `migrations/postgresql/*.sql`, vérifie leur structure minimale, calcule un checksum SHA-256, applique uniquement les migrations absentes et refuse une migration déjà appliquée dont le contenu a changé. La CLI expose :

```bash
openinfra database status
openinfra database apply-migrations
openinfra database apply-migrations --dry-run
```

L'API expose `/api/v1/database/schema` pour le statut opérationnel du schéma.

## Compatibilité

La CLI et les services applicatifs forment le contrat stable initial. Les futurs adaptateurs REST avancé, GraphQL, worker asynchrone et UI devront consommer les mêmes ports applicatifs sans modifier les invariants de domaine.

## Environnement d’exécution

Le runtime Docker exécute la solution comme un service complet. PostgreSQL est démarré avec healthcheck, les migrations sont appliquées par la CLI OpenInfra dans un conteneur dédié, l’API démarre uniquement après succès de migration, puis un conteneur `smoke` exécute des scénarios fonctionnels sur l’API et la CLI en backend PostgreSQL.

## Sécurité applicative v0.5.0 et cycle de vie v0.7.0

La sécurité initiale est portée par un domaine `security`, un service applicatif `SecurityService` et des adaptateurs JSON/PostgreSQL. Les jetons API sont validés avant les opérations protégées lorsque l’API est démarrée en mode `auth_required`. Les rôles intégrés sont résolus en permissions déterministes par `BuiltinRolePolicy`. Les secrets ne sont jamais persistés en clair : le service calcule un hash SHA-256 et compare les valeurs avec `hmac.compare_digest`.

La compatibilité ascendante est conservée : l’API reste ouverte par défaut pour les scénarios v0.4.0, tandis que Docker active explicitement l’authentification pour valider le comportement sécurisé en environnement d’exécution.


## Cycle de vie sécurité v0.7.0

Le module sécurité reste dans la couche application et s’appuie sur le port `SecurityRepository`. Les secrets ne sont jamais retournés après création générée et les sorties d’inventaire n’exposent ni `token_hash` ni valeur de jeton. Le cycle de vie couvre :

- création de jeton avec TTL optionnel ;
- authentification par comparaison constante `hmac.compare_digest` ;
- inventaire paginé par tenant ;
- révocation auditée ;
- rotation d’un jeton administrateur avec révocation atomique de l’ancien jeton et création du remplaçant ;
- persistance PostgreSQL via `0003_security_token_lifecycle.sql` sans rupture des jetons existants.

La compatibilité ascendante est conservée : l’authentification API reste explicitement activable, tandis que le runtime Docker l’active systématiquement pour valider le chemin sécurisé.

## v0.7.0 — IAM persistant utilisateurs/groupes

La couche sécurité est étendue par un sous-domaine IAM persistant. Les entités `IdentityUser`, `IdentityGroup` et `GroupMembership` restent dans la couche domaine. Le service applicatif `IdentityService` orchestre les commandes administratives et délègue l’autorisation à `SecurityService` avec la permission `security.admin`.

La compatibilité ascendante est conservée : un jeton API reste porteur de ses rôles propres. Lorsqu’un sujet de jeton correspond à un utilisateur IAM actif, `SecurityService` agrège les rôles du jeton, les rôles directs de l’utilisateur et les rôles hérités des groupes actifs. Les permissions finales sont recalculées à partir de cette liste effective par `BuiltinRolePolicy`.

Les adaptateurs JSON et PostgreSQL implémentent le même port `IdentityRepository`. La migration PostgreSQL `0004_identity_users_groups.sql` utilise un partitionnement par `tenant_id`, des index adaptés aux lectures par sujet/groupe et un index d’audit pour les actions `identity.%`.

## v0.8.0 — ABAC contextuel tenant/site/environnement

La v0.8.0 ajoute une couche ABAC complémentaire au RBAC. Le RBAC conserve la responsabilité d’accorder une permission fonctionnelle (`ipam.allocate`, `database.schema.read`, etc.). ABAC restreint ensuite le contexte d’exécution avec des attributs explicites : `site_code` et `environment` dans ce socle initial.

Le modèle respecte la séparation hexagonale :

- domaine : `AccessPolicyRule`, `AccessRequestContext`, effet `allow` / `deny` ;
- application : `AccessPolicyService` pour créer, lister, désactiver, évaluer et autoriser ;
- ports : `AccessPolicyRepository` ;
- infrastructure : adaptateurs JSON et PostgreSQL ;
- interfaces : CLI `openinfra access *` et endpoints `/api/v1/access/*`.

Le comportement est compatible avec les versions précédentes : en absence de règle applicable à un principal et une permission, l’accès reste gouverné uniquement par RBAC. Si une règle s’applique à un sujet ou à l’un de ses rôles pour la permission demandée, le contexte doit correspondre à au moins une règle `allow`, et aucune règle `deny` ne doit correspondre. Les règles `deny` priment toujours.

La persistance PostgreSQL est ajoutée par `0005_access_policy_abac.sql` avec partitionnement par `tenant_id`, index GIN sur sujets/rôles/sites/environnements et index audit `access.policy.%`.


## v0.9.0 — Audit trail exploitable et intégrité chaînée

La v0.9.0 ajoute une couche applicative d’audit consultable indépendamment des modules métier. Les services existants continuent d’écrire des `AuditEvent`; les adaptateurs JSON et PostgreSQL les enrichissent avec `previous_hash` et `record_hash`. Le service `AuditTrailService` expose la liste paginée, l’export JSON/JSONL et la vérification de chaîne avec permission `audit.read`. L’architecture reste hexagonale : le domaine contient les objets d’intégrité, l’application orchestre les cas d’usage, l’infrastructure persiste et calcule le chaînage au plus près de l’écriture transactionnelle, et les interfaces CLI/API exposent des contrats stables.
