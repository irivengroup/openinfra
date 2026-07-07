- Ajout `TST-P08-WEB-FIXED-HEADER` pour valider le header fixe et le scroll du contenu sous-jacent.
## 0.29.40 - 2026-07-07

- Ajout TST-P08-WEB-ITRM-REFERENCE-ICON pour le pictogramme ITRM orienté référentiel/référence.

## 0.29.40 - 2026-07-07

- Ajout `TST-P08-WEB-API-DOCS-BACKEND-LINKS` pour verrouiller le branchement Swagger/ReDoc sur les routes documentaires réelles du backend API.
- Mise à jour du test roadmap TST-P08-WEB-RESTORED-PIE-PALETTE pour verrouiller la restauration action/vert des camemberts.
- Alignement CDC REQ-00780 sur P08 / EPIC-0801 / release 0.29.40.

## 0.29.38

- Ajout `TST-P08-WEB-BACKEND-GLOBAL-SEARCH` pour verrouiller la recherche globale backend groupée ITRM/IPAM/Discovery.
- Alignement CDC `REQ-00778` sur P08 / EPIC-0801 / 0.29.38.

## 0.29.37

- Ajout `TST-P08-WEB-GLOBAL-SEARCH-HEADER` pour verrouiller la double barre header, la recherche globale centrée, les résultats groupés par composant et les liens Swagger/ReDoc.
- Alignement CDC `REQ-00777` et extension de `TST-P08-WEB-CONTEXTUAL-ALERTS` au retrait des textes permanents hérités des alertes.

## 0.29.36

- Ajout `TST-P08-WEB-CONTEXTUAL-ALERTS` pour verrouiller l’absence d’alertes informatives affichées par défaut dans openinfra-web.
- Alignement CDC `REQ-00776` : alertes visibles réservées aux problèmes caractérisés et aux soumissions de formulaire.

## 0.29.35

- Ajout `TST-P08-WEB-DASHBOARD-SCOPING` pour verrouiller le titre court `Dashboard` et l’isolation du contenu d’accueil dans openinfra-web.
- Ajout de la vérification locale des fichiers d’enrôlement proxy Enterprise.
- Ajout du test roadmap `TST-P11-DISCOVERY-PROXY-ENROLLMENT-VERIFY`.
- Alignement CDC `REQ-00773`.

## 0.29.33

- Ajout du test roadmap `TST-P11-DISCOVERY-PROXY-CLI-ENROLLMENT`.
- Alignement CDC `REQ-00771` et contrats CLI/API Discovery pour l’enrôlement proxy Enterprise.

## 0.29.32

- Ajout de la topologie opérationnelle IPAM pour consolider VRF, préfixes, adresses, réservations, VLAN/VXLAN et ASN/BGP.
- Ajout du test roadmap `TST-P11-IPAM-TOPOLOGY`.
- Alignement CDC `REQ-00770` et contrats API/CLI/dashboard/OpenAPI.

## 0.29.31

- Ajout de la parité dashboard IPAM Enterprise++ pour les contrats `/api/v1/ipam/*`.
- Ajout du test roadmap `TST-P11-IPAM-DASHBOARD-PARITY`.
- Alignement CDC `REQ-00769` et découverte API IPAM.


## 0.29.30

- P10 étendu : jumeau numérique DCIM initial exposé par API, CLI et dashboard.
- Ajout de `TST-P10-DCIM-DIGITAL-TWIN` pour verrouiller la consolidation salle/rack/câblage/énergie/refroidissement et la non-duplication des règles métier.
- Alignement CDC `REQ-00768`.

## 0.29.29

- P10 étendu : dashboard DCIM énergie/refroidissement aligné sur les contrats API existants.
- P09 renforcé : sélecteurs ITRM label/value, valeurs internes normalisées conservées et retrait des types obsolètes `physical-server`/`disk`.

## v2 / OpenInfra 0.29.29

- P10 renforcé : opérations énergie/refroidissement DCIM exposées dans `openinfra-web` via les contrats backend existants power devices, circuits, cooling zones, power reservations et capacité rack.
- Ajout de `TST-P10-DCIM-ENERGY-COOLING-WEB` pour verrouiller les formulaires dashboard, les champs chaîne A/B, watts, derating, disjoncteur, températures et les routes API/OpenAPI réelles.
- Alignement CDC `REQ-00766`.

## v2 / OpenInfra 0.29.28

- P10 renforcé : opérations de câblage DCIM exposées dans `openinfra-web` via les contrats backend existants patch panels, ports et câbles.
- Ajout de `TST-P10-DCIM-CABLING-WEB` pour verrouiller les formulaires dashboard, les champs endpoints A/B, connecteur, média, statut, chemin câble et les routes API réelles.
- Alignement CDC `REQ-00765`.

## v2 / OpenInfra 0.29.27

- P10 renforcé : élévation rack DCIM exposée dans `openinfra-web` via le contrat existant `/api/v1/dcim/rack-elevation`.
- Ajout du choix de format `json/svg/html` aux formulaires web Plan de salle et Élévation rack.
- Ajout de `TST-P10-DCIM-RACK-ELEVATION-WEB` pour verrouiller la parité dashboard/API et l’absence de logique métier d’occupation U côté navigateur.
- Alignement CDC `REQ-00764`.

## v2 / OpenInfra 0.29.26

- P10 renforcé : localisation/relocalisation d’équipement DCIM exposée par API HTTP et dashboard web.
- Ajout de `TST-P10-DCIM-LOCATION-API` pour verrouiller le contrat `/api/v1/dcim/locations`, la parité web et les contraintes rack/U.
- Alignement CDC `REQ-00763`.

## v2 / OpenInfra 0.29.25

## 0.29.25

- P09 renforcé : taxonomie ITRM complète des catégories et types de ressources datacenter.
- Ajout du contrat `resource-taxonomy` en CLI/API et BFF web.
- Filtrage dynamique du type de ressource par catégorie dans les formulaires ITRM, avec mécanisme générique de listes dépendantes.
- Alignement CDC `REQ-00760` à `REQ-00762` et ajout de `TST-P09-ITRM-RESOURCE-TAXONOMY`.


- Ajout de `TST-P09-ITRM-RECONCILIATION` pour verrouiller la réconciliation gouvernée ITRM, le dry-run, l’apply contrôlé et l’audit objet.
- Alignement P09 avec `REQ-00759`.

## v2 / OpenInfra 0.29.23

- Ajout de `TST-P09-ITRM-AS-OF-AUDIT` pour verrouiller la restitution historique ITRM, les relations `as_of` et l’audit par objet.
- Alignement P09 avec `REQ-00758`.

## v2 / OpenInfra 0.29.22

- Ajout de `TST-P08-WEB-TITLEBAR-SPACING` pour verrouiller l’aération verticale responsive de la titlebar dashboard.
- Ajout de `TST-P08-WEB-BEARER-FALLBACK` pour verrouiller le fallback `OPENINFRA_BOOTSTRAP_TOKEN` et l’absence d’erreur brute `missing bearer token` côté web.
- Alignement P08 avec `REQ-00755`.

## v2 / OpenInfra 0.29.20

- Ajout de TST-P08-WEB-FORM-CONTRACTS et TST-P08-WEB-RESPONSIVE-PIES.
- Alignement P08 avec REQ-00752 à REQ-00754.

## v2 / OpenInfra 0.29.19

- Renommage transversal ITRM : CLI/API/RBAC/frontend primaires en `itrm`, alias `ri` et `sot` compatibles et dépréciés progressivement.
- Ajout de la validation des alertes dashboard contextuelles : suppression de l’alerte succès permanente `Backend prêt` sur l’accueil.

## v2 / OpenInfra 0.29.19

- Ajout `TST-P08-WEB-COMPONENT-STATS` : validation du dashboard d’accueil avec métriques et camemberts par composant.

# CHANGELOG — OpenInfra Roadmap

## v2.0.0

- Alignement sur OpenInfra CDC/SFG/STG v4.8.1 corrigé.
- Ajout des phases dédiées éditions, installateurs, systemd, LVM/PGDATA, LDAP/IPA, multisite et synchronisation quasi temps réel.
- Mise à jour des releases macro.
- Ajout de 114 epics.
- Ajout de la matrice `14-alignement-cdc-v4.8.1.csv`.
- Ajout du plan de livraison par édition.
- Ajout du plan installateurs par scope.
- Ajout du plan LVM/PGDATA par édition.
- Correction explicite : `openinfra.service` remplace tout modèle `ancien service backend obsolète`.
- Ajout des validations spécifiques à `install.ini`, PGDATA `/data/openinfra/` et tailles par édition.

## v1.0.0

- Roadmap initiale alignée CDC v4.0.0.

## 0.29.14

- P09 initialisée par ITRM Quality & Certification.
- Ajout du pilotage qualité/certification ITRM dans CLI, API et dashboard web.
- Ajout de la permission `itrm.quality.read` et des audits `itrm.quality.*`.

## 0.29.15

- P08 renforcé : `openinfra-web` adopte le thème Bootstrap 5 Dashboard et le header principal unique adapté aux domaines OpenInfra.
- Bootstrap 5 est servi localement dans le domaine présentation/rendering, sans CDN runtime.
- Ajout du test roadmap de parité UI Bootstrap/API-only.

## 0.29.16

- P08 web renforcé : formulaires métier typés sans champ générique Attributs.
- Navigation sidebar en accordéons avec transitions fade ; suppression du menu d'opérations interne.
- Trust `openinfra-web` ↔ backend server-side ; aucun token API demandé à l'opérateur.
- Cible `install.ini` `[web_database]` ajoutée pour les références DSN/credentials PostgreSQL du service web.
- v0.29.33 : P08 ajoute la charte graphique premium Bootstrap 5 openinfra-web, sans changement de structure page, validée par TST-P08-WEB-PREMIUM-THEME.
