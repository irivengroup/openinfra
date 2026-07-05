# OpenInfra v0.29.11

OpenInfra est une solution Python orientée objet pour référentiel d'infrastructure, IPAM/DDI, DCIM, inventaire, import/export, sécurité, éditions Lite/Pro/Enterprise et installateurs autonomes.

**Version courante : 0.29.11 — Correctif P07/P08 de modèle runtime : configuration canonique post-installation, backend API-only, LDAP/IPA côté web et mTLS front/back/agent.**

## v0.29.11 — Runtime post-installation, backend API-only et sécurisation des flux

Cette livraison corrige et verrouille le modèle d'exploitation post-installation :

- `/opt/openinfra/config/openinfra.conf` devient la configuration runtime canonique.
- `/etc/openinfra` est un symlink vers `/opt/openinfra/config`, conservant le chemin compatible `/etc/openinfra/openinfra.conf`.
- `install.ini` et `.env` sont des entrées de bootstrap ; les services ne dépendent plus de `installers/` après installation.
- Les migrations backend sont copiées sous `/opt/openinfra/share/migrations/postgresql`.
- Le verrou `/opt/openinfra/config/.openinfra-installed.lock` empêche les installations multiples non contrôlées.
- Le backend reste API-only pour les opérateurs : pas de login LDAP/IPA direct côté backend.
- Le frontend web porte l'authentification opérateur, y compris LDAP/IPA en Pro/Enterprise.
- Les agents consomment uniquement l'API backend avec leur mécanisme technique d'enrôlement.
- Hors Lite, les échanges frontend-backend, agent-backend et backend-backend imposent TLS 1.3 et mTLS.
- Lite reste strictement local et loopback-only.

Nouvelle commande de contrôle :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli auth policy \
  --edition enterprise \
  --mode ipa \
  --url ldaps://ipa.example.net \
  --base-dn dc=example,dc=net \
  --bind-dn-ref env:OPENINFRA_IPA_BIND_DN \
  --bind-password-ref env:OPENINFRA_IPA_BIND_PASSWORD
```

## Installateurs autonomes

Les installateurs restent les points d'entrée d'installation réels :

```text
installers/setup/lite/install.py
installers/setup/pro/server/install.py
installers/setup/pro/web/install.py
installers/setup/enterprise/server/install.py
installers/setup/enterprise/web/install.py
installers/setup/enterprise/agent/install.py
```

Chaque installateur déploie son contenu autonome : `src/`, `pyproject.toml`, requirements de production par scope, unité systemd rendue et migrations backend quand le scope gère PostgreSQL.

## Validations principales

```bash
PYTHONPATH=src:. python -m pytest
PYTHONPATH=src:. python scripts/quality_gate.py
PYTHONPATH=src python -m openinfra.interfaces.cli installer validate --root installers
PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1
python -m build
python scripts/verify_artifact.py dist/*.whl
```
