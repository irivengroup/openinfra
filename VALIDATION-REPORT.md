# Rapport de certification locale — OpenInfra Python POO v0.34.5

**Date de certification :** 20 juillet 2026  
**Candidat :** `openinfra-0.34.5-final`  
**Référentiels actifs :** CDC `4.10.0`, roadmap `2.3.0`, release `REL-13`, gate `GATE-12`

## Décision

Le code source et les artefacts Python OpenInfra **0.34.5** sont **GO pour livraison comme candidat certifié localement**.

La publication en production reste **NO-GO** tant que les deux catégories de preuves externes suivantes ne sont pas produites sur l’infrastructure cible :

1. `pip-audit` exécuté avec accès fonctionnel à la base de vulnérabilités ;
2. qualifications live PostgreSQL, Oracle 19c Enterprise, Docker Compose, systemd, SAML/LDAP/Team Sync et GATE-11/GATE-12 avec un commit Git réel.

Cette restriction ne masque aucun échec produit local : tous les contrôles exécutables dans l’environnement courant passent. L’audit Python distant est classé **non exécutable localement** à cause d’une panne DNS vers PyPI, et non comme PASS.

## Périmètre 0.34.5 certifié

- identité d’installation Ed25519 et demande d’activation signée localement ;
- entitlement offline signé, lié à la licence, l’installation, l’entreprise, l’édition, au quota d’hôtes et aux échéances ;
- période de grâce fixe de 30 jours, notification, détection du recul d’horloge et comportement fail-closed ;
- persistance JSON, PostgreSQL et Oracle ;
- verrou PostgreSQL `FOR UPDATE` et contrôle du quota dans la même unité de travail que la création d’équipement ;
- migration PostgreSQL et Oracle `0059_runtime_offline_licensing.sql` ;
- CLI offline, API HTTP, réponse `402 Payment Required`, installateurs Pro/Enterprise et notifications accessibles ;
- contrat OpenAPI principal et contrat CDC ;
- CDC 4.10.0, roadmap 2.3.0, workflow GitHub Actions et qualification GATE-12 ;
- packaging wheel/sdist et smoke du wheel installé hors de l’arbre source ;
- charte graphique approuvée préservée.

## Résultats de certification

| Contrôle | Résultat |
|---|---:|
| Collecte pytest | **1 557 tests** |
| Suite Python complète, exécutée par lots isolés | **1 557/1 557 PASS** |
| Couverture globale conservatrice | **48 238 instructions, 961 non couvertes, 98,01 % PASS** |
| Ruff format | **465 fichiers PASS** |
| Ruff lint | **PASS** |
| mypy strict | **132 modules PASS** |
| `compileall` | **PASS** |
| Bandit SAST | **PASS** |
| Quality gate global | **PASS** |
| Frontend React | **79/79 PASS** |
| Contrat statique frontend | **PASS** |
| Accessibilité WCAG 2.2 AA | **PASS** |
| ESLint JSX/accessibilité | **PASS** |
| Build Vite | **PASS** |
| Shell JavaScript initial | **2 556 octets bruts / 1 265 octets gzip PASS** |
| `npm audit --audit-level=high --omit=optional` | **0 vulnérabilité** |
| `pip-audit` | **NON EXÉCUTABLE — résolution DNS PyPI indisponible** |
| CDC 4.10.0 | **859 exigences, 665 tests, 859 traces, zéro référence orpheline** |
| Roadmap 2.3.0 | **24 phases, 14 releases, 141 epics, 16 jalons, 13 gates** |
| Catalogue PostgreSQL | **59 migrations** |
| Catalogue Oracle | **59 migrations** |
| OpenAPI principal et CDC | **PASS** |
| Alignement Enterprise | **PASS** |
| GATE-12 | **7/7 PASS** |
| Build wheel/sdist | **PASS** |
| `twine check` | **PASS** |
| Vérification de contenu | **PASS** |
| Smoke du wheel installé hors dépôt | **PASS** |
| Audit placeholders/secrets privés | **PASS** |

## Stratégie de tests et couverture

La suite monolithique accumule des ressources dans l’environnement d’exécution local. La certification utilise donc la même suite, sans suppression de test, avec isolation par fichier et quatre workers :

```bash
PYTHONPATH=src:. python -m pytest -n 4 --dist loadfile
```

La mesure de couverture est volontairement conservatrice : aucun hook automatique de couverture des sous-processus n’est activé. Le résultat de **98,01 %** est donc obtenu sans gonflement par instrumentation externe, sans abaissement du seuil et sans nouvelle exclusion de code.

## Contrats CDC, roadmap et migrations

- CDC actif : `docs/specifications/OpenInfra-CDC-SFG-STG-v4.10.0` ;
- roadmap active : `docs/specifications/OpenInfra-Roadmap-Developpement-v2.3` ;
- CDC historique 4.9.0 et roadmap historique 2.2.0 conservés sans altération ;
- PostgreSQL et Oracle exposent le même catalogue ordonné de 59 migrations ;
- la dernière migration est `0059_runtime_offline_licensing.sql` ;
- Oracle reste réservé à l’édition Enterprise ;
- Lite reste exemptée de licence commerciale ;
- Pro et Enterprise deviennent fail-closed lorsque `OPENINFRA_LICENSE_ENFORCEMENT=true`.

## Packaging et smoke installé

Les artefacts produits sont :

- `openinfra-0.34.5-py3-none-any.whl` ;
- `openinfra-0.34.5.tar.gz`.

Le smoke du wheel installé dans un répertoire Python isolé vérifie notamment :

- la version 0.34.5 ;
- les trois routes HTTP de licence ;
- les 59 migrations et la migration terminale 0059 ;
- les scripts console, dont `openinfra-gate12` ;
- la politique GATE-12 et le runbook offline ;
- les actifs runtime, OpenAPI et frontend embarqués.

## Audit d’obsolescence

Le balayage final ne trouve :

- aucun `TODO`, `FIXME`, placeholder ou `NotImplementedError` dans le produit, les installateurs, scripts, tests et workflows actifs ;
- aucune clé privée d’autorité ou clé Ed25519 privée embarquée ;
- aucune constante active encore figée à 58 migrations ;
- aucune référence active à CDC 4.9.0 ou roadmap 2.2.0 hors historique et tests de préservation documentaire.

Les sections historiques du changelog, de la traçabilité et du README restent conservées lorsqu’elles décrivent une version antérieure.

## Limites et preuves externes requises

Les contrôles suivants ne peuvent pas être certifiés dans l’environnement courant :

- audit Python distant, la résolution DNS de PyPI étant indisponible ;
- migration et reprise sur PostgreSQL réel ;
- migration, reprise et charge sur Oracle 19c Enterprise réel ;
- démarrage Docker Compose complet, aucun moteur Docker/Podman n’étant exposé ;
- services systemd sur RHEL cible ;
- fédération SAML, LDAP/IPA et Team Sync avec fournisseurs réels ;
- preuves GATE-11/GATE-12 signées par un commit Git réel et une identité de publication approuvée.

Ces contrôles restent bloquants dans la CI/CD ou dans la procédure de promotion de production.

## Commandes de validation

```bash
python -m ruff format --check src tests scripts docker installers
python -m ruff check src tests scripts docker installers
python -m mypy src/openinfra
python -m compileall -q src/openinfra installers/setup
python -m bandit -q -r src/openinfra

PYTHONPATH=src:. python -m pytest -n 4 --dist loadfile
python -m coverage report --precision=2 --fail-under=98
PYTHONPATH=src:. python scripts/quality_gate.py

npm --prefix web ci --ignore-scripts
npm --prefix web test
npm --prefix web run lint
npm --prefix web run build
npm --prefix web audit --audit-level=high --omit=optional

python -m pip_audit -r requirements/security-audit.txt --progress-spinner off
python -m build
python -m twine check dist/*
python scripts/verify_artifact.py dist/*
```

## Commandes GitHub compactes

```bash
git add . && git commit -m "Livraison OpenInfra Python POO v0.34.5" && git push
```

## Docker Compose — redémarrage complet avec suppression des volumes

```bash
docker compose --env-file .env down --volumes --remove-orphans && docker compose --env-file .env up --build -d postgres migrate runtime-secrets auth-bootstrap api web pgadmin
```

Vérification :

```bash
docker compose --env-file .env ps && docker compose --env-file .env logs --no-color --tail=200 migrate runtime-secrets auth-bootstrap api web
```

Arrêt :

```bash
docker compose --env-file .env down --remove-orphans
```
