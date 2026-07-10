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
