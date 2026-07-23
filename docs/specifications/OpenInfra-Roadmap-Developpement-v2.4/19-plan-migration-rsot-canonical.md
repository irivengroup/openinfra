# Plan de migration RSOT canonique — OpenInfra 0.34.6

| Ancien contrat | Remplacement obligatoire |
| --- | --- |
| `openinfra itrm ...` | `openinfra rsot ...` |
| `openinfra ri ...` | `openinfra rsot ...` |
| `openinfra sot ...` | `openinfra rsot ...` |
| `/api/v1/itrm/*` | `/api/v1/rsot/*` |
| `/api/v1/ri/*` | `/api/v1/rsot/*` |
| `/api/v1/sot/*` | `/api/v1/rsot/*` |
| rôles `itrm:*`, `ri:*`, `sot:*` | rôles `rsot:*` |
| capacités `core_ri`, `core_sot`, `core_*resources_inventory` | `core_rsot` |
| modules Python ITRM/RI | `openinfra.application.source_of_truth_services` et `openinfra.application.rsot_quality_services` |

Les intégrations doivent être migrées avant déploiement. Les fonctions métier ne changent pas.
