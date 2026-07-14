# OpenInfra — Roadmap de développement 2.2.0

La roadmap 2.2.0 est alignée sur le CDC/SFG/STG 4.9.0. Elle conserve les phases P00 à P18 et conserve les phases de scale-out puis ajoute une phase cloud-native dédiée :

- **P19 — Socle runtime haute performance Pro/Entreprise** : ASGI, pools bornés, streaming, budgets et CI.
- **P20 — Scale-out données et frontend** : PgBouncer, read replicas, curseurs, outbox/workers, frontend modulaire et observabilité p95/p99.
- **P21 — Kubernetes & Cloud-native** : inventaire multi-cluster, topologie applicative et physique, expositions, sécurité, GitOps et capacité.

## Règle de priorité

P19 et P20 constituent le socle de performance et de scale-out. P21 est exécutée par incréments compatibles ; aucune migration massive ou extraction en microservice n’est acceptée sans mesure, ADR, tests et rollback.

## Références

- CDC : `OpenInfra-CDC-SFG-STG-v4.9.0`
- Alignement : `14-alignement-cdc-v4.9.0.csv`
- Release fondation : OpenInfra `0.33.0`
- Seuil de couverture : 98 % minimum

## Validation

```bash
python docs/specifications/OpenInfra-Roadmap-Developpement-v2.2/scripts/validate_roadmap.py
python scripts/validate_enterprise_alignment.py
```
