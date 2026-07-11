# OpenInfra v0.29.96 — Rapport de validation

Date de validation : `2026-07-11`  
Release : `0.29.96`  
Périmètre : P16 / EPIC-1602 — simulation de changement et planification de migration

## Résultat global

La livraison ajoute un moteur de simulation gouverné sous **RSOT → Simulation & migrations**. Il évalue les conséquences techniques et métier de changements projetés, produit des rapports versionnés, calcule la préparation et propose des vagues consultatives. Le moteur travaille exclusivement sur des projections : il ne modifie aucune donnée de production, ne transmet aucun ordre d'exécution et ne crée aucun changement ITSM natif.

- Tests Python collectés et validés : **791 PASS** dans **121 fichiers**.
- Tests unitaires : **321 PASS**.
- Tests d'intégration : **466 PASS**.
- Tests d'architecture : **3 PASS**.
- Tests de performance : **1 PASS**.
- Couverture exacte : **98,0407 %**, soit **27 021 / 27 561** lignes couvertes.
- Seuil bloquant : **98 % PASS**.
- Tests frontend Node.js : **30 PASS**.
- Lint frontend, accessibilité JSX, contrat WCAG 2.2 AA et build Vite : **PASS**.
- Audit npm production : **0 vulnérabilité**.

La campagne Python existante de 785 tests a été exécutée par fragments exhaustifs. Les six tests supplémentaires de couverture de bord ont ensuite été exécutés avec les parcours Simulation concernés. Les lignes exécutées ont été consolidées par union des données Coverage.py ; le taux publié est calculé avec sa précision réelle et non avec l'arrondi d'affichage de Coverage.py.

## Fonctionnalités validées

- Scénarios tenant-aware, idempotents et versionnés.
- Dix types de changement : déplacement, ajout, retrait ou indisponibilité d'équipement, évolution VLAN, VRF, sous-réseau, DNS ou pare-feu, et indisponibilité PDU.
- Machine d'états explicite : `draft`, `queued`, `running`, `completed`, `failed`, `cancelled`.
- Validation stricte des cibles RSOT, états avant/après, hypothèses et charges JSON.
- Analyse multidimensionnelle : dépendances, flux, IPAM, énergie, refroidissement, coûts, services métier et qualité des données.
- Détection des impacts critiques, avertissements, blocages et hypothèses manquantes.
- Scores de préparation par scénario, application, actif, sous-réseau ou site.
- Groupes d'affinité et dépendances bloquantes déduits du graphe RSOT.
- Vagues de migration ordonnées, consultatives et résistantes aux cycles.
- Rapports d'impact immuables et versionnés.
- Comparaison déterministe avant/après entre deux rapports compatibles.
- Échecs d'exécution persistés et auditables.
- Garantie `production_mutation=false`, `execution_allowed=false`, `execution_order=false` et `itsm_native_change_created=false`.

## Interfaces

### REST

Neuf routes sont exposées :

- `GET /api/v1/simulation-scenarios` ;
- `GET /api/v1/simulation-scenarios/get` ;
- `POST /api/v1/simulation-scenarios/create` ;
- `POST /api/v1/simulation-scenarios/run` ;
- `POST /api/v1/simulation-scenarios/cancel` ;
- `GET /api/v1/impact-reports` ;
- `GET /api/v1/impact-reports/get` ;
- `GET /api/v1/scenario-comparisons` ;
- `POST /api/v1/scenario-comparisons/create`.

Les deux spécifications OpenAPI sont validées par un parseur YAML strict refusant les clés dupliquées :

- `docs/api/openapi.yaml` ;
- `docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/09-API/OpenAPI/openapi.yaml`.

### CLI

La parité publique est fournie sous une hiérarchie unique :

```bash
openinfra simulation create
openinfra simulation list
openinfra simulation get
openinfra simulation run
openinfra simulation cancel
openinfra simulation report
openinfra simulation reports
openinfra simulation compare
openinfra simulation comparisons
```

Les changements sont chargés depuis un tableau JSON non vide. Les fichiers absents, illisibles, mal formés ou contenant des éléments non objets sont refusés avant création.

### Interface web

- Entrée unique **RSOT → Simulation & migrations**.
- Aucun composant principal supplémentaire dans le header ou la sidebar.
- Six opérations alignées entre React et le runtime statique packagé.
- Formulaires typés, validations anticipées, erreurs accessibles et résultats structurés.
- Navigation clavier, lecteurs d'écran, contraste renforcé et réduction des mouvements conservés.

## Sécurité et autorisations

- Permissions dédiées : `simulation.read`, `simulation.write`, `simulation.execute`, `simulation.admin`.
- Isolation systématique par tenant.
- Validation stricte des identifiants, filtres, états et charges JSON.
- Audit des créations, exécutions, annulations et comparaisons.
- Outbox transactionnel PostgreSQL pour les événements critiques.
- Aucune commande de production ni secret stocké dans les scénarios.

## Persistance et migration

- Repository JSON pour le mode local et les tests déterministes.
- Repository PostgreSQL transactionnel pour la production.
- Migration `0045_simulation_migration_planning.sql`.
- Nombre total de migrations packagées : **45**.
- Tables partitionnées et indexées pour scénarios, changements, rapports, constats, scores, groupes, dépendances, vagues, comparaisons et outbox.
- Contraintes de tenant, statut, version, unicité et intégrité explicites.

## CI/CD et packaging

Les contrôles de livraison vérifient désormais :

- les modules domaine, application et mapping Simulation ;
- les neuf routes OpenAPI et runtime ;
- la migration `0045` et le total de 45 migrations ;
- les contrats CLI, HTTP, PostgreSQL, interface et sécurité ;
- le wheel, le sdist et l'installation hors arbre source ;
- la présence des assets, points d'entrée et autres fonctionnalités historiques.

## Qualité, sécurité et typage

- `ruff format --check src tests scripts docker installers` : **PASS**, 212 fichiers.
- `ruff check src tests scripts docker installers` : **PASS**.
- `mypy src/openinfra` : **PASS**, 72 fichiers source.
- `bandit -q -r src/openinfra` : **PASS**.
- `python -m compileall -q src tests scripts docker installers` : **PASS**.
- Validation OpenAPI stricte des deux spécifications : **PASS**.
- `python scripts/security_gate.py --project-root .` : **PASS**.
- `python scripts/quality_gate.py --project-root .` : **PASS**.
- `python scripts/native_runtime_smoke.py --project-root .` : **PASS**.
- `python scripts/validate_enterprise_alignment.py --project-root .` : **PASS**.
- Six profils d'installation Lite/Pro/Entreprise : **PASS**.
- `python scripts/validate_frontend.py --project-root .` : **PASS**.

## Frontend

- `npm --prefix web run lint` : **PASS**.
- `npm --prefix web run a11y` : **PASS**.
- `npm --prefix web run a11y:jsx` : **PASS**.
- `npm --prefix web test` : **30 PASS**.
- `npm --prefix web run build` : **PASS**, Vite 8.1.4.
- `npm --prefix web audit --omit=dev --audit-level=high` : **0 vulnérabilité**.
- Parité React/runtime packagé : **PASS**.

## Packaging et smoke tests

- Build wheel `openinfra-0.29.96-py3-none-any.whl` : **PASS**.
- Build sdist `openinfra-0.29.96.tar.gz` : **PASS**.
- Vérification de l'artefact : **PASS**.
- Installation du wheel dans une cible vierge hors arbre source : **PASS**.
- Version runtime et métadonnées : `0.29.96` — **PASS**.
- Points d'entrée `openinfra`, `openinfra-api`, `openinfra-web` : **PASS**.
- OpenAPI packagé et neuf routes Simulation : **PASS**.
- Routes historiques Graphe, Flux, Certificats, Conformité réseau et Opérations terrain : **PASS**.
- Quatre assets runtime web : **PASS**.
- Migrations packagées : **45**, dernière migration `0045_simulation_migration_planning.sql` — **PASS**.
- Import du benchmark Graphe depuis le wheel installé : **PASS**.

## CDC et roadmap

L'EPIC-1602 et ses exigences figuraient déjà dans le CDC et la roadmap de référence. L'implémentation ne crée pas de nouvelle exigence fonctionnelle, réglementaire ou architecturale au-delà de ce périmètre planifié. Conformément à la politique de livraison OpenInfra :

- le CDC reste inchangé et n'est pas réémis ;
- la roadmap reste inchangée et n'est pas réémise ;
- la migration PostgreSQL `0045` est incluse dans la livraison applicative ;
- la compatibilité ascendante des interfaces existantes est préservée.

## Contrôles limités par l'environnement

- `pip-audit --strict --requirement requirements/security-audit.txt` est **non concluant** : la résolution DNS de `pypi.org` est indisponible dans le runner.
- Docker et Podman ne sont pas disponibles ; la recette Compose n'a pas pu être exécutée en conteneurs.
- Aucun serveur PostgreSQL live n'est disponible ; migrations, repositories et transactions sont validés statiquement et par tests d'intégration simulés.
- Aucun navigateur E2E n'est fourni ; les contrats DOM/CSS/ARIA, JSX-a11y, tests Node.js et build frontend ont été exécutés.
