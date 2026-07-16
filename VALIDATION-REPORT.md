# Rapport de validation — OpenInfra Python POO v0.33.9

## Objet de la livraison

La version **0.33.9** stabilise trois régressions indépendantes apparues dans les validations et dans l’espace de gestion DCIM :

1. le job CI `Discovery multisource reconciliation regression` échouait parce que le contrat de la racine HTTP n’intégrait pas les routes Kubernetes déjà livrées en 0.33.8 ;
2. le workflow `Validate EPIC-1806 support model` exécutait le validateur Support Readiness sans installer préalablement le package OpenInfra ;
3. le catalogue agrégé et plusieurs opérations CRUD DCIM accédaient aux repositories PostgreSQL hors `UnitOfWork`, provoquant :

```text
postgresql operation requires an active unit of work
```

Aucune migration PostgreSQL, route API, commande CLI, permission RBAC ou modification de thème n’est introduite.

## Correctifs livrés

### Réconciliation Discovery multisource

Le contrat d’intégration de la racine HTTP expose désormais explicitement le groupe de routes Kubernetes existant. Le job Discovery vérifie de nouveau l’ensemble cohérent domaine, réconciliation, CLI, HTTP, Web et migrations sans faux négatif lié à une attente obsolète.

### Support Readiness — EPIC-1806

Le workflow dédié installe maintenant le projet en mode editable avant d’exécuter `scripts/support_readiness.py` :

```bash
python -m pip install -e .
```

Le contrat d’intégration du workflow rend cette étape obligatoire afin d’éviter toute nouvelle exécution du validateur sans package importable.

### Frontières transactionnelles DCIM

Les lectures, validations et mutations des espaces de gestion suivants sont désormais exécutées dans un `UnitOfWork` actif :

- Sites ;
- Bâtiments ;
- Étages ;
- Salles ;
- Zones ;
- Châssis/Racks ;
- catalogue agrégé `/api/v1/dcim/topology-catalog`.

Les actions de consultation, création, modification, suppression, capacité et listing partagent ainsi le même contrat transactionnel sur les backends JSON et PostgreSQL. Le paramètre `include_retired=true` est également propagé au listing des racks du catalogue.

Un repository gardé de non-régression refuse immédiatement toute opération DCIM exécutée hors unité de travail et couvre le cycle de vie complet de la topologie.

## Validation exécutée

### Suites de régression Python

- Discovery multisource : **106/106 PASS** ;
- Transactional outbox et workers spécialisés : **63/63 PASS** ;
- Support Readiness EPIC-1806 : **19/19 PASS** ;
- cycle de vie et discipline transactionnelle DCIM : **14/14 PASS** ;
- contrats de release, documentation, workflows, runtime Docker minimal, performance frontend et promotion scale-out : **35/35 PASS**.

Les suites ciblées ont été exécutées avec l’auto-chargement des plugins pytest externes désactivé afin d’isoler l’environnement du dépôt :

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src \
python -m pytest -p pytest_cov.plugin -q --no-cov <suites ciblées>
```

### Qualité statique

- Ruff format : **PASS** ;
- Ruff lint : **PASS** ;
- mypy : **120 fichiers source conformes** ;
- `compileall` : **PASS** ;
- Bandit sur `src/openinfra` : **PASS**, aucun finding bloquant ;
- `scripts/security_gate.py` : **PASS**.

### Documentation et contrats API

- OpenAPI produit : **PASS** ;
- OpenAPI CDC : **PASS** ;
- documentation GA version 0.33.9 : **PASS** ;
- manifeste documentaire GA : **PASS** ;
- Support Readiness : **PASS**.

### Frontend

- tests Node : **79/79 PASS** ;
- ESLint : **PASS** ;
- contrôles JSX et accessibilité : **PASS** ;
- WCAG 2.2 AA : **PASS** ;
- build Vite : **PASS** ;
- bundle initial : **2 556 octets bruts / 1 264 octets gzip** ;
- chunks dynamiques : **13** ;
- `npm audit --audit-level=high` : **0 vulnérabilité** ;
- `npm audit --omit=dev --audit-level=high` : **0 vulnérabilité**.

### Packaging

- wheel `openinfra-0.33.9-py3-none-any.whl` : **PASS** ;
- sdist `openinfra-0.33.9.tar.gz` : **PASS** ;
- contrôle du contenu des artefacts : **PASS** ;
- build du wheel depuis le contexte Docker minimal : **PASS** ;
- smoke du wheel installé hors de l’arbre source : **PASS** ;
- version installée : **0.33.9** ;
- routes Kubernetes : **16** ;
- migrations : **56** ;
- dernière migration : `0056_kubernetes_gitops_drift.sql` ;
- assets runtime : **20**.

Le sdist embarque notamment le workflow EPIC-1806 corrigé, le test transactionnel DCIM, le contrat HTTP Discovery et les services DCIM modifiés.

## Non-régression visuelle

Le fichier `web/src/openinfra-theme.css` est bit pour bit identique à celui de la version 0.33.8 :

```text
fb7feabe378613ac41efb18db94b0d95a8faa916b6f782c9fd0ea2b0d8e9fcf4
```

Aucune couleur, surface, transparence, règle de survol ou autre comportement du thème n’a été modifié.

## Validations non exécutables localement

- la suite pytest globale a été lancée mais n’a pas terminé dans la fenêtre locale de **30 minutes** ; le seuil de couverture contractuel **>= 98 %** doit donc être recalculé et confirmé par GitHub Actions ;
- `pip-audit --strict --requirement requirements/security-audit.txt` n’a pas pu interroger PyPI à cause d’un échec de résolution DNS vers `pypi.org` ; aucun résultat de vulnérabilité Python n’est donc revendiqué localement ;
- le binaire Docker n’est pas disponible dans l’environnement courant : le build Docker réel et les smokes Docker Compose restent à confirmer par la CI ou sur un poste équipé de Docker.

Ces limites n’affectent pas les suites de régression ciblées, les contrôles statiques, le build Python, le build frontend ni le smoke du wheel installé, tous exécutés avec succès.

## Documentation de planification

Le **CDC 4.9.0** et la **roadmap v2.2** restent inchangés. Cette livraison corrige des régressions d’implémentation et de CI sans nouvelle exigence fonctionnelle, réglementaire ou architecturale.
