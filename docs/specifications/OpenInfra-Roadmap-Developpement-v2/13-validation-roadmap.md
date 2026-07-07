# Validation roadmap v2

## Synthèse

- Version roadmap : 2.0.0
- Référence CDC : OpenInfra CDC/SFG/STG v4.8.1 corrigé
- Phases : 19
- Releases : 9
- Epics : 114
- Gates Go/No-Go : 8
- Risques : 12
- Tests roadmap : 20
- Décisions CDC mappées : 21

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


### v0.29.34 — Discovery Enterprise proxy enrollment verification

- Ajout `TST-P11-DISCOVERY-PROXY-ENROLLMENT-VERIFY`.
- Alignement CDC `REQ-00773` et CLI Discovery `proxy-enroll-verify`.

### v0.29.33 — Discovery Enterprise proxy CLI enrollment

Ajout du test `TST-P11-DISCOVERY-PROXY-CLI-ENROLLMENT` pour verrouiller l’enrôlement CLI local/distant des proxies Discovery Enterprise auprès des backends, avec refus Lite/Pro.
- v0.29.33 : P08 ajoute la charte graphique premium Bootstrap 5 openinfra-web, sans changement de structure page, validée par TST-P08-WEB-PREMIUM-THEME.

### v0.29.34 — Dashboard court et contenu accueil isolé

- Ajout `TST-P08-WEB-DASHBOARD-SCOPING`.
- Alignement CDC `REQ-00774` et validation frontend/runtime : titre court `Dashboard`, métriques et statistiques d’accueil strictement limitées à la page overview.
