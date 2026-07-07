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
