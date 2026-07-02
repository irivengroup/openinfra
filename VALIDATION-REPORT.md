# OpenInfra Python POO v0.8.0 — Validation Report

Date locale de génération : 2026-07-02

## Synthèse

Release v0.8.0 validée localement avec les outils disponibles dans l’environnement courant. Cette version ajoute un socle ABAC contextuel tenant/site/environnement au-dessus du RBAC existant, sans rupture de compatibilité : en absence de règle ABAC applicable, le comportement RBAC existant est conservé ; lorsqu’une règle s’applique à un sujet ou un rôle pour une permission donnée, elle restreint le contexte autorisé.

## Changements validés

- Domaine `access_policy` : effets `allow`/`deny`, règles actives, sujets, rôles, sites, environnements et wildcard contrôlé.
- Service applicatif `AccessPolicyService` : création, inventaire paginé, évaluation, autorisation et désactivation auditée.
- Référentiels JSON et PostgreSQL pour les règles ABAC.
- Migration PostgreSQL `0005_access_policy_abac.sql` avec table partitionnée par tenant, index GIN et index audit dédié.
- CLI `openinfra access create-rule/list-rules/evaluate/deactivate-rule`.
- Extension `openinfra ipam allocate` avec `--auth-token`, `--site-code`, `--environment`.
- API HTTP `/api/v1/access/rules`, `/api/v1/access/evaluate`, `/api/v1/access/deactivate-rule`.
- Runtime Docker : smoke tests ABAC contre API authentifiée et CLI PostgreSQL.
- Documentation, OpenAPI, GitHub Actions, tests unitaires, tests d’intégration et runbooks mis à jour.

## Validations exécutées localement

### Tests automatisés et couverture

Commande :

```bash
PYTHONPATH=src python3 -m pytest -q
```

Résultat : PASS.

```text
76 tests passants
Couverture totale : 90.05 %
Seuil de couverture : 90 %
```

### Quality gate projet

Commande :

```bash
PYTHONPATH=src python3 scripts/quality_gate.py
```

Résultat : PASS.

Le quality gate exécute les tests avec couverture, valide les sources contractuelles CDC intégrées, vérifie la cohérence des fichiers critiques, la version et les migrations attendues.

### Compilation Python

Commande :

```bash
PYTHONPATH=src python3 -m compileall -q src tests scripts docker
```

Résultat : PASS.

### CLI smoke tests

Commandes exécutées :

```bash
PYTHONPATH=src python3 -m openinfra.interfaces.cli version
PYTHONPATH=src python3 -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0001_bootstrap --root migrations/postgresql
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0002_security_rbac --root migrations/postgresql
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0003_security_token_lifecycle --root migrations/postgresql
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0004_identity_users_groups --root migrations/postgresql
PYTHONPATH=src python3 -m openinfra.interfaces.cli database render-migration --name 0005_access_policy_abac --root migrations/postgresql
PYTHONPATH=src python3 -m openinfra.interfaces.cli security bootstrap-token --backend json --data /tmp/openinfra-v08-cli-smoke.json --tenant default --subject abac-admin --role admin --token '<token-local-32-plus-chars>'
PYTHONPATH=src python3 -m openinfra.interfaces.cli security bootstrap-token --backend json --data /tmp/openinfra-v08-cli-smoke.json --tenant default --subject abac-worker --role ipam:operator --token '<token-local-32-plus-chars>'
PYTHONPATH=src python3 -m openinfra.interfaces.cli access create-rule --backend json --data /tmp/openinfra-v08-cli-smoke.json --tenant default --admin-token '<admin-token>' --name cli-par1-prod-ipam --permission ipam.allocate --effect allow --subject abac-worker --site-code PAR1 --environment prod
PYTHONPATH=src python3 -m openinfra.interfaces.cli access list-rules --backend json --data /tmp/openinfra-v08-cli-smoke.json --tenant default --admin-token '<admin-token>'
PYTHONPATH=src python3 -m openinfra.interfaces.cli access evaluate --backend json --data /tmp/openinfra-v08-cli-smoke.json --tenant default --token '<worker-token>' --permission ipam.allocate --site-code PAR1 --environment prod
PYTHONPATH=src python3 -m openinfra.interfaces.cli ipam allocate --backend json --data /tmp/openinfra-v08-cli-smoke.json --tenant default --actor cli-smoke --auth-token '<worker-token>' --vrf default --prefix 10.8.0.0/24 --hostname srv-cli-smoke --idempotency-key cli-v08-0001 --site-code PAR1 --environment prod
PYTHONPATH=src python3 -m openinfra.interfaces.cli dcim locate --backend json --data /tmp/openinfra-v08-cli-smoke.json --tenant default --asset-tag SRV-0001 --site PAR1 --building BAT-A --room MMR1 --row B --column 12 --rack R42 --u-position 18
```

Résultat : PASS.

### Validation YAML

Commande exécutée avec PyYAML :

```bash
python3 - <<'PY'
from pathlib import Path
import yaml
for name in ('compose.yaml', '.github/workflows/ci.yml', 'docs/api/openapi.yaml'):
    with open(name, 'r', encoding='utf-8') as handle:
        yaml.safe_load(handle)
PY
```

Résultat : PASS.

### Environnement Docker — génération sécurisée

Commande :

```bash
python3 scripts/docker_environment.py init
stat -c '%a %n' .env
rm -f .env
```

Résultat : PASS. Le fichier `.env` généré localement est créé avec le mode `0600`, puis supprimé avant packaging.

### Contrôle marqueurs incomplets

Commande :

```bash
python3 - <<'PY'
import ast
from pathlib import Path
roots = [Path('src'), Path('tests'), Path('scripts'), Path('docker')]
for root in roots:
    for path in root.rglob('*.py'):
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Pass):
                raise SystemExit(f'ast.Pass found: {path}:{node.lineno}')
PY
```

Résultat : PASS.

## Validations non exécutées localement

Les validations suivantes sont configurées dans `.github/workflows/ci.yml`, mais les outils nécessaires ne sont pas installés dans l’environnement courant :

```text
ruff : indisponible localement
mypy : indisponible localement
bandit : indisponible localement
python -m build : module build indisponible localement
Docker Compose runtime réel : Docker indisponible localement
PostgreSQL réel hors Docker : aucun serveur PostgreSQL externe disponible
```

## Risques résiduels

- Le socle ABAC v0.8.0 est opérationnel, testé en JSON, testé en PostgreSQL simulé et intégré au runtime Docker, mais la validation PostgreSQL réelle reste à exécuter via Docker Compose ou une CI équipée de Docker.
- Les politiques ABAC restent initiales : elles couvrent tenant, permission, sujet, rôle, site et environnement. Les contraintes attributaires complexes, expressions temporelles, approbations, politiques par ressource fine et intégrations OIDC/LDAP/SAML/SCIM restent hors périmètre de cette version.
- Les modules UI web complète, Discovery distribué, imports massifs, graphes avancés et orchestration de jobs distribués restent à développer sur les prochaines releases.
