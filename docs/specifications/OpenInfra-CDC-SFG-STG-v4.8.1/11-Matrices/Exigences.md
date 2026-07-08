---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# Matrice des exigences — lecture humaine

Le fichier normatif est `Exigences.csv`. Ce document synthétise la volumétrie.

| Domaine | Libellé | Nombre |
| --- | --- | --- |
| AI | IA & Automatisation | 22 |
| API | API & Intégrations | 23 |
| DATA | Données & PostgreSQL | 14 |
| DCIM | Data Center Infrastructure Management | 28 |
| DEP | Dependency Mapping | 22 |
| DISC | Discovery distribué | 35 |
| IPAM | IP Address Management Enterprise++ | 49 |
| ITAM | IT Asset Management | 21 |
| OPS | Administration & exploitation | 35 |
| QA | Qualité & validation | 16 |
| SEC | Sécurité | 22 |
| RSOT | RSOT (Ressource Source of Truth) | 21 |
| WEB | Portail web OpenInfra | 7 |

Les exigences N1 sont obligatoires. Les exigences N2 structurent les releases suivantes. Les exigences N3 ne sont pas utilisées dans cette version pour éviter les options non cadrées.

- **REQ-00643** — Le filesystem applicatif `/opt/openinfra/` doit rester distinct du filesystem PostgreSQL backend.
- **REQ-00644** — Le mountpoint `/opt/openinfra/` doit être possédé par le compte et groupe `openinfra`.
- **REQ-00645** — Le mountpoint PostgreSQL backend par défaut doit être `/data/openinfra/`.
- **REQ-00646** — Le VG PostgreSQL backend par défaut doit être `datavg`.
- **REQ-00647** — Le LV PostgreSQL backend par défaut doit être `openinfradata_lv`.
- **REQ-00648** — La taille initiale du LV PostgreSQL backend dépend de l édition : Lite `2GB`, Pro `100GB`, Entreprise `1TB`.
- **REQ-00649** — Le propriétaire des données PostgreSQL doit être le compte système gestionnaire PostgreSQL résolu par l installateur.
- **REQ-00650** — Le terme `pgsql user` doit être traité comme rôle logique et non comme nom Unix imposé.
- **REQ-00651** — Le compte `openinfra` ne doit pas avoir d écriture directe arbitraire sur les fichiers internes PostgreSQL.
- **REQ-00652** — Le symlink `/opt/openinfra/data` doit pointer vers `/data/openinfra/`.
- **REQ-00653** — L ownership du symlink et de la cible doit suivre le compte PostgreSQL résolu lorsque le système le permet.
- **REQ-00654** — L installateur backend doit créer ou valider le LV PostgreSQL avant l initialisation PostgreSQL.
- **REQ-00655** — L installateur doit refuser une configuration où `/opt/openinfra/` et `/data/openinfra/` désignent le même filesystem physique non validé.
- **REQ-00656** — En cluster, l installateur doit configurer automatiquement la réplication PostgreSQL.
- **REQ-00657** — En cluster, la synchronisation doit être quasi temps réel par défaut.
- **REQ-00658** — Le mode quasi temps réel doit sélectionner au moins un standby local ou faible latence.
- **REQ-00659** — Le mode strict `local` doit être disponible pour Entreprise lorsque validé par architecture.
- **REQ-00660** — La réplication WAN inter-site ne doit pas être strictement synchrone par défaut.
- **REQ-00661** — Le replication lag doit être supervisé et alerté.
- **REQ-00662** — Le cluster doit tester la promotion d un standby et la reprise applicative.
- **REQ-00663** — La réintégration d un ancien primaire doit être automatisée ou guidée par runbook exécutable.
- **REQ-00664** — Le backend `openinfra.service` doit rester le seul service autorisé à orchestrer les migrations PostgreSQL.
- **REQ-00665** — Le frontend ne doit jamais accéder directement au symlink `/opt/openinfra/data` pour lire PostgreSQL.
- **REQ-00666** — L agent ne doit jamais accéder directement au symlink `/opt/openinfra/data` pour écrire PostgreSQL.
- **REQ-00667** — L édition Pro doit supporter la modélisation de plusieurs sites.
- **REQ-00668** — L édition Pro doit supporter le RBAC par site.
- **REQ-00669** — L édition Pro doit produire des rapports filtrés par site.
- **REQ-00670** — L édition Pro doit supporter la discovery directe multi-sites depuis backend central sans agents distribués obligatoires.
- **REQ-00671** — L édition Entreprise doit supporter le multisite distribué avec agents régionaux.
- **REQ-00672** — L édition Entreprise doit supporter le clustering des agents par site ou région.
- **REQ-00673** — L édition Entreprise doit router les jobs de discovery par site, région, VRF ou tenant.
- **REQ-00674** — L édition Entreprise doit fournir un statut de santé par site.
- **REQ-00675** — Le modèle de données doit représenter les sites, régions, latence réseau et rôles de réplication.
- **REQ-00676** — Les sauvegardes PostgreSQL doivent cibler `/data/openinfra/` et les WAL associés.
- **REQ-00677** — Les runbooks doivent distinguer extension du LV applicatif et extension du LV PostgreSQL.
- **REQ-00678** — La surveillance disque doit différencier `/opt/openinfra/` et `/data/openinfra/`.
- **REQ-00679** — L installateur doit produire un rapport post-installation listant comptes, mountpoints, symlink, modes de réplication et sites.
- **REQ-00680** — Le fichier de réponses ne doit jamais contenir de mot de passe PostgreSQL en clair.
- **REQ-00681** — Le dry-run doit afficher les opérations LVM, PostgreSQL, réplication et symlink avant exécution.
- **REQ-00682** — Le rollback doit retirer ou restaurer les changements de symlink sans supprimer les données PostgreSQL validées sauf demande explicite.
- **REQ-00683** — La création des réplicas doit utiliser des identités de réplication dédiées et non le superuser PostgreSQL applicatif.
- **REQ-00684** — La configuration quasi temps réel doit être versionnée dans l inventaire d installation.
- **REQ-00685** — La bascule cluster doit préserver la VIP et le routage des écritures vers le primaire actif.
- **REQ-00686** — Les lectures de reporting peuvent être routées vers un réplica dédié en Pro/Entreprise.
- **REQ-00687** — Les migrations backend doivent être exécutées une seule fois par cluster via verrou distribué.
- **REQ-00688** — Le support multisite doit être cohérent avec les connecteurs ITSM externes Pro/Entreprise.
- **REQ-00689** — Les permissions du symlink ne doivent pas permettre d escalade du compte applicatif vers le compte PostgreSQL.
- **REQ-00690** — La CI documentaire doit valider les matrices stockage, réplication, symlink et multisite v4.7.
- **REQ-00691** — Les tests de charge doivent couvrir la synchronisation quasi temps réel sous écriture concurrente.
- **REQ-00692** — Les tests chaos doivent couvrir perte du standby faible latence et reconfiguration contrôlée.
- **REQ-00693** — Les tests multisites doivent couvrir Pro centralisé et Entreprise distribué.
- **REQ-00694** — Les recommandations contradictoires des versions précédentes doivent être corrigées par la v4.7.

- **REQ-00750** — Le composant public anciennement nommé Ressources Inventory/RI doit être exposé partout sous le nom RSOT (Ressource Source of Truth)/RSOT, avec contrats primaires CLI/API/RBAC rsot et alias ri/sot compatibles.
- **REQ-00751** — Le dashboard d’accueil openinfra-web ne doit pas afficher d’alerte succès permanente de readiness ; les alertes visibles doivent être réservées aux erreurs et aux soumissions de formulaire.
- **REQ-00759** — RSOT doit exposer une réconciliation gouvernée permettant de planifier ou appliquer une mise à jour d’objet sans écrasement silencieux des attributs protégés.

- **REQ-00765** — Le dashboard DCIM doit exposer les opérations de câblage terrain patch panel, port et câble via les contrats backend existants.
- **REQ-00766** — Le dashboard DCIM doit exposer les opérations énergie/refroidissement power devices, circuits, zones, réservations et capacité rack via les contrats backend existants.
- **REQ-00767** — Les sélecteurs de catégories et types de ressources RSOT doivent afficher les libellés métier, conserver les valeurs normalisées internes et ne plus proposer les types obsolètes `physical-server` et `disk`.
- **REQ-00768** — OpenInfra doit exposer un jumeau numérique DCIM initial consolidant plan salle, racks, équipements, câblage et capacité énergie/refroidissement via API, CLI et dashboard.


### REQ-00773 — Vérification locale d’enrôlement proxy Enterprise

OpenInfra doit permettre la vérification locale en CLI des fichiers d’enrôlement proxy Discovery Enterprise générés par la commande distante. La vérification doit rester réservée à Enterprise, contrôler le schéma JSON, les résultats backend, les codes HTTP, les réponses JSON et les permissions de fichier afin qu’un opérateur puisse valider un proxy HA hors-ligne avant exploitation.

### REQ-00772 — Charte graphique premium openinfra-web

Le portail openinfra-web doit remplacer les couleurs basic Bootstrap par une charte visuelle premium inspirée cloud provider, appliquée via Bootstrap 5 et CSS produit, sans modifier la structure des pages ni importer d’asset tiers. Les assets CSS doivent couvrir header, sidebar, cartes, boutons, badges, formulaires, focus rings, résultats, camemberts et transitions.

### REQ-00775 — Ombres de contenu allégées openinfra-web

Les blocs de contenu du portail openinfra-web doivent utiliser une ombre portée plus légère que les effets de navigation, afin de rendre les pages plus fluides visuellement. La correction cible les titlebars, cartes, métriques, formulaires, synthèses et cartes composants ; le header principal et le menu latéral conservent leurs effets existants.

**Acceptation :** Les assets CSS exposent `--openinfra-content-shadow` et `--openinfra-content-shadow-hover`; les blocs de contenu utilisent ces variables dédiées ; les validateurs frontend et tests web empêchent un retour aux ombres trop fortes sur les cards et composants.
- **REQ-00776** — Les pages composant openinfra-web ne doivent pas afficher d’alerte informative ou succès par défaut ; les alertes visibles doivent être strictement contextuelles et les textes hérités des anciennes alertes permanentes doivent être retirés.
- **REQ-00777** — Le header openinfra-web doit être transformé en double barre avec recherche globale centrée, icône loupe SVG, résultats groupés par composant et actions Swagger/ReDoc intégrées au thème.


### REQ-00777 — Double barre header et recherche globale openinfra-web

Le header du portail doit exposer un second bandeau dédié à la recherche globale et à la documentation API. Le champ est centré par rapport à la page, occupe 50 % de l’espace disponible sur desktop, embarque une icône loupe SVG, et affiche les résultats groupés par composant. Les actions Swagger et ReDoc sont accessibles depuis ce bandeau sans réintroduire les anciens contrôles Login/Sign-up.

**Acceptation :** Les assets runtime contiennent `openinfra-global-toolbar`, `openinfra-global-search`, `renderGlobalSearchResults`, les styles de grille 50 %, les liens `/docs` et `/redoc`; les tests frontend vérifient le regroupement par composant et l’absence des anciens contrôles supprimés.

- **REQ-00778** — La recherche globale du header openinfra-web doit interroger le backend OpenInfra et retourner des résultats métiers groupés par composant RSOT, IPAM et Discovery.

### REQ-00778 — Recherche globale backend OpenInfra

La recherche globale ne doit pas se limiter au filtrage local des opérations visibles. Elle doit appeler un service backend transverse, agréger RSOT, IPAM et Discovery, appliquer les permissions existantes et retourner des résultats groupés par composant avec libellé, description, type, score et route API.

**Acceptation :** `GET /api/v1/search/global`, `openinfra search global` et le double header web consomment le même contrat applicatif ; les tests vérifient le groupement, les limites de requête et l’absence de fuite de données lorsqu’un composant n’est pas autorisé.
### REQ-00779 — Recherche globale tolérante aux erreurs réseau

**Exigence :** la recherche globale openinfra-web ne doit jamais exposer les erreurs réseau techniques brutes du navigateur et doit respecter le préfixe API public configuré.

**Acceptation :** l’appel est construit depuis `apiBaseUrl`, l’indisponibilité backend affiche un message générique et le fallback local groupé par composant reste disponible.

### REQ-00780 — Camemberts palette initiale lisible

**Exigence :** les camemberts de statistiques du Dashboard doivent utiliser la palette initiale lisible : bleu action pour les lectures et vert pour les mutations.

**Acceptation :** les assets CSS utilisent `--openinfra-action` et `--openinfra-green` pour le gradient et les légendes ; le duo bleu nuit/fuchsia n’est plus utilisé dans le rendu des camemberts.


### REQ-00781 — Swagger/ReDoc backend API réels

**Exigence :** les boutons Swagger et ReDoc du header `openinfra-web` doivent ouvrir la documentation réelle du backend API à partir des liens publiés par `/config.json`.

**Justification :** éviter qu’un portail web servi séparément du backend affiche des boutons visuellement présents mais non branchés sur `openinfra-api`.

**Acceptation :** `/config.json` publie `apiDocumentation`; les boutons utilisent `apiDocumentation.swaggerUrl` et `apiDocumentation.redocUrl`; `openinfra-web` proxyfie `/docs`, `/swagger`, `/redoc`, `/openapi.yaml` et `/api/v1/openapi.yaml` vers le backend API lorsque les liens sont same-origin.

### REQ-00782 — Icône RSOT référentiel/référence

**Exigence :** l’entrée RSOT du portail `openinfra-web` doit utiliser une icône représentant un référentiel ou une référence, et non une table générique.

**Acceptation :** les catalogues d’icônes React/runtime exposent `reference`; le module RSOT l’utilise dans le header, le menu latéral et les cartes de composant ; l’ancien mapping `table` est interdit pour RSOT.

### REQ-00783 — Header fixe openinfra-web

**Exigence :** le double header `openinfra-web` doit rester fixe en haut de viewport, porter une ombre plus prononcée que les blocs de contenu et laisser les pages scroller exactement sous ce bandeau sur toute la largeur lorsque le contenu dépasse la hauteur disponible.

**Acceptation :** les assets runtime exposent `openinfra-header-stack`, `--openinfra-header-shadow`, `--openinfra-fixed-header-height`, `scroll-padding-top`, un calcul dynamique d’offset et des règles CSS évitant le recouvrement du contenu principal et du menu latéral. L’ombre du header est supérieure aux ombres de contenu allégées.

## v0.29.59 — rollback conflict-aware des imports massifs

OpenInfra ajoute `REQ-00802` pour couvrir le rollback opérable des imports massifs appliqués : dry-run par défaut, restauration versionnée RSOT, mise en retrait sans suppression physique, détection de conflits et publication CLI/API/OpenAPI/discovery/portail web.

## v0.29.60 — guides migration données

OpenInfra ajoute `REQ-00803` pour couvrir les guides opérables de migration depuis Device42, NetBox, Nautobot, GLPI et CSV : template, étapes, contrôles, rollback, critères de succès et publication CLI/API/OpenAPI/discovery/portail web sans mutation RSOT.
