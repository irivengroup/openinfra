# OpenInfra v0.29.6 — validation report

## Objet

Version corrective complète issue de v0.29.5. Cette livraison traite la dette prioritaire P05 avant reprise Discovery : orchestration native LVM/PGDATA, filesystem applicatif CDC `/opt/openinfra/` pour tous les scopes installés y compris `enterprise/agent`, filesystem PostgreSQL `/data/openinfra/` uniquement pour backend/all-in-one, résolution/création du compte système PostgreSQL, symlink data, override systemd PGDATA et migrations backend.

## Changements validés

- `installers/setup/**/install.py` reste le point d'entrée autonome par scope.
- `enterprise/agent` respecte désormais la disposition CDC : FS/LVM applicatif `/opt/openinfra/` géré par l'installateur.
- `enterprise/agent` reste sans PostgreSQL, sans PGDATA, sans symlink `/opt/openinfra/data` et sans migrations backend.
- Ajout d'un plan filesystem applicatif interne : `rootvg/openinfra_lv`, `2GB`, `xfs`, monté sur `/opt/openinfra/`, propriétaire `openinfra:openinfra`.
- Ajout d'un plan filesystem PostgreSQL depuis `install.ini` : `vgname`, `lvname`, `lvsize`, monté en interne sur `/data/openinfra/`.
- Le `install.ini` ne révèle toujours pas le mountpoint, le owner/group, le scope, l'édition, le service ou les opérations.
- Le compte système `openinfra` est créé si absent avant montage/déploiement applicatif.
- Le compte système PostgreSQL est résolu depuis le packaging OS, puis créé si absent.
- LVM est orchestré de manière idempotente : validation VG, création LV si absent, formatage XFS si nécessaire, entrée `/etc/fstab`, montage et `chown`.
- Les scopes backend/all-in-one créent le symlink `/opt/openinfra/data -> /data/openinfra/`.
- Les scopes backend/all-in-one rendent l'override systemd PostgreSQL `PGDATA=/data/openinfra/`.
- Les migrations backend restent source unique sous `installers/migrations/postgresql`.
- CDC v4.8.1 et roadmap v2 mis à jour pour supprimer l'ancienne exception FS applicatif agent.
- Tests et gates renforcés pour vérifier que tous les scopes ont un `application_filesystem`, et que seuls backend/all-in-one ont un `postgresql_filesystem`.

## Validations exécutées

```bash
PYTHONPATH=src:. python -m compileall -q src tests scripts docker installers
python -m ruff format --check src tests scripts docker installers
python -m ruff check src tests scripts docker installers
python -m mypy src/openinfra
bandit -q -r src/openinfra
PYTHONPATH=src:. python scripts/security_gate.py --project-root .
pip-audit --dry-run
PYTHONPATH=src:. python -m pytest -q
PYTHONPATH=src:. python scripts/quality_gate.py
PYTHONPATH=src python -m openinfra.interfaces.cli version
PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1
PYTHONPATH=src python -m openinfra.interfaces.cli installer validate --root installers
PYTHONPATH=src python -m openinfra.interfaces.cli installer dry-run --root installers
PYTHONPATH=src python scripts/validate_autonomous_installer.py --root installers
PYTHONPATH=src python scripts/validate_enterprise_alignment.py --project-root .
PYTHONPATH=src python scripts/native_runtime_smoke.py --project-root .
python installers/setup/lite/install.py --dry-run --json
python installers/setup/pro/server/install.py --verify-only --json
python installers/setup/enterprise/agent/install.py --dry-run --json
python -m build
python scripts/verify_artifact.py dist/*.whl
```

## Résultats

- Compileall : PASS.
- Ruff format : PASS.
- Ruff lint : PASS.
- Mypy : PASS, 39 modules.
- Bandit : PASS.
- Security gate : PASS.
- pip-audit dry-run : PASS, 512 packages audités en dry-run, aucune vulnérabilité connue.
- Pytest : PASS, 344 tests.
- Couverture globale : PASS, 98.01 % pour un seuil de 98 %.
- Quality gate : PASS.
- CLI version : PASS, 0.29.6.
- CDC v4.8.1 : PASS, 735 exigences, 543 tests.
- Installateurs : PASS, 6 profils.
- Enterprise alignment : PASS.
- Native runtime smoke : PASS.
- Migrations PostgreSQL : PASS, 23 migrations chargées et validées.
- YAML compose/openapi : PASS.
- Build wheel/sdist : PASS.
- verify_artifact : PASS.

## Non exécuté

Docker Compose réel avec PostgreSQL live n'a pas été exécuté : Docker n'est pas disponible dans l'environnement courant.

## Dette restante prioritaire

P05 est livré côté moteur installateur natif. La dette suivante avant reprise Discovery est P06 : fondation HA PostgreSQL/cluster initial, uniquement après validation du déploiement live Docker/PostgreSQL ou environnement Linux cible.
