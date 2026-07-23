# OpenInfra v0.34.19

OpenInfra 0.34.19 corrige la matérialisation du contexte de build Docker observée lorsque le runbook `RSOT_QUALITY_NON_AUTHORITATIVE_SOURCE.md` manque dans l’arbre local alors que le backend de packaging l’exige. Le contrôle strict n’est pas contourné : la source qualifiée est complète, le Dockerfile embarque désormais l’ensemble de `docs/`, et un préflight déterministe bloque immédiatement toute source incomplète avant l’installation Python.

## Correctif du contexte Docker et du packaging — v0.34.19

- copie atomique de l’arborescence documentaire complète par `COPY docs ./docs` ;
- validation préalable de chaque source `force-include` déclarée dans `pyproject.toml` ;
- diagnostic explicite des fichiers absents et des sources non couvertes par les instructions `COPY` ;
- backend de packaging rendu transactionnel : aucune ressource partiellement stagée lorsqu’une source requise manque ;
- `.dockerignore` versionné et inclus dans le sdist afin de stabiliser le contexte Docker sans exclure les ressources runtime ;
- tests unitaires et d’intégration couvrant source incomplète, ressource non copiée, staging/cleanup et build de wheel en contexte minimal ;
- quality gate GitHub Actions dédié avant la construction des distributions ;
- aucune migration, aucune rupture API/CLI/RBAC et aucune modification de la charte graphique approuvée.

Voir `docs/runbooks/RUNTIME_DOCKER.md`.

## Alerte de source non autoritative RSOT — v0.34.18

- finding stable `non_authoritative_source` avec champ gouverné, source observée, source attendue et règle autoritative ;
- message opérateur explicite sans suppression ni modification des champs historiques ;
- résolution déterministe des chemins simples, globaux (`*`) et imbriqués tels que `hardware.serial_number` ;
- dégradation du score d’autorité et statut `warning` cohérents entre service, CLI, HTTP et synthèse tenant ;
- audit enrichi par le score d’autorité, le nombre d’anomalies et le nombre d’anomalies non autoritatives ;
- rendu accessible dans les portails React et runtime, avec échappement des données dynamiques ;
- preuve GATE-14 `TST-RSOTQUAL-048`, OpenAPI, CI, runbook, packaging et smoke installé synchronisés ;
- aucune migration, aucune rupture API/CLI/RBAC et aucune modification de la charte graphique approuvée.

Voir `docs/runbooks/RSOT_QUALITY_NON_AUTHORITATIVE_SOURCE.md`.

### Résultats autonomes 0.34.18

- **295/295** fichiers de tests Python et **1 687/1 687** tests réussis ;
- couverture exacte : **49 396/50 392**, soit **98,023495792983 %** ;
- **100/100** tests frontend autonomes ;
- **60/60** migrations PostgreSQL/Oracle ;
- GATE-14 : **31 automatisées, 588 partielles, 48 externes, 44 sélecteurs et 77 fichiers d’évidence** ;
- wheel et sdist reproductibles bit à bit ; vérification stricte du contenu et smoke installé local : **PASS** ;
- promotion final-candidate maintenue en **NO-GO** jusqu’à la fermeture des gates d’outillage, de registres et d’infrastructure externes.

## Contrôle RBAC de la qualité RSOT — v0.34.17

OpenInfra 0.34.17 ferme la preuve contractuelle `TST-RSOTQUAL-047` : un rôle sans permission `rsot.quality.read` ne peut consulter aucun résultat de qualité RSOT par service, CLI, API HTTP ou portail. L’incrément corrige également la réouverture du backend JSON afin qu’elle ne réinjecte jamais les données de démonstration dans un fichier existant.

- contrôle `rsot.quality.read` exécuté avant toute lecture d’objet ou de synthèse ;
- refus cohérent par service, CLI et API HTTP pour un rôle `dcim:operator` ;
- aucune donnée métier divulguée dans les sorties refusées ;
- aucune mutation du fichier d’état ni événement qualité lors d’un refus ;
- initialisation JSON de démonstration limitée à la création initiale du fichier ;
- preuve GATE-14 `TST-RSOTQUAL-047` exécutée explicitement dans la CI.

Voir `docs/runbooks/RSOT_QUALITY_RBAC.md`.

### Résultats autonomes 0.34.17

- **293/293** fichiers de tests Python et **1 680/1 680** tests réussis ;
- couverture exacte : **49 374/50 371**, soit **98,020686506125 %** ;
- **99/99** tests frontend autonomes ;
- GATE-14 : **30 automatisées, 589 partielles, 48 externes, 43 sélecteurs et 74 fichiers d’évidence**.

OpenInfra 0.34.16 ferme la preuve contractuelle `TST-RSOTQUAL-046` : un objet RSOT complet, récent et alimenté par une source autoritative obtient un score de qualité supérieur ou égal à 90 et le statut `certified`. Le résultat est identique par service, CLI et API HTTP, audité, puis présenté dans les portails React et runtime sous forme de rapport accessible. L’incrément conserve toutes les preuves qualifiées jusqu’à 0.34.15, n’ajoute aucune migration et ne modifie pas la charte graphique approuvée.

## Certification qualité RSOT autoritative — v0.34.16

- calcul inchangé des dimensions de complétude, fraîcheur, autorité et confiance ;
- certification réservée aux objets sans erreur ni avertissement et dont le score est `>= 90` ;
- règle de gouvernance autoritative vérifiée sur l’attribut `serial` ;
- cohérence du résultat entre service, CLI, API HTTP et synthèse ;
- audit `rsot.quality.evaluate` et `rsot.quality.summary` contrôlé ;
- rapport accessible dans les deux portails avec scores par dimension, statut, anomalies et JSON brut ;
- preuve GATE-14 `TST-RSOTQUAL-046` exécutée explicitement dans la CI ;
- runbook et contrats de packaging synchronisés ;
- aucune migration et aucune modification de la charte graphique.

Voir `docs/runbooks/RSOT_QUALITY_CERTIFICATION.md`.

### Résultats autonomes 0.34.16

- **292/292** fichiers de tests Python et **1 679/1 679** tests réussis ;
- couverture exacte : **49 373/50 370**, soit **98,020647210641 %** ;
- **97/97** tests frontend autonomes ;
- **60/60** migrations PostgreSQL/Oracle ;
- GATE-14 : **29 automatisées, 590 partielles, 48 externes, 42 sélecteurs et 71 fichiers d’évidence** ;
- promotion final-candidate maintenue en **NO-GO** jusqu’à la fermeture des gates d’outillage et d’infrastructure externes.

## Assistant RAG gouverné et cité — v0.34.15

- réponses extractives fondées uniquement sur les sources autorisées du tenant ;
- références `source_objects` dédupliquées avec clé RSOT, URI, document, fragment et score ;
- contrat `governance.mode=read-only` et `source_data_mutation_performed=false` ;
- validation distincte obligatoire avant tout changement avec `change_validation_required=true` ;
- absence de capacités d’exécution dans `execution_capabilities=[]` ;
- audit du nombre d’objets sources et de la garantie de non-mutation, sans question en clair ;
- rapport accessible dans les portails React et runtime avec réponse, objets sources, citations et scores ;
- preuve GATE-14 `TST-FUNC-0010` exécutée explicitement dans la CI ;
- aucune migration et aucune modification de la charte graphique.

Voir `docs/runbooks/GOVERNED_RAG_ASSISTANT.md`.

## Consultation historique RSOT « time travel » — v0.34.14

- résolution du snapshot applicable à une date ISO-8601 ;
- provenance explicite du système source, de l’acteur, de l’horodatage et de l’identifiant du snapshot ;
- relations entrantes et sortantes filtrées par leurs fenêtres de validité historiques ;
- invariants de cohérence vérifiés entre clé, identifiant, version et payload ;
- restitution bornée par `relation_limit`, avec `complete=false` lorsque la cartographie n’est pas exhaustive ;
- commande CLI `openinfra rsot get-object-as-of`, endpoint `GET /api/v1/rsot/object-as-of` et rapport accessible dans les deux portails ;
- lecture seule et audit `rsot.object.time-travel.read` ;
- preuve GATE-14 `TST-FUNC-0009` exécutée explicitement dans la CI ;
- aucune migration et aucune modification de la charte graphique.

Voir `docs/runbooks/RSOT_TIME_TRAVEL.md`.

## Analyse d’impact d’un changement applicatif — v0.34.13

- parcours borné du graphe RSOT depuis la ressource modifiée ;
- classification configurable des applications, services, bases et ressources métier ;
- rapport des dépendances dominatrices critiques, des services affectés et du risque SPOF racine ;
- résultats déterministes, auditables et explicitement marqués incomplets lorsque `max_nodes` est atteint ;
- commande CLI `openinfra graph change-impact`, endpoint `GET /api/v1/graph/change-impact` et opération équivalente dans les deux portails ;
- rendu accessible avec synthèse, tableaux des services et dépendances, puis visualisation et JSON brut ;
- exécution synchrone ou via le worker spécialisé `graph.change-impact` ;
- preuve GATE-14 `TST-FUNC-0005` exécutée explicitement dans la CI ;
- aucune migration et aucune modification de la charte graphique.

Voir `docs/runbooks/APPLICATION_CHANGE_IMPACT.md`.

## Découverte distribuée SNMP/SSH — v0.34.12

- publication atomique du résultat d’un job et de sa preuve immuable ;
- authentification du collector par empreinte de certificat, validation du worker, du bail et du jeton de fencing ;
- compatibilité stricte entre le type du collector et la source SNMP, SSH ou WinRM ;
- identifiant de preuve déterministe lié au job, rejeu identique accepté et rejeu divergent rejeté ;
- historique conservé sans écrasement silencieux et SHA-256 de preuve rattaché au job complété ;
- rapprochement multi-source bloquant l’écriture RSOT lorsqu’un attribut diverge ;
- commande CLI `openinfra discovery job-result`, endpoint `POST /api/v1/discovery/jobs/result` et opérations dans les deux portails ;
- preuve GATE-14 `TST-FUNC-0004` exécutée explicitement dans la CI ;
- aucune migration et aucune modification de la charte graphique.

Voir `docs/runbooks/DISTRIBUTED_DISCOVERY_RESULTS.md`.

## Import massif asynchrone CSV/XLSX — v0.34.11

- dépôt HTTP binaire en streaming, sans chargement intégral en mémoire ;
- limite de 512 Mio pour CSV et de 50 Mio pour XLSX ;
- protections contre archives XLSX chiffrées, surdimensionnées, trop nombreuses ou à expansion XML excessive ;
- soumission idempotente du job `imports.bulk-dataset`, suivi HTTP et reprise par checkpoint persistant ;
- traitement par worker spécialisé avec création RSOT et disponibilité maintenue de l’API interactive ;
- opérations équivalentes dans les portails React et runtime embarqué ;
- preuve GATE-14 `TST-FUNC-0003` exécutée explicitement dans la CI ;
- commande déclarative `openinfra auth policy` sans création d’état local `.openinfra.json`.

Voir `docs/runbooks/ASYNC_BULK_IMPORTS.md`.

## Localisation DCIM et réservation IP concurrente — v0.34.10

- localisation structurée jusqu’au site, bâtiment, étage, salle, grille, zone, rack, position U, face et coordonnées ;
- fiche d’intervention JSON/HTML et payload compact de repérage accessibles par CLI, API et portails ;
- opération **Fiche d’intervention équipement** recherchable sous **DCIM → Localisation & capacité** ;
- allocation IP atomique sous concurrence, persistance transactionnelle et rejeu idempotent ;
- preuves GATE-14 `TST-FUNC-0001` et `TST-FUNC-0002` exécutées dans la CI ;
- aucune migration et aucune modification de la charte graphique.

Voir `docs/runbooks/DCIM_LOCATION_IPAM_CONCURRENCY.md`.

## Synchronisation IPAM vers DNS/DHCP — v0.34.9

- journal durable, idempotent et verrouillé par tenant et clé d’exécution ;
- adaptateurs BIND/nsupdate, PowerDNS et Kea sans shell, avec TLS vérifié et délais bornés ;
- prélecture fournisseur et rollback exact de l’état antérieur ;
- compensation inverse et état fail-closed `compensation_failed` lorsque le résultat est incertain ;
- permission dédiée `ipam.ddi.sync`, CLI `openinfra ipam ddi-sync` et API `POST /api/v1/ipam/ddi-sync` ;
- migration additive `0060_ipam_ddi_execution_journal.sql`, catalogues PostgreSQL/Oracle alignés 60/60 ;
- `TST-FUNC-0008` promu en preuve GATE-14 automatisée ;
- compatibilité préservée pour `ddi-preview`, les réservations IPAM et les fonctionnalités existantes.

Voir `docs/runbooks/IPAM_DDI_SYNCHRONIZATION.md`.


## Recommandation de placement DCIM — v0.34.9

- sélection des racks actifs d’une salle avec filtrage optionnel de zone et de face ;
- calcul des blocs U contigus en tenant compte des équipements et panneaux de brassage ;
- validation de la puissance résiduelle du rack et des circuits simples ou A/B redondants ;
- refus fail-closed lorsque la zone de refroidissement ou sa capacité est absente ;
- classement stable par ajustement physique, marges électriques et marge thermique ;
- CLI `openinfra dcim recommend-placement`, API `GET /api/v1/dcim/placement-recommendations` et portail DCIM ;
- aucune réservation implicite, aucune migration et aucun changement de charte graphique.

Voir `docs/runbooks/DCIM_PLACEMENT_RECOMMENDATIONS.md`.

## Complétude contractuelle — P25 / REL-15 / GATE-14

- CDC 4.12.0 : 861 exigences, 667 tests, 861 lignes de traçabilité et 529 entités ;
- roadmap 2.5.0 : P25, REL-15, EPIC-2501 à EPIC-2504 et GATE-14 ;
- registre exhaustif de 667 preuves : 31 automatisées, 588 partielles et 48 externes ;
- 44 sélecteurs pytest réels, validés par analyse AST, rattachés aux preuves automatisées ;
- 77 fichiers d’évidence distincts, aucun test sans preuve et aucune exigence N1 non classifiée ;
- scanner d’hygiène contextuel : les règles de détection sont exclues par chemin exact, tandis que les sources produit restent contrôlées ;
- packaging du registre, de la politique, du runbook et du validateur dans le wheel et le sdist ;
- workflow GitHub Actions complet : formatage, lint, typage, tests, couverture, sécurité, frontend, build, vérification et smoke isolé.

Les preuves `partial` et `external` ne constituent jamais une validation fonctionnelle complète. La promotion production reste NO-GO tant que les qualifications externes ne sont pas exécutées sur l’infrastructure cible et rattachées au véritable commit de publication.

Voir `docs/runbooks/CONTRACT_COMPLETENESS_PROMOTION.md`.

## RSOT canonique — P24 / REL-14 / GATE-13

- commande publique unique `openinfra rsot` ;
- routes publiques uniques `/api/v1/rsot/*` ;
- anciens endpoints ITRM/RI/SOT explicitement non trouvés ;
- rôles intégrés exclusivement sous `rsot:reader`, `rsot:operator` et `rsot:governance-admin` ;
- capacité d’édition unique `core_rsot` ;
- suppression des modules Python de compatibilité ITRM/RI ;
- guide de migration opérateur et tests de rejet de tous les anciens contrats ;
- qualification GATE-13 sur six contrôles exécutables, packaging et smoke du wheel installé.

Voir `docs/runbooks/RSOT_CANONICAL_MIGRATION.md`.

## Licence runtime offline — GATE-12

- identité d’installation Ed25519 et demande d’activation signée ;
- entitlement signé hors ligne par une autorité dont seule la clé publique est déployée ;
- liaison stricte UUID de licence, UUID d’installation, entreprise, édition, quota d’hôtes et échéances ;
- persistance transactionnelle JSON, PostgreSQL et Oracle avec migration `0059_runtime_offline_licensing.sql` ;
- contrôle du quota d’hôtes dans la même unité de travail que la création d’équipement ;
- statuts `missing`, `active`, `grace`, `expired` et `invalid`, avec détection du recul d’horloge ;
- blocage CLI et HTTP 402 lorsque `OPENINFRA_LICENSE_ENFORCEMENT=true` ;
- bootstrap installateur Pro/Enterprise avec permissions Unix strictes et demande offline générée localement ;
- notifications accessibles dans les portails React et statique, sans exposition de matériel secret ;
- qualification bloquante GATE-12 sur sept contrôles et exclusion de toute clé privée d’autorité de l’arbre produit.

Voir `docs/runbooks/OFFLINE_RUNTIME_LICENSING.md`.

## Parité PostgreSQL / Oracle — P22 / GATE-11

- catalogue Oracle complet `0001` à `0060`, aligné sur les noms, versions et fonctionnalités du catalogue PostgreSQL ;
- convertisseur déterministe PostgreSQL → Oracle 19c, limité aux constructions réellement utilisées par OpenInfra et bloquant toute syntaxe PostgreSQL résiduelle ;
- manifeste `installers/migrations/oracle/manifest.json` avec empreintes SHA-256 source/cible et nombre d’instructions ;
- adaptation des types, UUID, JSON, CLOB/BLOB, identités, contraintes, index fonctionnels, partitionnement hash, `MERGE`, DML et blocs PL/SQL ;
- refus des index B-tree sur LOB, des clés d’index dépassant la limite conservatrice de 6 000 octets, des identifiants incompatibles et des migrations modifiées manuellement ;
- journal Oracle `applying` / `applied` / `failed`, contrôle des deux empreintes, détection de dérive et reprise idempotente après interruption ;
- compatibilité de reprise avec l’ancien historique Oracle limité à `0001_document_state.sql` ;
- migration `0058_oracle_document_shards.sql` et persistance Oracle segmentée par collection métier, avec reprise transparente depuis l’ancien document global ;
- contrôle optimiste par segment : une collision sur un domaine est refusée sans bloquer les écritures d’un autre domaine dans les autres processus ;
- garde d’édition centralisée : toute sélection Oracle en Lite ou Pro échoue avant chargement du pilote, connexion ou migration ;
- readiness Oracle exigeant les shards et l’application cohérente des 60 migrations ;
- GATE-11 bloquant dans les workflows CI avant lint, typage, sécurité, build et promotion ;
- packaging du catalogue PostgreSQL, du catalogue Oracle et du manifeste dans le wheel et le sdist ;
- aucune modification du thème, d’une route API, d’une commande CLI métier ou d’une permission RBAC.

La génération et la validation locale s’effectuent avec :

```bash
python scripts/generate_oracle_migrations.py
python scripts/validate_oracle_migrations.py
```

Le second appel est non destructif et échoue si une migration Oracle ou le manifeste diverge du résultat déterministe attendu. Voir `docs/runbooks/ADVANCED_IDENTITY_ORACLE_SYSTEMD.md`.

## Identité avancée, Team Sync et production systemd — P22 / REL-12

- authentification SAML 2.0 avec validation cryptographique, configuration fournisseur chargée uniquement depuis le serveur et mapping groupes → rôles OpenInfra ;
- LDAP/IPA avancé avec LDAPS, StartTLS, autorité de certification, pagination, timeouts, referrals et résolution bornée des groupes imbriqués ;
- Team Sync idempotent pour LDAP, OAuth, Auth Proxy signé HMAC et Okta, avec propriété des appartenances par source, audit et politique contrôlée des orphelins ;
- PostgreSQL reste le backend de référence et le choix automatique lorsqu’aucun backend n’est configuré ;
- déploiement serveur standard avec `openinfra.conf`, fichiers de secrets protégés et unités systemd pour migrations, génération du jeton bootstrap, API/Web et synchronisation des équipes ;
- correction historique de la migration PostgreSQL `0057_federated_identity_team_sync.sql` conservée et transposée dans le catalogue Oracle ;
- aucune modification de la charte graphique ni suppression d’API, de CLI ou de permission existante.

Voir `docs/runbooks/ADVANCED_IDENTITY_ORACLE_SYSTEMD.md` et `docs/runbooks/RUNTIME_NATIVE.md`.

## Configuration runtime interne

Les variables `OPENINFRA_IMAGE_TAG`, `OPENINFRA_WEB_EDITION`, `OPENINFRA_WEB_PUBLIC_API_BASE_URL` et `OPENINFRA_BOOTSTRAP_TOKEN` ne sont plus administrées dans `.env`. OpenInfra résout le tag depuis `VERSION`, découvre l’édition du backend, utilise le BFF same-origin `/api` et génère le jeton bootstrap dans un stockage runtime protégé. Les anciennes entrées `.env` sont purgées de façon atomique et idempotente.

## Qualification Cloud-native — P21 / EPIC-2106

- sept preuves immuables couvrant EPIC-2101 à EPIC-2106 ;
- contrôle SHA-256, fraîcheur, version, catalogue fermé et protection contre le path traversal ;
- benchmark runtime réel sur trois clusters, dont un snapshot de 50 000 ressources ;
- vérification des fingerprints déterministes et du mapping physique ;
- validation du read model de capacité cluster/namespace ;
- probes de sécurité contre les secrets en clair, les références inter-namespace et les chemins physiques orphelins ;
- workflow GitHub Actions bloquant `cloud-native-promotion.yml` ;
- intégration au quality gate, au sdist et au smoke du wheel installé ;
- aucune migration supplémentaire, aucun changement API/CLI métier et aucune modification du thème.

Voir `docs/runbooks/CLOUD_NATIVE_PROMOTION.md` et `docs/release/cloud-native-promotion-policy.json`.

## Correctif PostgreSQL — UnitOfWork Kubernetes — v0.33.8

- toutes les lectures des repositories Kubernetes et GitOps s’exécutent dans un `UnitOfWork` actif ;
- les imports idempotents vérifient désormais l’existence et écrivent dans la même unité de travail ;
- les corrélations exposition/sécurité et les tendances de capacité conservent leurs lectures associées dans une frontière transactionnelle explicite ;
- les évaluations GitOps lisent l’état attendu et observé puis écrivent audit/outbox dans une transaction unique, sans transaction imbriquée ;
- un test de non-régression interdit tout nouvel accès repository Kubernetes hors unité de travail ;
- aucune migration, route API, commande CLI ou modification du thème.

## Capacité Kubernetes — P21 / EPIC-2105

- agrégation cluster et namespace des demandes, limites et consommations ;
- capacités CPU/mémoire issues des Nodes et stockage issu des Volumes ;
- alertes warning/critical sur seuils explicites ;
- tendances limitées à 96 snapshots et 1 000 000 de ressources cumulées ;
- exports JSON et CSV ;
- parité API, CLI et UI Discovery ;
- aucune nouvelle migration, fingerprints historiques préservés.

Documentation : `docs/architecture/kubernetes-capacity.md` et `docs/operations/kubernetes-capacity.md`.

## Conformité GitOps et dérive observée — P21 / EPIC-2104

- états GitOps attendus immuables, versionnés par empreinte SHA-256 et liés à un commit Git complet ;
- politiques explicites pour labels, annotations, owner, environnement et ressources inattendues ;
- comparaison déterministe avec les snapshots Kubernetes observés existants ;
- dérives typées et auditables, sans correction automatique silencieuse ;
- persistance PostgreSQL partitionnée et outbox transactionnelle via `0056_kubernetes_gitops_drift.sql` ;
- six opérations en parité HTTP, CLI, OpenAPI et portail Discovery ;
- `automatic_remediation=false` contractuel.

Voir `docs/architecture/kubernetes-gitops-drift.md` et `docs/operations/kubernetes-gitops-drift.md`.

## Filtres multicritères des pages de gestion

- critères toujours visibles, même lorsque la liste courante ne fournit encore aucune valeur ;
- séparation professionnelle entre **Contexte parent** et **Critères métier** ;
- ordre canonique Organisation → Filiale/Subdivision → Site → Bâtiment → Étage → Salle → Ligne/Colonne → Rack ;
- filtres parents en cascade avec invalidation des descendants ;
- contexte DCIM enrichi pour rendre Étage, Ligne et Colonne réellement filtrables ;
- panneau de recherche entièrement aligné sur les surfaces, bordures, transparences, typographie et boutons du thème existant ;
- aucune modification de la palette graphique.

Voir `docs/ui/MANAGEMENT_CONTEXT_HIERARCHY.md`.

## Corrélation sécurité cloud-native — P21 / EPIC-2103

- images OCI normalisées et digest SHA-256 optionnel ;
- association explicite ou contextuelle aux documents SBOM existants ;
- contextualisation des findings actifs et critiques par workload/pod ;
- corrélation des empreintes de certificats avec l’inventaire PKI ;
- références de secrets approuvées, masquées pour les fournisseurs externes et hachées ;
- aucun contenu de secret, mot de passe, token ou clé privée ingéré ;
- rapport déterministe et borné, avec signalement explicite d’une corrélation tronquée ;
- compatibilité des fingerprints de snapshots historiques préservée ;
- API, CLI, OpenAPI et portail Discovery en parité ;
- aucune nouvelle migration et aucune modification de la charte graphique.

Voir `docs/architecture/kubernetes-cloud-native-security.md` et `docs/operations/kubernetes-security-correlation.md`.

## Gestion CRUD unifiée

La navigation web consolide les opérations CRUD homogènes en une entrée **Gestion de …** par ressource. Chaque espace propose une liste complète et paginée, une recherche plein texte, des filtres multicritères, un accès aux détails, un bouton **+ Nouveau**, des actions **Éditer** et **Supprimer**, puis un retour automatique à la liste après mutation. Les endpoints API et les commandes CLI historiques restent inchangés.


## Expositions cloud-native — P21 / EPIC-2102

- corrélation `ingress`, `load-balancer`, `dns-record`, `service` et `mesh-route` ;
- endpoints DNS/IP/ports normalisés et scopes `cluster`, `internal`, `external` ;
- corrélation avec la matrice de flux existante (`ANY`, `CIDR`, `OBJECT`) ;
- corrélation avec les objets et relations de dépendance RSOT ;
- graphe déterministe d’exposition jusqu’aux workloads et dépendances réseau ;
- signalement des expositions externes non gouvernées sans mutation automatique de l’infrastructure ;
- bornes de protection : 10 000 déclarations de flux, 10 000 relations et 2 048 objets RSOT ;
- API, CLI, OpenAPI et portail Discovery en parité ;
- aucune migration supplémentaire et aucune modification de la charte graphique.

Voir `docs/architecture/kubernetes-cloud-native-topology.md` et `docs/operations/kubernetes-topology.md`.

## Kubernetes & Cloud-native — P21 / EPIC-2101

- inventaire `namespace`, `node`, `workload`, `pod`, `service`, `ingress`, `network-policy` et `volume` ;
- instantanés limités à 50 000 ressources et pagination curseur PostgreSQL ;
- intégrité référentielle stricte, relations typées et isolation inter-namespace ;
- rejet des attributs contenant des clés sensibles ;
- mapping `pod → node → VM → hyperviseur → serveur → rack → salle → site` ;
- API, CLI et portail Discovery en parité ;
- permissions `kubernetes.read` et `kubernetes.write`, rôles dédiés et audit ;
- persistance JSON et PostgreSQL partitionnée via migration `0055_kubernetes_topology_inventory.sql` ;
- roadmap **2.2.0** avec P21, REL-11, M13 et GATE-10 ;
- aucune modification de la charte graphique.

Voir `docs/architecture/kubernetes-cloud-native-topology.md` et `docs/operations/kubernetes-topology.md`.

## Promotion Enterprise Scale-out — GATE-09 / REL-10 — v0.32.12

- agrégation de sept preuves certifiées produites par P20 et les gates Enterprise ;
- contrôle de version, fraîcheur, SHA-256 et cohérence du commit source ;
- workflow protégé `enterprise-scaleout-promotion.yml` ;
- aucune mutation d'infrastructure par le certificateur.

Voir `docs/runbooks/ENTERPRISE_SCALEOUT_PROMOTION.md` et `docs/release/enterprise-scaleout-promotion-policy.json`.

## Chaos multisite — P17 / EPIC-1706 — v0.32.11

- six scénarios obligatoires : partition réseau, perte de site, perte d’agent, perte DB, saturation de file et perte frontend ;
- harness externe à protocole fixe `preflight` / `inject` / `recover` / `verify-recovered`, sans shell libre ;
- harness absolu, exécutable, non symbolique et non modifiable par le groupe ou les autres utilisateurs ;
- endpoints de santé et d’intégrité obligatoirement en HTTPS ;
- mesure de disponibilité, taux d’erreur, temps de récupération et SHA-256 avant/après ;
- récupération systématique dans le nettoyage et arrêt de campagne après un rollback non vérifié ;
- refus de certification en cas de corruption, perte de travail acquitté, SLO dépassé ou preuve altérée ;
- six rapports bruts, manifeste d’évidence signé par digest et rapport final conservés 90 jours ;
- gate CI, quality gate et packaging étendus ;
- aucune migration PostgreSQL, aucune rupture API/CLI métier et aucune modification du thème.

Voir `docs/runbooks/MULTISITE_CHAOS.md` et `docs/operations/multisite-chaos-profile.json`.

## Observabilité multisite — P17 / EPIC-1705 — v0.32.10

- lag maximal des agents Discovery calculé à partir des heartbeats réellement persistés ;
- déduplication d’un même collecteur lorsqu’il dessert plusieurs VRF d’un même site ;
- métriques Prometheus bornées par `region` et `site`, sans identifiant de tenant, d’utilisateur ou d’objet métier ;
- fédération HTTPS des `/metrics` de chaque site avec file service discovery et redirections désactivées ;
- dashboard Grafana `OpenInfra Multisite Operations` avec filtres région/site ;
- visibilité sur disponibilité API, p95 HTTP, erreurs 5xx, agents, réplication PostgreSQL et files de jobs ;
- six alertes multisites et seuils versionnés dans un profil machine-readable ;
- validateur strict des fichiers de cibles : `host:port`, labels exacts `region`, `site`, `service`, aucune donnée secrète ;
- gate CI et quality gate bloquants ;
- aucune migration PostgreSQL, aucune rupture API/CLI métier et aucune modification du thème.

Voir `docs/runbooks/MULTISITE_OBSERVABILITY.md` et `docs/operations/multisite-observability-profile.json`.

## PRA/PCA complets — P17 / EPIC-1704 — v0.32.9

- certification applicable aux éditions Pro et Enterprise ;
- réutilisation des plans et exercices DR immuables livrés par EPIC-1703 ;
- mesure conservatrice du RPO à partir du pire cas entre lag de réplication et perte de données PITR ;
- mesure conservatrice du RTO à partir du pire cas entre exercice DR et récupération PITR ;
- contrôle de fraîcheur des sauvegardes, restauration, intégrité, chiffrement et cohérence PITR ;
- dix étapes de procédure obligatoires, toutes explicitement attestées ;
- cinq sources hachées en SHA-256 et manifeste final protégé par un digest déterministe ;
- workflow GitHub Actions manuel sur environnement protégé et runner dédié ;
- gate CI et quality gate bloquants ;
- aucune migration PostgreSQL, aucune modification d’API/CLI métier et aucune modification du thème.

Voir `docs/runbooks/PRA_PCA_CERTIFICATION.md` et `docs/operations/pra-pca-profile.json`.

## Hiérarchie bleu nuit et profondeur transparente — v0.32.8

- menus racine de la sidebar, contextes et titres de page en bleu nuit très foncé proche du noir ;
- palette IONOS/OpenInfra inchangée et verrouillée par tests de non-régression ;
- transparence appliquée aux surfaces de navigation, cartes, formulaires, recherche, tableaux et panneaux secondaires ;
- aucun `opacity` appliqué aux conteneurs lisibles : textes, icônes et contrôles conservent leur contraste ;
- effets de profondeur par `backdrop-filter` avec fallback opaque pour les navigateurs non compatibles ;
- mode contraste renforcé, réduction des animations, responsive et accessibilité conservés ;
- synchronisation stricte du thème entre le frontend React et le runtime packagé.
- fond du composant racine actif invariant au hover/focus ; seuls l’icône, le texte et le chevron passent au bleu turquoise.

## Support et maintenance — P18 / EPIC-1806

- profils Lite, Pro et Enterprise avec canaux et horaires de service ;
- sévérités S1 à S4 avec objectifs de réponse, de mise à jour et de restauration ;
- cycle de vie active, maintenance, sécurité uniquement et fin de vie ;
- politique de patch par criticité ;
- migrations directes N-1, migrations étagées N-2 et rollback obligatoire ;
- escalade L1, L2, L3 et incident command ;
- preuve `support-readiness` signée et workflow CI bloquant.

Voir `docs/ga/SUPPORT.md`, `docs/runbooks/SUPPORT_MAINTENANCE.md` et `docs/release/support-maintenance-policy.json`.

## Documentation GA — P18 / EPIC-1804

- point d'entrée unique dans `docs/ga/README.md` ;
- guides administrateur, utilisateur, API, installation, exploitation, PRA/PCA, upgrade et diagnostic ;
- manifeste machine-readable versionné ;
- validation des liens, sections, commandes CLI, opérations OpenAPI et marqueurs de version ;
- workflow GitHub Actions dédié et contrôle intégré au quality gate ;
- aucune modification de la charte graphique ni des contrats métier.

Voir `docs/ga/README.md` et `docs/architecture/ga-documentation-governance.md`.

## Audit sécurité de release — P18 / EPIC-1802

- catalogue fermé de huit contrôles : secrets/workflows, SAST, RBAC/authentification, dépendances Python/Node, dépôt, image et DAST ;
- exécution sans shell, timeout borné et environnement enfant réduit ;
- redaction des secrets avant persistance des preuves ;
- empreinte SHA-256 de chaque sortie et digest global du rapport ;
- workflow de release sur tags, image construite, topologie Compose réelle et artefacts conservés 90 jours ;
- certification impossible si un contrôle est absent, non exécuté, indisponible, en timeout ou en échec ;
- gestionnaire `.env` idempotent générant tous les secrets obligatoires sans écraser les valeurs existantes.

Voir `docs/architecture/release-security-certification.md` et `docs/runbooks/RELEASE_SECURITY.md`.

## Benchmarks Enterprise Scale — P18 / EPIC-1801

- profil de certification de capacité v2 rétrocompatible avec les preuves v1 historiques ;
- six familles obligatoires : API, IPAM, imports, Discovery, base de données et graphes ;
- runner HTTP asynchrone en lecture seule, keep-alive, concurrence et tâches en vol bornées ;
- chemins de qualification externalisés pour viser un dataset Enterprise réellement représentatif ;
- p95, p99, taux d'erreur, débit, octets et distribution des statuts par famille ;
- intégration des six preuves et de leurs SHA-256 dans `capacity_certification` ;
- workflow Enterprise bloquant : aucun `capacity_certification=true` n'est possible si une famille manque ou dépasse les seuils.

Voir `docs/architecture/enterprise-observability-capacity.md` et `docs/runbooks/OBSERVABILITY_CAPACITY.md`.

## Observabilité et charge Enterprise — P20 / EPIC-2005

- instrumentation API, BFF, workers, outbox, files asynchrones, pools PostgreSQL et réplication ;
- endpoints `/metrics` API et web compatibles avec les workers ASGI multiprocessus ;
- propagation W3C `traceparent` et export OTLP/HTTP optionnel ;
- pile Compose optionnelle Prometheus, OpenTelemetry Collector, Tempo et Grafana ;
- règles d'alerte p95/p99, 5xx, saturation, file bloquée, DLQ, pool et lag réplique ;
- profil v2 versionné avec six benchmarks métier, cinq phases de charge et quatre scénarios de chaos ;
- rapport atomique avec empreintes SHA-256 et gate `--enforce` ;
- aucune certification possible sans preuves Enterprise complètes.

Voir `docs/architecture/enterprise-observability-capacity.md` et `docs/runbooks/OBSERVABILITY_CAPACITY.md`.

## Frontend modulaire et virtualisé — P20 / EPIC-2004

- huit chunks métier plus le Dashboard, chargés à la navigation ;
- manifeste initial limité aux métadonnées statistiques ;
- index de recherche et taxonomie RSOT différés ;
- cache de requêtes mémoire avec TTL, déduplication, invalidation et `AbortController` ;
- protection contre les réponses concurrentes obsolètes ;
- virtualisation automatique au-delà de 40 résultats ;
- observation LCP, INP et tâches longues ;
- budgets CI de 250 Kio JavaScript brut et 150 Kio gzip pour le shell initial ;
- aucune persistance sensible dans le navigateur et aucune modification CSS.

Voir `docs/architecture/modular-virtualized-frontend.md` et `docs/operations/frontend-performance.md`.

## Outbox et workers spécialisés — P20 / EPIC-2003

- soumission idempotente des jobs par tenant ;
- claims concurrents, leases renouvelables et jetons de fencing monotones ;
- retries bornés, dead-letter queue et rejeu sous permission administrative ;
- workers spécialisés reporting, imports, graphes et RAG, plus dispatcher d’outbox ;
- dépôt contrôlé des artefacts d’entrée, résultats vérifiés par SHA-256 et stockage hors PostgreSQL ;
- parité CLI, REST, OpenAPI et métriques d’exploitation.

Voir `docs/architecture/transactional-outbox-workers.md` et `docs/runbooks/ASYNC_WORKERS.md`.


## Sécurité, design system et documentation API

La version `0.30.6` durcit les planchers de dépendances audités, harmonise les deux portails avec un système de design bleu nuit commun et organise Swagger/ReDoc selon la hiérarchie **Composant → Contexte métier → Endpoint**.

Le correctif `0.30.6` rend l’état actif des composants du header plus discret : aucune surface blanche, un fond bleu/cyan translucide, un repère inférieur fin et une icône atténuée par opacité.

- `cryptography>=48.0.1,<50.0` ;
- `urllib3>=2.7.0,<3.0` pour l'outillage de développement et d'audit ;
- 51 tests frontend couvrant palette, contrastes, parité des thèmes et accessibilité ;
- 331 opérations OpenAPI classifiées dans 69 contextes et 16 composants ;
- `x-tagGroups` pour ReDoc et tri métier déterministe dans Swagger UI.

Voir `docs/operations/api-documentation-organization.md`.


## Pagination keyset et exports progressifs — P20 / EPIC-2002

OpenInfra 0.30.7 remplace les offsets profonds des collections PostgreSQL non bornées par des curseurs opaques signés. Les jetons sont liés au tenant, aux filtres et au tri, empêchant leur réutilisation hors contexte. Les anciens curseurs numériques restent acceptés temporairement pour compatibilité et la réponse suivante fournit immédiatement un curseur opaque.

Les exports JSON, CSV et XLSX sont désormais sérialisés au fil des pages dans un tampon borné qui bascule sur disque au-delà du seuil. Les signatures HMAC, la vérification SHA-256 et le téléchargement par chunks sont conservés.

```bash
PYTHONPATH=src:. python scripts/benchmark_cursor_pagination.py \
  --iterations 5000 --p95-threshold-ms 1 \
  --output build/reports/cursor-pagination.json --enforce
```

Voir `docs/operations/keyset-pagination-streaming.md`.

## Plan de données PostgreSQL haute performance — P20 / EPIC-2001

- PgBouncer `pool_mode=transaction` devant le primaire et le standby ;
- réplication physique PostgreSQL avec bootstrap idempotent ;
- lectures GET/HEAD routées uniquement vers un standby sain et sous le seuil de lag ;
- fallback vers le primaire configurable ;
- cohérence lecture-après-écriture par jeton signé à courte durée de vie ;
- statut opérationnel via `GET /api/v1/database/routing?tenant_id=default` ;
- métriques d’acquisition primaire, réplique et fallback par worker.

Voir `docs/operations/postgresql-read-routing.md`.

Le correctif `0.30.6` supprime également la substitution `psql` invalide utilisée par le contrôle final de `pg_hba_file_rules`. Le bootstrap peut désormais être relancé directement après l’échec observé en `0.30.2`, sans supprimer le volume primaire.

## Socle haute performance livré en P19

- API et BFF Web ASGI stateless, multiprocessus et réplicables par défaut en Pro/Entreprise ;
- concurrence, backlog, keep-alive et workers bornés et configurables ;
- pool PostgreSQL `psycopg_pool` par worker avec budget global bloquant ;
- client HTTP BFF asynchrone persistant, keep-alive, timeouts distincts et streaming ;
- restauration atomique de l’environnement après arrêt ou erreur de démarrage ;
- rollback explicite `--runtime legacy`, réservé aux incidents contrôlés ;
- gate CI p95/p99 du transport ASGI avec rapport JSON `capacity_certification=false` ;
- CDC 4.9.0 et roadmap 2.1.0 réalignés sur les exigences Pro/Entreprise.

```bash
PYTHONPATH=src:. pytest -q --no-cov \
  tests/integration/test_asgi_performance_runtime.py \
  tests/performance/test_high_performance_runtime_benchmark.py

PYTHONPATH=src:. python scripts/benchmark_high_performance_runtime.py \
  --requests 500 --concurrency 50 --warmups 25 \
  --output build/reports/high-performance-runtime.json --enforce
```

Le benchmark P19 détecte les régressions du transport applicatif ; il ne constitue pas une certification de capacité. La qualification complète sur PostgreSQL réel, PgBouncer, réplicas, endurance, spike, saturation et chaos est un gate P20 distinct.

## Séquencement professionnel P19 / P20

| Capacité | État 0.30.7 | Étape suivante |
|---|---|---|
| ASGI API/Web, backpressure, workers | Livrée | Observabilité fine P20 |
| Pool PostgreSQL borné | Livré | PgBouncer et routage lecture/écriture livrés en EPIC-2001 |
| BFF HTTP persistant et streaming | Livré | Tests de saturation inter-services P20 |
| Gate transport p95/p99 | Livré et bloquant | Certification de capacité/endurance P20 |
| Pagination par curseur | Livrée en EPIC-2002 | Certification PostgreSQL réelle P20 |
| Outbox et workers spécialisés | Périmètre fonctionnel EPIC-2003 livré | Qualification PostgreSQL/S3 réelle et politiques de rétention |
| Frontend modulaire/virtualisé | Livré en EPIC-2004 | Qualification Web Vitals réelle et observabilité EPIC-2005 |
| Stockage objet des payloads massifs | Livré : filesystem atomique et S3 compatible | Qualification S3 réelle et politiques de rétention P20 |

Voir `docs/architecture/high-performance-pro-enterprise.md` et `docs/runbooks/HIGH_PERFORMANCE_RUNTIME.md`.

## Historique v0.29.105

OpenInfra v0.29.105 corrige les lenteurs de chargement du portail web sans modifier le comportement métier livré en v0.29.104. Le Dashboard est rendu immédiatement, le bootstrap local est agrégé, la disponibilité backend est non bloquante et les catalogues volumineux sont chargés uniquement lorsque le formulaire sélectionné en a besoin.

## Performance du portail web

Les assets statiques utilisent désormais des URL versionnées, un cache immutable, des ETag et la compression gzip. Le JavaScript principal passe d’environ 260 Ko à 47 Ko transférés avec gzip ; l’ensemble CSS/JavaScript initial passe d’environ 620 Ko à moins de 125 Ko. Le Dashboard n’émet plus neuf requêtes de démarrage : il utilise uniquement `/bootstrap.json` et une sonde `/ready` asynchrone.

```bash
python -m pytest -q --no-cov \
  tests/integration/test_openinfra_web.py \
  tests/integration/test_frontend_runtime_startup.py

npm --prefix web test
```

Voir `docs/operations/web-loading-performance.md` pour les politiques de cache, les budgets, le chargement paresseux et les contrôles de diagnostic.

## Reprise après sinistre multisite

Le parcours **DCIM → Pilotage multisite** permet de définir les sites primaire et de secours, le mode de réplication, le RPO, le RTO et l’âge maximal d’une sauvegarde. Chaque exercice produit une preuve immuable `passed` ou `failed` selon les mesures et confirmations explicites fournies par l’opérateur.

```bash
openinfra multisite dr-plan-configure --help
openinfra multisite dr-plans --help
openinfra multisite dr-drill-execute --help
openinfra multisite dr-drills --help
```

Voir `docs/operations/multisite-disaster-recovery.md` pour les prérequis, la procédure de perte réelle d’un site, le failback, les critères RPO/RTO, l’audit et le rollback.

## Discovery régionale distribuée Enterprise

Le parcours est rangé sous **DCIM → Pilotage multisite**. Une route associe un triplet région/site/VRF à un collector `network-proxy` ou `datacenter-proxy` actif, disposant d’un endpoint HTTPS et de la portée correspondante. Lite et Pro restent strictement exclus de cette capacité distribuée.

```bash
openinfra multisite route-configure --help
openinfra multisite routes --help
openinfra multisite job-route --help
openinfra multisite route-disable --help
```

Voir `docs/operations/enterprise-regional-discovery-routing.md` pour l’enrôlement, les permissions, le routage, l’audit, la persistance et le rollback.

## Multisite Pro centralisé

Le parcours est rangé sous **DCIM → Pilotage multisite**. Il permet d’affecter les niveaux `viewer`, `operator` ou `admin` à une identité pour un site donné, de consulter le périmètre effectif et de générer des rapports immuables sur les bâtiments, étages, salles, racks et équipements accessibles.

```bash
openinfra multisite grant-upsert --help
openinfra multisite sites --help
openinfra multisite report-generate --help
openinfra multisite reports --help
```

Voir `docs/operations/pro-centralized-multisite.md` pour les permissions, les règles de portée, la persistance, l’audit et les limites d’édition.

## Assistant RAG gouverné

Le parcours est rangé sous **RSOT → Assistant gouverné / Index de connaissances / Imports-exports RAG**. Les documents sont versionnés, les synchronisations RSOT sont en lecture seule et les jobs d’import/export restent idempotents et relançables par lots.

```bash
openinfra rag document-upsert --help
openinfra rag sync-rsot --help
openinfra rag ask --help
openinfra rag job-create --help
openinfra rag job-run --help
```

Voir `docs/operations/rag-governed-assistant.md` pour le modèle de permissions, les citations, l’audit, la persistance et les limites de sécurité.

## SBOM, vulnérabilités et exposition

Les imports sont versionnés par application, release et environnement, bornés à 10 MiB, normalisés et protégés par empreinte SHA-256. La comparaison des releases reconnaît les mises à niveau d’un même package au lieu de les présenter comme une suppression suivie d’un ajout. Les évaluations de risque expliquent chaque facteur de contexte et peuvent être exportées en JSON ou CSV.

```bash
openinfra sbom import --help
openinfra sbom vulnerability-import --help
openinfra sbom exposure-upsert --help
openinfra sbom assess --help
openinfra sbom compare --help
```

Voir `docs/operations/sbom-vulnerabilities-exposure.md` pour les formats, les règles de confiance, les permissions, la persistance et les procédures d’exploitation.

## GreenOps, énergie et capacité

OpenInfra distingue toujours les mesures observées des estimations. Chaque donnée conserve sa source, sa période, son périmètre, sa méthode et son empreinte d’idempotence. Les rapports utilisent `Decimal`, publient les hypothèses PUE et les facteurs carbone appliqués, puis exposent l’énergie IT, l’énergie totale, les émissions estimées, les anomalies, les prévisions et les scores GreenOps par site, rack, PDU, actif ou application.

Les recommandations de consolidation ou de capacité sont strictement consultatives et portent `requires_human_approval=true`. Elles ne déplacent, n’arrêtent et ne modifient aucune ressource de production.

```bash
openinfra greenops measurement-ingest --tenant default \
  --admin-token "$OPENINFRA_TOKEN" \
  --idempotency-key greenops-par01-20260701 \
  --source-code dcim-meter --kind observed --scope rack \
  --scope-key rack-a01 --site-code par-01 \
  --period-start 2026-07-01T00:00:00+00:00 \
  --period-end 2026-07-02T00:00:00+00:00 --energy-kwh 125.4

openinfra greenops report-generate --tenant default \
  --admin-token "$OPENINFRA_TOKEN" --site-code par-01 \
  --period-start 2026-07-01 --period-end 2026-07-31 \
  --scope site
```

Voir `docs/operations/greenops-energy-capacity.md` pour les unités, les hypothèses, les permissions, les API/CLI, la persistance et les procédures de validation.

## FinOps et coûts

Le parcours **ITAM → FinOps & coûts** consolide les coûts cloud, SaaS, datacenter, énergie, licences, support et contrats. Les imports sont asynchrones, idempotents et contrôlés par empreinte SHA-256. Les allocations utilisent des règles prioritaires et conservent explicitement toute part non attribuable.

Les budgets, anomalies, prévisions, showbacks et chargebacks contrôlés sont disponibles en CLI, API HTTP, OpenAPI et dans les deux portails web. Tous les montants utilisent `Decimal`; une période clôturée est protégée par un digest reproductible. Le chargeback reste consultatif et ne produit aucune écriture comptable ou mutation ITSM.

```bash
openinfra finops import-submit --tenant default --admin-token "$OPENINFRA_TOKEN" \
  --idempotency-key finops-aws-2026-06-0001 --source aws-cur \
  --records-file costs.json

openinfra finops report-generate --tenant default --admin-token "$OPENINFRA_TOKEN" \
  --kind showback --period-start 2026-06-01 --period-end 2026-06-30 \
  --group-by application --currency EUR
```

Voir `docs/operations/finops-costs-showback.md` pour le modèle, les permissions, les règles de clôture, les contrats API/CLI et les procédures d’exploitation.

## Organisation de la navigation

- **IPAM** : adressage, **Conformité réseau** et **Flux réseau** ;
- **Sécurité** : contrôles de sécurité et **Certificats & PKI** ;
- **ITAM** : actifs, contrats, licences et **FinOps & coûts**.

Cette organisation ne modifie aucun endpoint ni identifiant d’opération ; elle évite la dispersion des fonctions transversales dans le premier niveau de navigation.

## Performance volumétrique du graphe RSOT

Le banc intégré génère des graphes synthétiques indexés jusqu’à 5 000 nœuds et mesure quatre scénarios : parcours à un niveau, filtrage par type de relation, analyse SPOF et pagination complète. Les cardinalités sont contrôlées à chaque exécution afin qu’une optimisation incorrecte ne puisse pas améliorer artificiellement les temps.

```bash
PYTHONPATH=src python -m openinfra.quality.dependency_graph_benchmark \
  --nodes 5000 \
  --spof-hubs 100 \
  --samples 3 \
  --warmups 1 \
  --output build/reports/dependency-graph-benchmark.json
```

Le processus retourne un code non nul si un p95 dépasse son seuil. Voir `docs/operations/dependency-graph.md` pour les objectifs, la méthodologie et l’interprétation du rapport.

## Formulaires et documentation API fiabilisés

Les deux portails partagent désormais exactement le même moteur de typage, de validation et de normalisation. Les adresses IP/CIDR, emails, téléphones, codes postaux, adresses MAC, noms DNS, URL, nombres, JSON et listes sont contrôlés avant émission, sans remplacer les validations métier du backend. Un validateur OpenAPI fondé sur un chargeur YAML à clés uniques bloque les doublons de mappings en CI et avant packaging.

## Visualisations d’impact et SPOF

L’analyse utilise les dominateurs enracinés : un objet est classé SPOF lorsque sa suppression rend inaccessibles d’autres objets depuis la racine, dans le sens de dépendance demandé. Les résultats sont bornés, filtrables, paginés et signalent explicitement toute projection tronquée afin de ne jamais présenter une analyse partielle comme exhaustive.

Le portail fournit une vue en couches accessible au clavier, un classement tabulaire des SPOF, un résultat JSON de repli et des exports JSON, CSV ou GraphML. Les mêmes capacités sont disponibles en CLI, API HTTP et OpenAPI avec la permission `rsot.read` et un audit systématique.

Voir `docs/operations/dependency-graph.md` pour les contrats, limites, commandes, exemples d’export et règles d’interprétation.

## Conformité réseau par golden configuration

Les baselines sont versionnées par équipement RSOT et plateforme. Les observations sont immuables, idempotentes et peuvent provenir de SSH, API, NETCONF, RESTCONF, gNMI, Discovery ou import. La comparaison JSON produit des dérives typées, respecte les chemins ignorés et critiques, rejette les secrets et reste strictement en lecture sur les équipements.

Les opérations sont disponibles en CLI, API HTTP, OpenAPI et portail web FR/EN. Voir `docs/operations/network-config-compliance.md` pour les contrats d’exploitation, les permissions, les limites documentaires et la procédure d’évaluation.

## Certificats et PKI

OpenInfra v0.29.90 réalise **P15 / EPIC-1503** avec un inventaire gouverné des certificats X.509 et de leurs endpoints TLS. Les chaînes PEM sont analysées et validées cryptographiquement, les empreintes SHA-256 servent d'identifiants immuables et la gouvernance (propriétaire, environnement, source, objet RSOT) reste révisable et auditée.

La capacité couvre l'import de chaînes leaf-first, le contrôle des liens émetteur/sujet et des signatures, l'inventaire des SAN DNS/IP/email/URI, la détection des certificats expirés ou proches de l'expiration, le contrôle du hostname présenté par les endpoints et les observations idempotentes. Aucun secret de clé privée n'est accepté ni stocké.

Les opérations sont disponibles en CLI, API HTTP, OpenAPI et portail web FR/EN. Voir `docs/operations/certificate-pki.md` pour les règles d'exploitation, les permissions, les seuils, les commandes et les limites de sécurité.

## Graphe de dépendances RSOT

Le moteur de graphe **P15 / EPIC-1501** reste une projection en lecture du RSOT. Il couvre l’exploration du voisinage, la recherche du chemin le plus court et l’analyse d’impact direct/indirect. **EPIC-1505** ajoute la détection des SPOF, les visualisations accessibles et les exports gouvernés sans modifier les objets ni les relations sources.

Les filtres par type de relation et le paramètre historique `as_of` sont disponibles en CLI, API HTTP, OpenAPI et portail web FR/EN. Toutes les consultations nécessitent la permission `rsot.read` et produisent un événement d’audit.

Voir `docs/operations/dependency-graph.md` pour les contrats d’exploitation et les commandes.

## Navigation web responsive

Le portail applique une navigation progressive fondée sur la largeur utile et la capacité réelle de la barre des onze composants :

- **écran large (`>= 1200 px`)** : sidebar persistante et scrollable sous le header fixe ;
- **tablette et portable compact (`768–1199,98 px`)** : sidebar masquée, icônes de composants alignées dans le header et ouverture d’un mégamenu multicolonne reprenant les mêmes contextes et opérations ;
- **mobile (`< 768 px`)** : remplacement de la barre de composants par une icône de menu unique ouvrant une navigation complète, scrollable et accessible au clavier.

La seconde barre conserve sa hauteur initiale tandis que la recherche reste compacte. Le sélecteur EN/FR, Swagger et ReDoc utilisent un gabarit légèrement réduit et restent alignés. Sur écran tactile, les cibles interactives passent automatiquement à 44 px afin de préserver l’accessibilité. Les menus se ferment par bouton, clic sur le backdrop ou touche `Échap`.

Voir `docs/operations/responsive-navigation.md` pour le contrat détaillé et `docs/ui/WEB_ACCESSIBILITY.md` pour la baseline d’accessibilité.

## Nomenclature DCIM des étages et portail multilingue

OpenInfra v0.29.86 remplace la nomenclature d’étage concaténant site et bâtiment par un code local, stable et lisible : `L-01` pour le premier sous-sol, `L00` pour le rez-de-chaussée et `L01` pour le premier étage. Les étages restent générés automatiquement depuis le type et les bornes du bâtiment ; aucune saisie libre de code ou de nom n’est demandée dans les nouveaux parcours.

La migration `0040_dcim_floor_nomenclature.sql` et la migration JSON intégrée réécrivent toutes les références DCIM dépendantes, préservent les noms personnalisés et conservent les anciens codes comme alias de lecture.

Le portail web supporte désormais intégralement le français et l’anglais. La langue est détectée depuis le navigateur ; toute langue non supportée utilise l’anglais. Un sélecteur EN/FR mémorise le choix opérateur. Le même moteur i18n est utilisé par le frontend React et par le portail statique livré dans le package Python.


## Résilience des workers et agents Discovery

OpenInfra v0.29.83 réalise **P14 / EPIC-1406** avec une file de jobs Discovery persistante, idempotente et récupérable après interruption d’un worker ou d’un agent. Un job validé est enregistré avant sa remise à un collector ; il ne peut donc plus être perdu à la suite d’un arrêt brutal entre l’autorisation et l’exécution.

Chaque réservation repose sur un bail expirant et un **jeton de fencing monotone**. Lorsqu’un worker disparaît, un autre peut reprendre le job après expiration du bail ; l’ancien worker ne peut plus terminer ou altérer le traitement avec son jeton périmé. Les échecs suivent une politique de tentatives bornées, puis basculent dans une **DLQ** (Dead-Letter Queue, file de quarantaine) administrable et auditée.

## Capacités livrées

- états persistants `queued`, `leased`, `retry-wait`, `completed` et `dead-letter` ;
- soumission idempotente par tenant et clé métier ;
- réservation atomique concurrente et reprise des baux expirés ;
- jetons de fencing empêchant le double traitement par un worker obsolète ;
- renouvellement de bail, terminaison idempotente et empreinte SHA-256 du résultat ;
- retries bornés, DLQ et rejeu explicite par un administrateur ;
- persistance JSON et PostgreSQL, partitionnée par tenant via la migration `0039_discovery_job_resilience.sql` ;
- CLI, API HTTP, OpenAPI et portail web alignés ;
- audit des soumissions, réservations, reprises, erreurs, mises en DLQ, rejeux et terminaisons ;
- tests domaine, services, concurrence, CLI, HTTP, portail, migration, sécurité et non-perte ;
- runbook `docs/runbooks/DISCOVERY_JOB_RESILIENCE.md`.

La réconciliation multisource v0.29.82 et les corrections DCIM/ITAM antérieures restent compatibles. Le CDC et la roadmap ne sont pas modifiés : EPIC-1406 était déjà défini et aucune nouvelle recommandation n’impacte l’existant.

## Opérations terrain DCIM

Le parcours **DCIM → Opérations terrain** guide les interventions physiques sans introduire de ticketing ITSM natif. Une fiche est générée depuis une cible réellement localisée, enrichie par les dépendances RSOT/Graphe, les flux déclarés et la redondance électrique A/B.

Interfaces principales :

```bash
openinfra dcim field-sheet-list --tenant default --admin-token "$OPENINFRA_TOKEN"
openinfra dcim field-sheet-generate --tenant default --admin-token "$OPENINFRA_TOKEN" \
  --target-type equipment --target-id PAR-SRV-001 \
  --title "Remplacement alimentation" \
  --purpose "Remplacer le bloc et contrôler le service" \
  --owner ops.owner --operator field.operator
```

Les preuves acceptées sont JPEG, PNG, WebP ou PDF, limitées à 2 Mio. Les paquets hors ligne sont limités au tenant et au site autorisés, expirent automatiquement et sont synchronisés uniquement si leur empreinte SHA-256 canonique correspond. Le runbook complet est disponible dans `docs/runbooks/FIELD_OPERATIONS.md`.


- [SBOM, vulnérabilités et exposition contextualisée](docs/operations/sbom-vulnerabilities-exposure.md)

## Imports massifs asynchrones CSV/XLSX

Les inventaires volumineux peuvent être déposés en flux binaire sur `/api/v1/imports/async-bulk-datasets`, puis traités par le worker spécialisé `imports` sans bloquer l’API interactive. La soumission est idempotente, les artefacts sont vérifiés par SHA-256, les lots et checkpoints sont persistants et la reprise est exposée par `resume_job_id`. Les deux portails fournissent la soumission et le suivi consolidé.

Les limites sont de 512 Mio pour CSV et 50 Mio pour XLSX, avec protections contre les archives chiffrées, le nombre excessif d’entrées et la décompression XML anormale. Le runbook opératoire complet est disponible dans [`docs/runbooks/ASYNC_BULK_IMPORTS.md`](docs/runbooks/ASYNC_BULK_IMPORTS.md).

