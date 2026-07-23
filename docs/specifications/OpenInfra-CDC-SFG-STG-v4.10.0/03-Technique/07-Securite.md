---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# Sécurité technique

## Objectif

TLS, mTLS collectors, secrets Vault, chiffrement, RBAC/ABAC, audit, protection SSRF, injection, path traversal et durcissement.

## Architecture cible

```text
Users / API Clients
        │
        ▼
Load Balancer / Ingress
        │
        ▼
API stateless replicas
        │
        ├──► PgBouncer / HAProxy ► PostgreSQL Cluster
        ├──► Redis / cache / rate limit
        ├──► Message Queue
        │        └──► Worker pools discovery/import/sync/graph/reporting
        ├──► Object Storage S3 compatible
        └──► OpenSearch-compatible index
```

## Exigences techniques applicables

### REQ-00018

Le domaine Objectifs doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Vérification :** Test import/export, test file de messages et test reprise.

### REQ-00021

Le domaine Principes doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Vérification :** Test import/export, test file de messages et test reprise.

### REQ-00024

Le domaine Architecture cible doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Vérification :** Test import/export, test file de messages et test reprise.

### REQ-00027

Le domaine Urbanisation doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Vérification :** Test import/export, test file de messages et test reprise.

### REQ-00030

Le domaine Choix technologiques doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Vérification :** Test import/export, test file de messages et test reprise.

### REQ-00033

Le domaine Modèle de données complet doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Vérification :** Test import/export, test file de messages et test reprise.

### REQ-00036

Le domaine Gestion des équipements doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Vérification :** Test import/export, test file de messages et test reprise.

### REQ-00039

Le domaine Localisation X/Y/Z doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Vérification :** Test import/export, test file de messages et test reprise.

### REQ-00042

Le domaine Historique doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Vérification :** Test import/export, test file de messages et test reprise.

### REQ-00045

Le domaine Audit doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Vérification :** Test import/export, test file de messages et test reprise.

### REQ-00048

Le domaine Cycle de vie doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Vérification :** Test import/export, test file de messages et test reprise.

### REQ-00051

Le domaine IPv4/IPv6 doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Vérification :** Test import/export, test file de messages et test reprise.

### REQ-00054

Le domaine VRF doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Vérification :** Test import/export, test file de messages et test reprise.

### REQ-00057

Le domaine ASN doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Vérification :** Test import/export, test file de messages et test reprise.

### REQ-00060

Le domaine BGP doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Vérification :** Test import/export, test file de messages et test reprise.

### REQ-00063

Le domaine EVPN/VXLAN doit supporter l’import/export asynchrone lorsque le volume dépasse les seuils configurés.

**Vérification :** Test import/export, test file de messages et test reprise.



## Règles d’exploitation

- Toute configuration doit être externalisée.
- Toute connexion sortante critique doit disposer d’un timeout.
- Toute dépendance externe doit être protégée par circuit breaker lorsque pertinent.
- Toute opération batch doit être découpée et relançable.
- Les métriques de saturation doivent être exposées.
- Les dashboards doivent couvrir API, base, workers, files, discovery, imports, IPAM et sécurité.


### REQ-00818 — Requêtes SQL statiques paramétrées DCIM

Les repositories PostgreSQL DCIM doivent construire les filtres métier par variantes de requêtes statiques et paramètres nommés, jamais par interpolation de fragments SQL dynamiques. La liste des racks filtre le statut actif par `%(status)s` lorsque les éléments retirés ne sont pas demandés, afin de satisfaire Bandit B608 et de préserver un contrat SQL auditables.
