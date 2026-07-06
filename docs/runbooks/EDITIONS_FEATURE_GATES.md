# Éditions, feature gates et quotas runtime — v0.29.0

## Objectif

Ce runbook décrit le contrôle runtime des éditions OpenInfra. Le mécanisme complète les profils installateurs : un déploiement Lite, Pro ou Enterprise est désormais contrôlé par le backend applicatif, pas uniquement par l'arborescence `installers/`.

## Source de vérité

Les éditions supportées sont :

| Édition | Équipements | Subnets/VLAN | IP/DNS | Utilisateurs | Collectors Discovery |
| --- | ---: | ---: | ---: | ---: | ---: |
| Lite | 200 | 20 | 200 | 5 | 0 |
| Pro | 5000 | 100 | 5000 | 100 | 0 |
| Enterprise | illimité | illimité | illimité | illimité | illimité |

Les capabilities `distributed_discovery_agents` et `installer_agent_scope` sont réservées à Enterprise. Les fonctionnalités cœur IT Ressources Management, DCIM, IPAM, RBAC, audit et import/export restent disponibles dans les trois éditions selon les quotas associés.

## Configuration runtime

Pour l'API :

```bash
export OPENINFRA_EDITION=lite
openinfra-api --backend postgresql --postgres-dsn "$OPENINFRA_DATABASE_DSN" --edition lite
```

Pour la CLI, les commandes utilisant le helper backend acceptent `--edition`. À défaut, `OPENINFRA_EDITION` est lu, puis `enterprise` est utilisé pour préserver la compatibilité ascendante.

## Contrôles manuels

```bash
openinfra edition list --data /tmp/openinfra-editions.json
openinfra edition feature-check --tenant default --edition lite --capability distributed_discovery_agents
openinfra edition quota-check --data /tmp/openinfra-editions.json --edition lite --tenant default --resource user --increment 1
```

Un `feature-check` refusé retourne le code `2` et un JSON explicite. Un `quota-check` refusé retourne également le code `2`.

## Garanties backend

- Les collectors Discovery sont refusés en Lite/Pro avant persistance.
- Les heartbeats, autorisations de jobs, désactivations et listings collectors sont également refusés en Lite/Pro.
- Les quotas Lite/Pro sont vérifiés avant création d'utilisateur, allocation IP, enregistrement d'adresse IP/DNS, création de prefix et création de VLAN.
- Enterprise conserve le comportement historique : aucune limite runtime par défaut, donc pas de transaction d'audit supplémentaire sur le chemin nominal.
- Les décisions bloquantes sont auditées via `edition.feature_gate.checked` et `edition.quota.checked`.

## Validation

```bash
ruff format --check src tests scripts docker
ruff check src tests scripts docker
mypy src/openinfra
bandit -q -r src/openinfra
PYTHONPATH=src:. pytest
PYTHONPATH=src python -m openinfra.interfaces.cli edition feature-check --tenant default --edition lite --capability distributed_discovery_agents
PYTHONPATH=src python -m openinfra.interfaces.cli edition quota-check --data /tmp/openinfra-editions.json --edition lite --tenant default --resource user --increment 1
```
