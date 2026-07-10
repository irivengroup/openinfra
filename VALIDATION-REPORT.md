# OpenInfra v0.29.91 — Rapport de validation

Date de validation : `2026-07-10`  
Release : `0.29.91`  
Périmètre : `P15 / EPIC-1504 — Conformité réseau « golden configuration »`

## Résultat global

La livraison ajoute une comparaison gouvernée entre configurations réseau de référence et configurations observées. Elle détecte les dérives sans appliquer automatiquement de changement aux équipements et sans créer une seconde source de vérité métier.

- Tests Python collectés : **725** dans **99 fichiers**.
- Tests unitaires : **289 PASS**.
- Tests d’intégration : **433 PASS**.
- Tests d’architecture : **3 PASS**.
- Couverture globale exacte : **98,0118460838 %** — `23 663 / 24 143` lignes couvertes.
- Seuil bloquant : **98 % PASS**.
- Tests frontend Node.js : **20 PASS**.
- Lint frontend, accessibilité JSX, contrat WCAG et build Vite : **PASS**.
- `npm audit --audit-level=high` : **0 vulnérabilité**.

Les 99 fichiers de tests ont été exécutés par groupes isolés avec fragments de couverture distincts, puis consolidés. La CLI principale a été segmentée par classes de tests afin d’éviter le timeout monolithique sans omettre de scénario.

## Conformité réseau « golden configuration »

Garanties validées :

- baseline JSON versionnée par équipement RSOT et plateforme ;
- propriétaire, environnement, justification et période de validité ;
- retrait non destructif et conservation de l’historique ;
- observations immuables et idempotentes ;
- détection des charges contradictoires pour une même clé d’idempotence ;
- validation de documents JSON structurés ;
- limites de taille, profondeur et nombre de nœuds ;
- rejet des secrets, mots de passe, jetons et matériaux de clé privée ;
- chemins JSON ignorés et chemins critiques gouvernés ;
- comparaison récursive déterministe ;
- dérives `missing`, `unexpected`, `mismatch` et `type-mismatch` ;
- états `compliant`, `drift` et `missing-observation` ;
- détection des incompatibilités de plateforme et d’équipement ;
- isolation stricte par tenant ;
- permissions `network_config.read` et `network_config.write` ;
- rôles `network-config:reader` et `network-config:operator` ;
- audit des baselines, retraits, observations et évaluations ;
- pagination bornée et détection des curseurs cycliques ou non progressifs ;
- persistance JSON et PostgreSQL ;
- migration PostgreSQL `0043_network_config_compliance.sql`, partitionnée et indexée ;
- six commandes CLI, six routes HTTP/OpenAPI et six opérations web FR/EN ;
- aucune remédiation automatique ni écriture directe sur les équipements réseau.

## Qualité, sécurité et typage

- `ruff format --check src tests scripts docker installers` : **PASS**, 179 fichiers.
- `ruff check src tests scripts docker installers` : **PASS**.
- `mypy src/openinfra` : **PASS**, 64 modules source.
- `bandit -q -r src/openinfra` : **PASS**.
- `python scripts/security_gate.py --project-root .` : **PASS**.
- `python scripts/quality_gate.py` : **PASS** sur la couverture consolidée.
- `python -m compileall -q src tests scripts docker installers` : **PASS**.
- Architecture POO stricte : **PASS**.
- Validation frontend React/runtime packagé : **PASS**.

## Frontend

- `npm ci --prefix web --ignore-scripts --no-audit --no-fund` : **PASS**.
- `npm --prefix web run lint` : **PASS**.
- `npm --prefix web run a11y` : **PASS**.
- `npm --prefix web run a11y:jsx` : **PASS**.
- `npm --prefix web test` : **20 PASS**.
- `npm --prefix web run build` : **PASS**, Vite 8.1.4.
- `npm --prefix web audit --audit-level=high` : **0 vulnérabilité**.
- Parité React/runtime packagé pour les six opérations de conformité réseau : **PASS**.
- Navigation responsive, accessibilité WCAG et traductions FR/EN : **PASS**.

## CDC, roadmap et installateurs

Aucune nouvelle recommandation ne modifie l’existant : EPIC-1504 était déjà défini dans la roadmap. Le CDC et la roadmap ne sont donc ni modifiés ni réémis.

- Comparaison des contenus byte-for-byte avec la v0.29.90 : **PASS**, 241 fichiers contractuels.
- Empreinte agrégée inchangée : `4af183c96e88196b6aa44f5ecd5a57ffc768c1c9cb54bbf0d8752af60e34a90c`.
- CDC v4.8.1 : **PASS** — 825 exigences et 625 tests contractuels.
- Roadmap v2 : **PASS** — 19 phases, 115 epics, 8 gates et 94 validations.
- Six installateurs autonomes Lite/Pro/Enterprise : **PASS**.
- Alignement Enterprise : **PASS**.

## Packaging et smoke tests

- Wheel : `openinfra-0.29.91-py3-none-any.whl` — **PASS**.
- Sdist : `openinfra-0.29.91.tar.gz` — **PASS**.
- Vérification d’artefact : **PASS**.
- Installation du wheel dans une cible vierge : **PASS**.
- Origine du module vérifiée dans la cible d’installation, hors arbre source : **PASS**.
- Version runtime et métadonnées : `0.29.91` — **PASS**.
- Trois points d’entrée console : **PASS**.
- OpenAPI packagé : **PASS**.
- Trois routes Graphe, six routes Matrice de flux, sept routes Certificats/PKI et six routes Conformité réseau : **PASS**.
- Trois assets web runtime : **PASS**.
- Migrations packagées : **43**, dernière migration `0043_network_config_compliance.sql` — **PASS**.
- Sdist et wheel sans cache, `node_modules`, `web/dist`, fichier de couverture ni artefact de build imbriqué : **PASS**.

## Contrôles limités par l’environnement

- `pip-audit --strict --requirement requirements/security-audit.txt` a été lancé mais reste **non concluant** : le runner ne peut pas résoudre `pypi.org`.
- Aucun daemon Docker ou Podman n’est disponible.
- Aucun serveur PostgreSQL live n’est disponible ; les migrations, adaptateurs, conversions, contraintes, index et politiques SQL sont validés statiquement et par tests simulés.
- La recette Chromium visuelle n’est pas disponible dans ce conteneur.
