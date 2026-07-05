---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# Discovery

## Objectif

La découverte couvre SNMP, SSH, WinRM/WMI, VMware, Proxmox, Hyper-V, Kubernetes, Cloud, LLDP/CDP, NetFlow/sFlow/IPFIX et réconciliation. Le terme agent désigne exclusivement un proxy collector OpenInfra Enterprise, similaire à une capsule Satellite, installé sur un serveur contrôlé par OpenInfra et jamais sur les équipements découverts.

## Capacités obligatoires

- Création, consultation, modification contrôlée et historisation des objets.
- Recherche par identifiants, tags, relations, tenant, site et état.
- Import/export asynchrone lorsque le volume dépasse les seuils.
- Audit systématique des actions critiques.
- API REST et GraphQL si la capacité est consommable par automatisation.
- RBAC/ABAC tenant-aware.
- Détection et gestion des conflits de données.
- Tests unitaires, intégration, performance et sécurité selon criticité.

## Sémantique agent/proxy collector

- `agent` = proxy collector OpenInfra Enterprise uniquement.
- Les agents sont autorisés seulement en édition Entreprise, en topologie étoile vers les backends servers.
- Lite et Pro n'utilisent pas d'agents/proxy distribués : les backends servers exécutent eux-mêmes la collecte autorisée.
- Un agent ne détient aucun RI local, n'écrit jamais dans PostgreSQL et ne contourne jamais l'API backend.
- Les échanges agent-proxy-backend imposent mTLS, enrôlement technique, scopes explicites, secrets par références sécurisées et audit complet.
- Agentless signifie aucun agent sur les cibles découvertes ; cela reste compatible avec des agents proxy Enterprise déployés comme collecteurs régionaux.

## Règles métier structurantes

1. La donnée déclarative validée reste prioritaire sur une découverte brute, sauf règle de réconciliation explicite.
2. Les suppressions critiques doivent être logiques ou précédées d’une preuve de non-impact.
3. Les objets liés ne doivent jamais être rendus orphelins sans événement de conflit ou règle de compensation.
4. Les imports doivent produire un rapport d’impact avant application.
5. Les modifications massives doivent être découpées en lots, auditables et annulables lorsque le domaine le permet.
6. Les données sensibles doivent être chiffrées, masquées et auditables.
7. Les recherches doivent être indexées et bornées.

## Exigences associées

### REQ-00008

La découverte doit être distribuée, bornée, planifiable, auditée, relançable et non bloquante pour l’API.

**Acceptation :** Un crash worker ne perd aucun job validé et l’API reste disponible.

### REQ-00094

Le périmètre SNMP du volume Discovery doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Acceptation :** Le dossier contient les règles de gestion SNMP, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.

### REQ-00095

Le domaine SNMP doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.

### REQ-00096

Le domaine SNMP doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.

### REQ-00097

Le périmètre SSH du volume Discovery doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Acceptation :** Le dossier contient les règles de gestion SSH, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.

### REQ-00098

Le domaine SSH doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.

### REQ-00099

Le domaine SSH doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.

### REQ-00100

Le périmètre VMware du volume Discovery doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Acceptation :** Le dossier contient les règles de gestion VMware, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.

### REQ-00101

Le domaine VMware doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.

### REQ-00102

Le domaine VMware doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Acceptation :** Le job est découpé en lots, relançable, journalisé et consultable par API.

### REQ-00103

Le périmètre Proxmox du volume Discovery doit être implémenté par une capacité documentée, exposée par API lorsque pertinent, sécurisée par RBAC et testée.

**Acceptation :** Le dossier contient les règles de gestion Proxmox, les critères d’acceptation et au moins un cas d’usage nominal et un cas d’erreur.

### REQ-00104

Le domaine Proxmox doit produire des événements d’audit structurés, corrélables et exploitables par l’observabilité.

**Acceptation :** Chaque opération critique génère un événement avec acteur, tenant, ressource, action, résultat et corrélation.



## Critères d’acceptation

La capacité est acceptée si les scénarios nominaux, erreurs, droits insuffisants, conflits et imports/exports sont validés par tests automatisés et si les journaux d’audit permettent de reconstituer les opérations.
