# Changelog

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
