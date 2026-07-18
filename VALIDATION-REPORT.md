# Rapport de validation — OpenInfra Python POO v0.34.4

## Décision

La version **0.34.4** atteint le niveau **GO pour la livraison logicielle locale**.

Le code, les migrations, les tests, la couverture, les contrôles statiques, le frontend, les contrats CDC/roadmap et le packaging reproductible sont cohérents et validés dans l’environnement de construction.

La promotion **REL-12 / GATE-11 en environnement cible reste NO-GO** tant que les preuves live n’ont pas été produites sur une instance Oracle 19c Enterprise réelle, un fournisseur d’identité SAML réel, une source Team Sync réelle et un hôte Linux systemd. La signature locale de packaging utilise également une clé Ed25519 éphémère, non une identité de publication approuvée.

## Objet de la version

La version 0.34.4 applique deux évolutions compatibles :

1. le **backend de base de données Oracle est désormais réservé exclusivement à l’édition Enterprise** ;
2. la persistance documentaire Oracle est segmentée par domaine afin d’éviter le verrou transactionnel global de l’ancien document CLOB unique.

PostgreSQL reste le backend par défaut et demeure disponible dans les éditions Lite, Pro et Enterprise.

La restriction concerne uniquement `database.backend=oracle`. Elle ne bloque pas SAML, LDAP avancé, Team Sync ni les autres capacités qui peuvent être disponibles selon la politique d’édition.

## Implémentation livrée

### Politique d’édition Oracle

- capacité interne explicite `ORACLE_DATABASE_BACKEND` ;
- valeur publique historique `oracle_database` conservée pour la rétrocompatibilité ;
- garde centralisée `EditionDatabasePolicy` ;
- refus Lite/Pro avant chargement du pilote, ouverture du pool, connexion ou migration ;
- acceptation Enterprise explicite ;
- contrôles propagés aux factories, CLI, API HTTP, ASGI, runtime systemd, installateurs, readiness et GATE-11 ;
- PostgreSQL et le backend JSON de développement restent inchangés.

### Segmentation transactionnelle Oracle

- migration additive `0058_oracle_document_shards.sql` ;
- catalogues PostgreSQL et Oracle alignés de `0001` à `0058` ;
- table de segments JSON versionnés par collection métier ;
- migration paresseuse et idempotente depuis `openinfra_document_state/global` ;
- réécriture limitée aux segments réellement modifiés ;
- contrôle optimiste indépendant par segment ;
- conflits sur un même segment refusés avec rollback ;
- domaines distincts pouvant progresser sans conflit global ;
- ancien document global conservé pour compatibilité et rollback opérationnel.

## Résultats de validation

| Contrôle | Résultat |
|---|---:|
| Catalogue PostgreSQL | **58 migrations PASS** |
| Catalogue Oracle | **58 migrations PASS** |
| Manifeste Oracle | **58 entrées PASS** |
| Dernière migration | **0058_oracle_document_shards.sql** |
| Générateur Oracle `--check` | **PASS** |
| Tests unitaires | **769/769 PASS** |
| Tests d’intégration | **731/731 PASS** |
| Tests d’architecture | **3/3 PASS** |
| Tests de performance | **11/11 PASS** |
| Total Python | **1 514/1 514 PASS** |
| Couverture globale | **47 280 lignes, 939 non couvertes, 98,013959 % PASS** |
| Seuil `--cov-fail-under=98` | **PASS sans baisse de seuil ni nouvelle exclusion** |
| Ruff format/lint | **453 fichiers PASS** |
| mypy strict | **PASS** |
| `compileall` | **PASS** |
| Bandit SAST | **PASS** |
| Frontend React | **79/79 PASS** |
| Contrat statique frontend | **PASS** |
| Accessibilité WCAG 2.2 AA | **PASS** |
| ESLint JSX | **PASS** |
| Build Vite | **PASS** |
| Audit npm | **0 vulnérabilité** |
| OpenAPI principal et CDC | **PASS** |
| CDC v4.9.0 | **845 exigences PASS** |
| Roadmap v2.2 | **23 phases, 137 epics, 12 gates PASS** |
| Quality Gate global | **PASS** |
| Build wheel et sdist | **PASS** |
| `twine check` | **PASS** |
| Contenu des artefacts | **PASS** |
| Installation et smoke du wheel hors dépôt | **PASS** |
| Packaging reproductible | **PASS** |
| Contrôles packaging | **7/7 PASS** |
| Identité de signature de publication | **NO-GO : clé locale éphémère** |

La matrice Python complète a été relancée de zéro sur l’arbre final. Résultat exact :

```text
Lignes mesurées   : 47 280
Lignes couvertes  : 46 341
Lignes manquantes : 939
Taux exact        : 98,01395939086295 %
Tests             : 1 514 PASS
Durée             : 227,71 s
```

## Packaging

Le certificateur de packaging termine avec les sept contrôles attendus :

1. wheel et sdist reproductibles octet pour octet avec `SOURCE_DATE_EPOCH=1784332800` ;
2. contenu runtime et release complet ;
3. installation isolée du wheel, `pip check` et smoke hors dépôt ;
4. dry-run et rollback transactionnel des six profils d’installation ;
5. SBOM SPDX 2.3 déterministe ;
6. manifeste Ed25519 généré et vérifié ;
7. manifeste SHA-256 généré et vérifié.

Le précédent diagnostic de blocage du certificateur a été levé : le contrôle complet termine normalement. Le traitement le plus long est la séquence des douze invocations d’installateurs ; chaque sous-processus dispose de son propre timeout et tous les profils terminent avec une preuve JSON valide.

La certification de publication demeure `false` uniquement parce que la clé locale est éphémère. Une clé de release approuvée et protégée doit être fournie par le pipeline de publication pour obtenir une certification de production.

## Compatibilité et non-régression

- PostgreSQL reste le backend transactionnel par défaut des trois éditions.
- Oracle est refusé en Lite et Pro et accepté uniquement en Enterprise.
- La sélection Oracle échoue avant toute connexion lorsque l’édition est incompatible.
- Les API métier, commandes CLI, permissions RBAC et formats publics existants sont conservés.
- L’alias public `oracle_database` reste accepté.
- Les installations Oracle antérieures à `0058` restent lisibles et migrables.
- Aucun endpoint ni aucune fonctionnalité existante n’est supprimé.
- La charte graphique et le thème approuvés ne sont pas modifiés.
- Python 3.11 et les versions supérieures déclarées restent supportés.

## Gouvernance

La règle Oracle Enterprise impacte le cadre d’architecture et de licence ; les référentiels ont donc été alignés :

- CDC v4.9.0 : `REQ-00844` et `TST-DATA-144` imposent Oracle uniquement en Enterprise ;
- roadmap v2.2 : P22, EPIC-2204, REL-12, M14 et GATE-11 sont alignés ;
- `docs/TRACEABILITY.md`, runbook Oracle/systemd, README et changelog sont cohérents avec la règle finale.

## Validations non exécutables dans l’environnement courant

### Oracle 19c réel

Aucune instance Oracle 19c ni client Oracle cible n’est disponible dans l’environnement de construction. Les 58 migrations n’ont donc pas été appliquées ici sur une base Oracle réelle avec le compte applicatif final.

La qualification cible doit valider :

- schéma vierge ;
- upgrade depuis l’historique antérieur ;
- migration du document global vers les segments ;
- permissions minimales ;
- contraintes, index, partitions et objets PL/SQL ;
- détection de conflit optimiste ;
- readiness après redémarrage ;
- sauvegarde et restauration opérationnelles.

### SAML, Team Sync et systemd réels

L’environnement ne fournit ni IdP SAML réel, ni annuaire Team Sync cible, ni hôte systemd actif. Les contrats et scénarios simulés passent, mais les preuves GATE-11 live restent obligatoires.

### Audit Python en ligne

`pip-audit` est installé, mais la résolution DNS vers PyPI n’est pas disponible dans l’environnement. Aucun résultat PASS local n’est revendiqué pour cet audit ; il reste bloquant en CI avec accès à la base de vulnérabilités.

### Docker Compose

Aucun moteur Docker ou Podman n’est disponible dans l’environnement courant. Les contrats Compose passent, mais le redémarrage complet de la stack n’a pas été exécuté localement.

## Commandes de validation

```bash
PYTHONPATH=src:. python scripts/generate_oracle_migrations.py --check
PYTHONPATH=src:. python scripts/validate_oracle_migrations.py
PYTHONPATH=src:. pytest
PYTHONPATH=src:. ruff format --check src tests scripts docker installers
PYTHONPATH=src:. ruff check src tests scripts docker installers
PYTHONPATH=src:. mypy src/openinfra
PYTHONPATH=src:. python -m compileall -q src/openinfra
PYTHONPATH=src:. bandit -q -r src/openinfra
python scripts/validate_openapi.py \
  docs/api/openapi.yaml \
  docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0/09-API/OpenAPI/openapi.yaml
PYTHONPATH=src:. python scripts/quality_gate.py
python -m build
python -m twine check dist/*
python scripts/verify_artifact.py \
  dist/openinfra-0.34.4-py3-none-any.whl \
  dist/openinfra-0.34.4.tar.gz
PYTHONPATH=src:. python scripts/release_packaging_audit.py \
  --project-root . \
  --output-dir artifacts/release-packaging-local \
  --source-date-epoch 1784332800 \
  --ephemeral-signing-key
```

## Qualification GATE-11 cible

La qualification Oracle doit être exécutée explicitement avec l’édition Enterprise :

```bash
openinfra-gate11 contracts ...
openinfra-gate11 oracle --edition enterprise ...
openinfra-gate11 saml ...
openinfra-gate11 team-sync ...
openinfra-gate11 systemd ...
openinfra-gate11 assemble ...
openinfra-gate11 evaluate ...
```

La décision finale doit porter sur les mêmes candidat, commit complet et environnement, avec cinq preuves fraîches et des empreintes SHA-256 valides.
