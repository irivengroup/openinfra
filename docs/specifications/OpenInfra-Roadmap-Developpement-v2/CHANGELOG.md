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
