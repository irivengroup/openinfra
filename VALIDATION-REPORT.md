# Rapport de certification locale — OpenInfra Python POO v0.34.8

**Date de certification :** 21 juillet 2026
**Candidat :** `openinfra-0.34.8-final-candidate`
**Référentiels actifs :** CDC `4.12.0`, roadmap `2.5.0`, phase `P25`, release `REL-15`, gate `GATE-14`

## Décision

Le code source, le frontend et les distributions Python OpenInfra **0.34.8** sont **GO pour livraison comme candidat certifié localement**.

La promotion en production reste **NO-GO** jusqu'à production des preuves externes suivantes sur l'infrastructure cible :

1. audit Python avec accès fonctionnel à PyPI ou à un miroir de vulnérabilités approuvé ;
2. qualification réelle PostgreSQL et Oracle 19c Enterprise ;
3. qualification Docker Compose et systemd ;
4. qualification SAML, LDAP/FreeIPA et Team Sync avec fournisseurs réels ;
5. exécution des rapports de promotion sur le commit de publication et conservation des preuves CI immuables.

L'audit Python distant n'a pas pu interroger PyPI en raison d'un échec de résolution DNS. Aucun résultat favorable n'est revendiqué pour ce contrôle.

## Périmètre fonctionnel 0.34.8

Cette version conserve les capacités certifiées jusqu'à 0.34.7 et matérialise la recommandation de placement DCIM exigée par `TST-FUNC-0007` :

- CDC actif `4.12.0` : 861 exigences, 667 tests contractuels, 861 lignes de traçabilité et 529 entités ;
- roadmap active `2.5.0` : P25, REL-15, EPIC-2501 à EPIC-2504 et GATE-14 ;
- recommandation déterministe de racks compatibles avec la hauteur U, la face, la puissance, la redondance A/B et le refroidissement demandés ;
- prise en compte de l'occupation par équipements et panneaux de brassage, des racks retirés, des limites rack/circuit et des zones thermiques ;
- exposition cohérente par service applicatif, CLI, HTTP, OpenAPI, portail React et runtime statique embarqué ;
- opération strictement consultative : aucune réservation de capacité ni mutation d'infrastructure ;
- registre exhaustif des 667 tests contractuels ;
- classification explicite de 20 preuves automatisées, 599 preuves partielles et 48 qualifications externes ;
- résolution statique de 28 sélecteurs pytest ;
- contrôle de 55 fichiers de preuve ;
- zéro preuve manquante et zéro exigence N1 non classifiée ;
- audit d'hygiène contextuel sans exclusion globale de l'arbre produit ;
- détection des chemins obsolètes, clés privées embarquées et alias publics historiques ;
- intégration GATE-14 dans la CLI, la CI, le wheel, le sdist et le smoke installé ;
- charte graphique approuvée inchangée.

Les preuves `partial` et `external` ne sont pas assimilées à une validation fonctionnelle complète. Elles restent des catégories explicites de traçabilité et de qualification à fermer selon leur périmètre.

## Résultats de certification

| Contrôle | Résultat |
|---|---:|
| Fichiers de tests Python | **280/280 PASS** |
| Suite Python complète | **1 616/1 616 PASS** |
| Durée suite Python isolée, 4 workers | **251,10 s** |
| Couverture globale exacte | **48 973 instructions, 48 005 couvertes, 968 non couvertes, 98,02340064933739 % PASS** |
| Couverture module GATE-14 | **431 instructions, 423 couvertes, 8 non couvertes, 98,14 % PASS** |
| Ruff format | **471 fichiers PASS** |
| Ruff lint | **PASS** |
| mypy strict | **132 modules PASS** |
| `compileall` | **PASS** |
| Bandit SAST, périmètre `src/openinfra` | **PASS** |
| Security gate dépôt/CI | **PASS** |
| Quality gate global | **code 0 / PASS** |
| Frontend React | **81/81 PASS** |
| Accessibilité HTML et JSX | **PASS** |
| Build Vite | **PASS** |
| Shell JavaScript initial | **2 556 octets bruts / 1 263 octets gzip PASS** |
| `npm audit --audit-level=high --omit=optional` | **0 vulnérabilité** |
| Audit Python distant | **NON EXÉCUTABLE — résolution DNS PyPI indisponible** |
| CDC 4.12.0 | **861 exigences, 667 tests, 861 traces, 529 entités** |
| Roadmap 2.5.0 | **26 phases, 16 releases, 149 epics, 18 jalons, 15 gates, 135 tests** |
| Alignements roadmap ↔ CDC | **140** |
| Catalogue PostgreSQL | **59 migrations** |
| Catalogue Oracle | **59 migrations** |
| OpenAPI principal et CDC | **PASS** |
| Alignement Enterprise | **PASS** |
| GATE-11 contrats | **9/9 PASS** |
| GATE-12 licensing offline | **7/7 PASS** |
| GATE-13 RSOT canonique | **6/6 PASS** |
| GATE-14 complétude contractuelle | **6/6 PASS** |
| Build wheel/sdist | **PASS** |
| `twine check` | **PASS** |
| Vérification du contenu des artefacts | **PASS** |
| Smoke du wheel installé hors dépôt | **PASS** |
| Audit alias ITRM/RI/SOT actifs | **0 constat** |
| Audit modules de compatibilité obsolètes | **0 constat** |
| Audit clés privées embarquées | **0 constat** |

## Stratégie de tests et couverture

Les 1 616 tests sont répartis sur quatre workers, mais chaque fichier est exécuté dans un processus Python indépendant avec un timeout borné. Les 280 fichiers de couverture parallèle ne sont fusionnés qu'après réussite complète de la campagne.

Cette isolation a détecté puis corrigé une fuite d'état préexistante dans un test SAML qui remplaçait globalement `importlib.import_module`. Le test restauré est autonome et repasse seul comme dans la campagne complète.

La couverture est exportée aux formats XML et JSON puis contrôlée par un seuil strict de 98 %. Aucune exclusion de couverture n'a été ajoutée et aucun résultat issu d'une exécution interrompue ou échouée n'est utilisé.

## Contrats CDC, roadmap et promotion

- CDC actif : `docs/specifications/OpenInfra-CDC-SFG-STG-v4.12.0` ;
- roadmap active : `docs/specifications/OpenInfra-Roadmap-Developpement-v2.5` ;
- exigence de complétude : `REQ-00861` ;
- test contractuel : `TST-COMP-164` ;
- matrice : `11-Matrices/Matrice-completude-contractuelle-v4.12.csv` ;
- registre : `docs/release/contract-proof-registry-v4.12.csv` ;
- politique : `docs/release/contract-completeness-promotion-policy.json` ;
- workflow : `.github/workflows/contract-completeness.yml` ;
- runbook : `docs/runbooks/CONTRACT_COMPLETENESS_PROMOTION.md` ;
- CDC 4.11.0 et roadmap 2.4.0 restent conservés pour la traçabilité historique.

## Sécurité et hygiène

- aucune clé privée d'autorité de licence n'est embarquée ;
- l'autorité Ed25519 reste chiffrée et opérée hors ligne ;
- les écritures sensibles et les rapports GATE-14 sont atomiques ;
- les états de licence corrompus restent traités en fail-closed ;
- l'audit d'hygiène exclut uniquement les fichiers exacts qui définissent ses propres règles ;
- les fichiers produit actifs restent analysés pour les marqueurs de développement interdits, les matériaux cryptographiques privés et les alias publics historiques ;
- la CI bloque la publication si l'un des contrôles GATE-11 à GATE-14 échoue.

## Packaging certifié

Les distributions vérifiées sont :

- `openinfra-0.34.8-py3-none-any.whl` ;
- `openinfra-0.34.8.tar.gz`.

Le smoke installé hors dépôt vérifie notamment :

- la version 0.34.8 ;
- les scripts console publics jusqu'à `openinfra-gate14` ;
- la taxonomie OpenAPI ;
- les 59 migrations PostgreSQL et Oracle ;
- les politiques, registres et runbooks GATE-11 à GATE-14 ;
- la route OpenAPI `/api/v1/dcim/placement-recommendations` et le runbook DCIM associé ;
- l'absence de dépendance à l'arbre source.

Les empreintes finales, le commit source et l'identité des deux constructions reproductibles sont portés par le manifeste du bundle final.

## Commandes de validation de référence

```bash
python -m ruff format --check src tests scripts docker installers
python -m ruff check src tests scripts docker installers
python -m mypy src/openinfra
python -m compileall -q src/openinfra scripts installers/setup
python -m bandit -q -r src/openinfra
python scripts/security_gate.py --project-root .
python -m pytest -q -n 4 --dist loadfile --cov=src/openinfra --cov-fail-under=98
python scripts/quality_gate.py
```

```bash
cd web
npm ci --ignore-scripts --no-audit --no-fund
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
| Vulnérabilités Python distantes | Non vérifié localement | exécuter l'audit depuis CI avec PyPI ou miroir approuvé |
| Oracle 19c Enterprise réel | À qualifier | appliquer les 59 migrations et exécuter GATE-11/GATE-12 sur runner Oracle |
| PostgreSQL réel et concurrence | À qualifier | exécuter migrations, repositories, quotas et charges concurrentes |
| Docker Compose | À qualifier | démarrage complet, readiness, migrations et smoke HTTP |
| systemd | À qualifier | installation native, permissions, secrets, timers et reprise |
| SAML/LDAP/Team Sync | À qualifier | tests avec IdP, LDAP/IPA et fournisseurs réels |
| Commit de publication | À lier au gel source | régénérer les rapports de promotion et conserver le manifeste signé |

## Décision finale locale

**GO local pour livraison comme candidat OpenInfra 0.34.8.**
**NO-GO production jusqu'à fermeture des preuves externes listées ci-dessus.**
