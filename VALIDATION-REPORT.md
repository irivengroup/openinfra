# OpenInfra v0.29.105 — Rapport de validation

Date : `2026-07-11`  
Release : `0.29.105`  
Nature : `correctif prioritaire de performance et de fiabilité du portail web`

## Périmètre livré

- Réduction du fan-out initial du Dashboard de neuf requêtes à deux : `/bootstrap.json` puis `/ready` en arrière-plan.
- Affichage immédiat du shell accessible sans attendre le backend.
- Chargement paresseux des référentiels pays, organisations, filiales, partenaires et topologie DCIM uniquement lorsqu’un formulaire en dépend.
- Déduplication des requêtes de catalogues simultanées et protection contre les réponses tardives d’une opération devenue inactive.
- Compression gzip déterministe des assets texte supérieurs ou égaux à 1 024 octets.
- ETag distinct pour les représentations identité et gzip, `Vary: Accept-Encoding` et réponses `304 Not Modified`.
- Cache `immutable` d’un an pour les URL versionnées et revalidation bornée pour les accès non versionnés.
- Maintien de `no-store` pour les réponses dynamiques, la configuration, le statut, la readiness et le proxy API.
- Parité du runtime statique packagé et du portail React, sans modification des contrats métier.
- Documentation d’exploitation, tests de budgets réseau et gate GitHub Actions dédiés.

## Mesures de transfert du runtime packagé

| Asset | Brut | Gzip déterministe | Ratio |
|---|---:|---:|---:|
| `bootstrap.min.css` | 232 111 octets | 31 119 octets | 13,41 % |
| `openinfra-web.css` | 47 009 octets | 8 741 octets | 18,59 % |
| `openinfra-web.js` | 266 231 octets | 47 987 octets | 18,02 % |
| `openinfra-i18n.js` | 61 713 octets | 19 613 octets | 31,78 % |
| `openinfra-form-fields.js` | 12 807 octets | 3 499 octets | 27,32 % |
| **Total** | **619 871 octets** | **110 959 octets** | **17,90 %** |

Budgets bloquants validés : JavaScript principal `< 55 Ko gzip`, ensemble initial `< 125 Ko gzip`, ratio global `< 22 %`.

## Résultats automatisés

### Python

- Suite exhaustive : **948 tests réussis** en **162,76 s**.
- Couverture globale : **98,004548 %** (`34 478 / 35 180` instructions).
- Seuil contractuel : **98 % — PASS**.
- Ruff format : **277 fichiers conformes**.
- Ruff lint strict : **PASS**.
- mypy strict : **88 modules — PASS**.
- `compileall` : **PASS**.
- Tests Web ciblés : **20 réussis**.

### Frontend

- Tests Node.js : **47 réussis**.
- Contrat des assets statiques : **PASS**.
- ESLint/JSX : **PASS**.
- Contrat WCAG 2.2 AA : **PASS**.
- Build Vite de production : **PASS**.
- `npm ci` : **220 packages installés, 0 vulnérabilité signalée**.
- Parité React/runtime statique : **PASS**.

### Cache, transport et démarrage

- Endpoint agrégé `/bootstrap.json` : **PASS**.
- Sonde `/ready` non bloquante : **PASS**.
- Absence de catalogues métier au chargement du Dashboard : **PASS**.
- Chargement à la demande et déduplication : **PASS**.
- Négociation gzip avec prise en charge de `q=0` et valeurs invalides : **PASS**.
- ETag identité/gzip distincts : **PASS**.
- Réponse conditionnelle `304` : **PASS**.
- Cache immutable des URL `?v=0.29.105` : **PASS**.
- Réponses dynamiques conservées en `no-store` : **PASS**.

### Sécurité

- Bandit SAST : **PASS**.
- Security gate secrets/CI/dépendances : **PASS**.
- Traversée de chemins, injection de token backend et sanitisation des erreurs proxy : **PASS**.
- Aucun secret ou mécanisme d’authentification déplacé dans le navigateur.
- `pip-audit` a été lancé avec la commande CI officielle, mais la résolution DNS de `pypi.org` a échoué dans l’environnement courant. Le gate CI strict reste configuré.

### API, CDC et roadmap

- OpenAPI principal : **PASS**.
- OpenAPI embarqué dans le CDC : **PASS**.
- Version OpenAPI : `0.29.105`.
- Nombre de paths OpenAPI : **318**.
- CDC v4.8.1 : **828 exigences / 628 tests — PASS**.
- Roadmap v2 : **19 phases / 115 epics / 8 gates / 97 tests — PASS**.
- CDC et roadmap non réémis : le correctif ne change aucun périmètre fonctionnel, architectural ou réglementaire.

### Base de données et migrations

- Total : **52 migrations PostgreSQL**.
- Dernière migration : `0052_multisite_disaster_recovery.sql`.
- Aucune migration ajoutée : le correctif concerne exclusivement le BFF et les assets Web.
- Les tests de régression JSON/PostgreSQL existants sont inclus dans les 948 tests réussis.

### Installateurs et runtime

- Six profils `install.ini` : **PASS**.
- Alignement Enterprise/CDC/roadmap : **PASS**.
- Validation des installateurs : **PASS**.
- Smoke runtime natif et unités systemd rendues : **PASS**.
- Docker et Podman absents de l’environnement ; les smokes conteneurisés restent des gates CI.

### Performance métier existante

Benchmark du graphe RSOT sur **5 000 nœuds** et **100 hubs SPOF** : **PASS**.

| Scénario | p95 mesuré | Seuil | Résultat |
|---|---:|---:|---|
| Parcours un niveau | 202,036 ms | 1 500 ms | PASS |
| Parcours filtré | 108,102 ms | 1 500 ms | PASS |
| Analyse SPOF | 223,525 ms | 5 000 ms | PASS |
| Pagination SPOF complète | 563,790 ms | 15 000 ms | PASS |

### Packaging

- Wheel : `openinfra-0.29.105-py3-none-any.whl`.
- sdist : `openinfra-0.29.105.tar.gz`.
- Vérification du contenu wheel : **PASS**.
- Installation du wheel dans un répertoire vierge : **PASS**.
- Smoke installé : version `0.29.105`, **19 routes multisites**, **52 migrations**, dernière migration `0052`, quatre assets runtime et trois points d’entrée publics : **PASS**.
- Le sdist contient la documentation de performance et le runbook de validation actualisé : **PASS**.

## Empreintes des packages Python

```text
openinfra-0.29.105-py3-none-any.whl
SHA-256: 600183334899bfcf3aa97ea69d704b462d381fd903c5b5ca25da3f1397ede862
Taille: 761664 octets

openinfra-0.29.105.tar.gz
SHA-256: b5f8cf44be9528efb100a808bddd869d094a10a7b5302988e0bec572aa69d8b8
Taille: 1564663 octets
```

## Risques résiduels

- Aucun test PostgreSQL réel n’a pu être exécuté localement ; aucune modification de schéma ou de dépôt n’est toutefois incluse dans cette version.
- Aucun smoke Docker/Podman n’a pu être exécuté localement.
- L’audit CVE Python distant dépend de la résolution DNS de PyPI et doit être confirmé par la CI.
- Les gains de temps ressentis dépendront de la latence réseau et du navigateur, mais les volumes transférés, le nombre de requêtes initiales et les politiques de cache sont désormais bornés par des tests bloquants.
