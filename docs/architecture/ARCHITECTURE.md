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

## v0.10.0 — Alignement roadmap REL-01/P03 Source of Truth

La version 0.10.0 reprend l'ordre de la roadmap et livre le premier incrément P03 avant de poursuivre les extensions P14. Le module Source of Truth introduit un agrégat `SourceOfTruthObject` pour les objets génériques et spécialisés, un agrégat `SourceRelation` pour les relations typées et un snapshot `SourceObjectSnapshot` pour l'historisation initiale.

Frontières conservées :

- domaine : invariants clés sûres, type d'objet, tags, attributs JSON, version, relation et validité temporelle ;
- application : `SourceOfTruthService`, contrôle `sot.read` / `sot.write`, audit et transactions ;
- infrastructure : `JsonSourceOfTruthRepository` et `PostgreSQLSourceOfTruthRepository` ;
- interfaces : commandes `openinfra sot *` et endpoints `/api/v1/sot/*`.

La migration `0007_source_of_truth_core.sql` reste additive et partitionnée par `tenant_id`. Elle ne modifie pas les migrations existantes et préserve la compatibilité des modules IPAM, DCIM, IAM, ABAC et audit.

## v0.11.0 — REL-01/P03 EPIC-0306 Gouvernance minimale des sources

La version 0.11.0 poursuit le jalon P03 avec une gouvernance minimale des sources autoritatives. Le domaine `SourceGovernanceRule` définit quel système est autoritatif pour un type d'objet SOT et un chemin d'attribut donné. L'évaluateur compare les attributs existants et entrants, détecte les chemins modifiés et produit une décision déterministe.

Frontières conservées :

- domaine : `SourceGovernanceRule`, chemins d'attribut gouvernés, stratégie `reject` ou `accept_with_audit`, évaluation des conflits ;
- application : `SourceGovernanceService` et enforcement dans `SourceOfTruthService` avant versionnement d'un objet existant ;
- ports : `SourceGovernanceRepository` ;
- infrastructure : `JsonSourceGovernanceRepository` et `PostgreSQLSourceGovernanceRepository` ;
- interfaces : commandes `openinfra sot *-governance-*` et endpoints `/api/v1/sot/governance*`.

Le comportement reste compatible : sans règle active applicable, les mises à jour SOT gardent le comportement v0.10.0. Une règle active peut refuser une modification non autoritative avec `reject`, ou l'accepter avec signalement auditable via `accept_with_audit`. La migration `0008_source_governance.sql` est additive, partitionnée par `tenant_id` et ne modifie aucun schéma antérieur.


## v0.12.0 — P04 EPIC-0401 Modèle physique DCIM

La version 0.12.0 démarre le jalon P04 de la roadmap avec le modèle physique DCIM. Le domaine représente site, bâtiment, étage, salle et zone de salle avec une grille obligatoire ligne/colonne. Les coordonnées X/Y/Z sont optionnelles mais validées comme triplet complet lorsqu’elles sont fournies.

Frontières conservées :

- domaine : `Site`, `Building`, `Floor`, `Room`, `RoomZone`, `Rack`, `EquipmentLocation` et invariants de grille ;
- application : `DcimTopologyService` pour définir la hiérarchie physique, `DcimLocationService` pour localiser un équipement et vérifier les conflits ;
- ports : extension de `DcimRepository` avec lecture/écriture de floors et zones ;
- infrastructure : adaptateurs JSON et PostgreSQL alignés sur le même contrat ;
- interfaces : `openinfra dcim define-room`, `openinfra dcim locate --floor --zone` et `POST /api/v1/dcim/rooms`.

La migration `0009_dcim_physical_model.sql` est additive. Elle conserve les données DCIM existantes, ajoute les étages, zones, coordonnées et index de recherche physique sans modifier les migrations précédentes.

## v0.13.0 — P04 EPIC-0402 Racks, faces et capacité U

La version 0.13.0 poursuit P04 avec le modèle rack exploitable. Le domaine DCIM ajoute `RackFace`, `RackCapacityReport`, les faces rack `front` / `rear`, la capacité U, le poids maximal et la capacité électrique. `EquipmentLocation` porte désormais la face de montage et la hauteur U. Le service applicatif `DcimRackService` centralise la définition des racks et les rapports de capacité.

L'invariant métier principal est transactionnel côté application : deux équipements ne peuvent pas occuper le même intervalle U sur la même face d'un même rack. Les deux faces d'un rack sont indépendantes : une unité U occupée en face avant peut être libre en face arrière. Cette modélisation reste compatible avec les localisations historiques, qui sont interprétées en face avant et hauteur 1 lorsque seule une position U existe.

La migration `0010_dcim_rack_capacity.sql` est additive. Elle ajoute les colonnes rack/équipement, les contraintes de validité et les index d'occupation sans modifier les migrations précédentes ni invalider les données existantes.

## v0.14.0 — P04 EPIC-0403 QR codes et chemins d’intervention

La version 0.14.0 ajoute les opérations terrain DCIM. Le domaine construit un payload QR compact dérivé du tenant, de l’asset tag et du chemin physique, génère un document SVG déterministe, assemble une fiche de localisation JSON/HTML et vérifie les scans par comparaison stricte du payload attendu. L’application expose `DcimFieldOperationService`, les interfaces ajoutent `openinfra dcim locator-sheet`, `openinfra dcim verify-scan`, `GET /api/v1/dcim/locator-sheet` et `POST /api/v1/dcim/verify-scan`.

L’invariant principal est opérationnel : la fiche terrain doit contenir le chemin complet site → bâtiment → étage → salle → zone → rack → face → position U, afin de réduire les erreurs de manipulation. La permission `dcim.identify` protège les opérations d’identification lorsque l’API authentifiée est activée.


## v0.15.0 — P04 EPIC-0404 Plans 2D salle et rack elevation

La version 0.15.0 ajoute la couche de visualisation DCIM sans déplacer la logique métier hors du domaine. Les objets `RoomPlan2D`, `RoomPlanCell`, `RackElevation` et `RackElevationUnit` agrègent les salles, racks et équipements déjà persistés pour produire des représentations JSON, SVG et HTML déterministes. Le service applicatif `DcimVisualizationService` orchestre les lectures via `DcimRepository`, applique les mêmes invariants de tenant/site/bâtiment/salle/rack et journalise chaque rendu dans l’audit.

Les ports restent hexagonaux : le magasin JSON et l’adaptateur PostgreSQL exposent les méthodes de lecture `list_racks_in_room` et `list_equipment_in_room`, sans dépendance de l’application à un format de stockage. Les interfaces ajoutent `openinfra dcim room-plan`, `openinfra dcim rack-elevation`, `GET /api/v1/dcim/room-plan` et `GET /api/v1/dcim/rack-elevation`.

La migration `0012_dcim_visualization_indexes.sql` est additive. Elle ajoute uniquement des index de lecture pour les grilles salle, les occupations rack et l’audit des rendus, sans modifier la forme des données existantes.


## v0.16.0 — P04 EPIC-0405 Câblage DCIM fondation

La version 0.16.0 ajoute une frontière métier dédiée au câblage sans diluer les responsabilités existantes. Le domaine DCIM porte `PatchPanel`, `DcimPortEndpoint`, `DcimPort`, `DcimCablePathSegment` et `DcimCable`. Ces objets imposent les invariants de compatibilité connecteur/média, l’unicité logique des endpoints, l’interdiction des boucles et la présence d’un chemin humain exploitable.

Le service applicatif `DcimCablingService` orchestre la création de panneaux, la génération déterministe des ports, la création des ports équipements, la connexion des câbles et la restitution de trace. Les repositories JSON et PostgreSQL implémentent le même port `DcimRepository`, ce qui conserve l’architecture hexagonale et la compatibilité des interfaces CLI/API.

La production est indépendante de Docker : le chemin de déploiement supporté est un service `systemd` natif démarrant `openinfra-api` depuis un virtualenv Python. Les actifs Docker existants sont conservés comme lab facultatif pour smoke local, mais le quality gate vérifie les actifs natifs `deploy/systemd/openinfra-api.service`, `docs/runbooks/RUNTIME_NATIVE.md` et `scripts/native_runtime_smoke.py`.
