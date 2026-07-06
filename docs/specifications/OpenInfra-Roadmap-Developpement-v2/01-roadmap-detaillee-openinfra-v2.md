# OpenInfra — Roadmap détaillée de développement alignée CDC v4.8.1

**Version :** 2.0.0  
**Référence :** OpenInfra CDC/SFG/STG v4.8.1 corrigé  
**Remplace :** Roadmap OpenInfra v1.0.0 alignée CDC v4.0.0  
**Approche :** programme industriel, agile contrôlé, gates Go/No-Go, exigences vérifiables, qualité bloquante, livraisons multi-éditions.

---

## 1. Objectif

Cette roadmap met à jour la trajectoire de développement OpenInfra pour l’aligner sur le CDC consolidé v4.8.1. Elle intègre désormais explicitement :

- les trois éditions **OpenInfra Lite**, **OpenInfra Pro** et **OpenInfra Entreprise** ;
- les quotas, capacités, feature gates, licences et abonnements ;
- les installateurs placés dans **`installers/`**, hors **`src/`** ;
- le fichier **`./config/install.ini`** propre à chaque scope d’installation ;
- l’installation automatique des dépendances par l’installateur ;
- le service backend canonique **`openinfra.service`** ;
- le service frontend **`openinfra-web.service`** ;
- le service agent discovery **`openinfra-agent.service`** ;
- l’abandon de **`ancien service backend obsolète`** ;
- le frontend **React + Bootstrap 5**, consommant exclusivement l’API backend ;
- la création du compte système **`openinfra`** et du filesystem applicatif **`/opt/openinfra/`** ;
- le stockage PostgreSQL dédié **`/data/openinfra/`** ;
- le symlink **`/opt/openinfra/data -> /data/openinfra/`** ;
- l’initialisation PostgreSQL avec **`PGDATA=/data/openinfra/`**, adapté au chemin réel du packaging ;
- les tailles PostgreSQL par édition : Lite **2GB**, Pro **100GB**, Entreprise **1TB** ;
- LDAP/IPA + RBAC/groupes pour Pro et Entreprise ;
- les connecteurs ITSM externes pour Pro et Entreprise, sans ITSM intégré ;
- le multisite Pro/Entreprise ;
- la réplication PostgreSQL automatique et quasi temps réel en cluster.

---

## 2. Décisions structurantes qui impactent la roadmap

| Décision | Impact roadmap |
|---|---|
| Multi-éditions dès le socle | Les phases P02 à P04 deviennent obligatoires avant MVP fonctionnel. |
| Installateurs hors `src` | Le stream packaging doit livrer avant les environnements pilotes. |
| `install.ini` par scope | Les tests installateurs deviennent des gates bloquants. |
| `openinfra.service` backend unique | Les packages, runbooks, tests et docs doivent interdire `ancien service backend obsolète`. |
| PGDATA `/data/openinfra/` | Le lot Data/LVM/PGDATA doit précéder migrations et HA. |
| PostgreSQL géré par backend | Les migrations sont exécutées par le scope backend uniquement. |
| LDAP/IPA Pro/Entreprise | L’IAM enterprise doit arriver avant pilote Pro. |
| Frontend API-only | La parité CLI/API/UI devient un critère de sortie. |
| Agents `openinfra-agent.service` | Discovery distribuée est repoussée au socle Entreprise, pas au Lite/Pro. |
| Connecteurs ITSM externes seulement | La roadmap exclut toute implémentation de ticketing natif. |

---

## 3. Releases macro



---

## 4. Phases programme

| ID | Phase | Période relative | Objectif | Critère de sortie |
| --- | --- | --- | --- | --- |
| P00 | Recalage programme sur CDC v4.8.1 | T0 à T0+1 mois | Mettre à jour backlog, architecture, risques et jalons avec toutes les décisions v4.8.1. | Matrice CDC→roadmap complète, priorisation validée, aucune incohérence ouverte. |
| P01 | Socle engineering et architecture | T0+1 à T0+3 mois | Mettre en place dépôt, architecture logicielle, CI/CD, conventions, API baseline et documentation dev. | Pipeline vert, socle exécutable, quality gates actifs, packaging reproductible. |
| P02 | Editions, feature gates et modèle de livraison | T0+2 à T0+4 mois | Implémenter Lite/Pro/Entreprise, quotas, capacités, licences/abonnements et règles de conformité éditions. | Une même base code livre trois éditions avec tests de gates et limites. |
| P03 | Installateurs hors src et configuration install.ini | T0+2 à T0+5 mois | Créer installers/ avec scopes par édition, config/install.ini, validation, dry-run, dépendances, rollback. | Installateurs idempotents, sans modification de src, validés par édition et scope. |
| P04 | Runtime systemd et packaging OS | T0+3 à T0+6 mois | Normaliser services canoniques openinfra.service, openinfra-web.service et openinfra-agent.service. | Aucun ancien service backend obsolète; services invariants; packages OS et unités validés. |
| P05 | Stockage LVM, PGDATA et migrations backend | T0+3 à T0+7 mois | Créer FS applicatif, FS PostgreSQL /data/openinfra/, symlink, PGDATA réel et migrations backend. | PGDATA=/data/openinfra/ adapté au chemin réel; migrations appliquées par backend. |
| P06 | PostgreSQL HA, synchronisation quasi temps réel et sauvegardes | T0+4 à T0+9 mois | Déployer PostgreSQL géré, Patroni/équivalent, VIP, réplication, PITR, tests failover. | Cluster autonome configuré avec FQDN/IP/mask/VIP/GW/DNS et bascule testée. |
| P07 | Authentification, LDAP/IPA, RBAC et groupes | T0+5 à T0+10 mois | Livrer auth locale Lite, LDAP/IPA Pro/Entreprise, mapping groupes→rôles, audit et permissions. | Pro/Entreprise s’authentifient via LDAP/IPA; RBAC par groupes testé. |
| P08 | Frontend React + Bootstrap 5 et parité CLI/API/UI | T0+5 à T0+11 mois | Livrer shell UI web, design system, appels API backend uniquement et parité fonctionnelle CLI/API/UI. | Toute commande CLI livrée dispose d’un parcours API/UI équivalent ou justifié. |
| P09 | IT Ressources Management, gouvernance et qualité de données | T0+6 à T0+13 mois | Livrer objets, relations, audit, historique, gouvernance source autoritative, scores et réconciliation. | CRUD complet, time travel initial, conflits visibles, qualité mesurée. |
| P10 | DCIM, localisation physique et capacité | T0+7 à T0+15 mois | Livrer sites, bâtiments, salles, lignes/colonnes/X/Y/Z, racks, U, câblage, PDU et capacité. | Un équipement physique est localisable univoquement et exploitable terrain. |
| P11 | IPAM Enterprise++ et DDI | T0+7 à T0+16 mois | Livrer IPv4/IPv6, VRF, ASN, BGP, EVPN/VXLAN, MPLS, NAT, DHCP, DNS, DDI, RPKI et capacité. | Allocation IP concurrente sans conflit, recherche IPAM indexée et audits complets. |
| P12 | ITAM, garanties/support constructeur et support tiers | T0+9 à T0+17 mois | Livrer actifs, logiciels, contrats, licences, garanties constructeur, support constructeur et support tiers séparé. | Le support tiers n’écrase jamais le support constructeur initial. |
| P13 | Imports, exports et connecteurs ITSM externes | T0+9 à T0+18 mois | Livrer imports/exports asynchrones, dry-run, rollback et connecteurs ServiceNow/Jira/GLPI/Freshservice pour Pro/Entreprise. | Aucun ITSM intégré; connecteurs externes testés, imports massifs reprenables. |
| P14 | Discovery, agents et réconciliation multisource | T0+10 à T0+21 mois | Livrer discovery locale, agents Entreprise, protocoles, proxyless/proxy-agent, preuves et scoring. | Agents alimentent la BDD centrale sans accès DB direct et avec mTLS. |
| P15 | Dependency mapping, flux, certificats et conformité réseau | T0+12 à T0+23 mois | Livrer graphes, matrices de flux, SPOF, certificats/PKI, conformité configuration réseau et drift. | Impact analysis et flux déclarés/observés exploitables. |
| P16 | Modules avancés enterprise | T0+16 à T0+28 mois | Livrer Field Ops, simulation, migration planning, FinOps, GreenOps, SBOM, exposition, Kubernetes avancé, Policy Engine et RAG. | Modules avancés gouvernés, non destructifs sans validation, intégrés aux droits. |
| P17 | Multisite, PRA/PCA et exploitation avancée | T0+18 à T0+30 mois | Consolider Pro multisite centralisé, Entreprise multisite distribué, DR, PRA/PCA et runbooks. | Bascule site, restauration, monitoring et procédures validés. |
| P18 | Industrialisation GA et scale enterprise | T0+24 à T0+34 mois | Valider performances, sécurité, chaos, migration, documentation, support, packaging et release. | Go GA signé, benchmarks et validations bloquantes passés. |

---

## 5. Streams d’exécution

| ID | Stream | Responsabilités |
| --- | --- | --- |
| STR-PROD | Produit & fonctionnel | Vision, backlog, priorisation, UX métier, critères d’acceptation, démonstrations et arbitrages. |
| STR-ARCH | Architecture enterprise | C4, ADR/RFC, urbanisation, décisions structurantes, gouvernance technique et revues d’architecture. |
| STR-DATA | Data/PostgreSQL | Modèle, migrations, partitionnement, LVM, PGDATA, HA, index, performance SQL, archivage. |
| STR-BE | Backend/API | Domain services, REST, GraphQL, jobs, outbox, webhooks, RBAC, sécurité applicative et CLI. |
| STR-FE | Frontend React/Bootstrap 5 | Interface web, parité CLI/API/UI, UX DCIM/IPAM/graphes, accessibilité, performance navigateur. |
| STR-DISC | Discovery & agents | Agents, protocoles, orchestration, discovery multisite, secrets, réconciliation et preuves. |
| STR-SEC | Sécurité & IAM | LDAP/IPA, RBAC/ABAC, SSO, MFA, Vault, chiffrement, audit, threat modeling, tests sécurité. |
| STR-SRE | Ops/SRE | Installateurs, systemd, Kubernetes, Helm, observabilité, backup, PRA/PCA, runbooks, support. |
| STR-QA | QA/Validation | Tests unitaires, intégration, fonctionnels, sécurité, performance, charge, chaos, non-régression. |
| STR-DOC | Documentation & enablement | SFG/STG, guides admin, API, runbooks, formation, migration, notes de release. |
| STR-ED | Editions & licensing | OpenInfra Lite/Pro/Entreprise, quotas, feature gates, abonnement/licence, conformité éditions. |
| STR-PKG | Packaging & installateurs | Dossier installers hors src, install.ini, dépendances OS, migrations backend, validation et rollback. |
| STR-MSITE | Multisite & HA | Topologies multisites, synchronisation quasi temps réel, VIP, agents régionaux, DR et tests de bascule. |

---

## 6. Description détaillée par phase

## P00 — Recalage programme sur CDC v4.8.1

**Période relative :** T0 à T0+1 mois

**Objectif :** Mettre à jour backlog, architecture, risques et jalons avec toutes les décisions v4.8.1.

**Critère de sortie :** Matrice CDC→roadmap complète, priorisation validée, aucune incohérence ouverte.

### Epics

#### EPIC-0001 — Matrice CDC v4.8.1 vers roadmap

- **Stream :** STR-PROD
- **Priorité :** P1
- **Résumé :** Cartographier toutes les décisions CDC v4.8.1 vers phases, epics, releases et validations.
- **Livrables :** Matrice CDC→roadmap; backlog recalé; écarts résolus.
- **Dépendances :** Aucun
- **Acceptation :** Chaque exigence structurante dispose d’une cible phase/release.

#### EPIC-0002 — ADR consolidation v4.8.1

- **Stream :** STR-ARCH
- **Priorité :** P1
- **Résumé :** Consolider décisions éditions, installateurs, services, stockage PostgreSQL et multisite dans les ADR/RFC.
- **Livrables :** ADR mis à jour; registre décisions; impacts architecture.
- **Dépendances :** Aucun
- **Acceptation :** Aucune décision de packaging/service/storage sans ADR.

#### EPIC-0003 — Priorisation MVP par édition

- **Stream :** STR-PROD
- **Priorité :** P1
- **Résumé :** Définir les seuils Lite/Pro/Entreprise et les fonctionnalités minimales par release.
- **Livrables :** Backlog édition; limites; critères d’acceptation.
- **Dépendances :** Aucun
- **Acceptation :** Lite/Pro/Entreprise ont chacun un MVP validable.

#### EPIC-0004 — Quality gates v4.8.1

- **Stream :** STR-QA
- **Priorité :** P1
- **Résumé :** Actualiser DoD/DoR et validations bloquantes avec installateurs, PGDATA, LDAP/IPA et multisite.
- **Livrables :** DoD; DoR; gates; plan tests.
- **Dépendances :** Aucun
- **Acceptation :** Aucune release sans tests installateur, service et migration.

#### EPIC-0005 — Runbook programme initial

- **Stream :** STR-SRE
- **Priorité :** P1
- **Résumé :** Définir procédures d’installation, rollback, migration et exploitation attendues.
- **Livrables :** Runbooks initiaux; plan validation exploitation.
- **Dépendances :** Aucun
- **Acceptation :** Les opérations critiques ont une procédure testable.

#### EPIC-0006 — Documentation roadmap v2

- **Stream :** STR-DOC
- **Priorité :** P1
- **Résumé :** Publier roadmap v2 et notes de changement.
- **Livrables :** Roadmap; changelog; matrices.
- **Dépendances :** Aucun
- **Acceptation :** Roadmap approuvée par produit, architecture, SRE et QA.

---

## P01 — Socle engineering et architecture

**Période relative :** T0+1 à T0+3 mois

**Objectif :** Mettre en place dépôt, architecture logicielle, CI/CD, conventions, API baseline et documentation dev.

**Critère de sortie :** Pipeline vert, socle exécutable, quality gates actifs, packaging reproductible.

### Epics

#### EPIC-0101 — Repository et architecture modulaire

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Créer dépôt, modules, packaging, conventions et frontières domaine/application/infrastructure/interfaces.
- **Livrables :** Repository; structure; configs; scripts dev.
- **Dépendances :** P00
- **Acceptation :** Un contributeur clone, teste et lance localement.

#### EPIC-0102 — API REST baseline et OpenAPI

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Livrer API versionnée, pagination, filtres, erreurs normalisées et OpenAPI.
- **Livrables :** REST v1; OpenAPI; tests API.
- **Dépendances :** P00
- **Acceptation :** Toutes les listes imposent limite et cursor.

#### EPIC-0103 — CLI baseline

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Créer CLI OpenInfra avec commandes version, doctor, config, install-validation et health.
- **Livrables :** CLI; tests; docs.
- **Dépendances :** P00
- **Acceptation :** La CLI appelle les mêmes services applicatifs que l’API.

#### EPIC-0104 — CI/CD complète

- **Stream :** STR-QA
- **Priorité :** P1
- **Résumé :** Mettre en place format, lint, type check, tests, sécurité, packaging, smoke et coverage gates.
- **Livrables :** GitHub Actions; artefacts; rapports.
- **Dépendances :** P00
- **Acceptation :** Pipeline vert obligatoire sur branche principale.

#### EPIC-0105 — Threat model initial

- **Stream :** STR-SEC
- **Priorité :** P1
- **Résumé :** Identifier menaces API, installateurs, secrets, discovery, LDAP/IPA et PostgreSQL.
- **Livrables :** Threat model; risques; exigences sécurité.
- **Dépendances :** P00
- **Acceptation :** Risques critiques ont mitigations et tests.

#### EPIC-0106 — Guide développeur initial

- **Stream :** STR-DOC
- **Priorité :** P2
- **Résumé :** Documenter installation dev, conventions, API, tests, branches et troubleshooting.
- **Livrables :** README; guide dev; contribution.
- **Dépendances :** P01
- **Acceptation :** Nouveau dev opérationnel sans assistance non documentée.

---

## P02 — Editions, feature gates et modèle de livraison

**Période relative :** T0+2 à T0+4 mois

**Objectif :** Implémenter Lite/Pro/Entreprise, quotas, capacités, licences/abonnements et règles de conformité éditions.

**Critère de sortie :** Une même base code livre trois éditions avec tests de gates et limites.

### Epics

#### EPIC-0201 — Edition model Lite/Pro/Entreprise

- **Stream :** STR-ED
- **Priorité :** P1
- **Résumé :** Implémenter modèle d’éditions, quotas, capacités activables et limites.
- **Livrables :** Edition registry; config; tests gates.
- **Dépendances :** P01
- **Acceptation :** Les quotas Lite/Pro/Entreprise sont appliqués et testés.

#### EPIC-0202 — Feature gates et licence Pro/Entreprise

- **Stream :** STR-ED
- **Priorité :** P1
- **Résumé :** Livrer feature gates, abonnement/licence Pro/Entreprise, audit et messages d’erreur.
- **Livrables :** License service; audit; tests.
- **Dépendances :** P02
- **Acceptation :** Une fonctionnalité non autorisée est bloquée proprement.

#### EPIC-0203 — Matrice capacités édition

- **Stream :** STR-ED
- **Priorité :** P1
- **Résumé :** Maintenir matrice capacité↔édition comme contrat de release.
- **Livrables :** CSV; docs; tests conformité.
- **Dépendances :** P02
- **Acceptation :** Chaque capacité a statut par édition.

#### EPIC-0204 — Quotas runtime

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Appliquer limites équipements, subnets/VLAN, réservations IP/DNS et utilisateurs.
- **Livrables :** Quota service; migrations; tests.
- **Dépendances :** P02
- **Acceptation :** Dépassement limite refusé sans corruption.

#### EPIC-0205 — Tests de conformité éditions

- **Stream :** STR-QA
- **Priorité :** P1
- **Résumé :** Automatiser scénarios Lite/Pro/Entreprise en CI.
- **Livrables :** Test matrix; fixtures; reports.
- **Dépendances :** P02
- **Acceptation :** CI valide les trois éditions.

#### EPIC-0206 — Notes de release par édition

- **Stream :** STR-PROD
- **Priorité :** P2
- **Résumé :** Définir format des notes et limites par édition.
- **Livrables :** Template release notes; guide support.
- **Dépendances :** P02
- **Acceptation :** Chaque release documente différences d’édition.

---

## P03 — Installateurs hors src et configuration install.ini

**Période relative :** T0+2 à T0+5 mois

**Objectif :** Créer installers/ avec scopes par édition, config/install.ini, validation, dry-run, dépendances, rollback.

**Critère de sortie :** Installateurs idempotents, sans modification de src, validés par édition et scope.

### Epics

#### EPIC-0301 — Arborescence installers hors src

- **Stream :** STR-PKG
- **Priorité :** P1
- **Résumé :** Créer installers/ par édition et scope, strictement hors src.
- **Livrables :** installers/; conventions; validation.
- **Dépendances :** P01
- **Acceptation :** Aucun script installateur n’est dans src.

#### EPIC-0302 — Fichier config/install.ini par scope

- **Stream :** STR-PKG
- **Priorité :** P1
- **Résumé :** Livrer install.ini pour all-in-one, server, web et agent selon édition.
- **Livrables :** Templates install.ini; schema; docs.
- **Dépendances :** P03
- **Acceptation :** Chaque scope possède config/install.ini validé.

#### EPIC-0303 — Installation automatique des dépendances

- **Stream :** STR-PKG
- **Priorité :** P1
- **Résumé :** Détecter OS, configurer dépôts si autorisé et installer dépendances requises.
- **Livrables :** Dependency resolver; logs; rollback.
- **Dépendances :** P03
- **Acceptation :** Blocage explicite si dépendance critique indisponible.

#### EPIC-0304 — Dry-run, impact plan et rollback

- **Stream :** STR-PKG
- **Priorité :** P1
- **Résumé :** Implémenter dry-run, plan d’impact, sauvegarde avant modification et rollback.
- **Livrables :** Installer modes; reports; tests.
- **Dépendances :** P03
- **Acceptation :** Dry-run ne modifie pas le système.

#### EPIC-0305 — Validation réseau minimale

- **Stream :** STR-PKG
- **Priorité :** P1
- **Résumé :** Valider FQDN/IP/mask/VIP/GW/DNS fournis par opérateur.
- **Livrables :** Network validator; errors.
- **Dépendances :** P03
- **Acceptation :** L’installateur détecte incohérences IP/VIP/DNS.

#### EPIC-0306 — Tests installateurs multi-OS

- **Stream :** STR-QA
- **Priorité :** P1
- **Résumé :** Automatiser tests installateurs RHEL/Ubuntu/Debian/SUSE selon cible.
- **Livrables :** CI matrix; containers/VM; reports.
- **Dépendances :** P03
- **Acceptation :** Chaque installateur passe smoke install.

---

## P04 — Runtime systemd et packaging OS

**Période relative :** T0+3 à T0+6 mois

**Objectif :** Normaliser services canoniques openinfra.service, openinfra-web.service et openinfra-agent.service.

**Critère de sortie :** Aucun ancien service backend obsolète; services invariants; packages OS et unités validés.

### Epics

#### EPIC-0401 — Service backend canonique openinfra.service

- **Stream :** STR-SRE
- **Priorité :** P1
- **Résumé :** Définir openinfra.service comme service backend unique pour toutes éditions.
- **Livrables :** Unit systemd; docs; tests.
- **Dépendances :** P03
- **Acceptation :** ancien service backend obsolète est interdit et absent.

#### EPIC-0402 — Service frontend openinfra-web.service

- **Stream :** STR-SRE
- **Priorité :** P1
- **Résumé :** Définir service web React/Bootstrap 5 consommant uniquement API backend.
- **Livrables :** Unit systemd; reverse proxy; tests.
- **Dépendances :** P04
- **Acceptation :** Le web ne se connecte jamais directement à PostgreSQL.

#### EPIC-0403 — Service agent openinfra-agent.service

- **Stream :** STR-SRE
- **Priorité :** P1
- **Résumé :** Définir service collecteur discovery alimentant la BDD centrale via API.
- **Livrables :** Unit systemd; mTLS; config.
- **Dépendances :** P04
- **Acceptation :** L’agent n’a aucun accès direct DB.

#### EPIC-0404 — Packages OS par scope

- **Stream :** STR-PKG
- **Priorité :** P1
- **Résumé :** Construire packages backend, web, agent et all-in-one selon éditions.
- **Livrables :** RPM/DEB; manifests; checksums.
- **Dépendances :** P03
- **Acceptation :** Packages installables et désinstallables proprement.

#### EPIC-0405 — Health, readiness et logs services

- **Stream :** STR-SRE
- **Priorité :** P1
- **Résumé :** Ajouter health checks, journald, logs JSON et diagnostics par service.
- **Livrables :** Health endpoints; log config.
- **Dépendances :** P04
- **Acceptation :** systemctl status et doctor exposent état utile.

#### EPIC-0406 — Tests interdiction services obsolètes

- **Stream :** STR-QA
- **Priorité :** P1
- **Résumé :** Valider absence ancien service backend obsolète et noms invariants.
- **Livrables :** Tests packaging; scan artefacts.
- **Dépendances :** P04
- **Acceptation :** CI échoue si service obsolète réapparaît.

---

## P05 — Stockage LVM, PGDATA et migrations backend

**Période relative :** T0+3 à T0+7 mois

**Objectif :** Créer FS applicatif, FS PostgreSQL /data/openinfra/, symlink, PGDATA réel et migrations backend.

**Critère de sortie :** PGDATA=/data/openinfra/ adapté au chemin réel; migrations appliquées par backend.

### Epics

#### EPIC-0501 — FS applicatif /opt/openinfra

- **Stream :** STR-DATA
- **Priorité :** P1
- **Résumé :** Créer/valider LV applicatif rootvg/openinfra_lv monté /opt/openinfra/ owner openinfra pour tous les scopes applicatifs incluant enterprise/agent.
- **Livrables :** LVM scripts; install.ini; tests.
- **Dépendances :** P03
- **Acceptation :** /opt/openinfra/ a owner openinfra:openinfra; enterprise/agent reste sans PostgreSQL ni PGDATA.

#### EPIC-0502 — FS PostgreSQL /data/openinfra

- **Stream :** STR-DATA
- **Priorité :** P1
- **Résumé :** Créer/valider datavg/openinfradata_lv monté /data/openinfra/ avec taille par édition.
- **Livrables :** LVM scripts; matrix; tests.
- **Dépendances :** P03
- **Acceptation :** Lite=2GB, Pro=100GB, Entreprise=1TB.

#### EPIC-0503 — PGDATA réel sous /data/openinfra

- **Stream :** STR-DATA
- **Priorité :** P1
- **Résumé :** Initialiser PostgreSQL avec PGDATA=/data/openinfra/ adapté au chemin réel du packaging.
- **Livrables :** initdb; service override; docs.
- **Dépendances :** P05
- **Acceptation :** PostgreSQL démarre avec PGDATA sur /data/openinfra/.

#### EPIC-0504 — Symlink /opt/openinfra/data

- **Stream :** STR-DATA
- **Priorité :** P1
- **Résumé :** Créer /opt/openinfra/data -> /data/openinfra/ avec ownership du gestionnaire PostgreSQL.
- **Livrables :** Symlink script; validation.
- **Dépendances :** P05
- **Acceptation :** Symlink valide, owner résolu par installateur.

#### EPIC-0505 — Compte système PostgreSQL logique

- **Stream :** STR-DATA
- **Priorité :** P1
- **Résumé :** Résoudre ou créer le compte système gestionnaire PostgreSQL selon OS/package sans imposer un nom.
- **Livrables :** Resolver; docs; tests.
- **Dépendances :** P05
- **Acceptation :** Le nom effectif est détecté et audité.

#### EPIC-0506 — Migrations backend automatiques

- **Stream :** STR-DATA
- **Priorité :** P1
- **Résumé :** Appliquer toutes les migrations backend dans le scope openinfra.service avant démarrage final.
- **Livrables :** Migration runner; locks; rollback.
- **Dépendances :** P05
- **Acceptation :** Frontend/agent ne peuvent pas appliquer de migrations.

---

## P06 — PostgreSQL HA, synchronisation quasi temps réel et sauvegardes

**Période relative :** T0+4 à T0+9 mois

**Objectif :** Déployer PostgreSQL géré, Patroni/équivalent, VIP, réplication, PITR, tests failover.

**Critère de sortie :** Cluster autonome configuré avec FQDN/IP/mask/VIP/GW/DNS et bascule testée.

### Epics

#### EPIC-0601 — Cluster PostgreSQL autonome

- **Stream :** STR-DATA
- **Priorité :** P1
- **Résumé :** Configurer primaire/réplicas, pooling, routage et VIP à partir des paramètres install.ini.
- **Livrables :** Patroni/équiv.; HAProxy; PgBouncer.
- **Dépendances :** P05
- **Acceptation :** Cluster bootstrappé sans expertise opérateur.

#### EPIC-0602 — Synchronisation quasi temps réel

- **Stream :** STR-DATA
- **Priorité :** P1
- **Résumé :** Configurer synchronisation quasi temps réel par défaut en mode cluster.
- **Livrables :** Config replication; monitoring.
- **Dépendances :** P06
- **Acceptation :** Replication lag surveillé et seuils définis.

#### EPIC-0603 — Mode strict optionnel

- **Stream :** STR-DATA
- **Priorité :** P1
- **Résumé :** Ajouter option stricte pour écritures critiques selon contraintes RPO.
- **Livrables :** Config; docs; tests.
- **Dépendances :** P06
- **Acceptation :** Mode strict documenté et testable.

#### EPIC-0604 — PITR et sauvegardes

- **Stream :** STR-SRE
- **Priorité :** P1
- **Résumé :** Configurer WAL archiving, sauvegarde chiffrée, rétention et restauration.
- **Livrables :** pgBackRest/équiv.; runbook.
- **Dépendances :** P06
- **Acceptation :** Restauration PITR démontrée.

#### EPIC-0605 — Tests failover sous charge

- **Stream :** STR-QA
- **Priorité :** P1
- **Résumé :** Valider bascule primaire pendant charge API/import.
- **Livrables :** Test chaos; reports.
- **Dépendances :** P06
- **Acceptation :** Aucune corruption, reprise contrôlée.

#### EPIC-0606 — Dashboards PostgreSQL

- **Stream :** STR-SRE
- **Priorité :** P1
- **Résumé :** Livrer métriques locks, lag, bloat, cache, I/O, connexions et requêtes lentes.
- **Livrables :** Grafana; Prometheus; alertes.
- **Dépendances :** P06
- **Acceptation :** Alertes critiques visibles.

---

## P07 — Authentification, LDAP/IPA, RBAC et groupes

**Période relative :** T0+5 à T0+10 mois

**Objectif :** Livrer auth locale Lite, LDAP/IPA Pro/Entreprise, mapping groupes→rôles, audit et permissions.

**Critère de sortie :** Pro/Entreprise s’authentifient via LDAP/IPA; RBAC par groupes testé.

### Epics

#### EPIC-0701 — Auth locale Lite

- **Stream :** STR-SEC
- **Priorité :** P1
- **Résumé :** Livrer authentification autonome Lite avec maximum 5 utilisateurs.
- **Livrables :** Auth service; tests.
- **Dépendances :** P02
- **Acceptation :** Lite fonctionne sans LDAP/IPA.

#### EPIC-0702 — LDAP/LDAPS Pro/Entreprise

- **Stream :** STR-SEC
- **Priorité :** P1
- **Résumé :** Intégrer LDAP/LDAPS pour Pro et Entreprise.
- **Livrables :** LDAP connector; config; docs.
- **Dépendances :** P07
- **Acceptation :** Login LDAP audité et sécurisé TLS.

#### EPIC-0703 — IPA/FreeIPA Pro/Entreprise

- **Stream :** STR-SEC
- **Priorité :** P1
- **Résumé :** Intégrer IPA/FreeIPA, groupes, certificats et mapping.
- **Livrables :** IPA connector; config; tests.
- **Dépendances :** P07
- **Acceptation :** Groupes IPA mappés vers rôles OpenInfra.

#### EPIC-0704 — RBAC par groupes utilisateurs

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Appliquer permissions par groupes/rôles, tenants, sites et scopes.
- **Livrables :** RBAC engine; tests.
- **Dépendances :** P07
- **Acceptation :** Refus et autorisations testés.

#### EPIC-0705 — Audit IAM

- **Stream :** STR-SEC
- **Priorité :** P1
- **Résumé :** Journaliser connexions, refus, changements mapping et élévations.
- **Livrables :** Audit events; reports.
- **Dépendances :** P07
- **Acceptation :** Audit immuable/append-only selon cible.

#### EPIC-0706 — Tests sécurité IAM

- **Stream :** STR-QA
- **Priorité :** P1
- **Résumé :** Tester injection LDAP, bypass RBAC, session, MFA/SSO quand applicable.
- **Livrables :** Security tests.
- **Dépendances :** P07
- **Acceptation :** Aucun contournement RBAC connu.

---

## P08 — Frontend React + Bootstrap 5 et parité CLI/API/UI

**Période relative :** T0+5 à T0+11 mois

**Objectif :** Livrer shell UI web, design system, appels API backend uniquement et parité fonctionnelle CLI/API/UI.

**Critère de sortie :** Toute commande CLI livrée dispose d’un parcours API/UI équivalent ou justifié.

### Epics

#### EPIC-0801 — Frontend React + Bootstrap 5 shell

- **Stream :** STR-FE
- **Priorité :** P1
- **Résumé :** Créer interface web, navigation, layout, auth shell et composants communs.
- **Livrables :** React app; Bootstrap 5; tests.
- **Dépendances :** P01
- **Acceptation :** Application web démarre et consomme API backend.

#### EPIC-0802 — Parité CLI/API/UI

- **Stream :** STR-FE
- **Priorité :** P1
- **Résumé :** Définir matrice commande CLI→API→UI et implémenter workflows essentiels.
- **Livrables :** Matrix; UI flows; tests.
- **Dépendances :** P08
- **Acceptation :** Aucune fonctionnalité CLI majeure sans parcours UI/API.

#### EPIC-0803 — Tables paginées et filtres indexés

- **Stream :** STR-FE
- **Priorité :** P1
- **Résumé :** Implémenter listes API cursor-based, filtres et tri contrôlé.
- **Livrables :** Components; API integration.
- **Dépendances :** P08
- **Acceptation :** UI n’appelle jamais d’endpoint non paginé.

#### EPIC-0804 — Administration éditions et quotas

- **Stream :** STR-FE
- **Priorité :** P1
- **Résumé :** Afficher édition active, limites, alertes de quotas et capacités.
- **Livrables :** Screens; alerts.
- **Dépendances :** P02
- **Acceptation :** Quota visible avant refus opérationnel.

#### EPIC-0805 — Accessibilité et responsive

- **Stream :** STR-FE
- **Priorité :** P1
- **Résumé :** Appliquer standards accessibilité et responsive pour exploitation.
- **Livrables :** A11y tests; UI docs.
- **Dépendances :** P08
- **Acceptation :** Tests a11y critiques passants.

#### EPIC-0806 — Tests E2E UI

- **Stream :** STR-QA
- **Priorité :** P1
- **Résumé :** Automatiser parcours login, ITRM, IPAM, DCIM, install status et admin.
- **Livrables :** E2E suite.
- **Dépendances :** P08
- **Acceptation :** Parcours critiques stables en CI.

---

## P09 — IT Ressources Management, gouvernance et qualité de données

**Période relative :** T0+6 à T0+13 mois

**Objectif :** Livrer objets, relations, audit, historique, gouvernance source autoritative, scores et réconciliation.

**Critère de sortie :** CRUD complet, time travel initial, conflits visibles, qualité mesurée.

### Epics

#### EPIC-0901 — Objets IT Ressources Management

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Livrer devices, interfaces, services, applications, relations et tags.
- **Livrables :** Domain model; API; UI.
- **Dépendances :** P01
- **Acceptation :** CRUD et historisation fonctionnent.

#### EPIC-0902 — Gouvernance sources autoritatives

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Définir source autoritative par attribut et priorité des sources.
- **Livrables :** Governance service; rules.
- **Dépendances :** P09
- **Acceptation :** Conflit source ne provoque jamais d’écrasement silencieux.

#### EPIC-0903 — Qualité et certification données

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Calculer scores qualité, fraîcheur et confiance.
- **Livrables :** Quality engine; dashboards.
- **Dépendances :** P09
- **Acceptation :** Objets incomplets et incohérents visibles.

#### EPIC-0904 — Historique time travel

- **Stream :** STR-DATA
- **Priorité :** P1
- **Résumé :** Restituer état à date pour objets et relations.
- **Livrables :** History schema; API as-of.
- **Dépendances :** P09
- **Acceptation :** Reconstruction à date validée.

#### EPIC-0905 — Audit objet

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Tracer toute modification critique avec source et corrélation.
- **Livrables :** Audit events; UI.
- **Dépendances :** P09
- **Acceptation :** Audit consultable par objet.

#### EPIC-0906 — Tests réconciliation

- **Stream :** STR-QA
- **Priorité :** P1
- **Résumé :** Tester fusion, conflit, source prioritaire et résolution.
- **Livrables :** Test suite.
- **Dépendances :** P09
- **Acceptation :** Réconciliation reproductible et auditée.

---

## P10 — DCIM, localisation physique et capacité

**Période relative :** T0+7 à T0+15 mois

**Objectif :** Livrer sites, bâtiments, salles, lignes/colonnes/X/Y/Z, racks, U, câblage, PDU et capacité.

**Critère de sortie :** Un équipement physique est localisable univoquement et exploitable terrain.

### Epics

#### EPIC-1001 — Modèle physique DCIM

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Livrer sites, bâtiments, étages, salles, zones, lignes, colonnes, X/Y/Z.
- **Livrables :** Model; API; UI.
- **Dépendances :** P09
- **Acceptation :** Localisation obligatoire pour équipement physique.

#### EPIC-1002 — Plans 2D et rack elevation

- **Stream :** STR-FE
- **Priorité :** P1
- **Résumé :** Afficher salles, racks, faces, U, équipements et QR codes.
- **Livrables :** UI plans; exports.
- **Dépendances :** P10
- **Acceptation :** Technicien localise sans ambiguïté.

#### EPIC-1003 — Câblage et chemins

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Modéliser ports, patch panels, câbles, conduits et chemins.
- **Livrables :** Cable model; UI.
- **Dépendances :** P10
- **Acceptation :** Chemin câble traçable de bout en bout.

#### EPIC-1004 — PDU énergie et refroidissement

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Modéliser PDU, UPS, chaînes A/B, capteurs et capacité.
- **Livrables :** Power/cooling model.
- **Dépendances :** P10
- **Acceptation :** Capacité espace/poids/énergie visible.

#### EPIC-1005 — Jumeau numérique initial

- **Stream :** STR-BE
- **Priorité :** P2
- **Résumé :** Créer représentation numérique cohérente salle/rack/énergie/câblage.
- **Livrables :** Digital twin baseline.
- **Dépendances :** P10
- **Acceptation :** Vue consolidée exploitable.

#### EPIC-1006 — Tests contraintes localisation

- **Stream :** STR-QA
- **Priorité :** P1
- **Résumé :** Valider ligne/colonne/X/Y/Z, rack/U et conflits de placement.
- **Livrables :** Constraint tests.
- **Dépendances :** P10
- **Acceptation :** Placement incohérent refusé.

---

## P11 — IPAM Enterprise++ et DDI

**Période relative :** T0+7 à T0+16 mois

**Objectif :** Livrer IPv4/IPv6, VRF, ASN, BGP, EVPN/VXLAN, MPLS, NAT, DHCP, DNS, DDI, RPKI et capacité.

**Critère de sortie :** Allocation IP concurrente sans conflit, recherche IPAM indexée et audits complets.

### Epics

#### EPIC-1101 — Core IPAM IPv4/IPv6/VRF

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Livrer VRF, prefixes, IP ranges, adresses et validations CIDR.
- **Livrables :** IPAM model; API.
- **Dépendances :** P09
- **Acceptation :** IPv4/IPv6 fonctionnent par VRF.

#### EPIC-1102 — Allocation IP transactionnelle

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Implémenter next-available-IP avec transactions, locks fins, idempotency keys.
- **Livrables :** Allocation service.
- **Dépendances :** P11
- **Acceptation :** Concurrence sans collision.

#### EPIC-1103 — DDI DNS/DHCP

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Corréler DNS, reverse, DHCP scopes/leases et réservations.
- **Livrables :** DDI connectors; checks.
- **Dépendances :** P11
- **Acceptation :** Conflits DNS/DHCP/IPAM détectés.

#### EPIC-1104 — ASN/BGP/EVPN/VXLAN/MPLS/NAT

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Ajouter objets réseau avancés et relations IPAM.
- **Livrables :** Advanced network model.
- **Dépendances :** P11
- **Acceptation :** Objets avancés exposés API/UI.

#### EPIC-1105 — Indexation IPAM massive

- **Stream :** STR-DATA
- **Priorité :** P1
- **Résumé :** Optimiser inet/cidr, VRF/site, partitions et requêtes critiques.
- **Livrables :** Indexes; benchmarks.
- **Dépendances :** P11
- **Acceptation :** Recherche IPAM VRF < objectifs.

#### EPIC-1106 — Tests IPAM charge

- **Stream :** STR-QA
- **Priorité :** P1
- **Résumé :** Tester forte volumétrie, pagination et allocations concurrentes.
- **Livrables :** Load tests.
- **Dépendances :** P11
- **Acceptation :** Objectifs p95/p99 mesurés.

---

## P12 — ITAM, garanties/support constructeur et support tiers

**Période relative :** T0+9 à T0+17 mois

**Objectif :** Livrer actifs, logiciels, contrats, licences, garanties constructeur, support constructeur et support tiers séparé.

**Critère de sortie :** Le support tiers n’écrase jamais le support constructeur initial.

### Epics

#### EPIC-1201 — Modèle ITAM actif physique

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Livrer lifecycle actif, propriétaires, coûts, statuts et localisations.
- **Livrables :** ITAM model; API; UI.
- **Dépendances :** P09
- **Acceptation :** Actifs liés au ITRM/DCIM.

#### EPIC-1202 — Garantie constructeur obligatoire

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Stocker garantie constructeur obligatoire sur équipement physique.
- **Livrables :** Warranty model; validations.
- **Dépendances :** P12
- **Acceptation :** Equipement physique incomplet refusé ou marqué non conforme.

#### EPIC-1203 — Support constructeur initial

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Stocker support constructeur initial sans écrasement.
- **Livrables :** Support model; UI.
- **Dépendances :** P12
- **Acceptation :** Support constructeur visible et non destructible.

#### EPIC-1204 — Support tiers séparé

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Ajouter support tiers sans remplacer constructeur.
- **Livrables :** Third-party contract model.
- **Dépendances :** P12
- **Acceptation :** Support tiers crée relation séparée.

#### EPIC-1205 — Licences et contrats

- **Stream :** STR-BE
- **Priorité :** P2
- **Résumé :** Livrer logiciels, licences, garanties, contrats, EOL/EOS.
- **Livrables :** Contracts; lifecycle.
- **Dépendances :** P12
- **Acceptation :** Rapports conformité disponibles.

#### EPIC-1206 — Tests non-écrasement support

- **Stream :** STR-QA
- **Priorité :** P1
- **Résumé :** Tester imports/discovery/API empêchant écrasement constructeur par tiers.
- **Livrables :** Regression tests.
- **Dépendances :** P12
- **Acceptation :** Aucune source tiers n’écrase constructeur.

---

## P13 — Imports, exports et connecteurs ITSM externes

**Période relative :** T0+9 à T0+18 mois

**Objectif :** Livrer imports/exports asynchrones, dry-run, rollback et connecteurs ServiceNow/Jira/GLPI/Freshservice pour Pro/Entreprise.

**Critère de sortie :** Aucun ITSM intégré; connecteurs externes testés, imports massifs reprenables.

### Epics

#### EPIC-1301 — Imports massifs async

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Livrer imports CSV/XLSX/JSON/API avec dry-run, mapping, validation, reprise.
- **Livrables :** Import service; UI.
- **Dépendances :** P09
- **Acceptation :** Import 1M lignes reprenable.

#### EPIC-1302 — Exports async et streaming

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Livrer exports massifs asynchrones, signés et filtrés.
- **Livrables :** Export service.
- **Dépendances :** P13
- **Acceptation :** Aucun export massif synchrone.

#### EPIC-1303 — Connecteur ServiceNow externe

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Synchroniser CI/liens tickets sans ITSM intégré pour Pro/Entreprise.
- **Livrables :** Connector; docs.
- **Dépendances :** P13
- **Acceptation :** Aucun objet ticket natif OpenInfra.

#### EPIC-1304 — Connecteurs Jira/GLPI/Freshservice

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Ajouter connecteurs ITSM externes Pro/Entreprise.
- **Livrables :** Connectors; tests.
- **Dépendances :** P13
- **Acceptation :** Connecteurs isolés par feature gates.

#### EPIC-1305 — Tests rollback import

- **Stream :** STR-QA
- **Priorité :** P1
- **Résumé :** Valider rollback, conflicts et reprise après crash.
- **Livrables :** Integration tests.
- **Dépendances :** P13
- **Acceptation :** Import interrompu reprend sans doublons.

#### EPIC-1306 — Guides migration données

- **Stream :** STR-DOC
- **Priorité :** P2
- **Résumé :** Documenter migrations depuis Device42/NetBox/GLPI/CSV.
- **Livrables :** Migration guides.
- **Dépendances :** P13
- **Acceptation :** Migration pilote documentée.

---

## P14 — Discovery, agents et réconciliation multisource

**Période relative :** T0+10 à T0+21 mois

**Objectif :** Livrer discovery locale, agents Entreprise, protocoles, proxyless/proxy-agent, preuves et scoring.

**Critère de sortie :** Agents alimentent la BDD centrale sans accès DB direct et avec mTLS.

### Epics

#### EPIC-1401 — Discovery locale Lite/Pro

- **Stream :** STR-DISC
- **Priorité :** P1
- **Résumé :** Livrer discovery locale sans agent proxy pour Lite/Pro.
- **Livrables :** Discovery jobs; UI.
- **Dépendances :** P11
- **Acceptation :** Discovery active selon limites édition.

#### EPIC-1402 — Agent Enterprise

- **Stream :** STR-DISC
- **Priorité :** P1
- **Résumé :** Livrer openinfra-agent.service comme collecteur régional/site.
- **Livrables :** Agent; mTLS; config.
- **Dépendances :** P04
- **Acceptation :** Agent publie résultats via API.

#### EPIC-1403 — Protocoles SNMP/SSH/WinRM

- **Stream :** STR-DISC
- **Priorité :** P1
- **Résumé :** Implémenter protocoles de base sécurisés.
- **Livrables :** Connectors; secrets.
- **Dépendances :** P14
- **Acceptation :** Secrets masqués, rate limit actif.

#### EPIC-1404 — VMware/Proxmox/Hyper-V/Kubernetes/Cloud

- **Stream :** STR-DISC
- **Priorité :** P1
- **Résumé :** Ajouter discovery virtualisation, cloud et Kubernetes.
- **Livrables :** Connectors.
- **Dépendances :** P14
- **Acceptation :** Assets découverts rapprochés.

#### EPIC-1405 — Réconciliation multisource

- **Stream :** STR-DISC
- **Priorité :** P1
- **Résumé :** Calculer preuve, score confiance et conflits.
- **Livrables :** Reconciliation engine.
- **Dépendances :** P09
- **Acceptation :** Aucun écrasement silencieux.

#### EPIC-1406 — Tests crash worker/agent

- **Stream :** STR-QA
- **Priorité :** P1
- **Résumé :** Valider reprise jobs, DLQ, idempotence et non-perte.
- **Livrables :** Resilience tests.
- **Dépendances :** P14
- **Acceptation :** Panne agent ne perd pas job validé.

---

## P15 — Dependency mapping, flux, certificats et conformité réseau

**Période relative :** T0+12 à T0+23 mois

**Objectif :** Livrer graphes, matrices de flux, SPOF, certificats/PKI, conformité configuration réseau et drift.

**Critère de sortie :** Impact analysis et flux déclarés/observés exploitables.

### Epics

#### EPIC-1501 — Dependency graph

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Livrer graphe applications, services, réseau, stockage, DCIM et alimentation.
- **Livrables :** Graph service; UI.
- **Dépendances :** P09
- **Acceptation :** Impact graph exploitable.

#### EPIC-1502 — Matrice de flux

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Comparer flux déclarés et observés NetFlow/sFlow/IPFIX/logs.
- **Livrables :** Flow model; UI.
- **Dépendances :** P15
- **Acceptation :** Flux orphelins et non autorisés visibles.

#### EPIC-1503 — Certificats et PKI

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Inventorier certificats, chaînes, SAN, expiration, propriétaires et endpoints.
- **Livrables :** Cert module.
- **Dépendances :** P15
- **Acceptation :** Certificats expirants détectés.

#### EPIC-1504 — Conformité réseau golden config

- **Stream :** STR-BE
- **Priorité :** P1
- **Résumé :** Comparer config attendue et découverte, détecter drift.
- **Livrables :** Config compliance.
- **Dépendances :** P15
- **Acceptation :** Drift réseau rapporté.

#### EPIC-1505 — Visualisations impact et SPOF

- **Stream :** STR-FE
- **Priorité :** P1
- **Résumé :** Afficher graphes, chemins, SPOF, filtres et exports.
- **Livrables :** Graph UI.
- **Dépendances :** P15
- **Acceptation :** SPOF critiques identifiés.

#### EPIC-1506 — Tests graphes volumétriques

- **Stream :** STR-QA
- **Priorité :** P1
- **Résumé :** Valider performances graphe, pagination et filtres.
- **Livrables :** Performance tests.
- **Dépendances :** P15
- **Acceptation :** Graphe 1 niveau sous objectif.

---

## P16 — Modules avancés enterprise

**Période relative :** T0+16 à T0+28 mois

**Objectif :** Livrer Field Ops, simulation, migration planning, FinOps, GreenOps, SBOM, exposition, Kubernetes avancé, Policy Engine et RAG.

**Critère de sortie :** Modules avancés gouvernés, non destructifs sans validation, intégrés aux droits.

### Epics

#### EPIC-1601 — Field Operations mobile/offline

- **Stream :** STR-BE
- **Priorité :** P2
- **Résumé :** Livrer fiches intervention, QR, checklists, photos et mode offline.
- **Livrables :** Mobile web; sync.
- **Dépendances :** P10
- **Acceptation :** Intervention terrain guidée.

#### EPIC-1602 — Simulation changement/migration

- **Stream :** STR-BE
- **Priorité :** P2
- **Résumé :** Simuler déplacement, coupure, VLAN, subnet, migration et impacts.
- **Livrables :** Simulation engine.
- **Dépendances :** P15
- **Acceptation :** Rapport avant/après généré.

#### EPIC-1603 — FinOps et coûts

- **Stream :** STR-BE
- **Priorité :** P2
- **Résumé :** Rattacher coûts cloud, datacenter, licences, énergie et contrats.
- **Livrables :** Cost model; reports.
- **Dépendances :** P12
- **Acceptation :** Showback par service/tenant.

#### EPIC-1604 — GreenOps

- **Stream :** STR-BE
- **Priorité :** P2
- **Résumé :** Calculer énergie, PUE, CO2 estimé et recommandations capacité.
- **Livrables :** Sustainability module.
- **Dépendances :** P10
- **Acceptation :** Rapports énergie par site/rack.

#### EPIC-1605 — SBOM/vulnérabilités/exposition

- **Stream :** STR-BE
- **Priorité :** P2
- **Résumé :** Importer SBOM, lier CVE, exposition et criticité métier.
- **Livrables :** SBOM registry.
- **Dépendances :** P12
- **Acceptation :** Risque contextualisé disponible.

#### EPIC-1606 — RAG gouverné

- **Stream :** STR-BE
- **Priorité :** P2
- **Résumé :** Livrer recherche naturelle et assistant RAG avec citations et permissions.
- **Livrables :** RAG service; audit.
- **Dépendances :** P09
- **Acceptation :** Réponse filtrée par droits, aucune action destructive.

---

## P17 — Multisite, PRA/PCA et exploitation avancée

**Période relative :** T0+18 à T0+30 mois

**Objectif :** Consolider Pro multisite centralisé, Entreprise multisite distribué, DR, PRA/PCA et runbooks.

**Critère de sortie :** Bascule site, restauration, monitoring et procédures validés.

### Epics

#### EPIC-1701 — Modèle multisite Pro

- **Stream :** STR-MSITE
- **Priorité :** P1
- **Résumé :** Livrer multisite centralisé Pro avec RBAC par site et rapports.
- **Livrables :** Site model; reports.
- **Dépendances :** P07
- **Acceptation :** Pro gère plusieurs sites sans agents régionaux.

#### EPIC-1702 — Modèle multisite Entreprise

- **Stream :** STR-MSITE
- **Priorité :** P1
- **Résumé :** Livrer multisite distribué avec agents régionaux et discovery par site/région/VRF.
- **Livrables :** Regional agents; routing.
- **Dépendances :** P14
- **Acceptation :** Entreprise découvre par région via agents.

#### EPIC-1703 — DR multisite

- **Stream :** STR-MSITE
- **Priorité :** P1
- **Résumé :** Définir réplication, restauration et bascule intersite.
- **Livrables :** DR runbooks; tests.
- **Dépendances :** P06
- **Acceptation :** Scénario perte site testé.

#### EPIC-1704 — PRA/PCA complets

- **Stream :** STR-SRE
- **Priorité :** P1
- **Résumé :** Documenter et valider RPO/RTO, sauvegardes, PITR et procédures.
- **Livrables :** Runbooks; evidence.
- **Dépendances :** P17
- **Acceptation :** RTO/RPO mesurés.

#### EPIC-1705 — Observabilité multisite

- **Stream :** STR-SRE
- **Priorité :** P1
- **Résumé :** Mesurer lag agents, DB, API, jobs, health par site.
- **Livrables :** Dashboards; alerts.
- **Dépendances :** P17
- **Acceptation :** Alertes par site visibles.

#### EPIC-1706 — Chaos multisite

- **Stream :** STR-QA
- **Priorité :** P1
- **Résumé :** Tester pannes réseau, site, agent, DB, file et frontend.
- **Livrables :** Chaos reports.
- **Dépendances :** P17
- **Acceptation :** Dégradation contrôlée sans corruption.

---

## P18 — Industrialisation GA et scale enterprise

**Période relative :** T0+24 à T0+34 mois

**Objectif :** Valider performances, sécurité, chaos, migration, documentation, support, packaging et release.

**Critère de sortie :** Go GA signé, benchmarks et validations bloquantes passés.

### Epics

#### EPIC-1801 — Benchmarks enterprise scale

- **Stream :** STR-QA
- **Priorité :** P1
- **Résumé :** Exécuter charge API, IPAM, imports, discovery, DB et graphes.
- **Livrables :** Benchmark reports.
- **Dépendances :** P06-P17
- **Acceptation :** Objectifs p95/p99 atteints ou écarts acceptés.

#### EPIC-1802 — Audit sécurité release

- **Stream :** STR-SEC
- **Priorité :** P1
- **Résumé :** Exécuter SAST, DAST, dependency scan, secrets scan, container scan, RBAC tests.
- **Livrables :** Security reports.
- **Dépendances :** P18
- **Acceptation :** Aucune vulnérabilité critique ouverte.

#### EPIC-1803 — Validation packaging release

- **Stream :** STR-SRE
- **Priorité :** P1
- **Résumé :** Vérifier packages, installateurs, checksums, SBOM, signatures et rollback.
- **Livrables :** Release artefacts.
- **Dépendances :** P03-P18
- **Acceptation :** Artefacts reproductibles et validés.

#### EPIC-1804 — Documentation GA

- **Stream :** STR-DOC
- **Priorité :** P1
- **Résumé :** Finaliser guides admin, utilisateur, API, installateurs, exploitation, PRA/PCA et upgrade.
- **Livrables :** Docs GA.
- **Dépendances :** P18
- **Acceptation :** Docs suffisantes pour production.

#### EPIC-1805 — Go/No-Go GA

- **Stream :** STR-PROD
- **Priorité :** P1
- **Résumé :** Consolider critères business, tech, sécurité, support et exploitation.
- **Livrables :** Go/No-Go report.
- **Dépendances :** P18
- **Acceptation :** GA signée ou refus motivé.

#### EPIC-1806 — Support et maintenance release

- **Stream :** STR-SRE
- **Priorité :** P1
- **Résumé :** Définir SLA support projet, lifecycle version, patch policy et migration.
- **Livrables :** Support model.
- **Dépendances :** P18
- **Acceptation :** Process release/support opérationnel.

---


## 7. Points de contrôle Go/No-Go

| ID | Gate | Périmètre | Critères | Règle de décision |
| --- | --- | --- | --- | --- |
| GATE-00 | Go programme v4.8.1 | P00 | Matrice CDC→roadmap complète; backlog priorisé; risques connus; arbitrages actés. | Programme autorisé uniquement si les décisions v4.8.1 sont tracées. |
| GATE-01 | Go Foundation Alpha | P01-P02 | CI verte; édition model testé; API baseline; services cibles documentés. | Autorise démarrage installateurs et runtime. |
| GATE-02 | Go Installer Alpha | P03-P06 | install.ini validé; dépendances installées; PGDATA /data/openinfra; openinfra.service; failover DB démontré. | Autorise MVP Lite/Pro. |
| GATE-03 | Go Lite MVP | P07-P11 | Limits Lite respectées; all-in-one opérationnel; UI/API/CLI ITRM/DCIM/IPAM. | Autorise pilote Lite. |
| GATE-04 | Go Pro MVP | P07-P13 | Backend/web séparés; LDAP/IPA; RBAC groupes; connecteurs ITSM externes; quotas Pro. | Autorise pilote Pro. |
| GATE-05 | Go Enterprise Foundation | P14-P17 | Agents, multisite, synchronisation quasi temps réel, cluster frontend/backend, DR testé. | Autorise pilote Entreprise. |
| GATE-06 | Go RC | P16-P18 | Modules avancés; sécurité; performance; docs; migrations et rollback validés. | Autorise release candidate. |
| GATE-07 | Go GA | P18 | Benchmarks; chaos; PITR; failover; sécurité; packaging; support; runbooks validés. | Autorise GA Enterprise Scale. |

---

## 8. Plan spécifique des éditions

| Edition | Release cible | Architecture | Services | Discovery | PostgreSQL | Limites |
| --- | --- | --- | --- | --- | --- | --- |
| Lite | REL-03 | All-in-one monolithique | openinfra.service | Discovery locale uniquement | PostgreSQL low, PGDATA 2GB | Equipements 200; subnets/VLAN 20; IP/DNS 200; utilisateurs 5 |
| Pro | REL-04 | Backend/web séparés | openinfra.service + openinfra-web.service | Discovery centralisée sans agent proxy | PostgreSQL medium, PGDATA 100GB, cluster DB optionnel | Equipements 5000; subnets/VLAN 100; IP/DNS 5000; utilisateurs 100 |
| Entreprise | REL-05 | Backend/web clusterisés + agents | openinfra.service + openinfra-web.service + openinfra-agent.service | Discovery distribuée via agents région/site/VRF | PostgreSQL large, PGDATA 1TB, >10Md entrées, quasi-sync | Illimité selon sizing et licence |

---

## 9. Plan installateurs

| Path | Edition | Scope | Service | Responsabilités |
| --- | --- | --- | --- | --- |
| installers/setup/lite | Lite | all-in-one | openinfra.service | Installe dépendances, PGDATA 2GB, migrations, UI intégrée ou servie par backend selon packaging. |
| installers/setup/pro/server | Pro | server/backend | openinfra.service | Installe backend, PostgreSQL géré, PGDATA 100GB, migrations et cluster DB optionnel. |
| installers/setup/pro/web | Pro | web/frontend | openinfra-web.service | Installe React/Bootstrap 5, endpoint API backend, aucun accès DB. |
| installers/setup/enterprise/server | Entreprise | server/backend | openinfra.service | Installe backend, PostgreSQL large, PGDATA 1TB, cluster, quasi-sync et migrations. |
| installers/setup/enterprise/web | Entreprise | web/frontend | openinfra-web.service | Installe frontend clusterisable, health checks et reverse proxy. |
| installers/setup/enterprise/agent | Entreprise | agent/discovery | openinfra-agent.service | Installe collecteur discovery régional, mTLS, endpoint central, aucune connexion DB. |

---

## 10. Plan stockage PostgreSQL / LVM / PGDATA

| Domaine | Edition | VG | LV | Mountpoint ou lien | Taille | Owner | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Applicatif | Tous scopes applicatifs incluant enterprise/agent | rootvg | openinfra_lv | /opt/openinfra/ | 2GB défaut | openinfra:openinfra | Configuration, binaires, logs applicatifs contrôlés; agent sans PostgreSQL ni PGDATA. |
| PostgreSQL data | Lite | datavg | openinfradata_lv | /data/openinfra/ | 2GB | Compte système gestionnaire PostgreSQL | PGDATA réel sous /data/openinfra/. |
| PostgreSQL data | Pro | datavg | openinfradata_lv | /data/openinfra/ | 100GB | Compte système gestionnaire PostgreSQL | PGDATA réel sous /data/openinfra/. |
| PostgreSQL data | Entreprise | datavg | openinfradata_lv | /data/openinfra/ | 1TB | Compte système gestionnaire PostgreSQL | PGDATA réel sous /data/openinfra/. |
| Symlink | Toutes | N/A | N/A | /opt/openinfra/data -> /data/openinfra/ | N/A | Compte système gestionnaire PostgreSQL | Symlink créé/validé par installateur. |

---

## 11. Validations bloquantes nouvelles par rapport à la v1

- La CI doit valider l’absence de `ancien service backend obsolète` dans les sources, paquets et livrables.
- Chaque dossier d’installation doit contenir `config/install.ini`.
- Les scripts d’installation doivent être hors `src`.
- Les dépendances OS doivent être détectées, installées ou refusées explicitement.
- Le backend doit appliquer toutes les migrations avant le démarrage final.
- Le frontend et l’agent ne doivent jamais appliquer de migration.
- `PGDATA` doit pointer sur `/data/openinfra/` ou le chemin réel dérivé sous ce mountpoint selon le packaging PostgreSQL.
- Le symlink `/opt/openinfra/data -> /data/openinfra/` doit être validé.
- Le compte système gestionnaire PostgreSQL ne doit pas être supposé par nom ; il doit être résolu ou créé par l’installateur.
- Pro et Entreprise doivent supporter LDAP/IPA et RBAC par groupes.
- Pro et Entreprise peuvent se connecter aux ITSM connus via connecteurs externes, sans ticketing OpenInfra intégré.
- En cluster, la réplication PostgreSQL doit être configurée automatiquement en mode quasi temps réel par défaut.
- Les éditions doivent être testées comme artefacts distincts à chaque release.

---

## 12. Synthèse d’impact sur la roadmap v1

La v1 plaçait l’essentiel de l’industrialisation en fin de programme. La v2 avance ces sujets en amont, car ils conditionnent les artefacts livrables : éditions, installateurs, services systemd, stockage, PGDATA, LDAP/IPA, cluster et multisite doivent être traités avant les pilotes Lite/Pro/Entreprise.

Le résultat est une roadmap plus exigeante au début, mais beaucoup plus réaliste pour une solution enterprise : les choix de packaging et d’exploitation ne sont plus ajoutés après les modules fonctionnels, ils structurent les livraisons dès Foundation Alpha.

## Incrément réalisé v0.29.10 — P06

Le jalon P06 est amorcé avant reprise Discovery par le plan installateur PostgreSQL HA/PITR : configuration streaming native, WAL archiving, répertoires PITR/backups, migration de registre HA, commande `database ha-plan` et failover contrôlé opérateur.

### Avancement v0.29.14 — P09 ITRM Quality & Certification

P09 démarre par la capacité de qualité et certification ITRM : évaluation individuelle des objets, synthèse tenant, score de complétude/fraîcheur/autorité/confiance, intégration des règles de source autoritative, RBAC `itrm.quality.read`, audit `itrm.quality.*`, API `/api/v1/itrm/quality/*`, CLI `openinfra itrm quality-*` et exposition dans le dashboard web.

### Avancement v0.29.15 — P08 Bootstrap 5 Dashboard Theme

P08 est consolidé par l'intégration du thème Bootstrap 5 Dashboard dans `openinfra-web`. Le portail web dispose désormais d'un header principal unique, d'une d'une sidebar Dashboard et d'une zone d'exécution API alignée sur les domaines CLI/API : Dashboard, ITRM, IPAM, DCIM, Discovery, Sécurité/RBAC, Audit et Runtime.

Le rendu reste dans le domaine présentation/rendering, les assets Bootstrap sont servis localement, et le navigateur ne reçoit aucun secret ni accès direct aux composants backend ou PostgreSQL.

### Avancement v0.29.16 — P08 Dashboard pilotable et trust web-backend

- Les formulaires `openinfra-web` sont typés par domaine et exposent les variables métier attendues par l'API/CLI.
- Le panneau latéral devient le menu principal : Dashboard direct, autres composantes en accordéons avec transition `fade`.
- Le navigateur ne saisit ni ne relaie de token API technique ; `openinfra-web` établit le trust server-side avec le backend.
- Les références DSN/credentials PostgreSQL du service web sont déclarées dans `[web_database]` et matérialisées dans le runtime serveur.


### Avancement v0.29.19 — P08 dashboard accueil statistiques composants

P08 est renforcé par une vue d’accueil réellement exploitable : chaque composant métier OpenInfra affiche ses métriques opérationnelles et un camembert lecture/mutation. Cette restitution reste API-only, déterministe et sans exposition de secrets côté navigateur.

### Avancement v0.29.19 — renommage transversal ITRM

Le composant inventaire public est désormais exposé sous le nom IT Ressources Management (ITRM). Les contrats primaires deviennent `openinfra itrm *`, `/api/v1/itrm/*`, les rôles `itrm:*` et les permissions `itrm.*`. Les anciens alias `ri` et `sot` restent disponibles pour préserver la compatibilité ascendante.

### Avancement v0.29.19 — alertes dashboard contextuelles

Le dashboard d’accueil ne présente plus l’alerte succès permanente `Backend prêt`. L’état backend reste visible dans la sidebar runtime ; les alertes dans la zone principale sont réservées aux erreurs et aux soumissions de formulaire réussies.
### Avancement v0.29.20 — formulaires web réellement fonctionnels et camemberts responsive

- Les formulaires openinfra-web sont alignés sur les routes backend `/api/v1/*` et sur les champs obligatoires des commandes applicatives.
- Le proxy web conserve le modèle BFF : aucun token opérateur dans le navigateur, injection bearer backend optionnelle uniquement côté serveur.
- Les camemberts de l’accueil sont doublés et responsives via `clamp()` avec règle mobile dédiée.


### Avancement v0.29.22 — titlebar dashboard aérée

- La titlebar `Dashboard de pilotage OpenInfra` gagne un espacement vertical responsive autour du titre et du sous-titre.
- Les sources React et les assets runtime CSS sont alignés afin que le rendu servi par `openinfra-web` corresponde au rendu de développement.
- Les validateurs frontend et tests d’intégration verrouillent la règle `padding-block: clamp(1rem, 2vw, 1.75rem)`.
### Avancement v0.29.22 — statut BFF web sans secret

- `openinfra-web` expose `/status` pour diagnostiquer les formulaires protégés et le trust server-side sans fuite de secret.
- Le proxy assainit les erreurs backend brutes `missing bearer token` avant retour navigateur.
- La roadmap P08 ajoute `TST-P08-WEB-BFF-STATUS`.


### Avancement v0.29.23 — P09 historique ITRM as-of et audit objet

- `openinfra itrm get-object-as-of` et `/api/v1/itrm/object-as-of` restituent un objet ITRM à une date donnée à partir des snapshots existants.
- `openinfra itrm list-relations --as-of` et le paramètre HTTP `as_of` filtrent les relations valides à une date donnée.
- `openinfra itrm list-object-audit`, `/api/v1/itrm/object-audit` et le filtre audit `target_id` rendent l’audit consultable par objet.
- Les formulaires web ITRM exposent ces opérations via le BFF sans token navigateur.
- La roadmap P09 ajoute `TST-P09-ITRM-AS-OF-AUDIT` et aligne `REQ-00758`.

### Avancement v0.29.24 — P09 réconciliation gouvernée ITRM

- `openinfra itrm reconcile-object` et `/api/v1/itrm/reconcile-object` produisent un plan de réconciliation déterministe avec chemins modifiés, conflits, règles obsolètes, version planifiée et attributs résultants.
- L’application est explicite via `--apply` ou `apply=true` et ne s’exécute que lorsque les règles de source autoritative acceptent la mise à jour.
- Les plans refusés et applications acceptées sont auditables par objet via `itrm.reconciliation.plan` et `itrm.reconciliation.apply`.
- La roadmap P09 ajoute `TST-P09-ITRM-RECONCILIATION` et aligne `REQ-00759`.

### Avancement v0.29.25 — P09 taxonomie ITRM catégories / types DC

- OpenInfra expose un catalogue ITRM structuré par catégories datacenter et types rattachés : serveurs, postes, périphériques, réseau, stockage, énergie, racks/facility, refroidissement, sécurité, télécom, cloud/virtualisation, logiciels/services, câblage et mobile/IoT.
- `openinfra itrm resource-taxonomy` et `/api/v1/itrm/resource-taxonomy` publient la taxonomie consommable par clients, intégrations et BFF web.
- Les créations, modifications et réconciliations ITRM acceptent `resource_category` et `resource_type`, valident que le type appartient à la catégorie, et enrichissent les attributs historisés.
- Le dashboard web filtre automatiquement le champ type de ressource selon la catégorie choisie ; le mécanisme de listes dépendantes est générique pour les formulaires analogues.
- La roadmap P09 ajoute `TST-P09-ITRM-RESOURCE-TAXONOMY` et aligne `REQ-00760`, `REQ-00761` et `REQ-00762`.
