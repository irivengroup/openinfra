# Rapport de validation — OpenInfra Python POO v0.34.3

## Décision

La version **0.34.3** atteint le niveau **GO pour la livraison logicielle locale** : le code, les tests, la couverture, les contrôles statiques, les contrats de gouvernance, le frontend et le packaging sont cohérents et validés dans l'environnement de construction.

La promotion **REL-12 / GATE-11 en environnement cible reste NO-GO** tant que le jeu complet de preuves live n'a pas été collecté sur :

- une instance Oracle 19c réelle avec le compte applicatif final ;
- un fournisseur d'identité SAML réel ;
- le service Team Sync connecté à l'annuaire cible ;
- un hôte Linux systemd exécutant les unités OpenInfra natives.

La 0.34.3 ne prétend donc pas certifier un environnement externe absent. Elle fournit le mécanisme reproductible, borné et fail-closed permettant de réaliser cette certification.

## Objet de la version

La version 0.34.2 avait établi la parité structurelle complète entre les 57 migrations PostgreSQL et Oracle. La version **0.34.3 ferme le volet opérationnel de GATE-11** en ajoutant une chaîne de qualification et de promotion fondée sur des preuves vérifiables.

Les principaux ajouts sont :

- une commande installée `openinfra-gate11` ;
- des collecteurs distincts pour les contrats statiques, Oracle live, SAML live, Team Sync live et systemd live ;
- une politique de promotion versionnée définissant cinq preuves obligatoires et leur durée maximale de validité ;
- l'épinglage de chaque preuve par SHA-256 ;
- le contrôle du candidat, du commit Git complet, de l'environnement cible et de la fraîcheur des preuves ;
- l'assemblage déterministe d'un manifeste de promotion ;
- une évaluation fail-closed refusant toute preuve manquante, périmée, modifiée, incohérente ou en échec ;
- un workflow GitHub Actions self-hosted pour la qualification réelle ;
- l'intégration de GATE-11 au Quality Gate global, au wheel, au sdist et au smoke hors dépôt ;
- un runbook d'exploitation complet pour Oracle, SAML, Team Sync et systemd.

Aucun secret, assertion SAML complète ni jeton d'identité n'est conservé dans les preuves. Seuls les compteurs, empreintes, identifiants bornés et métadonnées nécessaires à l'audit sont persistés.

## Contrat GATE-11 livré

La politique `docs/release/advanced-identity-oracle-promotion-policy.json` impose les preuves suivantes :

| Preuve | Fraîcheur maximale |
|---|---:|
| `gate11-contracts` | 168 heures |
| `gate11-oracle-live` | 24 heures |
| `gate11-saml-live` | 24 heures |
| `gate11-team-sync-live` | 24 heures |
| `gate11-systemd-live` | 24 heures |

Le workflow `.github/workflows/advanced-identity-oracle.yml` réalise :

- la matrice statique Python 3.11 et 3.13 ;
- la génération et la validation de la preuve contractuelle ;
- Ruff, mypy, Bandit, tests, OpenAPI, build et smoke du wheel ;
- un job live conditionnel sur runner `self-hosted`, `linux`, `openinfra-gate11` ;
- la collecte des quatre preuves externes ;
- l'assemblage et l'évaluation du manifeste ;
- la conservation des preuves de promotion pendant 365 jours.

Le job live ne s'exécute que lorsque `OPENINFRA_GATE11_LIVE_TESTS=true` est défini dans les variables GitHub de l'environnement qualifié.

## Socle Oracle préservé

La 0.34.3 conserve et revalide le socle livré en 0.34.2 :

- **57 migrations PostgreSQL** ;
- **57 migrations Oracle 19c correspondantes** ;
- manifeste déterministe avec empreintes PostgreSQL et Oracle ;
- générateur PostgreSQL vers Oracle en mode fail-closed ;
- exécuteur Oracle avec états `applying`, `applied` et `failed` ;
- contrôle de dérive et reprise contrôlée ;
- compatibilité avec l'ancien historique Oracle limité à `0001_document_state.sql` ;
- readiness exigeant l'application cohérente de l'intégralité du catalogue.

PostgreSQL reste le backend par défaut. Oracle demeure un choix explicite pour les éditions Pro et Enterprise côté serveur.

## Résultats de validation

| Contrôle | Résultat |
|---|---:|
| Catalogue PostgreSQL | **57 migrations PASS** |
| Catalogue Oracle | **57 migrations PASS** |
| Manifeste Oracle | **57 entrées PASS** |
| Générateur Oracle `--check` | **PASS** |
| Tests unitaires | **758/758 PASS** |
| Tests d'intégration | **727/727 PASS** |
| Tests d'architecture | **3/3 PASS** |
| Tests de performance | **11/11 PASS** |
| Total Python | **1 499/1 499 PASS** |
| Couverture globale | **47 144 lignes, 928 non couvertes, 98,0316 % PASS** |
| Seuil `--cov-fail-under=98` | **PASS sans baisse de seuil ni nouvelle exclusion** |
| Nouveau collecteur GATE-11 | **560/561 lignes, 99 %** |
| Ruff format | **450 fichiers PASS** |
| Ruff lint | **PASS** |
| mypy strict | **128 modules PASS** |
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
| Quality Gate global | **PASS** |
| Security gate source : secrets, SAST et RBAC | **PASS** |
| Benchmark ASGI — API health p95 | **20,846 ms / seuil 150 ms PASS** |
| Benchmark ASGI — Web bootstrap p95 | **0,274 ms / seuil 150 ms PASS** |
| Benchmark ASGI — BFF proxy p95 | **0,493 ms / seuil 200 ms PASS** |
| Pagination keyset profonde p95 | **0,026089 ms / seuil 1 ms PASS** |
| Build wheel et sdist | **PASS** |
| `twine check` wheel et sdist | **PASS** |
| Vérification du contenu des artefacts | **PASS** |
| Installation et smoke du wheel hors dépôt | **PASS** |
| Packaging reproductible, SBOM, checksums et rollbacks | **7/7 contrôles PASS** |
| Identité de signature de publication | **NO-GO : clé locale éphémère non fiable** |
| Certification sécurité de publication externe | **NO-GO : contrôles réseau, conteneur et DAST indisponibles** |

## Couverture

La couverture a été recalculée sur l'intégralité des suites de la version 0.34.3. Les fichiers d'intégration ont été segmentés uniquement pour respecter la limite de durée de l'environnement d'exécution ; leurs résultats ont été cumulés avec `coverage --append` sans réutiliser une mesure antérieure.

Résultat exact :

```text
Lignes mesurées  : 47 144
Lignes couvertes : 46 216
Lignes manquantes: 928
Taux exact       : 98,03156287120312 %
```

L'unique ligne non couverte du nouveau module GATE-11 est la garde d'exécution directe `if __name__ == "__main__"`. Aucun pragma d'exclusion ni abaissement du seuil n'a été ajouté pour atteindre le résultat.

## Packaging et publication

Les distributions ont été construites depuis le sdist puis contrôlées avec `twine check` et le validateur de contenu du projet. Le wheel a ensuite été installé avec ses dépendances dans un environnement Python neuf, hors du dépôt source.

Les sept contrôles de packaging passent :

1. wheel et sdist reproductibles octet pour octet avec `SOURCE_DATE_EPOCH=1784332800` ;
2. contenu runtime et release complet ;
3. dry-run et rollback transactionnel des six profils d'installation ;
4. SBOM SPDX 2.3 déterministe ;
5. manifeste Ed25519 généré et vérifié ;
6. manifeste SHA-256 généré et vérifié ;
7. installation isolée, `pip check` et smoke du wheel.

La certification de publication reste néanmoins **NO-GO** avec les preuves locales, car la signature a été produite avec une clé Ed25519 éphémère. Une clé de release approuvée, protégée et fournie par le pipeline de publication est obligatoire pour transformer ce contrôle en certification de production.

Le smoke hors dépôt confirme notamment :

- la version module et distribution `0.34.3` ;
- la commande `openinfra version` ;
- les six points d'entrée, dont `openinfra-gate11` ;
- les 57 migrations et la dernière migration `0057_federated_identity_team_sync.sql` ;
- les actifs Oracle, SAML, Team Sync, systemd, OpenAPI, Web et promotion.

## Sécurité de publication

Le contrôle local de sécurité des sources passe pour :

- la détection de secrets et la cohérence des workflows ;
- Bandit SAST ;
- les régressions RBAC et authentification.

La **certification de sécurité de publication** reste distinctement NO-GO dans cet environnement :

- `pip-audit` et l'audit npm en ligne ne peuvent pas joindre leurs bases de vulnérabilités ;
- Docker et Trivy ne sont pas disponibles pour scanner le système de fichiers et l'image ;
- l'API et le frontend ne sont pas démarrés, donc la sonde DAST HTTP ne peut pas aboutir.

Ces résultats sont enregistrés comme `not-run` ou `failed`, jamais convertis en PASS. Les contrôles correspondants restent bloquants dans les workflows de promotion disposant des services et accès requis.

## Non-régression

- PostgreSQL reste le backend par défaut.
- Oracle reste un choix explicite Pro/Enterprise serveur.
- Aucun endpoint métier, aucune commande CLI publique et aucune permission RBAC n'est supprimé.
- SAML, LDAP/IPA avancé, Team Sync, API, Web et runtime systemd conservent leurs contrats publics.
- Les 57 migrations PostgreSQL et Oracle sont conservées sans dérive.
- Le thème et la charte graphique approuvés ne sont pas modifiés.
- Les distributions restent compatibles Python 3.11 et versions ultérieures déclarées par le projet.
- Les preuves GATE-11 ne contiennent aucun secret d'authentification réutilisable.

## Validations non exécutables dans l'environnement courant

### Oracle 19c réel

Aucune instance Oracle 19c ni client Oracle n'est disponible dans l'environnement de construction. Les 57 migrations n'ont donc pas été appliquées ici sur un schéma Oracle réel avec le compte applicatif final.

La qualification cible doit au minimum valider :

- l'application complète sur schéma vierge ;
- la reprise depuis l'ancien historique `0001_document_state` ;
- les permissions minimales du compte applicatif ;
- les contraintes, index, partitions et objets PL/SQL effectivement créés ;
- la readiness après redémarrage ;
- la détection de dérive ;
- la restauration opérationnelle après sauvegarde, Oracle réalisant des commits implicites sur les DDL.

### SAML, Team Sync et systemd réels

L'environnement ne fournit ni IdP SAML réel, ni annuaire externe qualifié pour Team Sync, ni hôte systemd actif. Les contrats, scénarios simulés et branches d'erreur passent, mais les quatre preuves live restent à produire sur l'infrastructure cible avec `openinfra-gate11`.

### Audit Python en ligne

`pip-audit` 2.10.1 est installé, mais son backend PyPI ne peut pas résoudre `pypi.org` dans l'environnement courant. Aucun résultat PASS n'est revendiqué pour l'audit Python local. Le contrôle reste obligatoire et bloquant dans GitHub Actions avec accès au service de vulnérabilités.

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
PYTHONPATH=src:. python scripts/quality_gate.py
python -m build
python -m twine check dist/*
python scripts/verify_artifact.py \
  dist/openinfra-0.34.3-py3-none-any.whl \
  dist/openinfra-0.34.3.tar.gz
```

## Commandes de qualification GATE-11 cible

Les paramètres exacts sont détaillés dans `docs/runbooks/ADVANCED_IDENTITY_ORACLE_SYSTEMD.md`. La séquence de promotion est :

```bash
openinfra-gate11 contracts ...
openinfra-gate11 oracle ...
openinfra-gate11 saml ...
openinfra-gate11 team-sync ...
openinfra-gate11 systemd ...
openinfra-gate11 assemble ...
openinfra-gate11 evaluate ...
```

La commande `evaluate` doit terminer avec succès sur les cinq preuves correspondant au même candidat, au même commit complet et au même environnement avant toute promotion REL-12.
