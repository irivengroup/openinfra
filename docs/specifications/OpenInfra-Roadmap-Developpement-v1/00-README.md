# OpenInfra — Roadmap détaillée de développement

**Version :** 1.0.0  
**Statut :** livrable de pilotage programme  
**Base documentaire :** CDC/SFG/STG OpenInfra v4.0.0  
**Périmètre :** Source of Truth, DCIM, ITAM, Discovery, Dependency Mapping, IPAM Enterprise++, sécurité, exploitation, IA/RAG et modules fonctionnels avancés, sans ITSM intégré.

## Contenu

| Fichier | Rôle |
|---|---|
| `01-roadmap-detaillee-openinfra.md` | Roadmap complète narrative et opérationnelle. |
| `02-roadmap-phases.csv` | Phases programme et critères de sortie. |
| `03-roadmap-releases.csv` | Releases macro Alpha, MVP, Beta, RC, GA. |
| `04-roadmap-epics.csv` | Backlog détaillé par epic, phase, stream, dépendances et acceptation. |
| `05-roadmap-jalons.csv` | Jalons de pilotage. |
| `06-roadmap-dependances.csv` | Dépendances entre phases. |
| `07-roadmap-go-nogo.csv` | Gates Go/No-Go. |
| `08-roadmap-risques.csv` | Risques spécifiques à la roadmap. |
| `09-roadmap-tests-validation.csv` | Plan de tests et preuves par phase. |
| `10-roadmap-streams.csv` | Streams d’exécution et responsabilités. |
| `11-plan-90-jours.md` | Plan opérationnel des 90 premiers jours. |
| `12-plan-equipe-et-gouvernance.md` | Organisation recommandée et gouvernance. |
| `13-validation-roadmap.md` | Résultats de validation documentaire. |

## Hypothèses structurantes

- Sprints de deux semaines, avec démonstration et revue qualité à chaque fin de sprint.
- Équipe cible recommandée : 1 directeur programme, 1 product owner, 1 architecte entreprise, 1 architecte solution, 1 DBA PostgreSQL senior, 1 SRE, 3 à 5 backend engineers, 2 frontend engineers, 2 discovery/network engineers, 1 security engineer, 2 QA automation engineers, 1 technical writer.
- Le planning est exprimé en durées relatives T0 afin de rester indépendant de la date de lancement.
- La première mise en production utile doit viser le périmètre SOT + DCIM localisation + IPAM transactionnel + sécurité de base, avant les modules avancés.
- Les exigences N1 du CDC v4 sont non négociables : PostgreSQL Cluster, partitionnement des tables massives, performance, concurrence, résilience, absence d’ITSM intégré.
- Les modules IA/RAG ne doivent jamais modifier des données sans validation humaine explicite et doivent toujours appliquer les permissions avant restitution.

## Synthèse

La roadmap privilégie une construction progressive : d’abord le socle industriel, ensuite le référentiel fiable, puis DCIM/IPAM, puis discovery et dépendances, puis extensions enterprise. La GA n’est acceptable qu’après validation de la performance, de la résilience, de la sécurité, du PRA/PCA, de l’observabilité et de la documentation.
