# Validation roadmap v2

## Synthèse

- Version roadmap : 2.0.0
- Référence CDC : OpenInfra CDC/SFG/STG v4.8.1 corrigé
- Phases : 19
- Releases : 9
- Epics : 114
- Gates Go/No-Go : 8
- Risques : 12
- Tests roadmap : 21
- Décisions CDC mappées : 22

## Contrôles attendus

Le script `scripts/validate_roadmap.py` vérifie :

- présence des fichiers obligatoires ;
- minimum de phases, epics, gates et tests ;
- présence des services canoniques ;
- absence de `ancien service backend obsolète` ;
- présence de `installers/`, `config/install.ini`, `/data/openinfra/`, `/opt/openinfra/data -> /data/openinfra/` ;
- présence des tailles PGDATA Lite/Pro/Entreprise ;
- présence de LDAP/IPA, RBAC, multisite et connecteurs ITSM externes ;
- absence de marqueurs de brouillon.
- `TST-P09-ITRM-TAXONOMY-LABELS` verrouille l’affichage des libellés opérateur, la conservation des valeurs internes et l’absence des types obsolètes `physical-server`/`disk`.


## Validation v0.29.31

La roadmap v2 intègre P11/IPAM Enterprise++ dashboard parity via TST-P11-IPAM-DASHBOARD-PARITY et l’alignement CDC REQ-00769.


### v0.29.32 — IPAM topologie opérationnelle

Ajout du test `TST-P11-IPAM-TOPOLOGY` pour verrouiller la consolidation nodes/edges IPAM par API, CLI, dashboard et OpenAPI.


### v0.29.35 — Discovery Enterprise proxy enrollment verification

- Ajout `TST-P11-DISCOVERY-PROXY-ENROLLMENT-VERIFY`.
- Alignement CDC `REQ-00773` et CLI Discovery `proxy-enroll-verify`.

### v0.29.33 — Discovery Enterprise proxy CLI enrollment

Ajout du test `TST-P11-DISCOVERY-PROXY-CLI-ENROLLMENT` pour verrouiller l’enrôlement CLI local/distant des proxies Discovery Enterprise auprès des backends, avec refus Lite/Pro.
- v0.29.33 : P08 ajoute la charte graphique premium Bootstrap 5 openinfra-web, sans changement de structure page, validée par TST-P08-WEB-PREMIUM-THEME.

### v0.29.35 — Dashboard court et contenu accueil isolé

- Ajout `TST-P08-WEB-DASHBOARD-SCOPING`.
- Alignement CDC `REQ-00774` et validation frontend/runtime : titre court `Dashboard`, métriques et statistiques d’accueil strictement limitées à la page overview.

### v0.29.35 — Ombres de contenu openinfra-web allégées

Validation attendue : `scripts/validate_frontend.py` et `tests/integration/test_openinfra_web.py` doivent contrôler les variables `--openinfra-content-shadow` et `--openinfra-content-shadow-hover`, ainsi que leur utilisation par les blocs de contenu.

### v0.29.36 — Alertes openinfra-web contextuelles uniquement

Validation attendue : `scripts/validate_frontend.py` et `tests/integration/test_openinfra_web.py` doivent interdire `alert alert-info` et `role="note"` dans les assets runtime, tout en conservant les alertes `success` strictement conditionnées à une soumission de formulaire.


## Validation v0.29.37

La roadmap v2 intègre P08/openinfra-web double barre et recherche globale via `TST-P08-WEB-GLOBAL-SEARCH-HEADER` et l’alignement CDC `REQ-00777`. La validation contextual alerts couvre aussi le retrait des messages permanents hérités des anciennes alertes.

## Validation v0.29.38

La roadmap v2 intègre P08/openinfra-web recherche globale backend via `TST-P08-WEB-BACKEND-GLOBAL-SEARCH` et l’alignement CDC `REQ-00778`. La validation couvre le service applicatif, l’API HTTP, la CLI et le fallback frontend.

## Validation v0.29.46 — accessibilité openinfra-web

La roadmap v2 intègre `TST-P08-WEB-ACCESSIBLE-NAVIGATION` pour verrouiller l’accessibilité du portail web sans modifier les contrats backend. L’alignement CDC ajoute `REQ-00789` sur P08 / EPIC-0805 / release 0.29.46.


## Validation v0.29.47 — badge édition header principal

La roadmap v2 intègre `TST-P08-WEB-EDITION-BADGE-HEADER` pour verrouiller le déplacement de l’édition runtime à côté du logo OpenInfra, le retrait de l’indication visible du mode d’authentification et le style fuchsia dégradé sans changement de gabarit Bootstrap. L’alignement CDC ajoute `REQ-00790` sur P08 / EPIC-0805 / release 0.29.47.

## Validation v0.29.48 — badge édition fuchsia effectif

La roadmap v2 intègre `TST-P08-WEB-EDITION-BADGE-FUCHSIA` pour verrouiller le rendu fuchsia effectif du badge d’édition, sans classe `text-bg-primary`, sans composante bleue dans le gradient dédié, et sans changement du gabarit Bootstrap `badge`. L’alignement CDC ajoute `REQ-00791` sur P08 / EPIC-0805 / release 0.29.48.
