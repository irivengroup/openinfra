# Migration vers le contrat RSOT canonique — OpenInfra 0.34.6

OpenInfra 0.34.6 retire définitivement les alias publics ITRM, RI et SOT. Le seul contrat pris en charge est **RSOT — Ressource Source of Truth**. Les fonctions métier sont conservées ; seuls les noms d’entrée publics et les imports Python historiques sont supprimés.

## Préparation obligatoire

1. Sauvegarder la base et `/opt/openinfra/config`.
2. Exporter les scripts, rôles, tableaux de bord et intégrations qui appellent OpenInfra.
3. Rechercher les anciennes chaînes : `openinfra itrm`, `openinfra ri`, `openinfra sot`, `/api/v1/itrm/`, `/api/v1/ri/`, `/api/v1/sot/`, `itrm:*`, `ri:*`, `sot:*`, `core_ri`, `core_sot`.
4. Corriger toutes les occurrences avant le déploiement 0.34.6.

## Remplacements obligatoires

| Ancien contrat | Contrat 0.34.6 |
| --- | --- |
| `openinfra itrm ...` | `openinfra rsot ...` |
| `openinfra ri ...` | `openinfra rsot ...` |
| `openinfra sot ...` | `openinfra rsot ...` |
| `/api/v1/itrm/*`, `/api/v1/ri/*`, `/api/v1/sot/*` | `/api/v1/rsot/*` |
| rôles `itrm:*`, `ri:*`, `sot:*` | rôles `rsot:*` |
| capacités `core_ri`, `core_sot`, `core_source_of_truth`, `core_*resources_inventory` | `core_rsot` |
| modules Python ITRM/RI | `openinfra.application.source_of_truth_services` et `openinfra.application.rsot_quality_services` |

Les anciennes commandes sont rejetées par la CLI avec le code 2. Les anciennes routes HTTP retournent 404. Les anciens rôles et identifiants de capacités sont rejetés par validation métier.

## Validation avant bascule

```bash
openinfra rsot resource-taxonomy
python docs/specifications/OpenInfra-CDC-SFG-STG-v4.11.0/scripts/validate_rsot_canonical.py
python docs/specifications/OpenInfra-Roadmap-Developpement-v2.4/scripts/validate_roadmap.py
openinfra-gate13 --project-root . --candidate-id openinfra-0.34.6-local --source-commit 0000000000000000000000000000000000000000 --output artifacts/gate13/report.json --enforce
```

## Rollback

Le rollback applicatif nécessite la réinstallation du paquet 0.34.5 correspondant au schéma déjà sauvegardé. Ne réintroduisez pas d’alias dans 0.34.6. Restaurez les configurations et automatismes sauvegardés, puis vérifiez les routes et permissions de la version restaurée avant réouverture du service.
