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

La version 0.25.0 a introduit une capacité d’import massif sans modifier le contrat atomique du framework générique livré en 0.24.0. L’architecture reste hexagonale : le domaine décrit les rapports bulk, checkpoints et métriques ; l’application orchestre l’autorisation `sot.write`, le parsing streaming, les batches, la persistance d’avancement et l’écriture Source of Truth ; l’infrastructure fournit les parseurs et les référentiels JSON/PostgreSQL.

Le flux CSV bulk utilise `ImportDatasetParser.iter_rows` pour produire les lignes une par une. Les batches sont bornés par `batch_size`, les checkpoints sont persistés selon `checkpoint_interval`, et la reprise par `resume_job_id` redémarre au `next_row_number` du dernier checkpoint. Les impacts et DLQ restent échantillonnés pour éviter les rapports non bornés sur très gros datasets.

Côté PostgreSQL, `bulk_import_jobs` et `bulk_import_checkpoints` sont partitionnées par hash du tenant. Les métriques, mappings et échantillons sont stockés en JSONB afin de conserver un schéma robuste tout en gardant une recherche opérationnelle par tenant, statut, date et job. Cette livraison prépare l’optimisation COPY contrôlée côté PostgreSQL sans introduire de dépendance runtime supplémentaire ni coupler le domaine à psycopg.

Interfaces exposées : `openinfra import bulk-dataset`, `openinfra import bulk-report`, `openinfra import bulk-checkpoint`, `POST /api/v1/imports/bulk-datasets`, `GET /api/v1/imports/bulk-report` et `GET /api/v1/imports/bulk-checkpoint`. Les endpoints Swagger UI, ReDoc et OpenAPI YAML restent exposés par `/docs`, `/swagger`, `/redoc`, `/openapi.yaml` et `/api/v1/openapi.yaml`.
## v0.25.2 — Séparation requirements production/dev

La livraison corrective 0.25.2 ne modifie pas le domaine métier. Elle renforce l'industrialisation : les dépendances production, PostgreSQL optionnelles et dev/CI sont séparées dans `requirements/`, tandis que le garde de sécurité CI vérifie que cette séparation reste effective.


## v0.26.0 — P06 EPIC-0603 Exports asynchrones et signés

Le module d’export suit la séparation hexagonale existante. Le domaine `data_export` modélise les jobs, statuts, formats, filtres et métadonnées d’artefact. Le service applicatif `ExportService` orchestre l’authentification, l’audit, la création non bloquante du job, l’exécution paginée par worker, la sérialisation CSV/JSON/XLSX, le calcul SHA-256, la signature HMAC-SHA256 et la vérification d’intégrité avant restitution de l’artefact.

La clé de signature n’est pas codée en dur : elle est créée et persistée par le backend via `ExportRepository.get_or_create_export_signing_secret`. L’adaptateur JSON la stocke dans le document d’état local de test, tandis que l’adaptateur PostgreSQL utilise `export_signing_keys`. Les tables `export_jobs` et `export_artifacts` sont partitionnées par hash du tenant afin de rester alignées avec la stratégie multi-tenant et forte volumétrie du socle PostgreSQL.

Les interfaces restent fines : le CLI expose `openinfra export request`, `run`, `report` et `artifact`; l’API expose `POST/GET /api/v1/exports/jobs`, `POST /api/v1/exports/run` et `GET /api/v1/exports/artifact`. Aucun appel réseau externe ni stockage objet externe n’est imposé dans cette baseline ; le design isole déjà le stockage d’artefacts derrière le port repository pour permettre une évolution compatible.
