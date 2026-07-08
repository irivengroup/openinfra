## v0.29.51 — P12 ITAM licences logicielles et contrats

L’incrément v0.29.51 réalise `EPIC-1205` pour les licences logicielles : entitlements, référence contrat, quantités achetées/assignées, conformité à date, API, CLI, portail web, OpenAPI, migration PostgreSQL partitionnée et tests de non-régression via `TST-P12-ITAM-SOFTWARE-LICENSES`.

- v0.29.50 : P08/EPIC-0804 expose l’administration éditions et quotas dans le portail web et l’API, avec discovery/OpenAPI, RBAC `security:admin` et parité CLI/CI.
- v0.29.49 : P08/EPIC-0805 ajuste le badge édition avec un dégradé fuchsia très foncé tirant vers prune chaud/bruné sans devenir marron, tout en conservant le gabarit Bootstrap.
- v0.29.48 : P08/EPIC-0805 corrige le badge édition pour garantir un dégradé fuchsia effectif, sans héritage bleu `text-bg-primary`, tout en conservant le gabarit Bootstrap.
- v0.29.48 : P08/EPIC-0805 déplace le badge édition dans le header principal, retire le badge visible du mode d’authentification et applique un fond fuchsia dégradé sans changer le gabarit.
- v0.29.46 : P08/EPIC-0805 ajoute l’accessibilité critique openinfra-web : skip-link, états ARIA, recherche globale annonçable et focus contenu principal.
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


### v0.29.32 — IPAM topologie opérationnelle

Ajout du test `TST-P11-IPAM-TOPOLOGY` pour verrouiller la consolidation nodes/edges IPAM par API, CLI, dashboard et OpenAPI.

### v0.29.35 — Discovery Enterprise proxy enrollment verification

- P11 ajoute `openinfra discovery proxy-enroll-verify` pour valider hors-ligne les fichiers d’enrôlement proxy Enterprise générés par `--config-output`.
- P08 simplifie le titre accueil en `Dashboard` et isole les métriques/statistiques d’accueil hors pages composants.
- La vérification couvre édition, schéma JSON, résultats backend, permissions POSIX et mode `--allow-partial`.

### v0.29.33 — Discovery Enterprise proxy CLI enrollment

Ajout du test `TST-P11-DISCOVERY-PROXY-CLI-ENROLLMENT` pour verrouiller l’enrôlement CLI local/distant des proxies Discovery Enterprise auprès des backends, avec refus Lite/Pro.
- v0.29.33 : P08 ajoute la charte graphique premium Bootstrap 5 openinfra-web, sans changement de structure page, validée par TST-P08-WEB-PREMIUM-THEME.
