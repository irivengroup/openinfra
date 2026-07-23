# OpenInfra CDC/SFG/STG v4.9.0

Le CDC 4.9.0 est la référence contractuelle consolidée pour OpenInfra Lite, Pro et Entreprise. Il remplace la version 4.8.1 sans supprimer ses exigences et ajoute la trajectoire haute performance Pro/Entreprise.

## Principes invariants

- Clean Architecture, DDD, monolithe modulaire et API-first.
- PostgreSQL Cluster comme source transactionnelle principale.
- aucun ITSM intégré ; connecteurs ITSM externes uniquement.
- Services canoniques : `openinfra.service`, `openinfra-web.service`, `openinfra-agent.service`.
- Installateurs sous `installers/`, configuration `config/install.ini`, migrations pilotées par le backend.
- Données PostgreSQL sous `/data/openinfra/`, avec `/opt/openinfra/data -> /data/openinfra/` et `PGDATA` dimensionné à 2GB, 100GB ou 1TB selon l’édition.
- Authentification locale Lite ; LDAP/IPA et RBAC groupe pour Pro/Entreprise.
- Frontend React + Bootstrap 5, accessible WCAG 2.2 AA et consommant exclusivement les APIs.
- Multisite et réplication quasi temps réel selon les capacités d’édition.

## Architecture haute performance 4.9.0

Pro et Entreprise utilisent par défaut un runtime ASGI stateless, un pool PostgreSQL borné et un BFF HTTP persistant. PgBouncer, les réplicas de lecture, les workers, l’outbox, le stockage objet et les read models sont introduits par étapes mesurées. La transformation conserve le monolithe modulaire tant qu’une séparation de service n’est pas justifiée par des métriques ou une isolation opérationnelle.

## Documents d’entrée

- [Delta v4.9](00-Delta-v4.9.md)
- [Index général](00-Index-general.md)
- [Architecture cible](01-Vision/03-Architecture-cible.md)
- [Architecture technique](03-Technique/01-Architecture.md)
- [Performance](03-Technique/04-Performance.md)
- [Concurrence](03-Technique/05-Concurrence.md)
- [Architecture par édition](03-Technique/10-Architecture-par-edition.md)
- [ADR ASGI](08-RFC-ADR/ADR-0018-ASGI-runtime-haute-performance.md)
- [ADR pooling](08-RFC-ADR/ADR-0019-Pooling-PostgreSQL-et-BFF.md)
- [ADR frontend](08-RFC-ADR/ADR-0020-Frontend-modulaire-performance.md)
- [Exigences](11-Matrices/Exigences.csv)
- [Matrice haute performance](11-Matrices/Matrice-haute-performance-v4.9.csv)

## Validation

```bash
python docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0/scripts/validate_docs.py
python scripts/validate_enterprise_alignment.py
python scripts/quality_gate.py
```
