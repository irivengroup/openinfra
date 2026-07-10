# OpenInfra v0.29.90 — Rapport de validation

Date de validation : `2026-07-10`  
Release : `0.29.90`  
Périmètre : `P15 / EPIC-1503 — Certificats et PKI`

## Résultat global

La livraison ajoute un inventaire PKI gouverné pour les certificats métier et les observations d'endpoints, sans stocker de clé privée et sans confondre ces actifs avec les identités techniques des agents Discovery.

- Tests Python collectés : **712** dans **96 fichiers**.
- Tests unitaires : **284 PASS**.
- Tests d’intégration : **425 PASS**.
- Tests d’architecture : **3 PASS**.
- Couverture globale exacte : **98,0005126891 %** — `22 938 / 23 406` lignes couvertes.
- Seuil bloquant : **98 % PASS**.
- Tests frontend Node.js : **20 PASS**.
- Lint frontend, accessibilité JSX, contrat WCAG et build Vite : **PASS**.
- `npm audit --audit-level=high` : **0 vulnérabilité**.

Les 96 fichiers de tests ont été exécutés dans des processus isolés avec fragments de couverture distincts, puis consolidés. Cette orchestration évite le timeout de la suite monolithique et empêche qu’un état partagé masque un échec.

## Inventaire Certificats et PKI

Garanties validées :

- import de chaînes PEM X.509 avec validation cryptographique ;
- extraction du sujet, de l’émetteur, du numéro de série, des dates, du CN, des SAN, des usages de clé, de l’algorithme et de l’empreinte SHA-256 ;
- prise en charge des signatures RSA, ECDSA, DSA, Ed25519 et Ed448 ;
- vérification de continuité sujet/émetteur et de la signature de chaque maillon ;
- limite de 16 certificats par chaîne ;
- rejet explicite de tout matériau de clé privée dans un bundle PEM ;
- inventaire révisable et historisé avec propriétaire, environnement et objet RSOT associé ;
- observations d’endpoints immuables et idempotentes ;
- détection des charges contradictoires pour une même clé d’idempotence ;
- contrôle hostname/SAN avec wildcard limité à un seul label ;
- états `healthy`, `warning`, `critical`, `expired`, `not-yet-valid` et `retired` ;
- seuils d’expiration gouvernés ;
- isolation stricte par tenant ;
- permissions `certificate.read` et `certificate.write` ;
- rôles `certificate:reader` et `certificate:operator` ;
- audit des imports, retraits, observations et évaluations ;
- pagination bornée et détection des curseurs cycliques ou non progressifs ;
- persistance JSON et PostgreSQL ;
- migration PostgreSQL `0042_certificate_pki_inventory.sql`, partitionnée et indexée ;
- sept commandes CLI, sept routes HTTP/OpenAPI et sept opérations web FR/EN.

## Qualité, sécurité et typage

- `ruff format --check src tests scripts docker installers` : **PASS**, 175 fichiers.
- `ruff check src tests scripts docker installers` : **PASS**.
- `mypy src/openinfra` : **PASS**, 62 modules source.
- `bandit -q -r src/openinfra` : **PASS**.
- `python scripts/security_gate.py --project-root .` : **PASS**.
- `python scripts/quality_gate.py` : **PASS**.
- `python -m compileall -q src tests scripts docker installers` : **PASS**.
- Architecture POO stricte : **PASS** ; les règles PKI sont encapsulées dans `CertificatePkiRules`.
- Validation frontend React/runtime packagé : **PASS**.

## Frontend

- `npm ci --prefix web --ignore-scripts --no-audit --no-fund` : **PASS**.
- `npm --prefix web run lint` : **PASS**.
- `npm --prefix web run a11y` : **PASS**.
- `npm --prefix web run a11y:jsx` : **PASS**.
- `npm --prefix web test` : **20 PASS**.
- `npm --prefix web run build` : **PASS**, Vite 8.1.4.
- `npm --prefix web audit --audit-level=high` : **0 vulnérabilité**.
- Parité React/runtime packagé pour les sept opérations PKI : **PASS**.
- Champs PEM multiligne, navigation responsive et traductions FR/EN : **PASS**.

## CDC, roadmap et installateurs

Aucune nouvelle recommandation ne modifie l’existant : EPIC-1503 était déjà défini dans la roadmap. Le CDC et la roadmap ne sont donc ni modifiés ni réémis.

- Comparaison byte-for-byte avec la v0.29.89 : **PASS**, 241 fichiers contractuels.
- Empreinte agrégée inchangée : `ae2fe54e60434a6bfe0f782bfec692b09613bd75dd7cefdc0300cde172f26e7a`.
- CDC v4.8.1 : **PASS** — 825 exigences et 625 tests contractuels.
- Roadmap v2 : **PASS** — 19 phases, 115 epics, 8 gates et 94 validations.
- Six installateurs autonomes Lite/Pro/Enterprise : **PASS**.
- Alignement Enterprise : **PASS**.

## Packaging et smoke tests

- Wheel : `openinfra-0.29.90-py3-none-any.whl` — **PASS**.
- Sdist : `openinfra-0.29.90.tar.gz` — **PASS**.
- Vérification d’artefact : **PASS**.
- Installation du wheel dans une cible vierge : **PASS**.
- Origine du module vérifiée dans la cible d’installation, hors arbre source : **PASS**.
- Version runtime et métadonnées : `0.29.90` — **PASS**.
- Trois points d’entrée console : **PASS**.
- OpenAPI packagé : **PASS**.
- Trois routes Graphe, six routes Matrice de flux et sept routes Certificats/PKI : **PASS**.
- Trois assets web runtime : **PASS**.
- Migrations packagées : **42**, dernière migration `0042_certificate_pki_inventory.sql` — **PASS**.
- Sdist et wheel sans cache, `node_modules`, `web/dist`, fichier de couverture ni artefact de build imbriqué : **PASS**.

## Contrôles limités par l’environnement

- `pip-audit --strict --requirement requirements/security-audit.txt` a été lancé mais reste **non concluant** : le runner ne peut pas résoudre `pypi.org`.
- Aucun daemon Docker ou Podman n’est disponible.
- Aucun serveur PostgreSQL live n’est disponible ; les migrations, adaptateurs, conversions, contraintes, index et politiques SQL sont validés statiquement et par tests simulés.
- La recette Chromium visuelle n’est pas disponible dans ce conteneur.
