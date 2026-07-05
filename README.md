# OpenInfra v0.29.10

OpenInfra est une solution Python orientée objet pour référentiel d'infrastructure, IPAM/DDI, DCIM, inventaire, import/export, sécurité, éditions Lite/Pro/Enterprise et installateurs autonomes.

**Version courante : 0.29.10 — P07 authentification locale/LDAP/IPA, RBAC externe mappé OpenInfra et audit des permissions avant reprise Discovery.**

## v0.29.10 — P07 Authentification, RBAC et audit

Cette livraison reprend la roadmap après le correctif runtime PostgreSQL v0.29.9. Elle ne poursuit pas Discovery. Elle traite le socle d'authentification attendu avant reprise fonctionnelle :

- Lite reste strictement en authentification locale `standard` ; LDAP/IPA y est refusé côté backend et installateur.
- Pro/Enterprise acceptent LDAP/IPA uniquement côté backend `server`.
- Les scopes `web` et `agent` ne se connectent jamais directement à LDAP/IPA ; ils passent par le backend.
- L'autorité de permissions reste OpenInfra : les groupes LDAP/IPA externes sont mappés vers des groupes/rôles OpenInfra.
- Les secrets LDAP/IPA ne sont jamais acceptés en clair : seules les références `env:`, `vault://`, `sops://`, `file://` et `kms://` sont valides dans la configuration.
- L'adaptateur LDAP/IPA utilise `ldaps://`, validation TLS obligatoire, bind de service optionnel, recherche utilisateur, validation du mot de passe utilisateur et résolution des groupes.
- Les dépendances LDAP/IPA restent séparées par scope via `installers/requirements/*-server.txt` et l'extra Python `openinfra[ldap]`.
- Les événements d'authentification externe et de permission sont auditables via la nouvelle migration PostgreSQL `0025_authentication_ldap_ipa_rbac.sql`.

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
