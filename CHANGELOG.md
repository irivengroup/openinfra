# Changelog

## 0.34.8 — 2026-07-21

### Ajouté

- recommandation DCIM de placement d’équipements fondée sur l’espace U contigu, la puissance rack, les circuits simples ou A/B redondants et la capacité thermique ;
- commande `openinfra dcim recommend-placement` et endpoint `GET /api/v1/dcim/placement-recommendations` ;
- opération de consultation dans les portails React et statique, sans modification de la charte graphique ;
- classement déterministe, compteurs de rejet explicites et audit `dcim.placement.recommended` ;
- runbook d’exploitation et contrat OpenAPI synchronisé avec le CDC 4.12.0.

### Qualité et compatibilité

- `TST-FUNC-0007` devient une preuve GATE-14 automatisée ; le registre contient désormais 20 preuves automatisées, 599 partielles et 48 externes ;
- aucun changement de schéma ni migration ; compatibilité ascendante des API, CLI, données JSON, PostgreSQL et Oracle ;
- Oracle reste réservé à l’édition Enterprise et le thème approuvé demeure inchangé.

## 0.34.7 — 2026-07-21

### Ajouté

- CDC 4.12.0 et roadmap 2.5.0 avec P25, REL-15, EPIC-2501 à EPIC-2504 et GATE-14.
- Registre exhaustif `contract-proof-registry-v4.12.csv` couvrant les 667 tests contractuels.
- Qualification `openinfra-gate14` avec six contrôles fail-closed et rapport JSON atomique.
- Résolution statique des sélecteurs pytest par analyse AST et classification explicite `automated`, `partial`, `external`.
- Workflow GitHub Actions GATE-14 et smoke du contrat installé depuis le wheel hors du dépôt.

### Corrigé

- Audit d’obsolescence rendu contextuel : exclusions limitées aux fichiers qui définissent ou testent les règles de détection.
- Références actives CDC/roadmap/version réalignées sur 4.12.0, 2.5.0 et 0.34.7 dans la CLI, les validateurs, la CI, les runbooks et le packaging.
- Aide du validateur d’installateur réalignée sur le CDC 4.12.0.

### Compatibilité

- Aucune route métier, commande CLI, permission RBAC, migration ou fonctionnalité existante supprimée.
- GATE-11, GATE-12 et GATE-13 restent exécutables et sont revalidés sur les référentiels actifs.
- PostgreSQL reste le backend par défaut ; Oracle 19c reste réservé à Enterprise.

## v0.34.6 — Canonicalisation RSOT définitive et qualification GATE-13

- retire définitivement les commandes CLI `itrm`, `ri` et `sot` au profit de la commande unique `rsot` ;
- retire les routes HTTP `/api/v1/itrm/*`, `/api/v1/ri/*` et `/api/v1/sot/*`, qui retournent désormais 404 ;
- supprime les rôles RBAC et identifiants de capacités historiques, avec `rsot:*` et `core_rsot` comme seuls contrats ;
- supprime les modules de compatibilité ITRM/RI et consolide la qualité métier dans `rsot_quality_services.py` ;
- ajoute le guide de migration opérateur, les tests de rejet explicites et la vérification du wheel installé ;
- ajoute CDC 4.11.0, roadmap 2.4.0, REL-14, P24 et GATE-13 avec six contrôles fail-closed ;
- conserve les fonctionnalités métier RSOT, les 59 migrations, la licence offline GATE-12 et la charte graphique approuvée.

## v0.34.5 — Licence runtime offline et qualification GATE-12

- ajoute une identité d’installation Ed25519 et une demande d’activation signée générée localement ;
- ajoute des entitlements offline signés, liés à l’entreprise, l’édition, l’installation, au quota d’hôtes et aux échéances ;
- applique une période de grâce de 30 jours, la détection du recul d’horloge et un comportement fail-closed en cas de corruption ;
- ajoute la migration `0059_runtime_offline_licensing.sql` aux catalogues PostgreSQL et Oracle ;
- fournit la persistance JSON/PostgreSQL/Oracle et sérialise le contrôle du quota dans la transaction métier ;
- expose statut, activation et renouvellement par CLI et HTTP, avec réponse 402 lorsque l’enforcement est actif ;
- intègre le bootstrap sécurisé dans les installateurs Pro/Enterprise et les notifications accessibles dans les deux portails ;
- ajoute GATE-12, son contrôleur de qualification, ses preuves et ses tests de non-régression ;
- conserve Lite sans licence commerciale, Oracle réservé à Enterprise et la charte graphique inchangée.

## v0.34.4 — Oracle Enterprise et état documentaire segmenté

- réserve le backend Oracle à l’édition Enterprise dans le domaine, les factories, la CLI, l’API, ASGI, systemd et les installateurs ;
- ajoute le symbole explicite `ORACLE_DATABASE_BACKEND` (valeur publique rétrocompatible `oracle_database`), refusé en Lite et Pro avant toute connexion ;
- ajoute la migration additive `0058_oracle_document_shards.sql` aux catalogues PostgreSQL et Oracle ;
- migre paresseusement et idempotemment l’ancien CLOB global vers des segments versionnés par collection métier ;
- limite chaque commit Oracle aux segments réellement modifiés et applique un contrôle optimiste indépendant par segment ;
- conserve la lecture et le rollback compatibles avec les installations Oracle antérieures à `0058` ;
- met à jour GATE-11, readiness, packaging, smoke, CDC v4.9.0 et roadmap v2.2 pour la règle Enterprise-only ;
- ne modifie ni les API métier, ni les permissions RBAC, ni la charte graphique.

## v0.34.3 — Qualification externe GATE-11 et preuves immuables

- ajoute l'exécutable `openinfra-gate11` pour qualifier les contrats REL-12, Oracle 19c réel, SAML 2.0 réel, l'idempotence Team Sync et le runtime systemd ;
- applique les migrations Oracle avec le compte applicatif puis exige le catalogue complet, `current=true` et une dérive vide ;
- valide une assertion SAML signée sans persister le jeton émis et conserve uniquement des empreintes et compteurs bornés ;
- exécute deux synchronisations Team Sync consécutives et impose zéro mutation lors de la seconde ;
- contrôle les unités systemd, leur activation, leur durcissement, leurs comptes, les permissions des secrets et les endpoints `/health` et `/ready` ;
- assemble cinq preuves JSON épinglées par SHA-256, liées au même candidat, commit et environnement, avec fraîcheur maximale de 24/168 heures ;
- produit une décision fail-closed `go`/`no-go` et refuse REL-12 si une preuve manque, dérive, expire ou ne correspond pas au candidat ;
- ajoute un workflow self-hosted `openinfra-gate11`, les tests unitaires/intégration, le packaging, le smoke wheel et le runbook d'exploitation ;
- conserve les 57 migrations PostgreSQL/Oracle, les interfaces publiques et le thème graphique sans modification.

## v0.34.2 — Parité complète des migrations Oracle 19c

- conversion déterministe des 57 migrations PostgreSQL vers un catalogue Oracle 19c de même ordre et de mêmes noms ;
- manifeste de parité avec empreintes SHA-256 des sources PostgreSQL et des artefacts Oracle ;
- validation bloquante des syntaxes résiduelles PostgreSQL, des LOB indexés, des clés d’index surdimensionnées et des dérives manuelles ;
- conservation des index uniques partiels par index fonctionnels Oracle et adaptation explicite des types, JSON, tableaux, partitions, DML et blocs PL/SQL ;
- exécuteur Oracle renforcé avec états `applying`, `applied`, `failed`, reprise idempotente contrôlée, détection de dérive et compatibilité de l’ancien historique `0001_document_state` ;
- disponibilité Oracle conditionnée à l’application complète du catalogue et à la cohérence des empreintes ;
- GATE-11 Oracle intégré à la CI, aux contrôles de packaging et au smoke test du wheel installé.

## v0.34.1 — Correctif de génération des partitions identité et Team Sync

- corrige la migration PostgreSQL `0057_federated_identity_team_sync.sql` qui produisait des identifiants de partition invalides tels que `identity_team_sync_sources_p 0` ;
- remplace le faux zéro-padding `%1$02s` de `format()` par `lpad()` et le format d’identifiant sûr `%I` ;
- crée déterministement les 96 partitions `p00` à `p31` pour les trois tables d’identité fédérée et Team Sync ;
- ajoute une validation générale refusant les largeurs `%0Ns` dangereuses dans les migrations PostgreSQL ;
- ajoute des tests de non-régression sur le rendu des noms, le catalogue et la politique de migration ;
- conserve PostgreSQL comme backend par défaut, Oracle optionnel, les interfaces SAML/LDAP/Team Sync et le déploiement systemd sans modification fonctionnelle ;
- aucune migration supplémentaire, aucun endpoint supprimé et aucune modification du thème.

## v0.34.0 — Identité avancée, Team Sync, Oracle et production systemd

- ajoute l’authentification SAML 2.0 avec validation cryptographique, configuration serveur de confiance et mapping groupes externes vers rôles OpenInfra ;
- enrichit LDAP/IPA avec LDAPS, StartTLS, CA, pagination, timeouts, referrals et groupes imbriqués bornés ;
- ajoute Team Sync idempotent pour LDAP, OAuth, Auth Proxy signé HMAC et Okta, avec audit et gestion contrôlée des identités orphelines ;
- ajoute Oracle Database comme backend optionnel Pro/Enterprise, PostgreSQL restant le backend par défaut ;
- ajoute les migrations Oracle et la migration PostgreSQL partitionnée `0057_federated_identity_team_sync.sql` ;
- rend l’installation et l’exploitation complètes sous systemd, sans dépendance Docker en production ;
- corrige les permissions du répertoire de jeton bootstrap pour permettre sa lecture par l’UID/GID runtime sans élargir les droits ;
- ajoute CLI, API, OpenAPI, unités/timer systemd, installateurs, tests, documentation et workflow GitHub Actions dédiés ;
- préserve la compatibilité ascendante et la charte graphique existante.

## v0.33.12 — Jeton bootstrap runtime interne

- retire `OPENINFRA_BOOTSTRAP_TOKEN` du contrat `.env` et purge automatiquement toute valeur héritée ;
- ajoute un volume Docker distinct `openinfra-runtime-secrets` et un service one-shot générant le jeton avec un CSPRNG ;
- impose un répertoire `0700`, un fichier `0400`, un propriétaire runtime dédié et le refus des liens symboliques ;
- conserve le jeton lors des redémarrages non destructifs et le régénère après `reset --volumes` ;
- fait lire le jeton par `auth-bootstrap`, `openinfra-web` et le smoke test via des montages en lecture seule ;
- ajoute `--token-file`, `--backend-bearer-token-file` et la consultation explicite `python scripts/docker_environment.py bootstrap-token` ;
- met à jour les contrats CDC existants REQ-00753/REQ-00756, la CI, les quality gates et les runbooks ;
- aucune migration PostgreSQL, aucun endpoint métier supprimé et aucune modification du thème.

## v0.33.11 — Configuration runtime interne Docker et Web

- retire `OPENINFRA_IMAGE_TAG`, `OPENINFRA_WEB_EDITION` et `OPENINFRA_WEB_PUBLIC_API_BASE_URL` du contrat `.env` ;
- résout le tag de l’image applicative depuis `VERSION` et l’applique via un override Compose temporaire supprimé après exécution ;
- purge automatiquement les trois anciennes clés des fichiers `.env` existants sans modifier les autres réglages ni secrets ;
- publie l’édition effective dans le document de découverte de l’API et la fait découvrir automatiquement par `openinfra-web` ;
- dérive l’URL API publique depuis le proxy BFF same-origin `/api`, avec maintien de l’option CLI de compatibilité ;
- ajoute les tests de migration `.env`, de génération d’override versionné, de validation de version, de découverte backend et de non-régression API/Web ;
- met à jour les quality gates, la documentation opérateur et l’exigence CDC existante REQ-00779 ;
- aucune migration PostgreSQL, aucun endpoint métier supprimé et aucune modification du thème.

## v0.33.10 — P21 / EPIC-2106 Qualification cloud-native et GATE-10

- livre le gate bloquant GATE-10 pour la promotion de REL-11 Kubernetes & Cloud-native ;
- agrège sept preuves immuables couvrant EPIC-2101 à EPIC-2106 ;
- vérifie SHA-256, fraîcheur, version, catalogue fermé et confinement des chemins ;
- ajoute une qualification runtime multi-cluster avec un snapshot réel de 50 000 ressources ;
- valide fingerprints déterministes, mapping physique et read model de capacité ;
- exécute des probes de rejet des secrets en clair, références inter-namespace et mappings physiques orphelins ;
- ajoute le workflow dédié, le runbook, la politique machine-readable, les tests et l’intégration packaging/smoke ;
- exclut désormais `node_modules`, `dist`, caches Vite, couvertures et logs du payload web des installateurs autonomes ;
- conserve la chaîne PostgreSQL à 56 migrations et le thème sans modification.

## v0.33.9 — Correctifs CI Discovery, support EPIC-1806 et UnitOfWork DCIM

- aligne le contrat racine HTTP sur les routes Kubernetes livrées en 0.33.8 afin de restaurer le job de réconciliation Discovery multisource ;
- installe explicitement le package OpenInfra dans le workflow Support Readiness avant l’exécution de `scripts/support_readiness.py` ;
- exécute toutes les lectures, validations et mutations des espaces de gestion DCIM Sites/Bâtiments/Étages/Salles/Zones/Racks dans un `UnitOfWork` actif ;
- protège le catalogue agrégé `/api/v1/dcim/topology-catalog` et les actions Détails/Éditer/Supprimer contre le contrat PostgreSQL strict ;
- ajoute un test de non-régression gardé couvrant le cycle de vie complet et refusant toute opération repository DCIM hors unité de travail ;
- inclut les racks retirés dans le catalogue lorsque `include_retired=true` ;
- aucune migration, aucun endpoint, aucune commande CLI et aucune modification du thème.

## v0.33.8 — Correctif UnitOfWork PostgreSQL pour Kubernetes

- corrige les lectures Kubernetes exécutées hors `UnitOfWork` avec le backend PostgreSQL ;
- couvre les topologies, expositions, corrélations sécurité, capacité, imports idempotents et états GitOps ;
- regroupe les lectures et écritures GitOps d’une évaluation dans une transaction unique, sans transaction imbriquée ;
- conserve le comportement JSON tout en alignant le service sur le contrat transactionnel strict PostgreSQL ;
- ajoute un test de non-régression qui échoue dès qu’un repository Kubernetes est appelé hors unité de travail ;
- aucune migration, aucun endpoint, aucune commande CLI et aucune modification du thème.

## v0.33.7 — Correctif frontend Kubernetes et régression CI Outbox

- ajoute le contexte frontend `Kubernetes et cloud-native` sous Discovery dans la sidebar et le mégamenu ;
- regroupe toutes les opérations Kubernetes existantes dans ce contexte au lieu du groupe générique `Autres` ;
- synchronise le contexte entre le frontend React et le runtime web packagé ;
- ajoute une localisation anglaise `Kubernetes and cloud-native` et un test de parité React/runtime ;
- corrige le test CI `Transactional outbox and specialized workers regression` qui figeait à tort `0054`/`0055` comme dernières migrations ;
- durcit les tests de politique de migration pour conserver l'ordre historique tout en acceptant la migration courante `0056_kubernetes_gitops_drift.sql` ;
- aucune modification du thème, des endpoints, du CLI ou du schéma PostgreSQL.

## v0.33.6 — P21 / EPIC-2105 Capacité cluster et namespace

- Ajout d’un read model Kubernetes de capacité cluster/namespace pour CPU, mémoire et stockage.
- Mesures typées et bornées dans les snapshots immuables : Nodes, Pods et Volumes uniquement.
- Agrégation demandes, limites, consommation, capacité, marges et alertes warning/critical.
- Tendances bornées à 96 snapshots et 1 000 000 de ressources cumulées maximum.
- Exports JSON/CSV, parité API/CLI/UI et cinq nouvelles opérations Discovery cloud-native.
- Compatibilité des fingerprints historiques préservée et aucune nouvelle migration PostgreSQL.
- CI, quality gate, packaging, smoke installé, documentation architecture/exploitation et validateur EPIC-2105 intégrés.

# Changelog

## v0.33.5 — P21 / EPIC-2104 Conformité GitOps et filtres multicritères de gestion

- ajout d’états GitOps attendus immuables liés à un commit Git complet, une source, un owner et un environnement ;
- politiques gouvernées pour labels, annotations, owner, environnement et détection des ressources inattendues ;
- comparaison déterministe expected-vs-observed avec dérives typées et fingerprint du rapport ;
- audit des évaluations et événement outbox `kubernetes.gitops.drift.detected` en cas de dérive ;
- six routes HTTP, six commandes CLI et six opérations Discovery pour l’import, la consultation et l’évaluation ;
- migration additive `0056_kubernetes_gitops_drift.sql`, partitionnée par tenant et indexée ;
- validateur EPIC-2104 intégré à la CI, au quality gate, au packaging et au smoke du wheel ;
- correction des pages `Gestion de …` : les critères multicritères contextuels et métier restent toujours visibles ;
- filtres organisés en sections `Contexte parent` et `Critères métier`, avec état explicite lorsqu’aucune valeur n’est disponible ;
- enrichissement des lignes DCIM aplaties pour rendre Étage, Ligne et Colonne réellement filtrables ;
- panneau de filtres aligné sur le thème OpenInfra existant sans ajout ni modification de couleur.

## v0.33.4 — Hiérarchie parentale normalisée des formulaires de gestion

- ordre canonique des contextes : Organisation → Filiale/Subdivision → Site → Bâtiment → Étage → Salle → Ligne/Colonne → Rack ;
- filtres parentaux prioritaires, affichés uniquement lorsqu'ils sont pertinents pour la ressource ;
- filtres en cascade : une modification de parent invalide automatiquement les descendants ;
- valeurs Ligne/Colonne multiples filtrables individuellement ;
- ordre des champs de rattachement normalisé dans les formulaires de gestion et les formulaires d'opération ;
- sélecteurs DCIM dépendants du contexte parent pour éviter les références incohérentes ;
- déplacement du code de gestion dans `web/src/management/` et du runtime correspondant dans `assets/management/`, avec façades de compatibilité ;
- aucune migration, aucun endpoint supprimé et aucune modification de la palette graphique.

## v0.33.3 — P21 / EPIC-2103 Corrélation sécurité cloud-native

- ajout d’un modèle sûr de références d’images OCI, certificats et secrets référencés dans les snapshots Kubernetes ;
- corrélation en lecture seule `workload/pod → image → SBOM → findings` avec comptage des vulnérabilités actives et critiques ;
- corrélation des empreintes de certificats avec l’inventaire PKI existant et signalement des certificats inconnus ou dégradés ;
- références de secrets strictement bornées et normalisées, avec masquage des fournisseurs externes et hachage SHA-256 de la référence originale ;
- refus de toute ingestion de contenu de Secret Kubernetes, mot de passe, token, clé privée ou URL de transport déguisée en référence OCI ;
- préservation bit pour bit des payloads canoniques et fingerprints des snapshots historiques lorsque les nouveaux champs sont absents ;
- rapport déterministe et borné à 2 000 documents SBOM et 10 000 findings, avec `correlation_truncated` uniquement lorsqu’un reliquat réel existe ;
- deux routes HTTP, deux commandes CLI et deux opérations Discovery supplémentaires ;
- validateur EPIC-2103 intégré à la CI, au quality gate, au packaging et au smoke du wheel installé ;
- aucune migration PostgreSQL supplémentaire et aucune modification du thème.

## v0.33.2 — Gestion CRUD unifiée et navigation opérateur consolidée

- Regroupement des familles CRUD homogènes sous une entrée unique `Gestion de …` dans la sidebar et le mégamenu.
- Huit espaces de gestion : sites, bâtiments, salles, châssis/racks, zones, organisations, filiales/subdivisions et partenaires.
- Page de gestion professionnelle avec recherche plein texte, filtres multicritères, tri, pagination bornée et option d’inclusion des objets retirés.
- Consultation des détails dans une boîte de dialogue accessible ; création et édition sur des vues dédiées ; suppression après confirmation et identification de l’opérateur.
- Retour automatique à la liste consolidée après création, modification ou suppression.
- Identifiants structurants rendus immuables en édition et sémantique de cycle de vie du backend conservée.
- Endpoints API, commandes CLI et catalogues CRUD historiques conservés intégralement pour compatibilité ascendante.
- Registre de gestion chargé paresseusement avec DCIM/ITAM afin de préserver les budgets de performance du shell initial.
- Parité structurelle entre le runtime web packagé et le portail React de référence.
- Aucune modification de la palette ou de la charte graphique ; seuls des styles structurels utilisant les tokens existants sont ajoutés.

## v0.33.1 — P21 / EPIC-2102 Expositions et dépendances réseau cloud-native

- ajout des ressources Kubernetes `load-balancer`, `dns-record` et `mesh-route` dans les snapshots immuables existants ;
- validation canonique des DNS, adresses IP, ports, protocoles, scopes, types de service et références RSOT ;
- rapport déterministe d’exposition corrélant endpoints Kubernetes, déclarations de flux et relations de dépendance RSOT ;
- identification explicite des expositions externes non gouvernées, sans mutation automatique de firewall, DNS, load balancer ou service mesh ;
- bornes de corrélation : 10 000 déclarations de flux, 10 000 relations RSOT et 2 048 objets de dépendance ;
- API, CLI, OpenAPI et portail Discovery alignés avec deux nouvelles opérations de lecture ;
- CI, quality gate, packaging et smoke du wheel étendus au contrat EPIC-2102 ;
- aucune migration PostgreSQL supplémentaire et aucune modification du thème.

## v0.33.0 — P21 / EPIC-2101 Kubernetes & Cloud-native topology

| Exigence / Epic | Implémentation | Vérification |
|---|---|---|
| REQ-00469 / EPIC-2101 | snapshots Kubernetes immuables et bornés à 50 000 ressources | tests domaine, service, HTTP, CLI et persistance |
| Graphe cloud-native | cluster, namespace, ownership, service routing et pod→node | empreinte déterministe et intégrité référentielle |
| Mapping physique | références externes VM→hyperviseur→serveur→rack→salle→site | tests de chaîne physique et couverture de mapping |
| Sécurité | permissions dédiées, audit et rejet des clés sensibles | RBAC, tests de secrets et security gate |
| Industrialisation | migration 0055, OpenAPI, portail Discovery, roadmap 2.2 et validateur P21 | CI, quality gate, packaging et smoke wheel |

- Nouvelle phase `P21`, release `REL-11`, jalon `M13` et gate `GATE-10` dans la roadmap 2.2.0.
- Le CDC reste en version 4.9.0 : `REQ-00469` et `REQ-00470` existaient déjà.
- Aucune modification de la charte graphique.

## 0.32.12 — 2026-07-14

- Matérialisation de `GATE-09 / REL-10` : certification finale de promotion Enterprise Scale-out après réalisation de tous les epics P20.
- Agrégation de sept preuves immuables : contrats P20, capacité Enterprise, chaos multisite, PRA/PCA, sécurité release, packaging signé et décision GA.
- Vérification bloquante de la version, de la fraîcheur, du verdict et de l'empreinte SHA-256 de chaque preuve.
- Ajout d'un manifeste canonique, d'un rapport `scaleout_promotion_certification`, d'un workflow protégé et d'un runbook dédié.
- Le workflow télécharge explicitement les artefacts de runs certifiants existants ; aucun moteur de benchmark, chaos ou PRA/PCA n'est dupliqué.
- Aucune migration PostgreSQL, aucune rupture API/CLI métier et aucune modification du thème.
- CDC et roadmap inchangés : `GATE-09` et `REL-10` étaient déjà définis dans la roadmap 2.1.

## 0.32.11 — 2026-07-14

- Réalisation de P17 / EPIC-1706 : certification de chaos multisite sur six classes de panne — réseau, site, agent, base de données, saturation de file et frontend.
- Runner de campagne sécurisé utilisant un harness externe à protocole fixe, sans commande shell arbitraire ni couplage à un fournisseur d’infrastructure.
- Mesure de la disponibilité, du taux d’erreur, du temps de récupération et de l’intégrité SHA-256 avant/après chaque panne.
- Récupération systématique après injection et arrêt immédiat de la campagne si le service ou le rollback n’est pas vérifié.
- Certification bloquante en cas de corruption, perte de travail acquitté, dépassement des objectifs SLO ou altération des six preuves.
- Workflow manuel protégé, profil machine-readable, runbook, validation CI, quality gate et vérification de packaging étendus.
- Aucune migration PostgreSQL, aucune rupture API/CLI métier et aucune modification du thème.
- CDC et roadmap inchangés : EPIC-1706 était déjà planifié et aucune nouvelle recommandation n’impacte l’existant.

## 0.32.10 — 2026-07-14

- Réalisation de P17 / EPIC-1705 : observabilité multisite par région et par site pour les éditions Pro et Enterprise.
- Agrégation du lag des agents Discovery à partir des heartbeats réellement persistés, avec déduplication des collecteurs utilisés par plusieurs VRF d’un même site.
- Export Prometheus borné des métriques `openinfra_multisite_agent_lag_seconds`, `openinfra_multisite_agent_health` et `openinfra_multisite_agent_collectors`, sans label de tenant ni d’utilisateur.
- Fédération HTTPS des endpoints `/metrics` des sites via file service discovery, répertoire monté en lecture seule et redirections désactivées.
- Ajout du dashboard Grafana `OpenInfra Multisite Operations` couvrant disponibilité API, p95, erreurs 5xx, agents, réplication PostgreSQL et files de jobs.
- Ajout de six alertes multisites, d’un profil machine-readable, d’un validateur de cibles et d’un runbook opérationnel.
- Gate CI et quality gate étendus avec tests de non-régression sur la cardinalité, les labels et les contrats d’observabilité.
- Aucune migration PostgreSQL, aucune rupture API/CLI métier et aucune modification du thème.
- CDC et roadmap inchangés : EPIC-1705 était déjà planifié et aucune nouvelle recommandation n’impacte l’existant.

## 0.32.9 — 2026-07-14

- Réalisation de P17 / EPIC-1704 : certification complète PRA/PCA pour les éditions Pro et Enterprise.
- Agrégation des plans et exercices DR existants avec preuves de sauvegarde/restauration, PITR et procédures opérationnelles.
- Mesure conservatrice du RPO, du RTO et de l’âge de sauvegarde à partir des pires observations réelles.
- Validation bloquante de la restauration, de l’intégrité, du chiffrement, de la cohérence PITR et de dix étapes de procédure.
- Hachage SHA-256 des cinq sources et digest déterministe du manifeste final pour détecter toute altération.
- Workflow manuel protégé `PRA/PCA Certification`, validateur dédié et intégration aux gates CI/quality gate.
- Aucune migration PostgreSQL, aucune rupture des contrats métier API/CLI et aucune modification du thème.
- CDC et roadmap inchangés : EPIC-1704 était déjà planifié et aucune nouvelle recommandation n’impacte l’existant.

## 0.32.8 — 2026-07-14

- Correctif de non-régression sur le survol/focus du composant racine actif de la sidebar.
- Le fond actif conserve exactement son rendu sélectionné ; la couche de hover transparente ne s’applique plus aux racines `.active`.
- Seuls l’icône, le texte et le chevron passent au bleu turquoise via l’héritage de `currentColor`.
- Ajout d’un test de cascade CSS empêchant qu’un hover générique tardif puisse de nouveau écraser la surface active.
- Aucune autre modification de la palette, des transparences, du responsive, des API, de la CLI ou du schéma PostgreSQL.

## 0.32.7 — 2026-07-14

- Raffinement visuel de la sidebar et de la hiérarchie contextuelle sans modification de la palette approuvée.
- Menus racine de la sidebar, contextes et titres de page en bleu nuit très foncé basé sur le token sémantique existant `--openinfra-ink`.
- Couche de profondeur transparente sur sidebar, barre contextuelle, cartes, formulaires, recherche, mégamenu, tableaux et surfaces secondaires.
- Transparence appliquée aux surfaces et non au contenu afin de préserver la lisibilité et les contrastes.
- Fallback sans `backdrop-filter`, mode contraste renforcé et comportement responsive/accessibilité conservés.
- Tests de non-régression verrouillant la palette, la synchronisation React/runtime et l'absence d'opacité appliquée au contenu.
- Aucune migration PostgreSQL, aucune rupture API/CLI et aucune nouvelle dépendance runtime.

## 0.32.6 — 2026-07-14

- Implémentation P18 / EPIC-1801 : benchmarks Enterprise Scale reproductibles sur topologie représentative.
- Profil de certification v2 exigeant six familles : API, IPAM, imports, Discovery, base de données et graphes.
- Runner HTTP asynchrone en lecture seule avec HTTPS obligatoire, keep-alive, concurrence et tâches en vol bornées.
- Mesure p95/p99, taux d’erreur, débit, octets et distribution des statuts pour chaque famille.
- Intégration des preuves benchmark et de leurs SHA-256 dans la certification de capacité GATE-07.
- Workflow Enterprise protégé et documentation d’exploitation alignés.
- Aucune migration PostgreSQL, aucune rupture API/CLI métier et aucune modification de la charte graphique.

## 0.32.5 — 2026-07-13

- Implémentation P18 / EPIC-1806 : support, maintenance, politique de patch et cycle de vie.
- Modèle machine-readable par édition avec sévérités S1-S4, objectifs de réponse, mise à jour et restauration.
- Cycle de vie active, maintenance, sécurité uniquement et fin de vie, avec règles de migration et rollback.
- Matrice d’escalade L1/L2/L3/incident command et preuve support-readiness signée compatible GATE-07.
- Workflow GitHub Actions, documentation GA, runbook et tests bloquants.
- Aucun changement de schéma PostgreSQL ni de charte graphique.

## 0.32.4 — 2026-07-13

- Correctif Docker : copie de toutes les ressources documentaires exigées par Hatchling avant `pip install`.
- Le build runtime partage explicitement la même définition locale entre migrate, auth-bootstrap, API, web et smoke afin d’éviter toute tentative de pull du tag local.
- Ajout de tests de non-régression du contexte de build Docker et des services Compose runtime.
- Aucun changement métier, migration ou thème.

## 0.32.3 — 2026-07-12

- Implémentation P18 / EPIC-1805 : gate Go/No-Go GA signé et reproductible.
- Politique fermée couvrant critères techniques, capacité, sécurité, packaging, documentation, exploitation, support et business.
- Approbations Ed25519 par rôle et politique de confiance externe.
- Validation des empreintes, dates de validité, risques et signature de décision.
- Rapport NO-GO motivé tant que les preuves GATE-07 ne sont pas complètes.
- Workflow GitHub Actions de promotion GA et runbook opérationnel.
- Aucun changement de schéma PostgreSQL ni de charte graphique.

# Changelog

## 0.32.2 — 2026-07-12

### Ajouté

- documentation GA P18 / EPIC-1804 structurée par rôle ;
- guides installation, administration, utilisateur, API, exploitation, PRA/PCA, mise à niveau et diagnostic ;
- manifeste `docs/ga/documentation-manifest.json` ;
- validateur `validate_ga_documentation.py` et rapport JSON ;
- workflow GitHub Actions dédié et gate bloquant intégré à la CI.

### Compatibilité

- aucune migration PostgreSQL ;
- aucun changement d'API ou de CLI ;
- aucune modification CSS ou du thème approuvé.

## 0.32.1 — 2026-07-12

- Implémentation de P18 / EPIC-1803 : certification reproductible du packaging de release.
- Double build byte-for-byte du wheel et du sdist avec `SOURCE_DATE_EPOCH`.
- SBOM SPDX 2.3 déterministe, manifeste SHA-256 et signature détachée Ed25519.
- Validation des six installateurs et preuve de rollback transactionnel.
- Installation du wheel en environnement vierge, `pip check` et smoke installé.
- Workflow de release bloquant et documentation d'exploitation.
- Aucun changement de thème ni de schéma PostgreSQL.

## 0.32.0 - 2026-07-12

### P18 / EPIC-1802 — audit sécurité de release

- gate de certification de sécurité agrégeant huit contrôles obligatoires et refusant toute preuve incomplète ;
- SAST Bandit, audit Python/Node, tests RBAC/authentification, scanner de secrets et scans Trivy dépôt/image ;
- sonde DAST HTTP réelle vérifiant santé, readiness, métriques, refus anonyme et en-têtes de sécurité web ;
- preuves atomiques nettoyées, empreintes SHA-256 par contrôle et digest global déterministe ;
- workflow bloquant sur tags avec image finale, runtime Compose réel, collecte de logs et rétention des preuves ;
- génération et mise à niveau idempotente du `.env`, incluant les secrets obligatoires PostgreSQL, cohérence de lecture et Grafana ;
- documentation d'architecture, runbook, tests unitaires/intégration et quality gate dédiés.

### Compatibility

- aucune migration PostgreSQL ;
- aucun changement des contrats métier API/CLI ;
- aucune modification CSS ou du thème ;
- le mode hors ligne reste explicitement non certifiant.

## 0.31.4 - 2026-07-12

### Fixed

- alignement déterministe de l'utilisateur non-root Docker sur l'UID/GID `10001:10001` du tmpfs Prometheus ;
- vérification d'écriture et nettoyage contrôlé de `PROMETHEUS_MULTIPROC_DIR` avant le fork Uvicorn ;
- diagnostic explicite en cas de montage non inscriptible, au lieu d'un `PermissionError` tardif dans un worker ;
- tests et gate d'observabilité empêchant toute divergence future entre l'image et Compose.

### Compatibility

- aucune migration PostgreSQL ;
- aucun changement des contrats API/CLI métier ;
- aucune modification CSS ou du thème.

## 0.31.3 - 2026-07-12

### Added

- instrumentation Prometheus et OpenTelemetry pour API, BFF, workers, outbox, files asynchrones et PostgreSQL ;
- endpoints `/metrics` API/web et propagation W3C `traceparent` ;
- pile d'observabilité Compose avec Prometheus, Tempo, OpenTelemetry Collector et Grafana provisionné ;
- règles d'alerte SLO p95/p99, erreurs, saturation, DLQ, pool et réplication ;
- profil et moteur stricts de certification Enterprise : paliers, endurance, spike, saturation et chaos ;
- workflow manuel de certification sur runner Enterprise protégé ;
- runbook, architecture, tests de sécurité, d'intégration et de non-régression.

### Changed

- version applicative et cache-busters alignés sur 0.31.3 ;
- contrats OpenAPI enrichis avec `/metrics` ;
- dépendances runtime séparées pour Prometheus et OpenTelemetry.

### Compatibility

- aucune migration PostgreSQL ;
- aucune modification CSS ou du thème ;
- OpenTelemetry désactivable et pile d'observabilité isolée derrière le profil Compose `observability`.

## 0.31.2 - 2026-07-12

### P20 / EPIC-2004 — frontend modulaire et virtualisé

- découpage du portail packagé et du portail React en huit chunks métier chargés à la demande ;
- Dashboard limité au manifeste statistique, sans catalogue métier ni taxonomie RSOT au démarrage ;
- index de recherche globale différé ;
- cache de requêtes mémoire avec TTL, déduplication, annulation, invalidation ciblée et protection contre les réponses obsolètes ;
- virtualisation des groupes de résultats dépassant 40 éléments ;
- observation LCP, INP et tâches longues avec budgets explicites ;
- gates Vite et Python pour les chunks, la taille du shell, la parité des 274 opérations et l’absence de stockage navigateur sensible ;
- documentation d’architecture, runbook, tests frontend/backend et packaging alignés ;
- aucune migration, aucun changement de contrat public et aucune modification du thème ou des feuilles de style.

## 0.31.1 - 2026-07-12

### P20 / EPIC-2003 — workers imports, graphes et RAG

- ajout des spécialisations durables `imports`, `graph` et `rag` sur le socle de jobs/outbox 0.31.0 ;
- worker imports pour les imports unitaires et massifs depuis un artefact externe immuable ;
- worker graphe pour parcours, impact, chemin, analyse SPOF et export hors base ;
- worker RAG pour synchronisation RSOT, import documentaire externalisé et export JSON/CSV des réponses ;
- dépôt d’artefacts d’entrée via CLI et HTTP avec contrôle d’accès, type MIME, SHA-256 et isolation tenant ;
- rôles dédiés de moindre privilège `async:import-worker`, `async:graph-worker` et `async:rag-worker` ;
- parité CLI, HTTP, OpenAPI, documentation, tests, smoke installé et packaging ;
- aucune migration supplémentaire et aucune modification du thème ou des feuilles de style.


## 0.31.0 - 2026-07-12

### P20 / EPIC-2003 — socle outbox et premier worker spécialisé

- file durable générique pour traitements asynchrones, idempotence par tenant et retries bornés ;
- leases avec jetons de fencing, reprise après expiration, DLQ et rejeu administré ;
- création atomique job/outbox/audit dans les unités de travail JSON et PostgreSQL ;
- migration additive `0054_async_outbox_workers.sql` et claims concurrents `FOR UPDATE SKIP LOCKED` ;
- worker pilote `reporting.async-queue-health` et dispatcher d’outbox idempotent ;
- artefacts content-addressed hors base sur filesystem atomique ou stockage S3 compatible signé AWS SigV4 ;
- permissions, rôles, CLI, API REST, OpenAPI, métriques, runbook, tests et gate CI dédiés ;
- aucune modification du thème ou des feuilles de style.


## 0.30.9 - 2026-07-12

### Corrigé

- Restauration du bleu IONOS `#003D8F` pour les composants racine inactifs de la sidebar.
- Restauration du même bleu nuit pour les titres contextuels des pages métier.
- Conservation stricte du correctif 0.30.8 : seul le texte, l’icône et le chevron du composant racine actif deviennent turquoise au survol ou au focus ; sa surface reste inchangée.
- Ajout de contrats Python et Node.js bloquant toute nouvelle régression vers une teinte noire.
- Aucune modification du CDC, de la roadmap, des migrations, des dépendances ou des contrats publics.

## 0.30.8 - 2026-07-12

### Corrigé

- Le survol ou le focus d’un composant racine déjà actif dans la sidebar conserve désormais son fond actif et applique uniquement au texte et à l’icône le turquoise clair du thème. Le composant ne devient plus sombre ou illisible.
- La parité React/runtime statique et un contrat de non-régression interdisent toute modification du fond, de la bordure ou de l’ombre pour cet état interactif ciblé.

## 0.30.7 - 2026-07-12

### P20 / EPIC-2002 — pagination par curseur et streaming des données

- remplacement de la pagination PostgreSQL `OFFSET` par des parcours keyset indexables sur les collections non bornées ;
- curseurs opaques Base64URL signés HMAC-SHA256, liés au tenant, aux filtres, au contexte et à l’ordre de tri ;
- compatibilité ascendante temporaire avec les curseurs numériques historiques, immédiatement migrés vers un curseur opaque ;
- migration additive `0053_keyset_pagination_indexes.sql` avec index composés tenant/tri ;
- génération progressive des exports JSON, CSV et XLSX avec tampon mémoire borné et débordement disque ;
- maintien des signatures d’artefacts, du téléchargement par chunks et des formats existants ;
- gate CI et benchmark p95 page initiale/page profonde, sans revendication de certification PostgreSQL réelle.

## 0.30.6 - 2026-07-11

### Correctif UI — navigation du header

- suppression de la carte blanche utilisée par le composant actif dans le header ;
- remplacement par un fond bleu/cyan translucide, un repère inférieur discret et une ombre réduite ;
- atténuation de l’icône active par opacité sans perdre le contraste non textuel WCAG ;
- maintien d’un contraste AA pour le libellé actif sur toute la plage du dégradé bleu du header ;
- parité stricte entre le portail React et le runtime statique packagé ;
- ajout de tests bloquants interdisant la réintroduction d’un fond blanc opaque pour l’état actif.

## 0.30.5 - 2026-07-11

### Sécurité des dépendances

- relèvement de `cryptography` à `>=48.0.1,<50.0` afin d'exclure les wheels embarquant une version OpenSSL vulnérable ;
- relèvement de `urllib3` à `>=2.7.0,<3.0` pour exclure les vulnérabilités de décompression et de redirection corrigées en 2.7.0 ;
- maintien d'un gate `pip-audit --strict` bloquant sur toutes les dépendances runtime, PostgreSQL, LDAP et développement ;
- mise à niveau préalable de `pip` dans la CI et l'image d'exécution.

### Expérience visuelle

- ajout d'un système de design commun aux portails React et packagé ;
- surfaces lumineuses, hiérarchie bleu nuit, profondeurs contenues, tableaux et formulaires affinés ;
- navigation, cartes, boutons, champs, alertes et résultats harmonisés ;
- conservation des modes contraste renforcé et réduction des mouvements ;
- aucune dépendance frontend ni ressource média supplémentaire.

### Documentation API

- regroupement des 331 opérations OpenAPI par **composant**, puis par **contexte métier** ;
- groupes hiérarchiques ReDoc via `x-tagGroups` ;
- groupes Swagger `Composant · Contexte`, triés selon l'ordre métier et repliés par défaut ;
- maintien des flux et de la conformité réseau sous IPAM, et des certificats sous Sécurité ;
- tests bloquants empêchant tout endpoint non classifié ou tout tag dupliqué.

## 0.30.4 - 2026-07-11

### Correctifs UI

- restauration d’une hiérarchie visuelle explicitement bleu nuit pour les textes principaux et secondaires ;
- remplacement des couleurs secondaires calculées par transparence, dont le rendu pouvait dériver vers le gris foncé selon le fond et le navigateur ;
- ajout de quatre jetons sémantiques de texte : principal, secondaire, atténué et subtil ;
- alignement des utilitaires Bootstrap `text-secondary`, `text-muted` et `text-body-secondary` sur la palette OpenInfra ;
- correction de la variable CSS non définie utilisée par la notice des champs obligatoires ;
- parité stricte des thèmes React et runtime packagé ;
- tests automatisés de teinte bleue, de contraste WCAG AA et d’absence de réintroduction des gris Bootstrap.

## 0.30.3 - 2026-07-11

### Correctifs

- correction de la validation post-rechargement de `pg_hba.conf` : suppression du placeholder `psql` non interprété dans une commande `-c` ;
- utilisation d’un littéral SQL sûr après validation stricte du nom du rôle de réplication ;
- ajout d’un test de non-régression qui échoue si `:'replication_user'` est transmis littéralement à PostgreSQL ;
- conservation de l’idempotence du bootstrap et compatibilité avec les volumes primaire/standby déjà créés.

## 0.30.2 - 2026-07-11

### Correctifs

- correction du bootstrap de réplication PostgreSQL : ajout idempotent d’une règle `pg_hba.conf` dédiée à la réplication physique ;
- rechargement et validation explicites de `pg_hba.conf` avant le démarrage du standby ;
- réseau Compose déterministe et configurable via `OPENINFRA_DOCKER_SUBNET` ;
- prise en charge des volumes primaires déjà initialisés ;
- reconstruction sûre d’un volume standby partiellement initialisé ;
- tests de non-régression sur l’idempotence, la sécurité et la topologie Compose.

## 0.30.1 - 2026-07-11

- Réalisation prioritaire de P20 / EPIC-2001 : PgBouncer en mode transaction, standby PostgreSQL chaud et routage lecture/écriture borné pour Pro et Entreprise.
- Ajout de deux pools PgBouncer indépendants devant le primaire et la réplique, avec authentification SCRAM-SHA-256, budgets de connexions et requêtes préparées côté client désactivées pour la compatibilité transactionnelle.
- Création idempotente du rôle de réplication, y compris sur les volumes PostgreSQL déjà initialisés, puis bootstrap du standby par `pg_basebackup -R`.
- Routage des requêtes GET/HEAD vers la réplique uniquement si elle est en recovery et sous le seuil de lag ; fallback automatique et observable vers le primaire.
- Garantie read-after-write via jeton HMAC-SHA256 Base64URL à durée de vie courte, relayé par le BFF dans un cookie HttpOnly/SameSite=Strict.
- Portée de lecture unique par requête pour conserver un snapshot cohérent et une seule connexion PostgreSQL, sans assouplir l’obligation d’unité de travail des repositories.
- Ajout de `/api/v1/database/routing`, des compteurs par worker, de tests de lag/panne/fallback/strict mode, du contrat Compose et d’un gate CI dédié.

## 0.30.0 - 2026-07-11

- Réalisation prioritaire de P19 / EPIC-1901 à EPIC-1905 pour le socle haute performance Pro et Entreprise.
- API et BFF Web exécutés par défaut sur ASGI avec politiques multiprocessus, concurrence, backlog et keep-alive bornés.
- Ajout d’un pool PostgreSQL `psycopg_pool` par worker avec délais d’acquisition, idle/lifetime et budget global de connexions refusant les configurations dangereuses.
- Remplacement du proxy Web bloquant par un client HTTP asynchrone persistant avec pools keep-alive, timeouts distincts et streaming sans buffering intégral.
- Ajout d’une portée d’environnement atomique restaurant exactement les variables du processus après arrêt, interruption ou échec de démarrage.
- Conservation du runtime historique via `--runtime legacy` uniquement pour rollback contrôlé, sans rupture des contrats métier, CLI, REST, OpenAPI, RBAC ou migrations.
- Ajout d’un gate CI p95/p99 déterministe du transport ASGI, d’un rapport JSON versionnable et de l’indicateur explicite `capacity_certification=false`.
- Réalignement du CDC en version 4.9.0 et de la roadmap en version 2.1.0 avec 12 exigences, phases P19/P20, ADR, risques, tests et gates Go/No-Go cohérents.
- Séparation explicite entre les capacités livrées en P19 et les évolutions P20 non encore revendiquées : PgBouncer, réplicas de lecture, pagination curseur, outbox/workers, frontend modulaire et certification de charge/endurance.

## 0.29.105 - 2026-07-11

- Correction prioritaire des lenteurs de chargement du portail web packagé.
- Compression gzip déterministe des ressources texte avec réduction du transfert initial d’environ 82 %.
- Ajout d’ETag, de réponses `304 Not Modified` et d’un cache immutable pour les URL d’assets versionnées.
- Remplacement de quatre requêtes locales de démarrage par un endpoint agrégé `/bootstrap.json`.
- Découplage de la disponibilité backend afin qu’un backend lent ou indisponible ne bloque plus l’initialisation de l’interface.
- Chargement paresseux et dédupliqué des catalogues pays, organisations, filiales, partenaires et topologie DCIM uniquement lors de l’ouverture des formulaires concernés.
- Ajout de tests de budgets de transfert, de cache, de compression, de revalidation conditionnelle et de non-régression du démarrage.

## 0.29.104 - 2026-07-11

- Réalisation de P17 / EPIC-1703 avec plans de reprise primaire/secours pour les éditions Pro et Enterprise.
- Ajout des objectifs RPO/RTO, du mode de réplication et du seuil de fraîcheur des sauvegardes.
- Ajout d’exercices immuables de perte du site primaire avec sept contrôles explicites et motifs d’échec stables.
- Garantie de sécurité : aucune promotion PostgreSQL, opération de fencing, restauration ou mutation DNS/VIP automatique.
- Ajout de sept routes REST/OpenAPI, sept commandes CLI, de la parité Web FR/EN et des persistances JSON/PostgreSQL.
- Ajout de la migration additive `0052_multisite_disaster_recovery.sql`, du runbook d’exploitation et du gate CI dédié.

## 0.29.103 - 2026-07-11

- Réalisation de P17 / EPIC-1702 avec un routage Discovery distribué réservé à l’édition Enterprise.
- Ajout de routes régionales déterministes par région, site et VRF vers des collectors `network-proxy` ou `datacenter-proxy` enrôlés.
- Validation systématique du site DCIM, du statut du collector, de son endpoint HTTPS et de sa portée autorisée avant configuration et avant chaque soumission.
- Réutilisation du moteur Discovery existant pour l’idempotence, les retries, les baux, le fencing et la DLQ, sans scan direct ni écriture RSOT par le module multisite.
- Ajout de 5 routes REST, de 5 commandes CLI, de la parité UI/OpenAPI, des persistances JSON/PostgreSQL et de la migration `0051_enterprise_regional_discovery_routing.sql`.
- Ajout d’un gate CI dédié, de tests domaine/service/CLI/HTTP/PostgreSQL/migration/Web et d’un runbook d’exploitation/rollback.
- Garantie explicite : les éditions Lite et Pro ne peuvent pas utiliser le routage régional distribué.

## 0.29.102 - 2026-07-11

- Réalisation de P17 / EPIC-1701 avec un pilotage multisite centralisé pour les éditions Pro et Enterprise.
- Ajout d’un RBAC par site combinant permissions globales et affectations locales `viewer`, `operator` ou `admin`.
- Ajout de rapports immuables consolidant bâtiments, étages, salles, racks/châssis et équipements depuis le DCIM.
- Ajout de 7 routes REST, de la parité CLI/UI/OpenAPI, des persistances JSON/PostgreSQL et de la migration `0050_pro_centralized_multisite.sql`.
- Ajout de rôles dédiés, de l’audit des affectations/révocations/rapports et d’un gate CI couvrant toutes les couches.
- Garantie explicite : aucun agent régional, proxy collector ou mécanisme distribué Enterprise n’est activé en Pro.

## 0.29.101 - 2026-07-11

- Réalisation de P16 / EPIC-1606 avec un assistant RAG local, déterministe et gouverné sous RSOT.
- Ajout de documents versionnés, fragments indexés, réponses citées, synchronisation RSOT en lecture seule et jobs d’import/export relançables.
- Filtrage strict tenant/permissions avant recherche, audit sans question en clair et absence garantie d’action destructive.
- Ajout de 13 routes REST, de la parité CLI/UI/OpenAPI, des adaptateurs JSON/PostgreSQL et de la migration `0049_rag_governed_assistant.sql`.
- Ajout d’un gate CI dédié couvrant domaine, service, CLI, HTTP, PostgreSQL, migration et interfaces.

## 0.29.100 - 2026-07-11

- Correction de l’écran blanc du portail web packagé causé par cinq références SBOM à `FIELD_SETS.cursor` alors que le champ partagé n’était pas déclaré.
- Ajout du champ de pagination partagé `cursor` et validation exhaustive des références `FIELD_SETS` dans le gate frontend.
- Validation du catalogue des composants, opérations et champs au démarrage afin de produire une erreur explicite plutôt qu’une exception silencieuse.
- Premier rendu du Dashboard avant les appels réseau pour éviter un écran vide lorsque le backend est lent ou indisponible.
- Ajout d’un écran d’erreur fatal accessible lorsque le montage ou l’initialisation JavaScript échoue.
- Durcissement du calcul des métriques de champs obligatoires contre une entrée de catalogue invalide.
- Remplacement du cache `immutable` des assets non versionnés par une revalidation systématique afin qu’un navigateur ne conserve pas un bundle défectueux après mise à niveau.

## 0.29.99 - 2026-07-11

- Réalisation de P16 / EPIC-1605 avec un module SBOM regroupé sous **Sécurité**, sans nouveau composant de premier niveau.
- Import strict des formats CycloneDX et SPDX JSON, versionnement par application/release/environnement et idempotence par empreinte SHA-256.
- Import des vulnérabilités CVE, contextes d’exposition et calcul de risque contextualisé avec raisons explicites et contrôles compensatoires.
- Comparaison de releases par identité logique PURL : une mise à niveau est classée comme changement de version et non comme suppression/ajout.
- Ajout de 14 routes HTTP/OpenAPI, des commandes `openinfra sbom`, des exports JSON/CSV et de la parité React/runtime packagé.
- Ajout de la persistance JSON/PostgreSQL, de l’outbox transactionnel et de la migration `0048_sbom_vulnerabilities_exposure.sql`.
- Ajout des tests domaine, cas limites, service, CLI, HTTP, PostgreSQL, migration, portail, OpenAPI, packaging et du gate CI SBOM.
- Garantie explicite : aucun scan actif, aucune exécution distante et aucune remédiation automatique.

## 0.29.98 - 2026-07-11

- Réalisation de P16 / EPIC-1604 avec un module GreenOps regroupé sous **DCIM**, sans nouveau composant de premier niveau.
- Ajout de sources de mesure, facteurs carbone versionnés, politiques par site et mesures énergétiques observées ou estimées.
- Calcul reproductible de l’énergie IT, de l’énergie totale, du PUE, des émissions CO₂e, des coûts énergétiques et des hypothèses appliquées.
- Ajout des anomalies, prévisions de capacité, scores GreenOps et recommandations consultatives exigeant une validation humaine.
- Idempotence globale par tenant et empreinte SHA-256, y compris entre partitions PostgreSQL temporelles.
- Ajout de 16 routes HTTP/OpenAPI, des commandes `openinfra greenops`, de la persistance JSON/PostgreSQL et de la migration `0047_greenops_energy_capacity.sql`.
- Ajout de la parité React/runtime packagé, des exports JSON/CSV, de la documentation d’exploitation et du gate CI GreenOps.
- Garantie explicite : aucune mesure estimée n’est présentée comme observée et aucune recommandation ne modifie la production.

## 0.29.97 - 2026-07-11

- Ajout de P16 / EPIC-1603 : imports de coûts idempotents, règles d’allocation, budgets, anomalies, prévisions, showback, chargeback contrôlé et clôture reproductible.
- Ajout de 18 routes FinOps, de la parité CLI, des interfaces React/runtime et de la migration PostgreSQL `0046_finops_costs_showback.sql`.
- Refus récursif des métadonnées de facturation contenant des clés sensibles et utilisation exclusive de montants `Decimal`.
- Reclassement de Flux réseau et Conformité réseau sous IPAM, et de Certificats & PKI sous Sécurité, sans rupture des routes ni permissions.
- Ajout des tests domaine, service, HTTP, CLI, migration, OpenAPI, UI, sécurité, packaging et couverture des cas limites.

## v0.29.96 — Simulation de changement et migration

- Ajout des scénarios immuables de changement/migration et de dix changements typés.
- Ajout de l’analyse multidimensionnelle RSOT, flux, IPAM, énergie, refroidissement, coûts et services métier.
- Ajout des scores de préparation, groupes d’affinité, dépendances bloquantes et vagues consultatives.
- Ajout de la comparaison déterministe de rapports avant/après.
- Ajout des dépôts JSON/PostgreSQL, de l’outbox transactionnel et de la migration `0045_simulation_migration_planning.sql`.
- Ajout de neuf routes HTTP/OpenAPI, des commandes `openinfra simulation` et du parcours **RSOT → Simulation & migrations**.
- Garantie explicite : aucune mutation de production, aucun ordre d’exécution et aucun changement ITSM natif.

## v0.29.95 — Field Operations mobile/offline

- Ajout des fiches d’intervention terrain issues du DCIM pour les équipements, racks, câbles, équipements électriques et certificats localisés.
- Ajout des chemins physiques complets, QR codes, codes-barres, checklists avant/après et avertissements RSOT/Graphe/flux/alimentation.
- Ajout des preuves immuables photo/PDF avec contrôle MIME, taille, base64 et empreinte SHA-256.
- Ajout des verrous logiques idempotents avec expiration, audit et événements outbox transactionnels.
- Ajout des paquets de synchronisation hors ligne bornés, expirables, limités au tenant/site autorisé et validés par empreinte canonique.
- Ajout de la persistance JSON et PostgreSQL partitionnée, de la migration `0044`, des API REST, de la CLI `openinfra dcim field-*` et du parcours web sous DCIM → Opérations terrain.
- Ajout des tests domaine, application, HTTP, CLI, migration, frontend, sécurité et non-régression.

## v0.29.94 — Tests volumétriques du graphe RSOT

- Réalisation de P15 / EPIC-1506 avec un banc de performance déterministe sans dépendance externe.
- Génération de topologies indexées jusqu’à 5 000 nœuds pour isoler les coûts du parcours, des filtres, de l’analyse SPOF et de la pagination.
- Mesures p50/p95 répétées après warm-up, contrôle de déterminisme des cardinalités et seuils de latence bloquants.
- Rapport JSON versionné, écrit atomiquement, incluant environnement, configuration, échantillons, seuils, observations et verdict global.
- Gate GitHub Actions exécuté sur Python 3.13 avec résumé Markdown dans le job CI.
- Tests unitaires, intégration et performance couvrant configuration invalide, échec de seuil, pagination sans doublon et topologie maximale.
- Aucun changement d’API, de CLI métier, de schéma PostgreSQL ou d’interface web.
- CDC et roadmap inchangés : EPIC-1506 était déjà planifié et aucune nouvelle recommandation n’impacte l’existant.

## v0.29.93 — Fiabilisation OpenAPI et formulaires typés

- Suppression de cinq déclarations de routes DCIM dupliquées qui rendaient `openapi.yaml` illisible par ReDoc et Swagger UI.
- Ajout d’un validateur YAML/OpenAPI refusant toute clé de mapping dupliquée, exécuté en tests et dans GitHub Actions.
- Calendriers natifs thémés pour tous les champs date et date-heure, avec normalisation applicative ISO-8601.
- Validation anticipée partagée des saisies IP/CIDR, email, téléphone, code postal, MAC, hostname, URL, nombres, JSON, CSV et texte.
- Parité stricte du moteur de formulaire entre React et le runtime statique packagé.
- Regroupement des opérations Graphe dans les sous-menus RSOT, sans changement des routes API ni de la CLI.
- Focus des champs de formulaire limité au changement de couleur de bordure, sans grossissement, translation ni halo.
- Tests frontend, OpenAPI, packaging et contrats d’accessibilité complétés.

## v0.29.92 — Visualisations d’impact et détection des SPOF

- Implémentation de P15 / EPIC-1505 sur la projection bornée du graphe RSOT existant, sans nouvelle source de vérité ni migration.
- Détection déterministe des points uniques de défaillance par dominateurs enracinés, avec directions entrante, sortante ou bidirectionnelle.
- Classement par nombre d’objets rendus inaccessibles, impact direct, ratio d’impact, agrégats et échantillon borné.
- Filtres de candidats par type, catégorie, type de ressource et statut, pagination par curseur opaque lié à la requête.
- Signalement explicite des analyses non exhaustives lorsque la projection atteint `max_nodes`.
- Exports gouvernés JSON, CSV normalisé et GraphML, avec annotations SPOF optionnelles et téléchargement atomique en CLI/web.
- Visualisation web en couches, navigable au clavier, responsive, compatible lecteurs d’écran, couleurs forcées et réduction des mouvements.
- CLI, API HTTP, OpenAPI, portail FR/EN, audit, tests de sécurité, tests d’intégration et smoke du wheel alignés.
- CDC et roadmap inchangés : EPIC-1505 était déjà planifié et aucune nouvelle recommandation n’impacte l’existant.

## v0.29.91 — Conformité réseau golden configuration

- Baselines versionnées par équipement RSOT et plateforme réseau.
- Observations immuables et idempotentes depuis SSH, API, NETCONF, RESTCONF, gNMI, Discovery ou import.
- Comparaison JSON structurée avec chemins ignorés/critiques, dérives typées et audit.
- Rejet des secrets et des clés privées dans les documents de configuration.
- CLI, API/OpenAPI et portail web FR/EN.
- Persistance JSON/PostgreSQL et migration `0043_network_config_compliance.sql`.
- Aucune remédiation automatique des équipements.

## v0.29.90 — Inventaire des certificats et PKI

- Implémentation de P15 / EPIC-1503 avec inventaire X.509 tenant-aware et gouverné.
- Import de chaînes PEM leaf-first, validation cryptographique des signatures et contrôle de la continuité émetteur/sujet.
- Empreinte SHA-256 comme identité immuable ; refus des collisions présentant un matériau différent.
- Inventaire des sujets, émetteurs, CN, SAN DNS/IP/email/URI, périodes de validité, algorithmes, tailles de clé et autorités de certification.
- Gouvernance révisable : propriétaire, environnement, source, rattachement RSOT, cycle de vie et version.
- Observations d'endpoints TLS immuables et idempotentes avec contrôle hostname/SAN.
- Évaluation déterministe des états `retired`, `not-yet-valid`, `expired`, `critical`, `warning` et `healthy`.
- Permissions `certificate.read`/`certificate.write`, rôles dédiés, isolation tenant et audit.
- Persistance JSON/PostgreSQL, migration `0042_certificate_pki_inventory.sql` partitionnée et indexée.
- Sept commandes CLI, sept routes HTTP/OpenAPI et sept opérations web FR/EN.
- Gate GitHub Actions, tests domaine/services/interfaces/PostgreSQL/web et vérification du wheel mis à jour.
- CDC et roadmap inchangés : EPIC-1503 était déjà planifié et aucune nouvelle recommandation n'impacte l'existant.

## v0.29.89 — Matrice de flux déclarés et observés

- Implémentation de P15 / EPIC-1502 comme comparaison gouvernée entre flux déclarés et observations réseau immuables.
- Déclarations tenant-aware avec sélecteurs `any`, objet RSOT ou CIDR, protocoles, plages de ports, décision allow/deny, priorité, propriétaire, justification et validité.
- Ingestion idempotente d'observations NetFlow, sFlow, IPFIX, pare-feu, application, import ou manuel, protégée par empreinte SHA-256.
- Classification déterministe en `compliant`, `denied-observed`, `undeclared-observed` et `declared-unobserved`.
- Fenêtre maximale de 31 jours, pagination, limites de charge et détection des curseurs non progressifs.
- Permissions dédiées `flow.read` et `flow.write`, rôles `flow:reader` et `flow:operator`, isolation tenant et audit.
- Persistance JSON et PostgreSQL partitionnée par tenant via `0041_flow_matrix.sql`.
- CLI, API HTTP, OpenAPI et portail web FR/EN alignés.
- Gate CI dédié et smoke du wheel vérifiant les six routes, les assets web et les 41 migrations.
- CDC et roadmap inchangés : EPIC-1502 était déjà planifié et aucune nouvelle recommandation ne modifie l'existant.

## v0.29.88 — Accessibilité transversale et raffinement visuel du header

- Application d’une baseline WCAG 2.2 AA à toutes les pages React et au runtime web packagé.
- Ajout de liens d’évitement vers le contenu, la navigation des composants et la recherche globale.
- Landmarks sémantiques, annonces `aria-live`, navigation clavier par flèches/Home/End/Échap et restauration du focus.
- Formulaires accessibles : libellés explicites, champs obligatoires annoncés, `aria-invalid`, validation native et résultats annoncés.
- Prise en charge de `prefers-contrast: more`, couleurs forcées, focus à double contraste et compensation du header fixe.
- Garantie qu’aucune information n’est portée uniquement par le son ; tout futur média devra fournir sous-titres/transcription et alternative visuelle.
- États actif/hover du header adoucis par transparence, rayons réduits et transitions bounce/fade courtes.
- Suppression automatique des animations avec `prefers-reduced-motion`.
- Réduction légère du sélecteur FR/EN et des boutons Swagger/ReDoc, avec maintien de cibles tactiles de 44 px sur pointeur grossier.
- Ajout d’un lint JSX `eslint-plugin-jsx-a11y`, de tests Node/Python dédiés et d’un gate CI accessibilité.
- Réalignement de `REQ-00789`, `REQ-00825`, `TST-WEB-090`, `TST-WEB-125` et `EPIC-0805` sans nouvelle exigence redondante.

## v0.29.87 — Ajustements UX du header et mégamenu au survol

- Restauration du padding vertical initial de la seconde barre du header (`0,5 rem`) sans modifier la hauteur compacte de la recherche (`2 rem`).
- Recherche globale centrée par rapport à la page et dimensionnée à 50 % de la largeur disponible sur tous les modes responsive.
- Retour à une disposition compacte des composants, alignés à droite sur écran large, sans étirement artificiel entre les icônes.
- Nouveaux états visuels actif, survol et focus à contraste renforcé, cohérents avec le thème bleu/cyan OpenInfra.
- Ouverture du mégamenu au survol et au focus clavier en mode 768–1199,98 px ; le clic reste un fallback tactile et accessible.
- Parité React/runtime packagé et mise à jour des gates frontend, Node.js et Python.
- Mise à niveau de Vite vers 8.1.4 et du plugin React associé ; audit npm ramené à zéro vulnérabilité.
- Réalignement de `REQ-00811`, `REQ-00825`, `TST-WEB-124`, `TST-WEB-125` et `EPIC-0805` sans création d'une exigence redondante.

## v0.29.86 — Graphe de dépendances RSOT, navigation responsive et analyse d’impact

- Refonte responsive de la navigation web en trois modes : sidebar desktop, mégamenu multicolonne tablette/portable compact et menu unique mobile.
- Breakpoints fonctionnels : sidebar à partir de 1200 px, mégamenu de 768 à 1199,98 px, navigation compacte sous 768 px.
- Les icônes de composants ouvrent le mégamenu sans sélectionner silencieusement une opération ; le Dashboard reste une navigation directe.
- Le menu compact reprend tous les composants, contextes et opérations de la sidebar, avec fermeture par backdrop, bouton dédié et touche Échap.
- Réduction de 25 % de la hauteur visuelle de la seconde barre du header et adaptation proportionnelle de la recherche globale.
- Alignement strict du sélecteur EN/FR avec Swagger et ReDoc ; agrandissement automatique des cibles sur écrans tactiles.
- Réduction de l’ombre du header tout en conservant une hiérarchie supérieure aux cartes et blocs de contenu.
- Parité React/runtime packagé et tests de régression responsive, accessibilité clavier et build frontend.

- Implémentation de EPIC-1501 comme projection tenant-aware du RSOT, sans duplication de la source de vérité.
- Parcours en largeur borné, déterministe et résistant aux cycles, avec directions entrante, sortante ou bidirectionnelle.
- Filtres de types de relation, restitution historique `as_of`, limites de profondeur et de volume, et indicateur de troncature.
- Recherche du chemin de dépendance le plus court entre deux objets RSOT.
- Analyse d’impact direct/indirect avec agrégats par type d’objet et catégorie de ressource.
- Exposition complète par service, CLI, API HTTP, OpenAPI et portail web FR/EN.
- Audit des consultations de graphe et tests de non-régression métier, CLI, HTTP, UI et sécurité.
- Aucune migration PostgreSQL : le moteur exploite les tables RSOT et relations historisées existantes.
- EPIC-1501 reste aligné sur la roadmap existante ; le CDC et la roadmap sont toutefois mis à jour pour formaliser la nouvelle navigation responsive et le header compact (`REQ-00811`, `REQ-00825`, `EPIC-0805`).

## v0.29.85 — Nomenclature DCIM des étages et portail FR/EN

- Abandon de la concaténation site/bâtiment dans les codes et noms d’étage.
- Nouvelle nomenclature locale au bâtiment : `L-01`, `L00`, `L01`, `L02`…
- Migration JSON automatique et migration PostgreSQL `0040_dcim_floor_nomenclature.sql` couvrant étages, salles, zones, racks et équipements.
- Compatibilité de lecture avec les alias historiques `<site>_<bâtiment>_ETG<n>`, `F<n>` et `ETG<n>`.
- Préservation des noms d’étage personnalisés et refus des collisions de niveaux.
- Internationalisation complète de l’interface web en français et anglais.
- Détection via `navigator.languages`, puis `navigator.language`, avec fallback anglais.
- Sélecteur EN/FR persistant et moteur i18n identique pour React et le portail packagé.
- Localisation des composants, opérations, formulaires, états, pays, continents, taxonomie et étages sans modification des valeurs API.
- Priorité garantie au runtime web packagé afin qu’un `web/dist` React incomplet ne masque jamais les assets contractuels Python.
- Mise à jour du CDC et de la roadmap, cette recommandation modifiant l’existant.

## v0.29.84 — Correctif CI DCIM et runtime GitHub Actions Node.js 24

- Correction du smoke `DCIM physical model` : réutilisation du code d’étage canonique produit par `define-room`.
- Correction préventive du smoke `DCIM cabling and energy foundation`, affecté par le même écart.
- Ajout de tests de non-régression sur le chaînage `define-room` → `locate`/`define-rack`.
- Migration de `actions/checkout` vers `v6`, `actions/setup-python` vers `v6` et `actions/setup-node` vers `v6`.
- Durcissement du gate de sécurité : refus explicite des actions JavaScript encore liées au runtime Node.js 20.
- Aucune migration PostgreSQL ; aucune modification du CDC ni de la roadmap.

## v0.29.83 — Résilience des workers et agents Discovery

- Ajout d’une file de jobs Discovery persistante avec états explicites et isolation tenant.
- Soumission idempotente, réservation atomique et récupération des baux expirés après crash worker.
- Ajout d’un jeton de fencing monotone empêchant les écritures d’un ancien propriétaire de bail.
- Renouvellement de bail, terminaison idempotente et contrôle de l’empreinte SHA-256 du résultat.
- Retries bornés, mise en DLQ et rejeu administré avec journal d’audit.
- Persistance JSON et PostgreSQL ; `FOR UPDATE SKIP LOCKED` pour les workers concurrents.
- Ajout de la migration additive `0039_discovery_job_resilience.sql`, partitionnée et indexée.
- Exposition complète par service, CLI, API HTTP, OpenAPI et portail web.
- Ajout des tests de crash/reprise, concurrence, non-perte, DLQ, CLI/API, migration et sécurité.
- Ajout d’un gate GitHub Actions dédié à EPIC-1406.
- CDC et roadmap inchangés, l’incrément étant déjà prévu sans nouvelle recommandation impactante.

## v0.29.82 — Réconciliation Discovery multisource gouvernée

- Ajout des preuves Discovery immuables, identifiées par UUID et empreinte SHA-256 canonique.
- Validation stricte des payloads JSON, limite de 1 MiB et refus des clés susceptibles de contenir des secrets.
- Calcul déterministe des scores confiance/fraîcheur/complétude et du score global pondéré.
- Détection des conflits par chemin d’attribut, conservation de toutes les variantes et idempotence par signature.
- Résolution complète et justifiée des conflits sans écriture automatique dans le RSOT.
- Persistance JSON et PostgreSQL partitionnée par tenant, indexée et paginée.
- Ajout de la migration PostgreSQL additive `0038_discovery_multisource_reconciliation.sql`.
- Exposition service, CLI, API HTTP, OpenAPI et portail web.
- Ajout des tests domaine, service, CLI, API, web, migration, sécurité et non-régression RSOT.
- Alignement de la version frontend sur 0.29.82 et ajout d’un job CI Node.js dédié au lint, aux tests et au build Vite.

## v0.29.81 — Profils Discovery virtualisation, Kubernetes et cloud

- Ajout du référentiel Discovery des profils VMware, Proxmox, Hyper-V, Kubernetes, AWS, Azure, GCP et OpenStack.
- Secrets référencés exclusivement en `vault://` et masqués dans les sorties publiques.
- Endpoints HTTPS obligatoires pour les connecteurs on-premises et OpenStack ; cloud public compatible sans endpoint local.
- Limites de concurrence et rate limit bornées.
- CRUD service, CLI, API HTTP et portail web.
- Ajout de la migration PostgreSQL additive `0037_discovery_integration_profiles.sql`.
- Aucun scan réseau ni écriture RSOT n’est exécuté par ce référentiel.

## v0.29.80 — Adresse complète sites DCIM, organisations et partenaires ITAM

- Correction effective de l’exposition DCIM site : les formulaires, CLI et API exigent rue, code postal, email et téléphone à la création.
- Conservation du pays comme valeur ISO alpha-2 avec affichage du nom seul dans les sélecteurs web et libellé `Pays`.
- Complément de l’adresse des organisations ITAM avec code postal et téléphone obligatoires.
- Clarification : les codes/noms d’étage générés sont calculés par OpenInfra à partir des attributs réels du modèle, sans imposer de noms de variables internes.
- Complément de l’adresse des partenaires ITAM avec code postal obligatoire.
- Ajout de la migration PostgreSQL additive `0036_site_organization_addresses.sql`.
- Ajout des tests service, CLI/API/Web, migration et documentation.
