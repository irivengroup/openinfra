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
| RI | Ressources Inventory | 21 |

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
