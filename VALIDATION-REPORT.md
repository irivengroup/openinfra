# OpenInfra v0.29.16 — rapport de validation

## Objet

v0.29.16 corrige le portail `openinfra-web` pour devenir un dashboard réellement pilotable par formulaires métier typés, sans champ générique `Attributs`, sans indication des méthodes HTTP dans l'UI, sans token API technique demandé à l'opérateur, avec version package fiable et trust server-side web ↔ backend.

## Changements validés

- `openinfra-web` affiche la version package via `/version` et fallback `/config.json`.
- Le navigateur ne transmet plus d'en-tête `Authorization` au backend via le proxy web.
- Le proxy web injecte un trust server-side contrôlé : `X-OpenInfra-Web`, `X-OpenInfra-Web-Trust`, `X-OpenInfra-Web-Version`.
- Les cibles `install.ini` `lite`, `pro/web` et `enterprise/web` déclarent `[web_database]` avec références DSN/user/password PostgreSQL.
- `/opt/openinfra/config/openinfra.conf` matérialise `OPENINFRA_WEB_DATABASE_*_REF` côté serveur uniquement.
- Le menu d'opérations interne à la page est supprimé ; les opérations sont déplacées dans les accordéons du panneau latéral.
- `Dashboard` reste une entrée latérale directe ; RI, IPAM, DCIM, Discovery et Sécurité/RBAC/Audit sont des accordéons avec transition fade.
- Les formulaires RI/IPAM/DCIM/Discovery/Sécurité exposent des inputs métier explicites : numéro de série, constructeur, modèle, site, bâtiment, salle, ligne, colonne, rack, IP de management, source, tags, scopes, certificat, endpoint, etc.

## Validations exécutées

| Validation | Résultat |
|---|---:|
| `PYTHONPATH=src:. python -m compileall -q src tests scripts docker installers` | PASS |
| `PYTHONPATH=src:. python scripts/validate_frontend.py --project-root .` | PASS |
| `PYTHONPATH=src python -m openinfra.interfaces.cli version` | PASS — 0.29.16 |
| `PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1` | PASS — 747 exigences, 552 tests |
| `PYTHONPATH=src python -m openinfra.interfaces.cli installer validate --root installers` | PASS — 6 profils |
| `PYTHONPATH=src python -m openinfra.interfaces.cli installer dry-run --root installers` | PASS |
| `python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_install_ini.py` | PASS |
| `python docs/specifications/OpenInfra-Roadmap-Developpement-v2/scripts/validate_roadmap.py` | PASS — 19 phases, 114 epics, 8 gates, 23 tests |
| `PYTHONPATH=src:. python scripts/security_gate.py --project-root .` | PASS |
| `PYTHONPATH=src python scripts/validate_autonomous_installer.py --root installers` | PASS — 6 profils |
| `PYTHONPATH=src python scripts/validate_enterprise_alignment.py --project-root .` | PASS |
| `PYTHONPATH=src python scripts/native_runtime_smoke.py --project-root .` | PASS |
| `python docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/scripts/validate_storage_multisite.py` | PASS |
| `PYTHONPATH=src:. python scripts/quality_gate.py` | PASS |
| Suite pytest exécutée par lots avec couverture combinée | PASS — 388 tests |
| `coverage report --fail-under=98` | PASS — 98 % |
| `node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js` | PASS |

## Validations pytest par lots

Les tests ont été exécutés par lots car la commande complète unique dépassait la fenêtre d'exécution disponible dans l'environnement.

- Architecture : PASS
- Unitaires complets : PASS
- CLI/API/HTTP : PASS
- Web : PASS
- Installateurs/runtime Docker : PASS
- RI Quality : PASS
- Discovery collectors : PASS
- IPAM/DCIM : PASS
- Import/Export : PASS
- PostgreSQL runtime/migrations/mapping : PASS
- Sécurité : PASS

Résultat combiné : **388 tests PASS**, couverture globale **98 %**.

## Non exécuté dans cet environnement

- `ruff format --check`, `ruff check`, `mypy`, `bandit`, `pip-audit` et `python -m build` : outils non installés dans l'environnement courant et installation externe indisponible.
- `npm run build` : dépendances Node non installées dans l'environnement courant ; les assets runtime servis ont été validés par `validate_frontend.py` et `node --check`.
- Docker Compose réel avec PostgreSQL live : Docker indisponible.

## Contrôle archive

- caches Python supprimés ;
- `.pytest_cache`, `.coverage*`, `.mypy_cache`, `.ruff_cache`, `build`, `dist`, `*.egg-info` absents ;
- `deploy/` absent ;
- `migrations/` racine absent ;
- `installers/setup/**/install.py` conservés ;
- `installers/migrations/postgresql` conservé ;
- `src/openinfra/interfaces/rendering/static` conservé ;
- aucun DSN PostgreSQL ni secret dans les assets navigateur.
