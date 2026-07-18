# Rapport de validation — OpenInfra Python POO v0.34.2

## Décision

La version **0.34.2** atteint le niveau **GO pour la livraison logicielle locale** : le code, les catalogues de migrations, les tests, la couverture, les contrôles statiques, la documentation et les distributions Python sont cohérents et validés.

La promotion **REL-12 / GATE-11 en environnement cible** reste **NO-GO** tant que les qualifications externes obligatoires n'ont pas été exécutées sur une instance Oracle 19c réelle, un fournisseur d'identité SAML réel et un hôte systemd actif.

## Objet de la version

OpenInfra disposait de 57 migrations PostgreSQL, mais d'une seule migration Oracle historique. La version 0.34.2 fournit désormais une parité complète et vérifiable :

- **57 migrations PostgreSQL** ;
- **57 migrations Oracle 19c correspondantes** ;
- mêmes numéros, noms fonctionnels et ordre d'application ;
- manifeste déterministe avec empreintes SHA-256 PostgreSQL et Oracle ;
- générateur PostgreSQL vers Oracle en mode fail-closed ;
- exécuteur Oracle avec journal d'état, reprise contrôlée et détection de dérive ;
- readiness Oracle conditionné à l'application cohérente du catalogue complet ;
- GATE-11 intégré aux workflows CI, au packaging et au smoke du wheel installé.

PostgreSQL reste le backend par défaut. Oracle doit être sélectionné explicitement et reste limité aux éditions Pro et Enterprise côté serveur.

## Implémentation validée

### Conversion PostgreSQL vers Oracle 19c

Le convertisseur prend en charge les constructions réellement utilisées par OpenInfra :

- types scalaires, UUID, JSON, tableaux sérialisés, CLOB et BLOB ;
- colonnes d'identité, séquences et valeurs par défaut ;
- contraintes d'intégrité, unicité et clés étrangères ;
- index fonctionnels Oracle pour préserver les index uniques partiels PostgreSQL ;
- partitionnement hash et création idempotente des objets associés ;
- `INSERT`, `UPDATE`, `DELETE`, `MERGE` et blocs PL/SQL ;
- identifiants protégés lorsqu'ils entrent en collision avec des mots réservés Oracle ;
- rejet des index PostgreSQL GIN sans équivalent direct ;
- contrôle conservateur de la taille des clés d'index Oracle.

Le générateur refuse toute migration laissant subsister une syntaxe PostgreSQL non transposée, une dérive manuelle, un index B-tree sur LOB, un identifiant incompatible ou une clé d'index dépassant la limite de sécurité définie.

### Exécution et reprise Oracle

L'exécuteur Oracle contrôle :

- la continuité du catalogue `0001` à `0057` ;
- le checksum de la migration Oracle ;
- le checksum de sa source PostgreSQL ;
- les états `applying`, `applied` et `failed` ;
- la dérive d'une migration déjà enregistrée ;
- la reprise contrôlée après interruption ;
- la compatibilité avec l'ancien historique limité à `0001_document_state.sql` ;
- l'application complète des 57 migrations avant de déclarer le backend prêt.

Les erreurs Oracle idempotentes acceptées sont bornées aux créations déjà réalisées et explicitement reconnues. Les autres erreurs restent bloquantes et sont enregistrées comme échec.

## Résultats de validation

| Contrôle | Résultat |
|---|---:|
| Catalogue PostgreSQL | **57 migrations PASS** |
| Catalogue Oracle | **57 migrations PASS** |
| Manifeste Oracle | **57 entrées PASS** |
| Générateur Oracle `--check` | **PASS** |
| Tests unitaires | **726/726 PASS** |
| Tests d'intégration | **724/724 PASS** |
| Tests d'architecture | **3/3 PASS** |
| Tests de performance | **11/11 PASS** |
| Total Python | **1 464/1 464 PASS** |
| Couverture globale | **46 583 lignes, 928 non couvertes, 98,01 % PASS** |
| Seuil `--cov-fail-under=98` | **PASS sans exclusion ajoutée** |
| Ruff format | **446 fichiers PASS** |
| Ruff lint | **PASS** |
| mypy strict | **127 modules PASS** |
| `compileall` | **PASS** |
| Bandit SAST sur `src/openinfra` | **PASS** |
| Tests frontend | **79/79 PASS** |
| Contrat statique frontend | **PASS** |
| Accessibilité WCAG 2.2 AA | **PASS** |
| ESLint JSX | **PASS** |
| Build Vite et budget initial | **PASS** |
| Audit npm | **0 vulnérabilité** |
| OpenAPI principal et CDC | **PASS** |
| Documentation GA | **PASS** |
| Support readiness EPIC-1806 | **PASS, clé éphémère non fiable pour promotion** |
| CDC v4.9.0 | **845 exigences PASS** |
| Roadmap v2.2 | **23 phases, 137 epics, 12 gates PASS** |
| Alignement Enterprise | **PASS** |
| Security gate | **PASS** |
| Build wheel et sdist | **PASS** |
| Vérification du contenu wheel/sdist | **PASS** |
| Installation du wheel hors dépôt | **PASS** |
| Smoke du wheel installé | **PASS** |

## Packaging vérifié

Le wheel et le sdist contiennent notamment :

- le catalogue PostgreSQL `0001` à `0057` ;
- le catalogue Oracle `0001` à `0057` ;
- `installers/migrations/oracle/manifest.json` ;
- l'exécuteur et les résolveurs Oracle ;
- la CLI de migration PostgreSQL/Oracle ;
- les unités systemd de migration, runtime secrets et Team Sync ;
- les runbooks Oracle, identité avancée et runtime natif ;
- les contrats OpenAPI, GA et de promotion.

Le smoke du wheel installé hors dépôt confirme la version 0.34.2, les 57 migrations, la dernière migration `0057_federated_identity_team_sync.sql`, les actifs runtime et les points d'entrée publics.

## Non-régression

- PostgreSQL reste le backend par défaut.
- Oracle reste un choix explicite Pro/Enterprise serveur.
- Aucun endpoint métier, aucune commande CLI publique et aucune permission RBAC ne sont supprimés.
- SAML, LDAP/IPA avancé, Team Sync, API, Web et runtime systemd conservent leurs contrats publics.
- La migration PostgreSQL 0057 et son correctif de nommage de partitions sont conservés.
- La charte graphique et le thème approuvé ne sont pas modifiés.
- Les distributions restent compatibles Python 3.11 et versions ultérieures déclarées par le projet.

## Validations non exécutables dans l'environnement courant

### Oracle 19c réel

Aucune instance Oracle 19c ni client Oracle n'est disponible dans l'environnement de construction. Les 57 migrations n'ont donc pas été appliquées ici sur un schéma Oracle réel avec le compte applicatif final. Cette qualification doit vérifier au minimum :

- application complète sur schéma vierge ;
- reprise depuis l'ancien historique `0001_document_state` ;
- permissions minimales du compte applicatif ;
- contraintes, index, partitions et objets PL/SQL effectivement créés ;
- readiness après redémarrage ;
- détection de dérive sur une migration déjà appliquée ;
- rollback opérationnel par restauration de sauvegarde, Oracle réalisant des commits implicites sur les DDL.

### SAML et systemd réels

L'environnement ne fournit ni fournisseur d'identité SAML réel ni hôte systemd actif (`systemctl` est hors ligne). Les validations cryptographiques et contractuelles passent, mais les scénarios d'exploitation réels restent à exécuter sur l'infrastructure cible.

### Audit Python en ligne

`pip-audit` n'a pas pu interroger PyPI en raison d'une indisponibilité DNS (`pypi.org` non résolu). Aucun résultat PASS n'est revendiqué pour ce contrôle local. Le job reste obligatoire et bloquant dans GitHub Actions, où l'accès au service de vulnérabilités doit être disponible.

### Docker Compose

Aucun moteur Docker ou Podman n'est installé dans l'environnement courant. Les contrats Compose et les tests associés passent, mais le redémarrage complet de la stack n'a pas été exécuté localement.

## Commandes de validation principales

```bash
PYTHONPATH=src:. python scripts/generate_oracle_migrations.py --check
PYTHONPATH=src:. python scripts/validate_oracle_migrations.py
PYTHONPATH=src:. pytest
PYTHONPATH=src:. ruff format --check src tests scripts docker installers
PYTHONPATH=src:. ruff check src tests scripts docker installers
PYTHONPATH=src:. mypy src/openinfra
PYTHONPATH=src:. bandit -q -r src/openinfra
python scripts/validate_openapi.py \
  docs/api/openapi.yaml \
  docs/specifications/OpenInfra-CDC-SFG-STG-v4.9.0/09-API/OpenAPI/openapi.yaml
python -m build
python scripts/verify_artifact.py dist/openinfra-0.34.2-py3-none-any.whl dist/openinfra-0.34.2.tar.gz
```
