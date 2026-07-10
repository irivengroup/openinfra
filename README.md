# OpenInfra v0.29.82

## Réconciliation Discovery multisource gouvernée

OpenInfra v0.29.82 réalise P14 / EPIC-1405. Les résultats issus de SNMP, SSH, WinRM, VMware, Proxmox, Hyper-V, Kubernetes, AWS, Azure, GCP, OpenStack, imports et saisies manuelles peuvent être enregistrés comme preuves immuables, puis rapprochés sans écriture automatique dans le RSOT (Ressource Source of Truth).

Le moteur calcule de façon déterministe les scores de confiance, fraîcheur, complétude et qualité globale. Les divergences sont exposées par chemin d’attribut avec toutes les variantes et leur preuve source. Une résolution exige une sélection explicite pour chaque conflit ainsi qu’une justification auditée. Les preuves et cas de rapprochement sont isolés par tenant, paginés et partitionnés sous PostgreSQL.

## Capacités livrées

- domaine POO typé pour preuves, scores, conflits, décisions et résolutions ;
- idempotence par signature canonique des preuves rapprochées ;
- persistance JSON et PostgreSQL avec migration additive `0038_discovery_multisource_reconciliation.sql` ;
- services applicatifs protégés par permissions RSOT de lecture/gouvernance ;
- commandes CLI, API HTTP, OpenAPI et formulaires web complets ;
- audit sans copie du payload de preuve ni matérialisation de secret ;
- tests unitaires, intégration, CLI, API, web, migration, sécurité et non-régression RSOT ;
- runbook `docs/runbooks/DISCOVERY_RECONCILIATION.md`.

Les corrections DCIM/ITAM et les profils Discovery livrés jusqu’en v0.29.81 restent compatibles.
