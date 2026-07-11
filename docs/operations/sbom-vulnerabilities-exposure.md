# SBOM, vulnérabilités et exposition contextualisée

OpenInfra conserve les nomenclatures logicielles **SBOM** (*Software Bill of Materials*), les vulnérabilités déclarées par des sources externes et le contexte d’exposition métier. Le module est rangé sous **Sécurité → SBOM & vulnérabilités**.

## Périmètre de confiance

OpenInfra importe et corrèle des données ; il ne lance aucun scan actif et n’exécute aucune remédiation. Une vulnérabilité doit provenir d’un scanner, d’un flux CVE ou d’un processus de gouvernance externe. Les constats produits restent analytiques et auditables.

## Formats acceptés

- CycloneDX JSON ;
- SPDX JSON.

Chaque document est rattaché à un tenant, une application, une release et un environnement. Le contenu source est borné à 10 MiB, validé, normalisé et identifié par SHA-256. Une réimportation identique est idempotente ; une nouvelle release reçoit une version de document incrémentale.

## Identité et comparaison des composants

La comparaison utilise l’identité logique du package. Pour un PURL, la version, les qualificateurs et le sous-chemin ne transforment pas une mise à niveau en suppression suivie d’un ajout. Une évolution de `pkg:pypi/requests@2.31.0` vers `pkg:pypi/requests@2.32.0` est donc classée comme changement de version.

## Risque contextualisé

Le score tient compte de :

- la sévérité CVSS ;
- l’exploitation connue et la maturité de l’exploit ;
- l’exposition Internet ;
- l’accessibilité par les flux déclarés ou observés ;
- la criticité métier ;
- les actifs et services associés ;
- les contrôles compensatoires.

Le résultat comprend le score contextualisé, la priorité et les raisons de calcul. Les contrôles compensatoires réduisent le score sans supprimer le constat ni l’historique.

## CLI

```bash
openinfra sbom import --help
openinfra sbom documents --help
openinfra sbom vulnerability-import --help
openinfra sbom exposure-upsert --help
openinfra sbom assess --help
openinfra sbom findings --help
openinfra sbom compare --help
openinfra sbom risk-export --help
```

Les imports SBOM utilisent un fichier JSON local. Les exports de risque sont disponibles en JSON ou CSV.

## API

Les routes sont publiées sous `/api/v1/sbom` : documents, vulnérabilités, expositions, évaluations de risque, comparaisons et exports. Les opérations d’écriture exigent les permissions SBOM dédiées ; toutes les lectures et écritures sont isolées par tenant.

## Sécurité et audit

- aucune donnée secrète n’est acceptée dans les métadonnées ;
- les URI et PURL sont validés avant persistance ;
- les dates doivent être timezone-aware et sont normalisées en UTC ;
- les événements critiques sont enregistrés dans un outbox transactionnel ;
- les requêtes PostgreSQL sont paramétrées ;
- la pagination est bornée et les curseurs sont validés ;
- les fichiers exportés ne contiennent aucun jeton d’authentification.

## Exploitation

La migration `0048_sbom_vulnerabilities_exposure.sql` crée les tables partitionnables et indexées nécessaires aux documents, vulnérabilités, contextes d’exposition, constats, comparaisons et événements. Le mode local conserve les mêmes contrats dans le magasin JSON.
