---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# Performance

## Objectif

Budgets p95/p99, indexation, pagination, requêtes bornées, EXPLAIN, pg_stat_statements, batch et cache contrôlé.

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

## Budgets contractuels v4.9.0

Les scénarios Pro et Entreprise mesurent débit, p50, p95, p99, taux d’erreur, saturation CPU/mémoire, attente des pools et lag des réplicas. Une moyenne seule est interdite. Les budgets initiaux sont : p95 lecture simple ≤ 300 ms, p99 ≤ 800 ms ; p95 mutation simple ≤ 500 ms, p99 ≤ 1 200 ms ; disponibilité API ≥ 99,9 % hors maintenance ; erreur technique < 0,1 % au débit nominal. Les seuils sont révisés uniquement par décision d’architecture accompagnée de mesures.

Le frontend impose un shell initial ≤ 150 KiB compressé, chargement paresseux des modules, absence de catalogues inutiles au Dashboard et budgets Web Vitals documentés dans ADR-0020.
