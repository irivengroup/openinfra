## v0.29.50 — Administration éditions et quotas API/UI

- Ajout `REQ-00793` : le portail openinfra-web et l’API HTTP exposent en lecture les politiques d’édition, les décisions de capacité et les décisions de quota runtime.
- Les routes `/api/v1/editions/policies`, `/api/v1/editions/feature-check` et `/api/v1/editions/quota-check` sont publiées par discovery/OpenAPI et protégées par `security:admin` lorsque l’authentification est active.
- Le composant Sécurité/RBAC/Audit du portail expose les trois opérations sans dupliquer les règles métier côté navigateur.

- Ajout `REQ-00792` pour garantir le badge édition fuchsia très foncé, tendant vers prune chaud/bruné sans rendu marron, avec conservation du gabarit Bootstrap `badge`.
- Ajout `REQ-00791` pour garantir le badge édition fuchsia effectif sans héritage bleu `text-bg-primary`, tout en conservant le gabarit Bootstrap `badge`.
- Ajout `REQ-00790` pour déplacer le badge édition dans le header principal, retirer l’indication visible du mode d’authentification et appliquer un fond fuchsia dégradé sans modifier le gabarit.
- Ajout de REQ-00789 et TST-WEB-090 pour verrouiller le skip-link, les états ARIA, la recherche globale annonçable et le focus contenu principal.
## 0.29.45 - 2026-07-07

- Ajout de REQ-00787 et TST-WEB-088 pour l’exposition ITAM dans Dashboard/header/sidebar/recherche avec icône pleine dédiée.
- Ajout de REQ-00788 et TST-WEB-089 pour les boutons Swagger/ReDoc réduits de moitié.

- Ajout `REQ-00786` et `TST-WEB-087` pour le panneau latéral accordéon sans masquage et scroll interne stable.
## 0.29.44 - 2026-07-07

- Ajout `REQ-00785` et `TST-ITAM-002` pour le rapport de couverture garantie/support ITAM par actif.

- Mise à jour `REQ-00783` / `TST-WEB-086` : le header fixe porte une ombre plus prononcée que les blocs de contenu et le scroll démarre sous le bandeau pleine largeur.
- Ajout `REQ-00783` et `TST-WEB-086` pour le header fixe openinfra-web avec scroll du contenu sous-jacent.
## 0.29.41 - 2026-07-07

- Mise à jour REQ-00782 / TST-WEB-085 : l’icône ITRM de référentiel/référence est désormais pleine et opaque comme les autres SVG de composants.

## 0.29.41 - 2026-07-07

- Ajout REQ-00779 / TST-WEB-082 : recherche globale sans exposition d’erreur technique et respect du préfixe `apiBaseUrl`.
- Mise à jour REQ-00780 / TST-WEB-083 : restauration de la palette initiale action/vert des camemberts Dashboard avec validations frontend anti-régression.

## 0.29.38

- Ajout `REQ-00778` et `TST-WEB-081` pour la recherche globale backend groupée par composant.
- Mise à jour OpenAPI avec `GET /api/v1/search/global`.

## 0.29.37

- Ajout `REQ-00777` et `TST-WEB-080` pour la double barre de header, la recherche globale centrée, la loupe SVG, les résultats groupés par composant et les actions Swagger/ReDoc.
- Mise à jour `REQ-00776` et `TST-WEB-079` : les textes permanents hérités des anciennes alertes informatives sont retirés du rendu UI.

## 0.29.36

- Ajout `REQ-00776` et `TST-WEB-079` : suppression des alertes informatives affichées par défaut sur les pages composant openinfra-web.
- Les textes permanents hérités des anciennes alertes informatives sont retirés du rendu UI à partir de la v0.29.37.
- Les alertes visibles restent réservées aux problèmes caractérisés et aux soumissions de formulaire réussies.

- Ajout REQ-00773 pour la vérification locale CLI des fichiers d’enrôlement proxy Discovery Enterprise.
- Ajout TST-DISCOVERY-076 pour valider édition Enterprise, schéma, résultats backend, permissions 0600 et mode --allow-partial.
- Ajout REQ-00771 pour l’enrôlement CLI direct des proxies Discovery Enterprise auprès des backends.
- Ajout TST-DISCOVERY-074 pour valider édition Enterprise, refus Lite/Pro, API dédiée et CLI local/distant.
- Ajout REQ-00770 pour la topologie opérationnelle IPAM consolidée.
- Ajout TST-IPAM-073 pour valider API, CLI, dashboard, OpenAPI et intégrité du graphe IPAM.
## Delta v0.29.31 — IPAM Enterprise++ dashboard

- Ajout REQ-00769 pour l'exposition des opérations IPAM Enterprise++ dans le dashboard.
- Ajout TST-IPAM-072 pour valider la parité frontend, les routes backend réelles et la découverte API IPAM.
- Les valeurs et invariants IPAM restent gérés par les services backend ; le navigateur ne duplique pas les règles métier.

## Delta v0.29.30 — jumeau numérique DCIM initial

- Ajout de `REQ-00768` et `TST-DCIM-071` : jumeau numérique DCIM initial exposé par API, CLI et dashboard via `GET /api/v1/dcim/digital-twin`, consolidant plan salle, racks, équipements, panneaux, ports, câbles et capacité énergie/refroidissement.
- Le document `dcim_digital_twin` agrège `summary`, `room_plan`, `racks`, `floor_equipment`, `cables` et `integrity` sans créer de stockage parallèle.
- Les règles métier restent portées par les services DCIM existants : occupation rack, câblage, capacité énergie/refroidissement et intégrité.

## Delta v0.29.29 — énergie/refroidissement DCIM dans le dashboard

- Ajout de `REQ-00766` et `TST-DCIM-069` : opérations énergie/refroidissement DCIM exposées dans le dashboard via les contrats existants `POST /api/v1/dcim/power-devices`, `POST /api/v1/dcim/power-circuits`, `POST /api/v1/dcim/cooling-zones`, `POST /api/v1/dcim/power-reservations` et `GET /api/v1/dcim/energy-cooling-capacity`.
- Ajout des champs opérateur chaîne électrique A/B, capacité watts, derating, calibre disjoncteur, rôle de zone, températures soufflage/retour et puissance attendue.
- Publication explicite des routes énergie/refroidissement dans le document de découverte API et OpenAPI afin de verrouiller la parité API/UI.

## Delta v0.29.28 — câblage DCIM dans le dashboard

- Ajout de `REQ-00765` et `TST-DCIM-068` : opérations de câblage DCIM exposées dans le dashboard via les contrats existants `POST /api/v1/dcim/patch-panels`, `POST /api/v1/dcim/ports` et `POST /api/v1/dcim/cables`.
- Ajout des champs opérateur endpoints A/B, connecteur, média, statut, chemin câble, longueur et libellé pour documenter le chemin de bout en bout.
- Conservation des validations métier côté service DCIM : compatibilité connecteur/média, existence des ports, occupation des endpoints et chemin obligatoire restent contrôlés par le backend.

## Delta v0.29.27 — élévation rack DCIM dans le dashboard

- Ajout de `REQ-00764` et `TST-DCIM-067` : élévation rack DCIM exposée dans le dashboard via le contrat existant `GET /api/v1/dcim/rack-elevation`.
- Ajout du choix `Format rendu` sur `Plan de salle` et `Élévation rack` pour les rendus `json`, `svg` et `html`.
- Conservation du calcul d’occupation rack côté service de visualisation DCIM ; le navigateur ne porte aucune logique métier d’occupation U.

## Delta v0.29.26 — localisation équipement DCIM API/UI

- Ajout de `REQ-00763` et `TST-DCIM-066` : localisation/relocalisation équipement DCIM par API HTTP et formulaire web.
- Alignement OpenAPI, discovery API, dashboard et matrices de traçabilité sur `POST /api/v1/dcim/locations`.
- Conservation des invariants existants : ligne, colonne, salle, rack, face, position U, hauteur U et coordonnées optionnelles sont validés par le service applicatif DCIM.

## Delta v0.29.25 — taxonomie ITRM catégories / types

- Ajout du catalogue ITRM catégories/types couvrant les ressources datacenter.
- Ajout du filtrage dynamique Catégorie -> Type de ressource dans le dashboard.
- Ajout de la validation backend des couples catégorie/type et du mécanisme générique optionsByField/optionsMap.

## v4.8.1 / OpenInfra 0.29.24

- Ajout de `REQ-00759` et `TST-ITRM-062` : réconciliation gouvernée ITRM avec dry-run déterministe, apply contrôlé, conflits non autoritatifs non appliqués et audit objet.

## v4.8.1 / OpenInfra 0.29.23

- Ajout de `REQ-00758` et `TST-ITRM-061` : restitution historique `as-of` ITRM, relations filtrées temporellement et audit par objet.
- Mise à jour API, CLI, OpenAPI, dashboard web et repositories JSON/PostgreSQL sans migration destructive des snapshots existants.

## v4.8.1 / OpenInfra 0.29.22

- Ajout de `REQ-00755` et `TST-WEB-058` : aération verticale responsive de la titlebar du dashboard d’accueil `openinfra-web`.
- Ajout de `REQ-00756` et `TST-WEB-059` : fallback bearer server-side depuis `OPENINFRA_BOOTSTRAP_TOKEN` lorsque le token web dédié est vide, sans exposition d’erreur brute `missing bearer token` au navigateur.

## v4.8.1 / OpenInfra 0.29.20

- Ajout des exigences REQ-00752 à REQ-00754 pour formulaires web réellement fonctionnels, injection bearer backend server-side et camemberts responsive doublés.
- Ajout des tests TST-WEB-055 à TST-WEB-057.

## v4.8.1 / OpenInfra 0.29.19

- Ajout `REQ-00750` et `TST-WEB-053` : renommage transversal du composant public en `IT Ressources Management/ITRM`, contrats primaires `itrm` et alias `ri`/`sot` dépréciés mais compatibles.
- Ajout `REQ-00751` et `TST-WEB-054` : suppression de l’alerte succès permanente `Backend prêt` sur l’accueil ; alertes visibles réservées aux erreurs et soumissions de formulaire.
- Ajout `REQ-00749` et `TST-WEB-052` : dashboard d’accueil `openinfra-web` avec statistiques et camemberts par composant métier.

## v4.8.1 - Correction des entrées existantes stockage PostgreSQL

- Mise à jour du mountpoint PostgreSQL backend : `/data/openinfra/`.
- Mise à jour du symlink : `/opt/openinfra/data -> /data/openinfra/`.
- Initialisation PostgreSQL sous `PGDATA=/data/openinfra/` ou chemin réel résolu sous ce mountpoint selon le packaging.
- Tailles par édition : Lite `2GB`, Pro `100GB`, Entreprise `1TB`.
- Clarification : `pgsql user` désigne le compte système gestionnaire PostgreSQL résolu/créé par l installateur, pas un nom Unix imposé.
- Aucun nouveau volume ni addendum ajouté : les entrées V29/V30, matrices et templates existants ont été corrigés.

# CHANGELOG — OpenInfra CDC/SFG/STG v4.8.0

## v4.8.0 — Configuration installateur `./config/install.ini`

### Ajouté

- Chaque dossier d'installation possède désormais son propre fichier `./config/install.ini`.
- L'opérateur ajuste les paramètres d'installation dans ce fichier selon les caractéristiques du serveur.
- Ajout des sections normalisées : `edition`, `scope`, `node`, `network`, `system_user`, `storage_application`, `storage_postgresql`, `database`, `cluster`, `auth`, `frontend`, `agent`, `installer`, `security`, `observability`.
- Ajout des règles de validation stricte : schéma, types, valeurs autorisées, cohérence édition/scope, cohérence LVM, cohérence HA, cohérence migrations.
- Ajout des templates `install.ini` pour Lite all-in-one, Pro server/web et Entreprise server/web/agent.
- Ajout des matrices `Matrice-install-ini-*` et du volume V30.
- Ajout d'une ADR dédiée au contrat `install.ini`.

### Corrigé

- Clarification du périmètre : la configuration d'installation est hors `src/`, dans `installers/<edition>/<scope>/config/install.ini`.
- Les scripts ne doivent pas être modifiés par l'opérateur ; seules les valeurs de `install.ini` sont ajustées.
- Les secrets ne doivent pas être stockés en clair dans `install.ini`; le fichier contient uniquement des références vers Vault, SOPS, fichiers protégés ou variables d'environnement.


## 4.5.0 — Service backend canonique

### Modifié

- Le backend, PostgreSQL géré et les migrations backend sont portés par `openinfra.service`.
- Le scope `server` reste un scope d'installation, mais ne crée pas de service systemd backend distinct.
- Les matrices systemd et installateurs sont alignées sur `openinfra.service` pour Lite, Pro et Entreprise.
- Les scripts de validation documentaire bloquent toute réintroduction d'un service backend dupliqué dans les matrices opérationnelles.

### Conservé

- `openinfra-web.service` pour le frontend React + Bootstrap 5.
- `openinfra-agent.service` pour les collecteurs d'auto discovery.
- Application exclusive des migrations par le scope backend/server.
- Aucun ITSM intégré ; connecteurs ITSM externes uniquement pour Pro et Entreprise.


## 4.4.0 — Installation autonome cluster, dépendances et migrations backend

### Ajouté

- Volume V26 dédié à l'installation autonome.
- Installateurs obligatoirement situés hors `src/` dans `installers/`.
- Installation automatique des dépendances par édition et par scope.
- Bootstrap cluster autonome à partir de FQDN, IP, masque, VIP, passerelle et DNS.
- Backend installer responsable de toutes les migrations backend.
- Interdiction des migrations depuis frontend et agents.
- Matrices installateurs, dépendances, migrations, ports et installation autonome.
- ADR-0011 et ADR-0012.
- Tests et exigences v4.4.

### Conservé

- Aucun ITSM intégré.
- Connecteurs ITSM externes uniquement pour Pro et Entreprise.
- Services systemd invariants entre éditions.
- `openinfra.service`, `openinfra-web.service`, `openinfra-agent.service`.
- Frontend React + Bootstrap 5 consommant exclusivement l'API backend.

# CHANGELOG

## 4.0.0 — Extension fonctionnelle enterprise

### Ajouté

- Volumes V13 à V24 : gouvernance de la donnée, qualité, flux réseau, certificats/PKI, conformité réseau, FinOps, Field Operations, simulation/migration, GreenOps, SBOM/vulnérabilités, Kubernetes avancé et policy engine.
- Vues fonctionnelles dédiées dans `02-Fonctionnel/` pour chaque nouveau volume.
- Exigences REQ supplémentaires numérotées et vérifiables.
- Cas d’usage UC supplémentaires.
- Tests TST-REQ supplémentaires.
- Entités de dictionnaire supplémentaires.
- Risques et conformité supplémentaires.
- Addendum CCTP/CdCF v4.

### Maintenu

- Exclusion stricte d’un ITSM intégré.
- PostgreSQL Cluster comme persistance transactionnelle principale.
- Exigences de partitionnement, hot/warm/cold, concurrence, résilience, sécurité et observabilité.

---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# CHANGELOG

## 3.0.0 — 2026-07-02

### Changements majeurs

- Transformation du CDC v2 en dossier SFG/STG versionné.
- Ajout d’une structure CCTP/CdCF prête pour consultation intégrateurs.
- Ajout de 12 volumes d’architecture et de spécifications.
- Ajout d’exigences numérotées `REQ-xxxxx` avec priorités N1/N2.
- Ajout des cas d’usage `UC-xxxx` et tests `TST-xxxx`.
- Ajout d’une matrice de traçabilité exigences/cas d’usage/tests.
- Ajout du modèle de données logique avec plus de 250 entités.
- Renforcement PostgreSQL : cluster HA, partitionnement, hot/warm/cold, PITR, réplicas, observabilité.
- Renforcement performance/concurrence : p95/p99, API bornées, import/export asynchrones, idempotence.
- Ajout des exigences IA et automatisation : RAG, suggestions, anomalies, gouvernance humaine.
- Ajout d’ADR/RFC et diagrammes C4/ERD/architecture.

### Compatibilité

Cette version conserve le périmètre v2 : IT Ressources Management, DCIM, ITAM, Discovery, Dependency Mapping, IPAM avancé et exclusion ITSM intégrée. Elle renforce la granularité documentaire et contractuelle.


## 4.3.0 - Alignement enterprise, éditions, ITSM externe et support constructeur

- Consolidation des éditions Lite, Pro et Entreprise dans le référentiel principal.
- Ajout du volume V25 Editions, Packaging et Alignement Entreprise.
- Ajout des matrices capacités, services systemd, intégrations ITSM et alignement enterprise.
- Règle systemd invariante : aucun nom de service ne dépend de l'édition.
- Backend canonique : openinfra.service.
- Agent discovery canonique : openinfra-agent.service.
- Frontend React + Bootstrap 5 API-only : openinfra-web.service.
- Connecteurs ITSM externes pour Pro et Entreprise uniquement, sans module ITSM intégré.
- Garantie constructeur et support constructeur obligatoires pour chaque équipement physique.
- Support tiers séparé et non destructif.
- Ajout de 20 exigences REQ-00489 à REQ-00508.
- Ajout de 20 tests TST-V43-001 à TST-V43-020.
- Ajout de 8 cas d'usage UC-V43-0001 à UC-V43-0008.
- Ajout de 6 risques RISK-0035 à RISK-0040.


## v4.6.0 — Authentification LDAP/IPA, RBAC groupes, compte système et FS LVM dédié

### Ajouté

- Authentification LDAP/LDAPS et FreeIPA/IPA obligatoire pour les éditions Pro et Entreprise.
- Gestion RBAC par groupes utilisateurs LDAP/IPA.
- Mapping groupes externes vers rôles applicatifs OpenInfra.
- Compte système canonique `openinfra` créé par root à l'installation pour toutes les éditions.
- Filesystem LVM dédié monté par défaut sur `/opt/openinfra/`.
- Valeurs LVM par défaut : `vgname=rootvg`, `lvname=openinfra_lv`, `lv_size=2GB`.
- Matrices de conformité pour authentification, RBAC, utilisateur système, sudoers contrôlés et LVM.
- Validateur documentaire `validate_auth_lvm.py`.

### Modifié

- Les installateurs intègrent la création du compte système avant installation applicative.
- Les installateurs intègrent la préparation du filesystem LVM avant déploiement de fichiers.
- Les installateurs Pro/Entreprise intègrent la configuration LDAP/IPA sans imposer d'expertise annuaire à l'opérateur.

### Sécurité

- Le compte `openinfra` ne doit pas disposer d'un shell interactif.
- Les droits élevés sont limités aux commandes et wrappers OpenInfra nécessaires.
- Les secrets LDAP/IPA sont stockés via le mécanisme de secret retenu par l'édition et jamais en clair dans les logs.

## v4.7.0 — Stockage PostgreSQL dédié, synchronisation quasi temps réel et multisite

### Ajouté
- Séparation stricte entre le filesystem applicatif `/opt/openinfra/` et les données PostgreSQL backend.
- Définition du LV PostgreSQL par défaut : `vgname=datavg`, `lvname=openinfradata_lv`, `mountpoint=/data/openinfra/`, `lv_size=Lite 2GB / Pro 100GB / Entreprise 1TB`.
- Création du symlink `/opt/openinfra/data -> /data/openinfra/` avec propriétaire logique PostgreSQL résolu par l'installateur.
- Clarification : le terme `pgsql user` désigne le compte système gestionnaire du service PostgreSQL, il ne fixe pas un nom Unix imposé.
- Installation cluster backend avec réplication et synchronisation automatique quasi temps réel.
- Support multisite pour les éditions Pro et Entreprise.
- Correction des recommandations incohérentes entre stockage applicatif, stockage PostgreSQL, ownership, symlink, migrations backend et cluster HA.

### Modifié
- Le filesystem `/opt/openinfra/` reste propriétaire `openinfra:openinfra` et ne doit plus être utilisé comme répertoire physique des données PostgreSQL.
- Les données PostgreSQL backend doivent être sous le contrôle exclusif du compte système PostgreSQL résolu par l'installateur.
- L'édition Pro supporte le multisite référentiel et opérationnel centralisé ; l'édition Entreprise supporte en plus le multisite distribué avec agents régionaux et clustering d'agents.

### Conservé
- Pas d'ITSM intégré.
- Services systemd canoniques : `openinfra.service`, `openinfra-web.service`, `openinfra-agent.service`.
- Backend seul autorisé à appliquer les migrations.
- v0.29.33 : ajout de la charte graphique premium openinfra-web, appliquée par CSS Bootstrap 5 compatible sans modification de structure ni import d’asset tiers.
- Ajout REQ-00775 pour l’allègement des ombres de contenu openinfra-web sans modification du header ni du menu latéral.
