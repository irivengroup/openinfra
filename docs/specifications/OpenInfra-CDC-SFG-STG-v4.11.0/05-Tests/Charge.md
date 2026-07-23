---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# Tests de charge

## Objectif

Valider utilisateurs simultanés, appels API/minute, workers et imports massifs.

## Scénarios obligatoires

- Démarrage cluster applicatif multi-réplicas.
- Test PostgreSQL primary/replica.
- Simulation de latence base et dépendances externes.
- Exécution import massif pendant consultations UI/API.
- Allocation IP concurrente.
- Recherche profonde avec pagination cursor-based.
- Purge et archivage partitionné.
- Restauration d’une partition.
- Bascule PostgreSQL sous charge.
- Vérification des dashboards et alertes.

## Critères d’acceptation

Les tests sont acceptés si les seuils définis dans les exigences N1 sont mesurés, reproductibles et historisés dans un rapport de validation.

## Matrice de charge v4.9.0

Les tests exécutent paliers, endurance, spike et saturation contrôlée. Ils couvrent API lecture/écriture, BFF streaming, acquisition PostgreSQL, dashboard, recherche, export et Discovery. Les résultats consignent p95/p99, erreurs, saturation et temps de récupération. Un test ne peut être déclaré passant sur le seul débit moyen.
