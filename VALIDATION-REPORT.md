# Rapport de certification locale — OpenInfra Python POO v0.34.6

**Date de certification :** 21 juillet 2026  
**Candidat :** `openinfra-0.34.6-local-candidate`  
**Référentiels actifs :** CDC `4.11.0`, roadmap `2.4.0`, phase `P24`, release `REL-14`, gate `GATE-13`

## Décision

Le code source et les artefacts Python OpenInfra **0.34.6** sont **GO pour livraison comme candidat certifié localement**.

La promotion en production reste **NO-GO** tant que les preuves externes suivantes ne sont pas produites sur l’infrastructure cible :

1. `pip-audit` exécuté avec accès fonctionnel à PyPI ou à un miroir de vulnérabilités approuvé ;
2. qualification live PostgreSQL et Oracle 19c Enterprise ;
3. qualification Docker Compose, systemd, SAML, LDAP/FreeIPA et Team Sync ;
4. rapports GATE-11, GATE-12 et GATE-13 associés au véritable SHA-1 du commit Git de publication.

L’absence de résultat `pip-audit` local est due à l’échec de résolution DNS de `pypi.org`. Aucun résultat PASS n’est revendiqué pour ce contrôle.

## Périmètre fonctionnel 0.34.6

Cette version conserve intégralement le licensing runtime offline livré en 0.34.5 et ajoute la canonicalisation définitive du domaine RSOT :

- la CLI expose exclusivement `openinfra rsot` ;
- les routes HTTP publiques utilisent exclusivement `/api/v1/rsot/*` ;
- les anciens alias `itrm`, `ri` et `sot` retournent un rejet explicite ou HTTP 404 ;
- les rôles RBAC utilisent exclusivement le préfixe `rsot:*` ;
- la capacité d’édition canonique est exclusivement `core_rsot` ;
- les modules applicatifs de compatibilité ITRM/RI sont supprimés ;
- les services qualité utilisent exclusivement les classes `Rsot*` ;
- le packaging empêche la réintroduction de modules, symboles, routes ou capacités historiques ;
- le guide de migration `RSOT_CANONICAL_MIGRATION.md` documente la rupture publique volontaire ;
- CDC 4.11.0, roadmap 2.4.0, P24, REL-14 et GATE-13 encadrent cette évolution ;
- la charte graphique approuvée reste inchangée.

## Résultats de certification

| Contrôle | Résultat |
|---|---:|
| Suite Python complète | **1 577/1 577 PASS** |
| Couverture globale conservatrice | **48 332 instructions, 959 non couvertes, 98,02 % PASS** |
| Ruff format | **467 fichiers PASS** |
| Ruff lint | **PASS** |
| mypy strict | **139 modules PASS** |
| `compileall` | **PASS** |
| Bandit SAST, périmètre CI `src/openinfra` | **PASS** |
| Security gate dépôt/CI | **PASS** |
| Quality gate global | **code 0 / PASS** |
| Frontend React | **79/79 PASS** |
| Contrat statique frontend | **PASS** |
| Accessibilité WCAG 2.2 AA | **PASS** |
| ESLint JSX/accessibilité | **PASS** |
| Build Vite | **PASS** |
| Shell JavaScript initial | **2 556 octets bruts / 1 265 octets gzip PASS** |
| `npm audit --audit-level=high --omit=optional` | **0 vulnérabilité** |
| `pip-audit` | **NON EXÉCUTABLE — résolution DNS PyPI indisponible** |
| CDC 4.11.0 | **860 exigences, 666 tests, 860 traces, 529 entités** |
| Roadmap 2.4.0 | **25 phases, 15 releases, 145 epics, 17 jalons, 14 gates, 129 tests** |
| Alignements roadmap ↔ CDC | **139** |
| Catalogue PostgreSQL | **59 migrations** |
| Catalogue Oracle | **59 migrations** |
| OpenAPI principal et CDC | **PASS** |
| Alignement Enterprise | **PASS** |
| GATE-11 contrats | **9/9 PASS** |
| GATE-12 licensing offline | **7/7 PASS** |
| GATE-13 RSOT canonique | **6/6 PASS** |
| Build wheel/sdist | **PASS** |
| `twine check` | **PASS** |
| Vérification du contenu des artefacts | **PASS** |
| Smoke du wheel installé hors dépôt | **PASS** |
| Audit alias ITRM/RI/SOT actifs | **0 constat** |
| Audit modules de compatibilité obsolètes | **0 constat** |
| Audit clés privées embarquées | **0 constat** |

## Stratégie de tests et couverture

Les 1 577 tests ont été exécutés sans suppression de scénario :

- 821 tests unitaires, architecture et performance ;
- 756 tests d’intégration ;
- quatre workers `pytest-xdist` ;
- distribution par fichier avec `--dist loadfile` ;
- lots bornés pour éviter les accumulations de ressources de l’environnement local ;
- une couverture unique recombinée après chaque lot entièrement réussi.

La couverture est calculée sans hook automatique des sous-processus, sans abaissement du seuil et sans nouvelle exclusion destinée à gonfler le résultat.

## Contrats CDC, roadmap et promotion

- CDC actif : `docs/specifications/OpenInfra-CDC-SFG-STG-v4.11.0` ;
- roadmap active : `docs/specifications/OpenInfra-Roadmap-Developpement-v2.4` ;
- exigence RSOT : `REQ-00860` ;
- test contractuel : `TST-RSOT-163` ;
- matrice : `11-Matrices/Matrice-rsot-canonical-v4.11.csv` ;
- politique : `docs/release/rsot-canonical-promotion-policy.json` ;
- workflow : `.github/workflows/rsot-canonical.yml` ;
- runbook : `docs/runbooks/RSOT_CANONICAL_MIGRATION.md` ;
- CDC 4.10.0 et roadmap 2.3.0 restent disponibles pour la traçabilité historique ;
- CDC 4.9.0 et roadmap 2.2.0 restent disponibles pour les versions historiques Oracle Enterprise.

## Compatibilité et rupture contrôlée

La suppression des alias publics ITRM/RI/SOT est une rupture volontaire prescrite par le contrat 4.11.0. Elle ne supprime aucune capacité métier RSOT.

Les intégrateurs doivent migrer :

- `openinfra itrm`, `openinfra ri` ou `openinfra sot` vers `openinfra rsot` ;
- `/api/v1/itrm/*`, `/api/v1/ri/*` ou `/api/v1/sot/*` vers `/api/v1/rsot/*` ;
- les rôles historiques vers `rsot:reader`, `rsot:operator` ou `rsot:governance-admin` ;
- les capacités historiques vers `core_rsot`.

Aucun wrapper silencieux de compatibilité n’est conservé, afin d’empêcher la prolongation indéfinie des anciens contrats.

## Sécurité

- aucune clé privée d’autorité de licence n’est embarquée ;
- l’autorité Ed25519 reste chiffrée et opérée hors ligne ;
- les écritures sensibles sont atomiques ;
- les états de licence corrompus sont traités en fail-closed ;
- la CI bloque la publication si GATE-12 ou GATE-13 échoue ;
- Bandit est appliqué au périmètre produit `src/openinfra`, conformément aux workflows CI ;
- le security gate contrôle les secrets, Dependabot, dependency review, CodeQL et la séparation runtime/dev.

## Packaging certifié

Les artefacts attendus sont :

- `openinfra-0.34.6-py3-none-any.whl` ;
- `openinfra-0.34.6.tar.gz` ;
- archive source reproductible OpenInfra 0.34.6 ;
- rapports GATE-11, GATE-12 et GATE-13 ;
- résumé JSON de certification ;
- manifeste SHA-256.

Le smoke installé vérifie notamment :

- la version 0.34.6 ;
- les scripts console publics, dont `openinfra-gate13` ;
- les trois routes de licence ;
- la taxonomie OpenAPI ;
- les 59 migrations PostgreSQL et Oracle ;
- les politiques et runbooks GATE-11, GATE-12 et GATE-13 ;
- l’absence de dépendance à l’arbre source.

## Commandes de validation de référence

```bash
python -m ruff format --check src tests scripts installers docker
python -m ruff check src tests scripts installers docker
python -m mypy
python -m compileall -q src scripts installers docker
python -m bandit -q -r src/openinfra
python scripts/security_gate.py --project-root .
python -m coverage report --precision=2 --fail-under=98
python scripts/quality_gate.py
```

```bash
cd web
npm ci
npm test
npm run lint
npm run a11y
npm run a11y:jsx
npm run build
npm audit --audit-level=high --omit=optional
```

```bash
rm -rf build dist
python -m build
python -m twine check dist/*
python scripts/verify_artifact.py dist/*
```

## Risques résiduels et validations externes

| Risque / validation | Statut | Action de fermeture |
|---|---|---|
| Vulnérabilités Python distantes | Non vérifié localement | exécuter `pip-audit` depuis CI avec PyPI ou miroir approuvé |
| Oracle 19c Enterprise réel | À qualifier | appliquer les 59 migrations et exécuter GATE-11 sur runner Oracle |
| PostgreSQL réel et concurrence | À qualifier | exécuter migrations, repositories et quota sous charge sur PostgreSQL cible |
| Docker Compose | À qualifier | démarrage complet, readiness, migrations et smoke HTTP |
| systemd | À qualifier | installation native, permissions, secrets, timers et reprise |
| SAML/LDAP/Team Sync | À qualifier | tests avec IdP, LDAP/IPA et fournisseurs réels |
| Commit de publication | Absent du snapshot local | régénérer les rapports avec le SHA-1 Git réel |

## Décision finale locale

**GO local pour livraison comme candidat OpenInfra 0.34.6.**  
**NO-GO production jusqu’à fermeture des preuves externes listées ci-dessus.**
