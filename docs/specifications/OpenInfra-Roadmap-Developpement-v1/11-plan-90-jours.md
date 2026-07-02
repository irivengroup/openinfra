# OpenInfra — Plan opérationnel des 90 premiers jours

## Objectif

Les 90 premiers jours doivent transformer le CDC/SFG/STG v4 en un programme exécutable avec socle technique réel, gouvernance active, CI/CD opérationnelle et première base applicative.

## Jours 1 à 15 — Cadrage et mobilisation

### Livrables

- Gouvernance programme.
- RACI.
- Backlog macro.
- Découpage exigences N1.
- Architecture principles.
- ADR initiaux.
- Definition of Done.
- Stratégie CI/CD.
- Stratégie sécurité.
- Choix outillage.

### Critères de sortie

- Équipe nommée.
- Standards validés.
- Dépôt créé.
- Première CI exécutée.
- Backlog priorisé.

## Jours 16 à 30 — Socle repository et architecture

### Livrables

- Structure monolithe modulaire.
- Conventions backend/frontend.
- Packaging initial.
- API health/version.
- OpenAPI initial.
- Tests unitaires de base.
- Scans sécurité de base.
- Documentation développeur.

### Critères de sortie

- Clone, install, test et run documentés.
- Pipeline bloquant actif.
- Standards de code appliqués.

## Jours 31 à 45 — PostgreSQL baseline

### Livrables

- PostgreSQL local/dev.
- Migrations versionnées.
- Schémas core initiaux.
- PgBouncer local si applicable.
- Scripts de reset dev.
- Première stratégie partitionnement.
- Tests migrations.

### Critères de sortie

- Migrations rejouables.
- Tests DB intégrés à la CI.
- Tables massives interdites sans stratégie explicite.

## Jours 46 à 60 — Core domain et API

### Livrables

- Tenants.
- Utilisateurs techniques.
- Tags.
- Champs personnalisés.
- Erreurs normalisées.
- Pagination cursor-based.
- RBAC initial.
- Audit initial.

### Critères de sortie

- API REST versionnée.
- Isolation tenant testée.
- Audit des mutations critiques actif.

## Jours 61 à 75 — Source of Truth MVP

### Livrables

- Devices.
- Interfaces.
- Relations.
- Statuts.
- Sources.
- Historique initial.
- UI listes/fiches.
- Recherche clé.

### Critères de sortie

- Un actif peut être créé, modifié, historisé, audité et consulté par UI/API.

## Jours 76 à 90 — DCIM/IPAM amorce et revue M01

### Livrables

- Sites.
- Bâtiments.
- Salles.
- Ligne/colonne/X/Y/Z.
- VRF.
- Prefix IPv4/IPv6.
- Adresse IP.
- Première allocation transactionnelle.
- Revue architecture/data/sécurité.

### Critères de sortie

- Localisation physique minimale validée.
- Allocation IP concurrente couverte par tests initiaux.
- Gate M01/M02 préparé.

## Go/No-Go à 90 jours

Le programme continue uniquement si :

- la CI/CD est stable ;
- le socle applicatif est exécutable ;
- les migrations sont maîtrisées ;
- l’équipe respecte la Definition of Done ;
- les premières APIs sont documentées ;
- les risques PostgreSQL et sécurité sont suivis ;
- aucune dette bloquante n’est masquée.
