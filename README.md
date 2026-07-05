# OpenInfra v0.29.13

OpenInfra est une solution Python orientée objet pour référentiel d'infrastructure, IPAM/DDI, DCIM, inventaire, import/export, sécurité, éditions Lite/Pro/Enterprise et installateurs autonomes.

**Version courante : 0.29.13 — réalignement RI, sémantique agents proxy Enterprise, dashboard web de pilotage et assets rendering.**


## v0.29.13 — RI, agents proxy Enterprise et dashboard de pilotage

- Le domaine public `Source of Truth/SOT` est renommé `Ressources Inventory/RI`.
- Les chemins primaires deviennent `openinfra ri *`, `/api/v1/ri/*` et les rôles `ri:*`.
- Les anciens alias `openinfra sot *`, `/api/v1/sot/*` et `sot:*` restent compatibles pour éviter une rupture opérationnelle.
- `agent` désigne exclusivement un proxy collector Enterprise en topologie étoile ; Lite et Pro collectent depuis les backends servers.
- Les assets web runtime sont déplacés sous `src/openinfra/interfaces/rendering/static`, cohérents avec le domaine présentation/rendering.
- `openinfra-web` devient un dashboard de pilotage API-only couvrant RI, IPAM, DCIM, Discovery, sécurité/RBAC, audit, import/export et runtime.

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

### v0.29.14 — RI Quality & Certification

OpenInfra expose maintenant la qualité RI comme capacité pilotable :

```bash
openinfra ri quality-object --tenant default --admin-token "$TOKEN" --key device/example
openinfra ri quality-summary --tenant default --admin-token "$TOKEN" --kind device
```

Les endpoints primaires sont `/api/v1/ri/quality/object` et `/api/v1/ri/quality/summary`. Les alias historiques `/api/v1/sot/...` et `openinfra sot ...` restent disponibles pour compatibilité ascendante.
