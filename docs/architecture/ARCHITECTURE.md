## v0.29.13 — openinfra-web API-only et Compose runtime

- `openinfra-web` est un service applicatif distinct du backend : il sert les assets frontend et proxyfie `/api/*` vers l'API interne.
- Le navigateur reste en same-origin sur `/api`; il ne reçoit aucun DSN PostgreSQL, secret LDAP/IPA, clé privée mTLS ou jeton d'enrôlement agent.
- Docker Compose inclut désormais `web` avec healthcheck dédié, dépendance sur `api:service_healthy` et smoke tests front/back.
- Le runtime natif rend `openinfra-web.service` via l'installateur autonome et lit la configuration canonique `/opt/openinfra/config/openinfra.conf` exposée par le symlink `/etc/openinfra`.

## v0.29.11 — Configuration runtime canonique, backend API-only et flux sécurisés

- `/opt/openinfra/config/openinfra.conf` est le fichier runtime canonique matérialisant les paramètres utiles de `install.ini` et des références `.env`.
- `/etc/openinfra` est un lien symbolique vers `/opt/openinfra/config`; les unités systemd lisent donc `/etc/openinfra/openinfra.conf` sans conserver `installers/` au runtime.
- Le verrou masqué `/opt/openinfra/config/.openinfra-installed.lock` empêche les réinstallations accidentelles.
- Les migrations backend post-installation sont copiées vers `/opt/openinfra/share/migrations/postgresql`.
- Hors Lite, les flux frontend-backend, agent-backend et backend-backend imposent TLS 1.3 et mTLS.

## v0.29.10 — P07 authentification LDAP/IPA et RBAC groupes

- Lite reste strictement limité à l'authentification locale `standard`.
- Pro et Enterprise acceptent LDAP/IPA uniquement côté frontend/web pour l'authentification opérateur.
- Le backend ne réalise pas de login LDAP/IPA opérateur direct ; il valide des jetons applicatifs, applique RBAC et audit.
- Les secrets de bind LDAP/IPA restent des références `env:`, `vault://`, `sops://`, `file://` ou `kms://`.
- Les groupes externes sont mappés explicitement vers des rôles OpenInfra ; l'annuaire authentifie l'identité mais n'autorise jamais les actions applicatives.
- L'émission des tokens applicatifs est basée sur les rôles OpenInfra effectifs.
- Les connexions externes réussies sont auditées sans journaliser les mots de passe, DN utilisateur en clair dans les payloads publics ou secrets de bind.

## v0.29.10 — P06 PostgreSQL HA/PITR

La version `0.29.10` ajoute le socle P06 avant reprise Discovery. L'installateur reste la source d'orchestration : les scopes backend/all-in-one déduisent un plan PostgreSQL HA/PITR depuis l'arborescence et le `install.ini` minimaliste. Lorsque `identity.peer_nodes` contient des pairs, le plan passe en topologie `near-real-time-streaming-cluster`; sinon il reste en `standalone-managed` avec primitives PITR et backup.

Le plan ne déplace pas de logique dans `src` et ne réintroduit pas `deploy/`. Il rend :

- `/opt/openinfra/config/postgresql-ha.json` pour audit opérateur ;
- `/data/openinfra/conf.d/openinfra-ha.conf` pour WAL archiving, hot standby, slots et synchronous commit ;
- `/data/openinfra/pitr` pour l'archive WAL ;
- `/data/openinfra/backups` pour les backups physiques.

Le failover n'est pas automatique : la configuration impose une validation opérateur et un précheck avant switchover/failover. Cette décision évite une promotion destructrice en cas de partition réseau.

## v0.29.6 — P05 LVM/PGDATA natif et FS applicatif CDC

La version `0.29.6` traite P05 : l'installateur orchestre réellement les filesystems LVM, le compte système `openinfra`, le filesystem applicatif CDC `/opt/openinfra/` pour tous les scopes installés y compris `enterprise/agent`, le filesystem PostgreSQL `/data/openinfra/` uniquement pour `lite/all-in-one`, `pro/server` et `enterprise/server`, le symlink `/opt/openinfra/data -> /data/openinfra/`, le compte système PostgreSQL résolu ou créé, l'override PGDATA systemd et les migrations backend. Les scopes `web` et `agent` restent exclus de PostgreSQL, de PGDATA et des migrations.

## v0.29.4 — Installateurs autonomes par scope

`installers/` est désormais un point d’entrée autonome : chaque scope dispose d’un `install.py` sous `installers/setup/...`. Ces programmes déploient `src/`, les requirements de production, `pyproject.toml`, l’unité systemd rendue et, pour les scopes backend/all-in-one, les migrations PostgreSQL. Les anciens dossiers racine `installers/lite`, `installers/pro` et `installers/enterprise` sont interdits.

## v0.29.3 — Politique filesystem applicatif par scope

Le CDC conserve le filesystem applicatif `/opt/openinfra` comme disposition entreprise pour les scopes applicatifs. Le contrôleur installateur distingue explicitement le filesystem applicatif de PostgreSQL : `all-in-one`, `server`, `web` et `enterprise/agent` gèrent `/opt/openinfra` en interne, tandis que PostgreSQL, PGDATA, symlink data et migrations restent strictement réservés aux scopes backend/all-in-one.

## v0.29.2 — Source unique migrations et bootstrap PostgreSQL backend

La version `0.29.2` supprime le dossier racine `migrations/`. Le catalogue applicatif `PostgreSQLMigrationCatalog.from_project_root()` et le runtime Docker utilisent la source projet `installers/migrations/postgresql`; après installation native, les migrations sont copiées et exécutées depuis `/opt/openinfra/share/migrations/postgresql`. Les scopes backend (`lite/all-in-one`, `pro/server`, `enterprise/server`) rendent aussi un plan de déploiement PostgreSQL OS-aware : détection, installation paquetaire si absent, activation systemd, démarrage, readiness, initialisation PGDATA et application des migrations.

## v0.29.2 — Installateurs comme source de vérité opérationnelle

La version `0.29.2` retire le dossier `deploy/` : les unités systemd ne sont plus livrées comme fichiers statiques. L'installateur déduit l'édition et le scope depuis `installers/setup/...`, valide un `install.ini` minimal, rend `openinfra.service`, `openinfra-web.service` ou `openinfra-agent.service`, puis applique les migrations backend depuis `/opt/openinfra/share/migrations/postgresql` après copie depuis la source projet lorsque le scope gère PostgreSQL.

## v0.29.0 — Éditions et garde-fous runtime

La version `0.29.0` ajoute une frontière domaine/application dédiée aux éditions OpenInfra. Le domaine `openinfra.domain.editions` définit `OpenInfraEdition`, `FeatureCapability`, `QuotaResource` et `EditionPolicyCatalog`. L'application expose `EditionRuntimeGuard`, injecté dans les services Discovery, IAM, IPAM et DCIM afin que les règles Lite/Pro/Enterprise soient appliquées avant persistance.

Le comptage runtime est porté par le port `RuntimeUsageRepository`, implémenté en JSON et PostgreSQL. Les requêtes PostgreSQL utilisent des statements statiques par ressource afin d'éviter toute construction SQL dynamique. L'édition active est fournie à la factory applicative via CLI, API ou `OPENINFRA_EDITION`; Enterprise reste la valeur par défaut pour préserver la compatibilité ascendante.

# Architecture OpenInfra Python


## v0.28.1 — Registry collectors et identité forte

La version `0.28.1` introduit la frontière Discovery sans coupler les collectors au moteur d'exécution. Le domaine porte l'identité (`CollectorIdentity`), les scopes (`DiscoveryScope`), l'agrégat collector (`DiscoveryCollector`) et la politique d'autorisation de job (`DiscoveryJobAuthorization`). Le service applicatif `DiscoveryCollectorService` orchestre les cas d'usage et écrit les événements d'audit. Les adaptateurs JSON et PostgreSQL implémentent le port `DiscoveryRepository` sans exposer de détails de stockage aux interfaces.

L'identité forte repose sur l'empreinte SHA-256 du certificat mTLS présenté par le collector. OpenInfra normalise cette empreinte, la compare en temps constant logique au moment de l'autorisation et refuse tout job si le collector est inconnu, désactivé, hors scope ou présenté avec une empreinte différente. Les secrets techniques nécessaires aux probes ne sont pas stockés dans OpenInfra : le registre conserve uniquement une référence Vault `vault://...`, ce qui garde la séparation entre inventaire d'identité et coffre de secrets.

PostgreSQL ajoute `discovery_collectors` via `0023_discovery_collector_registry.sql`, partitionnée par hash de `tenant_id`, avec contraintes explicites sur les statuts, les types de collectors, les scopes JSONB, les empreintes et les références Vault. Les interfaces CLI et HTTP ne contiennent pas de logique métier : elles construisent des commandes applicatives et sérialisent les résultats.

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
- Les opérations IPAM passent par des services transactionnels : modèle VRF/agrégats/préfixes/ranges/adresses et allocation idempotente.
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

Le moteur `PostgreSQLMigrationExecutor` charge par défaut les fichiers `installers/migrations/postgresql/*.sql`, vérifie leur structure minimale, calcule un checksum SHA-256, applique uniquement les migrations absentes et refuse une migration déjà appliquée dont le contenu a changé. La CLI expose :

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

## v0.10.0 — Alignement roadmap REL-01/P03 IT Ressources Management

La version 0.10.0 reprend l'ordre de la roadmap et livre le premier incrément P03 avant de poursuivre les extensions P14. Le module IT Ressources Management introduit un agrégat `SourceOfTruthObject` pour les objets génériques et spécialisés, un agrégat `SourceRelation` pour les relations typées et un snapshot `SourceObjectSnapshot` pour l'historisation initiale.

Frontières conservées :

- domaine : invariants clés sûres, type d'objet, tags, attributs JSON, version, relation et validité temporelle ;
- application : `SourceOfTruthService`, contrôle `itrm.read` / `itrm.write`, audit et transactions ;
- infrastructure : `JsonSourceOfTruthRepository` et `PostgreSQLSourceOfTruthRepository` ;
- interfaces : commandes `openinfra itrm *` et endpoints `/api/v1/itrm/*`.

La migration `0007_source_of_truth_core.sql` reste additive et partitionnée par `tenant_id`. Elle ne modifie pas les migrations existantes et préserve la compatibilité des modules IPAM, DCIM, IAM, ABAC et audit.

## v0.11.0 — REL-01/P03 EPIC-0306 Gouvernance minimale des sources

La version 0.11.0 poursuit le jalon P03 avec une gouvernance minimale des sources autoritatives. Le domaine `SourceGovernanceRule` définit quel système est autoritatif pour un type d'objet ITRM et un chemin d'attribut donné. L'évaluateur compare les attributs existants et entrants, détecte les chemins modifiés et produit une décision déterministe.

Frontières conservées :

- domaine : `SourceGovernanceRule`, chemins d'attribut gouvernés, stratégie `reject` ou `accept_with_audit`, évaluation des conflits ;
- application : `SourceGovernanceService` et enforcement dans `SourceOfTruthService` avant versionnement d'un objet existant ;
- ports : `SourceGovernanceRepository` ;
- infrastructure : `JsonSourceGovernanceRepository` et `PostgreSQLSourceGovernanceRepository` ;
- interfaces : commandes `openinfra itrm *-governance-*` et endpoints `/api/v1/itrm/governance*`.

Le comportement reste compatible : sans règle active applicable, les mises à jour ITRM gardent le comportement v0.10.0. Une règle active peut refuser une modification non autoritative avec `reject`, ou l'accepter avec signalement auditable via `accept_with_audit`. La migration `0008_source_governance.sql` est additive, partitionnée par `tenant_id` et ne modifie aucun schéma antérieur.



## v0.29.31 — P11 IPAM Enterprise++ dashboard et découverte API

La version 0.29.31 complète l'exposition opérateur IPAM Enterprise++ dans `openinfra-web`. Les formulaires du dashboard couvrent les contrats `/api/v1/ipam/*` existants pour VRF, agrégats, préfixes, plages, adresses, VLAN/VXLAN, ASN/BGP, observations DNS/DHCP, DDI, capacité, bindings, conflits, allocation et assistant de réservation.

L'architecture reste hexagonale : le navigateur ne porte aucune règle métier IPAM et ne parle pas à la base. Les valeurs saisies sont transmises au BFF `openinfra-web`, puis aux endpoints API qui délèguent aux services applicatifs `IpamModelService`, `IpamAllocationService`, `IpamConflictService`, `IpamDdiService` et `IpamUiService`. Le document de découverte API racine expose désormais une section `ipam` afin de rendre les contrats automatisables directement découvrables.

## v0.29.30 — P10 DCIM jumeau numérique initial

La version 0.29.30 introduit un jumeau numérique DCIM initial de salle. Le contrat `GET /api/v1/dcim/digital-twin`, la commande `openinfra dcim digital-twin` et l’opération web `Jumeau numérique salle` retournent une représentation consolidée `dcim_digital_twin` contenant plan salle, racks, équipements, panneaux, ports, câbles, énergie/refroidissement, élévations et contrôles d’intégrité.

La frontière reste hexagonale : `DcimVisualizationService` orchestre les ports repository et les services applicatifs existants, sans stockage parallèle ni logique métier dupliquée côté interface. Les invariants d’occupation rack/U, câblage, capacité watts, réservations et marge thermique restent dans le domaine et les services applicatifs spécialisés.

## v0.29.29 — P10 DCIM énergie/refroidissement dashboard et OpenAPI

La version 0.29.29 complète la parité opérateur P10/DCIM pour l’énergie et le refroidissement. `openinfra-web` expose les formulaires `Définir un équipement électrique`, `Définir un circuit électrique`, `Définir une zone de refroidissement`, `Réserver la puissance équipement` et `Capacité énergie/refroidissement`, tous adossés au service applicatif existant `DcimEnvironmentService`.

La frontière reste hexagonale : le dashboard collecte les paramètres métier, le BFF relaie vers `/api/v1/dcim/*`, le service applicatif orchestre les ports repository et le domaine conserve les invariants capacité watts, redondance A/B, derating, marge de refroidissement et réservation par actif. Le document de découverte API et `docs/api/openapi.yaml` publient les mêmes contrats afin d’éviter une divergence UI/API.

## v0.29.28 — P10 DCIM câblage dashboard

La version 0.29.28 complète l’ergonomie P10/DCIM pour les opérations de câblage. `openinfra-web` expose les formulaires `Définir un panneau de brassage`, `Définir un port DCIM` et `Connecter un câble`, tous adossés aux services applicatifs existants `DcimCablingService`. Le navigateur reste un client API : il collecte les paramètres métier et laisse le domaine valider la compatibilité connecteur/média, l’existence des ports, l’occupation des endpoints, le chemin câble et les conflits.

Le champ `Chemin câble` est typé CSV dans le catalogue runtime et produit une liste `path_segments`, ce qui rend exploitable le traçage de bout en bout via `GET /api/v1/dcim/cable-trace` sans introduire de modèle UI parallèle.

## v0.29.27 — P10 DCIM élévation rack dashboard

La version 0.29.28 complète la parité web de la visualisation DCIM : `openinfra-web` expose l’opération `Élévation rack` directement adossée au contrat `GET /api/v1/dcim/rack-elevation`. Le navigateur ne réimplémente aucun calcul d’occupation U ; il transmet uniquement site, bâtiment, salle, rack, face et format au backend via le proxy same-origin, puis affiche la réponse du service de visualisation.

Le formulaire `Plan de salle` expose également le paramètre `format`, ce qui rend explicites les rendus `json`, `svg` et `html` déjà supportés par le domaine `RoomPlan2D` et par l’API HTTP. Les champs métier de lecture DCIM sont déclarés requis dans le catalogue runtime afin de limiter les appels incomplets dès l’interface opérateur tout en conservant la validation serveur comme autorité.

## v0.29.26 — P10 DCIM localisation équipement API/UI

La version 0.29.26 rend la localisation et la relocalisation d’équipement DCIM consommables par API HTTP et par `openinfra-web`, sans créer de chemin parallèle au service applicatif `DcimLocationService`. Le contrat `POST /api/v1/dcim/locations` applique les mêmes invariants que la CLI `openinfra dcim locate` : site, bâtiment, salle, ligne et colonne obligatoires ; étage, zone, rack, face, position U, hauteur U et coordonnées X/Y/Z optionnels mais validés lorsqu’ils sont fournis.

La réponse sérialise un équipement complet avec son chemin humain, ce qui stabilise les intégrations BFF, les workflows terrain et les tests d’acceptation P10. Le dashboard ajoute le formulaire `Localiser un équipement` en utilisant le proxy same-origin `/api/v1/dcim/locations`; aucun secret ni DSN n’est exposé côté navigateur.

## v0.12.0 — P04 EPIC-0401 Modèle physique DCIM

La version 0.12.0 démarre le jalon P04 de la roadmap avec le modèle physique DCIM. Le domaine représente site, bâtiment, étage, salle et zone de salle avec une grille obligatoire ligne/colonne. Les coordonnées X/Y/Z sont optionnelles mais validées comme triplet complet lorsqu’elles sont fournies.

Frontières conservées :

- domaine : `Site`, `Building`, `Floor`, `Room`, `RoomZone`, `Rack`, `EquipmentLocation` et invariants de grille ;
- application : `DcimTopologyService` pour définir la hiérarchie physique, `DcimLocationService` pour localiser un équipement et vérifier les conflits ;
- ports : extension de `DcimRepository` avec lecture/écriture de floors et zones ;
- infrastructure : adaptateurs JSON et PostgreSQL alignés sur le même contrat ;
- interfaces : `openinfra dcim define-room`, `openinfra dcim locate --floor --zone`, `POST /api/v1/dcim/rooms` et `POST /api/v1/dcim/locations`.

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

La production est indépendante de Docker : le chemin de déploiement supporté est un service `systemd` natif démarrant `openinfra-api` depuis un virtualenv Python. Les actifs Docker existants sont conservés comme lab facultatif pour smoke local, mais le quality gate vérifie les actifs natifs `docs/runbooks/RUNTIME_NATIVE.md`, le rendu systemd installateur et `scripts/native_runtime_smoke.py`.


## v0.17.0 — P04 EPIC-0406 Énergie et refroidissement fondation

La version 0.17.0 ajoute la frontière énergie/refroidissement au modèle DCIM existant. Le domaine porte les équipements électriques (`PowerDevice`), les circuits A/B (`PowerCircuit`), les zones de refroidissement (`CoolingZone`), les réservations d’équipements (`RackPowerReservation`) et le rapport consolidé `RackEnergyCoolingReport`.

Frontières conservées :

- domaine : invariants de capacité, dérating, tension, température, alimentation A/B et refroidissement ;
- application : `DcimEnvironmentService`, contrôles de capacité source/circuit/rack/zone et audit ;
- ports : extension de `DcimRepository` pour les lectures/écritures énergie et refroidissement ;
- infrastructure : adaptateurs JSON et PostgreSQL sur le même contrat ;
- interfaces : commandes `openinfra dcim define-power-device`, `define-power-circuit`, `define-cooling-zone`, `reserve-power`, `energy-cooling-capacity` et endpoints `/api/v1/dcim/*energy*`.

La migration `0014_dcim_energy_cooling_foundation.sql` est additive, partitionnée par `tenant_id`, indexée par source, rack, circuit et zone. Elle ne modifie aucune migration précédente. Le runtime de production reste serveur natif ; Docker n’est pas requis pour exécuter OpenInfra en production.

Le workflow GitHub Actions se déclenche sur toutes les branches en `push`, sur toutes les pull requests et via `workflow_dispatch`, afin d’éviter les non-exécutions observées lorsque les pushes ne ciblent pas `main`.


## IPAM P05 / EPIC-0501

Le modèle IPAM est séparé du moteur d'allocation transactionnelle. `IpamModelService` gouverne les objets stables : VRF, agrégats IPv4/IPv6, préfixes, plages d'allocation/réservation/exclusion, adresses suivies et capacité de préfixe. Les adaptateurs JSON et PostgreSQL implémentent le même port `IpamRepository`, ce qui conserve l'indépendance des cas d'usage vis-à-vis de la persistance.

Les chevauchements sont contrôlés par tenant et VRF. Un chevauchement de préfixe ou d'agrégat est refusé dans le même VRF afin de préserver l'unicité opérationnelle, tandis que le même espace d'adressage reste autorisé dans des VRF distincts. PostgreSQL reçoit des tables partitionnées par `tenant_id` et des index par VRF/prefixe/adresse pour rester compatible avec les objectifs très grand volume.


## IPAM P05 / EPIC-0502

L’allocation IP transactionnelle est portée par `IpamAllocationService` et reste indépendante de la persistance. Le service ouvre une unité de travail courte, acquiert un verrou logique par tenant/VRF/prefixe via le port `IpamRepository.acquire_allocation_lock`, lit les réservations, les adresses suivies et les plages IPAM, puis délègue la sélection déterministe à `IpAllocationPolicy`.

Règles appliquées :

- l’idempotency key retourne la réservation existante sans créer de doublon ;
- les plages `allocation` restreignent le pool candidat lorsqu’elles existent ;
- les plages `reservation` et `exclusion` bloquent l’allocation automatique ;
- les adresses déjà réservées ou enregistrées sont traitées comme occupées ;
- PostgreSQL utilise un `pg_advisory_xact_lock` calculé sur `tenant/VRF/prefixe`, complété par des contraintes uniques ;
- le backend JSON utilise le verrou réentrant du document store pendant toute l’unité de travail.

Cette conception couvre l’acceptation EPIC-0502 : 100 allocations concurrentes dans un même préfixe ne produisent aucune collision.


## v0.20.0 — P05 EPIC-0503 VLAN/VXLAN/ASN/BGP fondation

La version 0.20.0 étend le bounded context IPAM avec les identifiants réseau utilisés par les fabrics modernes : groupes VLAN, VLAN, VNI/VXLAN, ASN et pairs BGP. L'objectif est de relier l'adressage IP aux plans réseau L2/L3 sans introduire de dépendance à un contrôleur externe.

Frontières conservées :

- domaine : `NetworkIdentifierPolicy`, `VlanGroup`, `Vlan`, `VxlanVni`, `AutonomousSystem` et `BgpPeer` portent les validations de VLAN ID, VNI, ASN, adresse BGP et route targets ;
- application : `IpamModelService` orchestre les écritures, vérifie la cohérence VRF/VLAN/VNI/ASN et produit l'audit métier ;
- ports : `IpamRepository` expose les écritures et lectures réseau sans coupler le domaine au stockage ;
- infrastructure : JSON atomique et PostgreSQL implémentent les mêmes contrats, avec contraintes SQL et index adaptés aux recherches par tenant, VRF, VLAN, VNI et ASN ;
- interfaces : CLI `openinfra ipam define-*` et endpoints `/api/v1/ipam/*` exposent un inventaire auditable et scriptable.

Les invariants principaux sont : VNI unique par tenant, VLAN attaché à un VNI dans le même VRF, ASN local et distant distincts pour un pair BGP, et route targets normalisées au format `ASN:NUMBER`. La migration `0017_ipam_networking_foundation.sql` est additive et préserve les migrations IPAM précédentes.

## v0.21.0 — P05 EPIC-0504 Détection conflits IPAM

La version 0.21.0 introduit un sous-domaine de contrôle IPAM centré sur la détection de divergences entre la source de vérité OpenInfra et les faits observés sur le réseau. Le modèle reste strictement transactionnel et POO : les objets `ObservedDnsRecord`, `ObservedDhcpLease` et `IpamConflict` encapsulent les règles de normalisation, de preuve et de sévérité.

Le service `IpamConflictService` agrège les données gérées et observées par tenant/VRF puis produit un rapport déterministe : chevauchements de préfixes, chevauchements de plages, doublons IP, leases actifs hors préfixe, conflit lease/réservation, et divergence DNS/PTR. Les résultats ne modifient pas la source de vérité ; ils sont auditables et exploitables par API/CLI pour déclencher une remédiation contrôlée.

La persistance PostgreSQL est additive via `0018_ipam_conflict_detection.sql`, avec tables partitionnées par `tenant_id` et index sur adresses observées, PTR et leases actifs.


## v0.22.0 — P05 EPIC-0505 UI IPAM opérationnelle

La version 0.22.0 introduit une couche UI IPAM strictement applicative et sans framework externe. Le service `IpamUiService` agrège les référentiels IPAM existants, le moteur de conflits et l’allocation transactionnelle pour produire un view model stable consommable par CLI, API JSON et rendu HTML serveur.

Le rendu HTML `/ui/ipam` reste volontairement léger : il expose les VRF, la capacité des préfixes, les réservations et les conflits sans créer de dépendance de production supplémentaire. Le workflow de réservation est séparé en deux modes : prévisualisation déterministe de la prochaine adresse disponible et application transactionnelle via le service d’allocation existant.


## v0.22.2 — Correctif runtime Docker/PostgreSQL

Le runtime Docker facultatif est corrigé pour respecter la séparation des responsabilités : l’image ne définit plus de healthcheck global, afin que les conteneurs one-shot `migrate` et `auth-bootstrap` n’héritent pas d’un contrôle HTTP réservé au service API. Les migrations PostgreSQL DCIM utilisent toutes la colonne réelle `audit_events.created_at` pour les index temporels.


## v0.22.2 — Administration PostgreSQL du lab Docker

Le runtime Docker facultatif ajoute un service `pgadmin` isolé sur le réseau Compose `openinfra`. Il ne participe pas au runtime de production et ne modifie pas les bounded contexts applicatifs. Sa responsabilité est limitée à l’administration manuelle de la base PostgreSQL du lab local.

Les données pgAdmin4 sont portées par le volume `openinfra-pgadmin-data`; le serveur PostgreSQL OpenInfra est préchargé via `docker/pgadmin/servers.json`. Les identifiants pgAdmin4 et PostgreSQL restent dans `.env`, créé localement avec permissions restreintes par `scripts/docker_environment.py`.

## v0.22.3 — Correctif migration IPAM PostgreSQL

La migration IPAM enterprise aligne désormais le schéma historique `prefixes` créé en `0001` avec le modèle P05 enrichi en ajoutant `family`, son backfill depuis `pg_catalog.family(prefixes.cidr)`, sa contrainte `NOT NULL` et son contrôle IPv4/IPv6 avant l’indexation tenant/VRF/famille/CIDR. Le lab Docker conserve pgAdmin4 avec un identifiant par défaut utilisant un domaine publiquement valide afin d’éviter le rejet des domaines réservés par pgAdmin4.

## v0.23.0 — P05 EPIC-0506 DDI intégration baseline

La version 0.23.0 termine la séquence P05 par une intégration DDI de base centrée sur la sécurité opérationnelle : une réservation IPAM existante peut produire une prévisualisation DNS/DHCP déterministe pour BIND, PowerDNS et Kea sans appel réseau implicite. Le domaine introduit des changements typés (`DdiChange`), les providers (`DdiProvider`), les divergences (`DdiDivergence`) et une enveloppe de prévisualisation (`DdiReservationPreview`) contenant aussi le plan compensatoire de rollback.

Le service applicatif `IpamDdiService` orchestre les connecteurs via le port `DdiConnector`, relit la réservation par clé d’idempotence, normalise FQDN, zone DNS, TTL et MAC DHCP, puis compare le plan attendu aux observations DNS/DHCP déjà connues par IPAM. Les divergences bloquantes (`error` ou `critical`) désactivent `safe_to_apply`, ce qui empêche une intégration silencieuse en présence de conflit forward DNS, PTR ou DHCP.

Les adaptateurs `BindDdiConnector`, `PowerDnsDdiConnector` et `KeaDdiConnector` génèrent des changements applicables par des intégrateurs externes ou un futur executor contrôlé. Cette livraison conserve la production indépendante de Docker, ne change pas le schéma PostgreSQL et continue d’utiliser l’audit append-only pour tracer chaque prévisualisation DDI.

## v0.23.1 — Correctif runtime API discovery

La version 0.23.1 ajoute une route racine explicite `GET /` et une route d’entrée versionnée `GET /api/v1`. Ces routes retournent un document JSON déterministe contenant l’identité du service, la version applicative, les URLs `/health`, `/ready`, `/api/v1/version` et `/api/v1/database/schema`. Le changement n’altère pas les contrats API existants ; il supprime uniquement l’ambiguïté opérationnelle observée lorsqu’un administrateur ouvre l’URL racine du conteneur API dans un navigateur.

L’entrypoint `openinfra-api` écrit également un événement JSON unique sur stdout au démarrage. Cette trace reste volontairement minimale et ne contient aucun secret ; elle facilite le diagnostic `docker logs openinfra-api` dans le lab Compose et le suivi systemd en runtime natif.

## v0.25.1 — P06 EPIC-0602 Import massif scalable

La version 0.25.0 a introduit une capacité d’import massif sans modifier le contrat atomique du framework générique livré en 0.24.0. L’architecture reste hexagonale : le domaine décrit les rapports bulk, checkpoints et métriques ; l’application orchestre l’autorisation `itrm.write`, le parsing streaming, les batches, la persistance d’avancement et l’écriture IT Ressources Management ; l’infrastructure fournit les parseurs et les référentiels JSON/PostgreSQL.

Le flux CSV bulk utilise `ImportDatasetParser.iter_rows` pour produire les lignes une par une. Les batches sont bornés par `batch_size`, les checkpoints sont persistés selon `checkpoint_interval`, et la reprise par `resume_job_id` redémarre au `next_row_number` du dernier checkpoint. Les impacts et DLQ restent échantillonnés pour éviter les rapports non bornés sur très gros datasets.

Côté PostgreSQL, `bulk_import_jobs` et `bulk_import_checkpoints` sont partitionnées par hash du tenant. Les métriques, mappings et échantillons sont stockés en JSONB afin de conserver un schéma robuste tout en gardant une recherche opérationnelle par tenant, statut, date et job. Cette livraison prépare l’optimisation COPY contrôlée côté PostgreSQL sans introduire de dépendance runtime supplémentaire ni coupler le domaine à psycopg.

Interfaces exposées : `openinfra import bulk-dataset`, `openinfra import bulk-report`, `openinfra import bulk-checkpoint`, `POST /api/v1/imports/bulk-datasets`, `GET /api/v1/imports/bulk-report` et `GET /api/v1/imports/bulk-checkpoint`. Les endpoints Swagger UI, ReDoc et OpenAPI YAML restent exposés par `/docs`, `/swagger`, `/redoc`, `/openapi.yaml` et `/api/v1/openapi.yaml`.
## v0.25.2 — Séparation requirements production/dev

La livraison corrective 0.25.2 ne modifie pas le domaine métier. Elle renforce l'industrialisation : les dépendances production, PostgreSQL optionnelles et dev/CI sont séparées dans `requirements/`, tandis que le garde de sécurité CI vérifie que cette séparation reste effective.


## v0.26.0 — P06 EPIC-0603 Exports asynchrones et signés

Le module d’export suit la séparation hexagonale existante. Le domaine `data_export` modélise les jobs, statuts, formats, filtres et métadonnées d’artefact. Le service applicatif `ExportService` orchestre l’authentification, l’audit, la création non bloquante du job, l’exécution paginée par worker, la sérialisation CSV/JSON/XLSX, le calcul SHA-256, la signature HMAC-SHA256 et la vérification d’intégrité avant restitution de l’artefact.

La clé de signature n’est pas codée en dur : elle est créée et persistée par le backend via `ExportRepository.get_or_create_export_signing_secret`. L’adaptateur JSON la stocke dans le document d’état local de test, tandis que l’adaptateur PostgreSQL utilise `export_signing_keys`. Les tables `export_jobs` et `export_artifacts` sont partitionnées par hash du tenant afin de rester alignées avec la stratégie multi-tenant et forte volumétrie du socle PostgreSQL.

Les interfaces restent fines : le CLI expose `openinfra export request`, `run`, `report` et `artifact`; l’API expose `POST/GET /api/v1/exports/jobs`, `POST /api/v1/exports/run` et `GET /api/v1/exports/artifact`. Aucun appel réseau externe ni stockage objet externe n’est imposé dans cette baseline ; le design isole déjà le stockage d’artefacts derrière le port repository pour permettre une évolution compatible.


## v0.27.0 — P06 EPIC-0604 Migration depuis référentiels existants

Le framework de migration legacy reste dans le bounded context import afin de réutiliser les parseurs CSV/JSON/XLSX, le mapping contrôlé, la DLQ et l’audit existants. La couche domaine porte les concepts `LegacyMigrationSource`, `MigrationTemplate`, `MigrationGap` et `MigrationPlanReport`. La couche application orchestre le dry-run sans effet de bord et persiste le rapport via le port `ImportRepository`. Les adaptateurs JSON/PostgreSQL stockent les plans, PostgreSQL utilisant la table partitionnée `migration_plan_reports` par hash du tenant pour conserver la scalabilité multi-tenant.



### IPAM topology graph

`IpamModelService.topology` construit un graphe opérationnel lecture seule à partir du repository IPAM : VRF, agrégats, préfixes, plages, adresses, réservations, VLAN/VXLAN, ASN/BGP et observations DNS/DHCP. Le rapport expose `nodes`, `edges`, `summary` et `integrity`, et journalise `ipam.topology.generated` sans introduire de stockage parallèle.


## Web UX global search and contextual messaging v0.29.37

La version `0.29.37` transforme le header `openinfra-web` en double barre. Le premier bandeau conserve l’identité produit et la navigation principale ; le second bandeau porte une recherche globale centrée, limitée à 50 % de la largeur disponible sur desktop, avec icône SVG loupe intégrée et résultats groupés par composant. Les actions `Swagger` et `ReDoc` sont exposées dans ce second bandeau via les URLs `apiDocumentation` publiées par `/config.json`, sans réintroduire les anciens contrôles Login/Sign-up.

La recherche globale est calculée côté navigateur sur le catalogue d’opérations déjà embarqué dans le dashboard. Elle indexe les libellés de composants, opérations, méthodes, chemins API et champs de formulaires. Les résultats sont rendus par groupes de composants pour préserver le contexte métier et sélectionner directement l’opération concernée.

La même livraison retire les textes permanents qui avaient été conservés après la suppression des alertes informatives par défaut. Les pages composant conservent le titre, le sous-titre, le formulaire et le panneau résultat ; les alertes visibles restent strictement contextuelles : `warning/error` pour un problème caractérisé et `success` uniquement après une soumission effective de formulaire. Le validateur frontend et les tests web verrouillent l’absence de `alert-info`, de `role="note"` et des textes hérités des anciennes alertes.

## Web UX contextual alerts v0.29.36

La version `0.29.36` supprime l’alerte informative affichée par défaut sur les pages composant `openinfra-web`. Depuis la v0.29.37, le message permanent issu de cette ancienne alerte est également retiré du rendu. Les alertes de la zone principale restent strictement contextuelles : `warning/error` pour un problème caractérisé et `success` uniquement après une soumission effective de formulaire. Le validateur frontend interdit `alert alert-info`, `role="note"` et les textes hérités des anciennes alertes dans les sources UI runtime pour empêcher toute régression.

## Discovery Enterprise proxy enrollment verification v0.29.35

La version `0.29.35` complète le cycle d’exploitation de l’enrôlement proxy Enterprise. La CLI expose `openinfra discovery proxy-enroll-verify` pour relire un fichier produit par `openinfra discovery proxy-enroll --config-output`, vérifier qu’il reste réservé à Enterprise, contrôler son schéma JSON, les backends enregistrés, les codes HTTP, les réponses backend et les permissions POSIX `0600`. La validation est locale et déterministe : elle ne ré-appelle pas les backends, afin de permettre les diagnostics offline et les contrôles CI/CD sur artefact d’enrôlement. L’option `--allow-partial` conserve les erreurs de schéma mais transforme un enrôlement backend partiel en avertissement pour les opérations HA.

## Discovery Enterprise proxy enrollment v0.29.33

La version `0.29.33` complète la frontière Discovery avec un enrôlement proxy Enterprise explicite. Le domaine accepte désormais les kinds `site-proxy`, `network-proxy` et `datacenter-proxy`; le service applicatif `DiscoveryCollectorService.enroll_proxy` applique le feature gate `distributed_discovery_agents`, vérifie que le kind est bien un proxy et persiste l’agrégat collector avec audit `discovery.proxy.enrolled`. L’interface HTTP expose `POST /api/v1/discovery/proxy-enrollments`; la CLI peut soit appeler directement un ou plusieurs backends (`openinfra discovery proxy-enroll`), soit écrire dans le backend local choisi (`openinfra discovery proxy-enroll-local`). Hors Enterprise, l’enrôlement est rejeté avant persistance.

### v0.29.33 — web theme layer

`openinfra-web` conserve une séparation stricte structure/comportement/style : React déclare les modules, opérations et champs ; Bootstrap 5 fournit les primitives ; `openinfra-web.css` applique la charte produit sans modifier l’arbre HTML. La charte remplace les couleurs Bootstrap basic par des variables CSS produit (`--openinfra-navy`, `--openinfra-action`, `--openinfra-cyan`) et des états cohérents pour boutons, badges, formulaires, focus, sidebar, header et cartes. Aucun asset tiers n’est embarqué.

## Web UX content shadow refinement v0.29.35

La version `0.29.35` sépare les effets d’élévation visuelle du contenu et de la navigation. Les blocs de contenu openinfra-web utilisent `--openinfra-content-shadow` et `--openinfra-content-shadow-hover`, plus légers que les tokens historiques de navigation. Le header principal et la sidebar restent inchangés pour préserver l’orientation opérateur, tandis que les cartes, métriques, titlebars et synthèses deviennent plus fluides visuellement.

## Backend global search v0.29.38

La version `0.29.38` introduit un service applicatif transverse `GlobalSearchService`. Il agrège ITRM, IPAM et Discovery via les ports/services existants, normalise le score de pertinence et retourne un contrat groupé par composant. Le service conserve la séparation Clean Architecture : l’UI et l’API ne lisent pas directement les repositories métiers.

L’endpoint `GET /api/v1/search/global` expose ce contrat à `openinfra-web` et à tout client API. Les composants protégés qui refusent le jeton courant sont marqués comme non visibles au niveau applicatif, sans fuite de contenu. La commande `openinfra search global` réutilise le même service pour garantir la parité CLI/API/UI.



### v0.29.42 — hiérarchie d’ombres et offset de scroll du header

La version 0.29.42 renforce le contrat layout du double header `openinfra-web`. Le conteneur fixe `openinfra-header-stack` porte `--openinfra-header-shadow`, plus visible que les ombres de contenu allégées, et couvre toute la largeur du viewport. Le contenu principal conserve son offset dynamique via `--openinfra-fixed-header-height`, tandis que `scroll-padding-top` garantit que les ancrages et mouvements de scroll démarrent sous la limite réelle du header.

L’ombre basse du second bandeau est neutralisée pour éviter un double effet visuel : la séparation entre header et page est centralisée sur le header complet, sans déplacer ni recouvrir le contenu métier.

### v0.29.41 — Documentation API backend depuis le portail web

`openinfra-web` expose désormais les routes documentaires `/docs`, `/swagger`, `/redoc`, `/openapi.yaml` et `/api/v1/openapi.yaml` comme proxy BFF vers `openinfra-api`. Le navigateur ne suppose plus que Swagger/ReDoc sont des assets du portail : les boutons du header lisent `apiDocumentation.swaggerUrl` et `apiDocumentation.redocUrl` depuis `/config.json`.

Par défaut, les liens restent same-origin pour simplifier les déploiements reverse-proxy. Lorsque le portail web et l’API sont publiés sur des origines distinctes, `OPENINFRA_WEB_PUBLIC_API_DOCS_BASE_URL` permet de déclarer l’origine documentaire publique du backend API. Les pages Swagger/ReDoc proxifiées reçoivent une CSP spécifique autorisant uniquement les viewers nécessaires, afin de conserver la CSP stricte du reste du portail.

### v0.29.41 — restauration de la palette initiale des camemberts

La visualisation des statistiques d’accueil conserve son calcul déterministe lecture/mutation et revient à la palette initiale `action/green`, plus lisible et moins fatigante que le duo bleu nuit/fuchsia. Le changement reste strictement CSS : il ne modifie ni le modèle de données, ni les contrats API, ni les métriques affichées.

### v0.29.41 — pictogramme ITRM orienté référentiel

Le composant ITRM conserve ses contrats API, CLI et formulaires existants, mais son pictogramme UI passe d’une icône tableau à une icône de référentiel/référence. La modification est limitée à la couche interface : elle touche le catalogue d’icônes React/runtime et le choix d’icône du module ITRM, sans modifier les données métier ni les permissions.

### v0.29.39 — robustesse UX de la recherche globale

Le double header `openinfra-web` résout l’URL de recherche globale via `apiBaseUrl` publié par `/config.json`, puis appelle `${apiBaseUrl}/v1/search/global`. Cette règle évite de figer `/api` dans les assets navigateur et préserve les déploiements reverse-proxy avec préfixe public personnalisé. En cas d’indisponibilité réseau/proxy, l’erreur technique navigateur est confinée côté état interne et l’UI rend uniquement un message métier générique avec fallback local.



La version 0.29.42 précise le comportement du double header fixe : `openinfra-header-stack` reste en haut de viewport, porte une ombre renforcée sur toute la largeur et le contenu démarre exactement sous la limite du header grâce à `--openinfra-fixed-header-height`, `scroll-padding-top` et au calcul dynamique de hauteur.

La version 0.29.45 corrige le flux du panneau latéral : les accordéons de composant ne sont pas positionnés hors flux et leurs panneaux ouverts n’utilisent plus de plafond `max-height` fixe. Le scroll est confié au conteneur `.openinfra-sidebar`, borné sous le header fixe, afin que les opérations longues restent accessibles sans chevauchement entre composants.


## v0.29.45 — couverture ITAM garantie/support par actif

OpenInfra v0.29.45 complète le slice ITAM livré en v0.29.43 avec une évaluation de couverture en lecture seule. Le domaine `PhysicalAssetSupportCoverageReport` calcule le statut de garantie constructeur, les jours restants, l’expiration et les compteurs de contrats tiers actifs, planifiés ou expirés sans modifier la persistance existante.

L’application expose ce calcul via `ItamSupportService.get_support_coverage_report`, protégé par `itam.read`. L’API HTTP ajoute `GET /api/v1/itam/support-coverage`, et la CLI ajoute `openinfra itam support-coverage`. Le calcul accepte un `as_of` optionnel pour rendre les tests, audits et exports historiques déterministes.

## v0.29.43 — profil support ITAM constructeur et tiers

OpenInfra v0.29.43 ajoute un slice ITAM transversal autour du profil de support par actif physique. Le domaine `PhysicalAssetSupportProfile` conserve la garantie et le support constructeur comme référence canonique, tandis que les contrats de support tiers sont enregistrés dans une collection séparée afin d’éviter tout écrasement de la donnée constructeur initiale.

La couche application expose `ItamSupportService` avec RBAC explicite (`itam.read`, `itam.write`) et audit des opérations constructeur/tier. Les adaptateurs de persistance JSON et PostgreSQL implémentent `ItamSupportRepository`; la migration `0027_itam_asset_support_profiles.sql` crée une table partitionnée par `tenant_id` pour préserver les objectifs de scalabilité multi-tenant. Les interfaces HTTP et CLI publient le même contrat métier via `/api/v1/itam/support-profile` et `openinfra itam`.


## v0.29.45 — exposition web ITAM transverse

L’architecture web aligne désormais le domaine ITAM avec les autres composants de premier niveau. Les opérations ITAM support-profile/support-coverage sont exposées dans le modèle de navigation runtime React et statique, et la recherche globale backend interroge les profils de support par numéro d’actif sans exposer de secret navigateur.


## OpenInfra Web — header runtime v0.29.48

L’édition OpenInfra est affichée au niveau du header principal, immédiatement après le logo produit, afin de rester visible sans dupliquer les informations dans la titlebar métier. L’indication permanente du mode d’authentification est supprimée de la surface UI : le frontend conserve `authMode` dans sa configuration publique pour piloter les flux, mais ne l’expose plus comme badge opérateur. Le style `openinfra-edition-badge` surcharge uniquement le fond et l’ombre du badge, sans modifier son gabarit Bootstrap.

## OpenInfra Web — accessibilité v0.29.46

La couche interface conserve le modèle API-only/BFF server-side, mais ajoute un contrat d’accessibilité explicite dans le domaine rendering : skip-link, landmarks, états actifs `aria-current`, accordéons liés par attributs ARIA, recherche globale exposée comme combobox/listbox et focus dirigé vers le contenu principal après sélection. Cette évolution ne modifie pas les contrats backend et ne duplique aucune règle métier côté navigateur.

## OpenInfra Web — badge édition fuchsia v0.29.48

Le header openinfra-web rend le badge d’édition à côté de la marque OpenInfra sans classe `text-bg-primary`. Cette décision évite l’héritage de la palette bleue Bootstrap tout en conservant le gabarit `.badge`. Le style dédié `badge.openinfra-edition-badge` est synchronisé entre le runtime statique et le frontend React.

## OpenInfra Web — badge édition fuchsia très foncé v0.29.49

Le badge d’édition reste dans le header principal, immédiatement après la marque OpenInfra. Le gabarit `.badge` est conservé sans modification dimensionnelle, mais le fond dédié passe à un dégradé fuchsia très foncé `#2a0015 → #4b001f → #6a1430`. La palette vise un rendu prune chaud/bruné sans utiliser de marron explicite ni de bleu Bootstrap. Les assets statiques et React partagent la même règle CSS afin d’éviter toute divergence runtime/build.
