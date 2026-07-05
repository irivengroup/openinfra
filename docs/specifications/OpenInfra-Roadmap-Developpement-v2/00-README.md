# OpenInfra — Roadmap de développement v2.0.0

Roadmap mise à jour pour alignement avec **OpenInfra CDC/SFG/STG v4.8.1 corrigé**.

## Contenu

- `01-roadmap-detaillee-openinfra-v2.md` : roadmap narrative complète.
- `02-roadmap-phases.csv` : 19 phases programme.
- `03-roadmap-releases.csv` : 9 releases macro.
- `04-roadmap-epics.csv` : 114 epics détaillés.
- `05-roadmap-jalons.csv` : jalons de pilotage.
- `06-roadmap-dependances.csv` : dépendances inter-phases.
- `07-roadmap-go-nogo.csv` : gates Go/No-Go.
- `08-roadmap-risques.csv` : risques et mitigations.
- `09-roadmap-tests-validation.csv` : tests et validations.
- `10-roadmap-streams.csv` : streams d’exécution.
- `11-plan-90-jours.md` : plan initial recalé sur v4.8.1.
- `12-plan-equipe-et-gouvernance.md` : gouvernance et équipe.
- `13-validation-roadmap.md` : preuve de validation documentaire.
- `14-alignement-cdc-v4.8.1.csv` : mapping CDC → roadmap.
- `15-plan-livraison-editions.csv` : plan Lite/Pro/Entreprise.
- `16-plan-installateurs.csv` : plan installateurs par scope.
- `17-plan-migration-pgdata-lvm.csv` : plan stockage, LVM, PGDATA.

## Décisions clés intégrées

- `openinfra.service` est le service backend canonique.
- `ancien service backend obsolète` est interdit.
- `openinfra-web.service` est le service frontend React + Bootstrap 5.
- `openinfra-agent.service` est le service collecteur discovery.
- Les installateurs sont dans `installers/`, hors `src/`.
- Chaque scope possède `config/install.ini`.
- PostgreSQL initialise ses données sous `/data/openinfra/`.
- `/opt/openinfra/data` pointe vers `/data/openinfra/`.
- Tailles PGDATA : Lite 2GB, Pro 100GB, Entreprise 1TB.
- Pro/Entreprise supportent LDAP/IPA, RBAC groupes, multisite et connecteurs ITSM externes.
