### Validation v0.29.82 — Réconciliation Discovery multisource gouvernée

Ajout de `REQ-00823` et `TST-WEB-122` : preuves immuables et hashées, scoring confiance/fraîcheur/complétude déterministe, conflits par chemin d’attribut, résolution complète justifiée, audit sans payload, pagination et migration PostgreSQL `0038_discovery_multisource_reconciliation.sql`, sans écriture RSOT directe.

- Ajout de `REQ-00800` et `TST-WEB-101` pour couvrir GLPI Inventory et Freshservice Assets comme connecteurs ITSM externes sans ticketing natif.
- Ajout de `REQ-00796` et `TST-WEB-097` pour couvrir P13 / EPIC-1302 : lecture streaming par chunks des artefacts d’export massifs signés avec offset, SHA-256 chunk et reprise client.
- Ajout de `REQ-00795` et `TST-WEB-096` pour couvrir P13 / EPIC-1301 : progression opérable des imports massifs reprenables via service, CLI, API, OpenAPI et portail web.
## v0.29.51 — ITAM licences logicielles, contrats et conformité

- Ajout de `REQ-00794` et `TST-WEB-095` pour couvrir P12 / EPIC-1205.
- Les licences logicielles ITAM portent référence licence, référence contrat, produit, éditeur, métrique, quantité achetée, quantité assignée, période de droit, statut, propriétaire et notes.
- Le rapport de conformité calcule `compliant`, `over_assigned`, `expired` ou `planned` sans dupliquer les règles dans le portail web.
- La migration PostgreSQL `0028_itam_software_license_entitlements.sql` ajoute une table partitionnée par tenant avec contraintes et index.

- Ajout de REQ-00789 et TST-WEB-090 pour l’accessibilité navigation/recherche openinfra-web.
## 0.29.45 - 2026-07-07

- Ajout de REQ-00787 et TST-WEB-088 pour l’exposition ITAM dans Dashboard/header/sidebar/recherche avec icône pleine dédiée.
- Ajout de REQ-00788 et TST-WEB-089 pour les boutons Swagger/ReDoc réduits de moitié.

## 0.29.44 - 2026-07-07

- Ajout `REQ-00786` et `TST-WEB-087` pour le panneau latéral accordéon sans masquage et scroll interne stable.
- Ajout `REQ-00785` et `TST-ITAM-002` pour le rapport de couverture garantie/support ITAM par actif.

# OpenInfra CDC/SFG/STG v4.8.1 — Correction stockage PostgreSQL et install.ini

Ce dossier consolide le CDC/SFG/STG OpenInfra avec l'alignement enterprise v4.3 et l'exigence v4.4 d'installation autonome des modes cluster.

## Correction v4.8.1

Cette correction met à jour les entrées existantes du CDC sans ajouter de nouveau volume : mountpoint PostgreSQL `/data/openinfra/`, symlink `/opt/openinfra/data -> /data/openinfra/`, PGDATA initialisé sous `/data/openinfra/`, tailles par édition Lite `2GB`, Pro `100GB`, Entreprise `1TB`.

## Ajout v4.4

Les installations cluster backend, frontend, PostgreSQL et agents d'auto discovery doivent être réalisables par un opérateur non expert. L'opérateur fournit uniquement les données réseau obligatoires : FQDN, IP, masque, VIP, passerelle et DNS. Les installateurs gèrent les dépendances, la configuration HA, les certificats, les services systemd, les migrations backend, les vérifications, les rapports et le rollback.

Les installateurs sont placés dans `installers/`, en dehors de `src/`.

## Services systemd canoniques

- `openinfra.service` : backend/API canonique, bootstrap PostgreSQL géré par OpenInfra, orchestration applicative, application des migrations backend ; en édition Lite, ce même service porte le mode all-in-one monolithique.
- `openinfra-web.service` : frontend React + Bootstrap 5 servant l'interface web.
- `openinfra-agent.service` : collecteur d'auto discovery pour l'édition Entreprise.
- `openinfra-worker.service` : traitements asynchrones lorsque le scope worker est séparé.
- `openinfra-scheduler.service` : planification des jobs.
- `openinfra-connector.service` : connecteurs externes, dont ITSM externe pour Pro et Entreprise.
- `openinfra-exporter.service` : métriques Prometheus lorsque le scope observabilité est activé.

Aucun nom de service ne doit contenir `lite`, `pro`, `enterprise` ou `enterprise`. Aucun service backend séparé supplémentaire ne doit être créé lorsque `openinfra.service` couvre déjà le backend, PostgreSQL géré et les migrations.

## Validation documentaire

```bash
python3 scripts/validate_docs.py
python3 scripts/validate_enterprise_alignment.py
python3 scripts/validate_autonomous_installer.py
```


# OpenInfra CDC/SFG/STG v4.3.0 — Dossier consolidé enterprise

Cette version consolide le CDC/SFG/STG OpenInfra v4, les extensions fonctionnelles v4, les éditions Lite/Pro/Entreprise, les règles de packaging, les agents de découverte, l'interface web React + Bootstrap 5, les connecteurs ITSM externes et le support constructeur obligatoire.

Principes non négociables :

- aucun ITSM intégré ;
- connecteurs ITSM externes uniquement pour Pro et Entreprise ;
- Lite monolithique avec quotas stricts ;
- Pro séparé backend/frontend, backend canonique `openinfra.service`, PostgreSQL medium, asynchrone, connecteurs ITSM ;
- Entreprise distribuée, backend canonique `openinfra.service`, agents, clustering frontend, profil PostgreSQL large ;
- noms systemd invariants par édition ;
- backend canonique `openinfra.service` ;
- agents discovery `openinfra-agent.service` ;
- frontend `openinfra-web.service`, React + Bootstrap 5, API-only ;
- support constructeur et garantie constructeur obligatoires et non écrasables par support tiers.

---


# OpenInfra — Dossier SFG/STG, CCTP/CdCF et architecture enterprise

**Version :** 4.0.0  
**Date :** 2026-07-02  
**Statut :** version enrichie enterprise, prête pour cadrage, consultation d’intégrateurs, lancement de conception détaillée et pilotage de développement.  
**Périmètre :** RSOT (Ressource Source of Truth), DCIM, ITAM, Discovery, Dependency Mapping, IPAM Enterprise++, sécurité, API, IA/automatisation, administration, qualité.  
**Exclusion structurante :** aucune fonction ITSM intégrée. Les outils ITSM sont intégrés par connecteurs externes uniquement.

## Contenu du livrable

Ce référentiel documentaire transforme le CDC initial en dossier industriel structuré :

- 12 volumes SFG/STG alignés sur la structure demandée ;
- CCTP/CdCF exploitable en appel d’offres ;
- exigences numérotées `REQ-xxxxx` ;
- cas d’usage `UC-xxxx` ;
- tests `TST-xxxx` ;
- matrice de traçabilité exigences → cas d’usage → tests ;
- modèle de données logique avec plus de 250 entités ;
- exigences PostgreSQL Cluster, partitionnement, hot/warm/cold et objectifs de performance ;
- ADR/RFC d’architecture ;
- diagrammes C4, PlantUML, Mermaid et ERD ;
- OpenAPI 3.1 et schéma GraphQL de référence ;
- registre des risques ;
- critères d’acceptation contractuels.

## Arborescence principale

```text
OpenInfra-CDC-SFG-STG-v4.8.1/
├── 00-README.md
├── 00-Index-general.md
├── 00-Note-de-cadrage-CCTP-CdCF.md
├── 01-Vision/
├── 02-Fonctionnel/
├── 03-Technique/
├── 04-Donnees/
├── 05-Tests/
├── 06-Exploitation/
├── 07-Architecture-Entreprise/
├── 08-RFC-ADR/
├── 09-API/
├── 10-Diagrammes/
├── 11-Matrices/
├── Volumes/
├── Annexes/
└── scripts/
```

## Règles contractuelles majeures

1. PostgreSQL Cluster est obligatoire comme socle transactionnel principal.
2. Les tables massives ne doivent jamais être monolithiques non partitionnées.
3. L’architecture doit supporter plus de 10 milliards d’entrées sans refonte majeure.
4. Toute lecture volumineuse doit être paginée et bornée.
5. Tout import/export massif doit être asynchrone.
6. Toute allocation IP doit être transactionnelle, idempotente et sûre en concurrence.
7. La localisation physique en salle impose ligne, colonne et coordonnées X/Y/Z lorsque disponibles.
8. Les opérations critiques doivent être auditées et traçables.
9. Les exigences N1 sont obligatoires et non négociables.
10. Les critères d’acceptation et tests associés conditionnent la réception.

## Validation locale du dossier

```bash
python3 scripts/validate_docs.py
```

Le script vérifie la présence des documents essentiels, l’unicité des exigences, l’absence de marqueurs de brouillon et la cohérence minimale des matrices.


## Extension v4.0.0 — améliorations fonctionnelles enterprise

La version 4.0.0 ajoute douze volumes fonctionnels avancés, sans introduire d’ITSM intégré :

- [Volume 13 — Gouvernance de la donnée et sources autoritatives](Volumes/V13-Gouvernance-de-la-donnee.md)
- [Volume 14 — Qualité, certification et réconciliation des données](Volumes/V14-Qualite-certification-reconciliation.md)
- [Volume 15 — Flux réseau, matrices de flux et segmentation](Volumes/V15-Flux-reseau-matrices-flux.md)
- [Volume 16 — Certificats, PKI et secrets référencés](Volumes/V16-Certificats-PKI-secrets-references.md)
- [Volume 17 — Conformité réseau et configuration attendue](Volumes/V17-Conformite-reseau-configuration-attendue.md)
- [Volume 18 — FinOps, coûts, showback et chargeback](Volumes/V18-FinOps-couts-chargeback.md)
- [Volume 19 — Field Operations et mobilité datacenter](Volumes/V19-Field-Operations-mobilite-datacenter.md)
- [Volume 20 — Simulation, analyse d’impact et migration planning](Volumes/V20-Simulation-impact-migration-planning.md)
- [Volume 21 — GreenOps et capacité énergétique](Volumes/V21-GreenOps-capacite-energetique.md)
- [Volume 22 — SBOM, vulnérabilités et exposition contextualisée](Volumes/V22-SBOM-vulnerabilites-exposition.md)
- [Volume 23 — Kubernetes avancé et mapping cloud-native](Volumes/V23-Kubernetes-avance-cloud-native-mapping.md)
- [Volume 24 — Policy Engine et conformité continue](Volumes/V24-Policy-Engine-conformite-continue.md)

Le dossier v4 ajoute également les exigences, entités, cas d’usage, tests, risques et lignes de conformité correspondants dans les matrices contractuelles.


## Extension v4.6.0

La version 4.6.0 ajoute le cadrage enterprise suivant :

- LDAP/IPA, groupes et RBAC pour OpenInfra Pro et OpenInfra Entreprise ;
- compte système `openinfra` créé par root dans toutes les éditions ;
- filesystem LVM dédié monté sur `/opt/openinfra/` avec `rootvg/openinfra_lv` et taille par défaut `2GB` ;
- création idempotente des prérequis système par les installateurs ;
- séparation stricte entre utilisateurs humains authentifiés et compte système de service.

## Addendum v4.7.0

Cette version ajoute le stockage PostgreSQL dédié, la réplication automatique quasi temps réel en mode cluster, le support multisite Pro/Entreprise et la correction des incohérences d'ownership entre application, base de données et symlink.

Décisions structurantes :

- `/opt/openinfra/` appartient au compte applicatif `openinfra`.
- Les données PostgreSQL backend sont stockées et initialisées dans `/data/openinfra/` sur le LV `datavg/openinfradata_lv`, avec taille par défaut par édition : Lite `2GB`, Pro `100GB`, Entreprise `1TB`.
- `/opt/openinfra/data` est un symlink vers `/data/openinfra/`, cible possédée par le compte système PostgreSQL résolu par l installateur.
- Le propriétaire logique du target et du symlink est le compte système gestionnaire PostgreSQL, résolu par l'installateur, sans imposer un nom Unix fixe.
- En cluster, l'installateur configure automatiquement la réplication et la synchronisation quasi temps réel.
- Pro et Entreprise supportent le multisite, avec des capacités distinctes documentées.


## Addendum v4.8.0 — Configuration installateur `./config/install.ini`

Chaque dossier d'installation OpenInfra doit contenir son propre fichier de configuration canonique `./config/install.ini`.
Ce fichier est édité par l'opérateur pour adapter l'installation aux caractéristiques du serveur, sans modifier les scripts d'installation.
L'installateur doit valider ce fichier avant toute action système, produire un dry-run, installer les dépendances, créer les comptes et filesystems, configurer les services et appliquer les migrations backend lorsque le scope le permet.

## v0.29.47 — Badge édition header principal

- Ajout `REQ-00790` : l’édition runtime est affichée juste après le logo OpenInfra dans le header principal.
- Le mode d’authentification n’est plus affiché comme badge permanent dans la titlebar, tout en restant disponible dans le contrat de configuration applicative.
- Le badge d’édition utilise un fond fuchsia dégradé sans modification de gabarit Bootstrap.


## v0.29.48 — Badge édition fuchsia effectif

- Ajout `REQ-00791` : le badge d’édition affiché après le logo OpenInfra ne doit pas hériter du fond bleu Bootstrap `text-bg-primary`.
- Le gabarit du badge reste inchangé via la classe Bootstrap `badge`, mais le fond est forcé par un sélecteur dédié fuchsia dégradé sans composante bleue.
- Le mode d’authentification reste non affiché comme badge permanent.


## v0.29.49 — Badge édition fuchsia très foncé

- Ajout `REQ-00792` : le badge d’édition affiché après le logo OpenInfra doit utiliser un dégradé fuchsia très foncé, tirant vers prune chaud/bruné sans devenir marron.
- Le gabarit Bootstrap `badge` reste inchangé : aucune modification de padding, hauteur, largeur minimale ou taille de police.
- Le mode d’authentification reste non affiché comme badge permanent.

## v0.29.50 — Administration éditions et quotas API/UI

- Ajout `REQ-00793` : le portail openinfra-web et l’API HTTP exposent en lecture les politiques d’édition, les décisions de capacité et les décisions de quota runtime.
- Les routes `/api/v1/editions/policies`, `/api/v1/editions/feature-check` et `/api/v1/editions/quota-check` sont publiées par discovery/OpenAPI et protégées par `security:admin` lorsque l’authentification est active.
- Le composant Sécurité/RBAC/Audit du portail expose les trois opérations sans dupliquer les règles métier côté navigateur.

## v0.29.59 — rollback conflict-aware des imports massifs

OpenInfra ajoute `REQ-00802` pour couvrir le rollback opérable des imports massifs appliqués : dry-run par défaut, restauration versionnée RSOT, mise en retrait sans suppression physique, détection de conflits et publication CLI/API/OpenAPI/discovery/portail web.

## v0.29.60 — guides opérables de migration données

OpenInfra ajoute `REQ-00803` pour exposer des guides structurés de migration Device42, NetBox, Nautobot, GLPI et CSV via CLI/API/OpenAPI/discovery/portail web, sans mutation RSOT.

## v0.29.61 — discovery locale Lite/Pro sans agent

OpenInfra ajoute `REQ-00804` pour exposer un plan de discovery locale Lite/Pro via CLI/API/OpenAPI/discovery/portail web, en mode dry-run, sans agent proxy, sans scan réseau exécuté, sans mutation RSOT et avec secrets `vault://` uniquement.

## v0.29.61 — panneau latéral web groupé par contexte

OpenInfra ajoute `REQ-00805` et `TST-WEB-106` pour regrouper les opérations du panneau latéral par contexte fonctionnel sous chaque composant. Le composant Intégrations est structuré par fournisseur ServiceNow, Jira Assets, GLPI Inventory et Freshservice Assets, sans publier OpenService dans `openinfra-web`.

## v0.29.62 — référentiel tenants ITAM

Ajout du cycle de vie CRUD des tenants ITAM, tenant par défaut unique, retrait logique, sélecteur web et auto-sélection mono-tenant.


## v0.29.63 — plan bootstrap agent Enterprise

OpenInfra expose `openinfra discovery agent-bootstrap-plan` et `POST /api/v1/discovery/agent-bootstrap-plan` pour produire un plan opérable `openinfra-agent.service` Enterprise. Le plan exige HTTPS, mTLS, secret `vault://`, compte de service non-root, publication de résultats par API et ne réalise ni installation ni matérialisation de secret.

## v0.29.64 — UX tenants ITAM

Ajout initial de l’exigence UX `REQ-00808`, désormais réalignée par `REQ-00814` : le portail distingue `Organisation` comme entreprise/groupe client et `Tenant` comme subdivision rattachée ; les références tenant restent des listes de sélection.
## v0.29.65 — DCIM sites, dépendances et responsive mobile

- `REQ-00809` — OpenInfra doit gérer les sites DCIM avec CRUD, retrait logique, conservation d’historique et cascade non destructive vers les dépendances de localisation.
- `REQ-00810` — Les formulaires web manipulant des références DCIM de localisation doivent utiliser des champs `select` alimentés par le catalogue backend, sans texte libre pour `site`, `bâtiment`, `étage`, `salle`, `zone`, `rack`, `ligne` ou `colonne`.
- `REQ-00811` — Le portail `openinfra-web`, y compris la sidebar, doit être responsive et exploitable sur tablettes/smartphones sans masquage d’actions.
### v0.29.71 — compatibilité CLI/CI des commandes édition

La commande `openinfra edition feature-check` accepte désormais les options backend homogènes, dont `--data`, comme `edition list` et `edition quota-check`. Cette exigence verrouille la parité CLI/CI des smoke tests d'administration des éditions sans modifier les décisions métier Lite/Pro/Enterprise.


### v0.29.72 — CRUD dépendances topologiques DCIM

La livraison v0.29.72 ajoute l'exigence `REQ-00813` et le test `TST-WEB-112` afin de gérer explicitement bâtiments, étages, salles et zones, avec validation de parents actifs, retrait logique et cascade non destructive vers les niveaux inférieurs.


## v0.29.74 — Formulaires ITAM racine et migrations minimales

Ajout de `REQ-00815` et `TST-WEB-114` : les formulaires Organisation sont traités comme des formulaires racine, sans sélecteur Organisation parent, Tenant parent ou tenant de sécurité. Les formulaires Tenant sélectionnent l'organisation parente et le tenant cible uniquement lorsque l'opération concerne un tenant existant. Aucune migration SQL supplémentaire n'est créée pour ce correctif UI ; `0031_itam_organization_identity.sql` reste conservée pour compatibilité ascendante.

## v0.29.73 — Organisations ITAM parent des tenants

Ajout de `REQ-00814` et `TST-WEB-113` : OpenInfra gère un référentiel Organisations ITAM avec carte d’identité entreprise complète. Les tenants, supports et licences doivent être rattachés à une organisation active. Le portail sélectionne d’abord l’organisation, filtre les tenants associés et propose un tenant implicite lorsque l’organisation n’a pas encore de tenant matérialisé.


Ajout de `REQ-00816` et `TST-WEB-115` : ITAM dispose désormais d’un référentiel partenaires accrédités par organisation pour les constructeurs, éditeurs logiciels et supports tiers. Les garanties, licences et contrats de support consomment ces partenaires actifs filtrés au lieu de champs fournisseurs libres.
### Validation v0.29.81 — Profils Discovery virtualisation, Kubernetes et cloud

Ajout de `REQ-00822` et `TST-WEB-121` : OpenInfra référence les profils de découverte VMware, Proxmox, Hyper-V, Kubernetes, AWS, Azure, GCP et OpenStack avec secrets `vault://` masqués, endpoint HTTPS lorsque nécessaire, limites de débit/concurrence et migration `0037_discovery_integration_profiles.sql`.

## v0.29.86 — Navigation responsive adaptative et header compact

- `REQ-00811` est réalignée sur trois modes sans perte d'opération : sidebar persistante à partir de 1200 px, mégamenu contextuel multicolonne entre 768 px et 1199,98 px, puis menu compact unique sous 768 px.
- `REQ-00825` compacte de 25 % la seconde barre du header, aligne recherche, FR/EN, Swagger et ReDoc sur un gabarit commun, conserve des cibles tactiles de 44 px et une ombre de header supérieure à celle des blocs.
- `TST-WEB-124` et `TST-WEB-125` valident la parité React/runtime, le clavier, le tactile, les breakpoints et le build frontend.

