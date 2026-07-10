# OpenInfra v0.29.94 — Rapport de validation

Date de validation : `2026-07-11`  
Release : `0.29.94`  
Périmètre : P15 / EPIC-1506 — tests volumétriques du graphe de dépendances

## Résultat global

La livraison industrialise la validation de capacité du Graphe RSOT sans modifier les contrats métier, les routes API, les commandes CLI, le schéma PostgreSQL ni l'interface. Elle ajoute un banc déterministe qui mesure les parcours à un niveau, les filtres, l'analyse des points uniques de défaillance (SPOF) et la pagination complète sur un graphe synthétique de 5 000 nœuds.

- Tests Python collectés et validés : **752 PASS** dans **106 fichiers**.
- Tests unitaires : **304 PASS**.
- Tests d'intégration : **444 PASS**.
- Tests d'architecture : **3 PASS**.
- Tests de performance : **1 PASS**.
- Couverture : **98,06150002015073 %**, soit **24 332 / 24 813** lignes couvertes.
- Seuil bloquant : **98 % PASS**.
- Tests frontend Node.js : **28 PASS**.
- Lint frontend, accessibilité JSX, contrat WCAG 2.2 AA et build Vite : **PASS**.
- Audit npm production : **0 vulnérabilité**.

La suite Python a été exécutée par fragments exhaustifs puis consolidée avec Coverage.py. Cette segmentation évite les limites d'exécution des parcours CLI monolithiques sans omettre de fichier ni de scénario.

## Banc volumétrique du Graphe

Le banc utilise le service public `DependencyGraphService` et un adaptateur RSOT synthétique indexé. Il génère des topologies reproductibles, vérifie les cardinalités et le déterminisme à chaque échantillon, puis produit un rapport JSON écrit atomiquement.

Configuration maximale validée :

- nœuds : **5 000** ;
- arêtes : **4 999** ;
- hubs SPOF : **100** ;
- échantillons mesurés : **3** après **1** préchauffage ;
- processeurs logiques détectés : **56** ;
- Python : **3.13.5**.

Mesures p95 observées le 11 juillet 2026 :

| Scénario | p95 observé | Seuil CI | Résultat |
|---|---:|---:|---|
| Parcours à un niveau, 5 000 nœuds | 244,779 ms | 1 500 ms | PASS |
| Parcours filtré `calls`, 2 501 nœuds | 106,017 ms | 1 500 ms | PASS |
| Analyse SPOF, 100 résultats | 201,123 ms | 5 000 ms | PASS |
| Pagination complète, 4 pages | 520,696 ms | 15 000 ms | PASS |

Le gate CI échoue si un seuil est dépassé, si une cardinalité devient incohérente, si le résultat n'est plus déterministe ou si la configuration est invalide. Les codes de sortie sont documentés : `0` succès, `1` seuil dépassé, `2` configuration ou invariant invalide.

Commande de référence :

```bash
PYTHONPATH=src python scripts/benchmark_dependency_graph.py \
  --nodes 5000 \
  --spof-hubs 100 \
  --samples 3 \
  --warmups 1 \
  --one-level-threshold-ms 1500 \
  --filtered-threshold-ms 1500 \
  --spof-threshold-ms 5000 \
  --pagination-threshold-ms 15000 \
  --output build/reports/dependency-graph-benchmark.json
```

## Architecture et compatibilité

- Le banc est isolé dans `openinfra.quality` et respecte la politique Python orientée objet stricte.
- Aucun accès aux fonctions internes du Graphe : seuls les ports et services publics existants sont exercés.
- Aucune dépendance runtime supplémentaire.
- Aucun changement de route API, de commande CLI, de structure de données ou de comportement public.
- Aucun traitement asynchrone artificiel : les mesures évaluent le coût réel des algorithmes et de la pagination.
- Rapport JSON versionné par `schema_version`, trié et exploitable par CI ou observabilité externe.
- Écriture atomique du rapport afin d'éviter les fichiers partiels.

## CI/CD

Un gate `Dependency graph volumetric benchmark` est ajouté à GitHub Actions sur Python 3.13. Il s'exécute avant le packaging avec les seuils documentés, produit `build/reports/dependency-graph-benchmark.json` et publie un résumé lisible dans `$GITHUB_STEP_SUMMARY`.

Les contrats de workflow vérifient :

- la présence du gate ;
- les paramètres de volumétrie ;
- les quatre seuils bloquants ;
- la génération du rapport JSON ;
- la publication du résumé GitHub Actions.

## Qualité, sécurité et typage

- `ruff format --check src tests scripts docker installers` : **PASS**, 191 fichiers.
- `ruff check src tests scripts docker installers` : **PASS**.
- `mypy src/openinfra` : **PASS**, 66 fichiers source.
- `bandit -q -r src/openinfra` : **PASS**.
- `python -m compileall -q src tests scripts docker installers` : **PASS**.
- `python scripts/validate_openapi.py docs/api/openapi.yaml` : **PASS**.
- `python scripts/validate_openapi.py src/openinfra/interfaces/web_assets/openapi.yaml` : **PASS**.
- `python scripts/security_gate.py --project-root .` : **PASS**.
- `python scripts/quality_gate.py --project-root .` : **PASS**.
- `python scripts/native_runtime_smoke.py --project-root .` : **PASS**.
- `python scripts/validate_enterprise_alignment.py --project-root .` : **PASS**.
- Six profils d'installation Lite/Pro/Entreprise : **PASS**.
- Validation CDC : **PASS**, version 4.8.1, 828 exigences et 628 tests contractuels.
- Validation roadmap : **PASS**, 19 phases, 115 epics, 8 gates et 97 tests.

## Frontend

Aucun comportement frontend n'est modifié par cet incrément. Les contrôles complets ont néanmoins été rejoués :

- `npm --prefix web run lint` : **PASS**.
- `npm --prefix web run a11y` : **PASS**.
- `npm --prefix web run a11y:jsx` : **PASS**.
- `npm --prefix web test` : **28 PASS**.
- `npm --prefix web run build` : **PASS**, Vite 8.1.4.
- `npm --prefix web audit --omit=dev --audit-level=high` : **0 vulnérabilité**.
- `python scripts/validate_frontend.py --project-root .` : **PASS**.
- Parité React/runtime packagé : **PASS**.

## Packaging et smoke tests

- Build wheel `openinfra-0.29.94-py3-none-any.whl` : **PASS**.
- Build sdist `openinfra-0.29.94.tar.gz` : **PASS**.
- Vérification d'artefact : **PASS**.
- Installation du wheel dans une cible vierge hors arbre source : **PASS**.
- Version runtime et métadonnées : `0.29.94` — **PASS**.
- Points d'entrée `openinfra`, `openinfra-api`, `openinfra-web` : **PASS**.
- OpenAPI packagé : **PASS**.
- Cinq routes Graphe, six routes Matrice de flux, sept routes Certificats/PKI et six routes Conformité réseau : **PASS**.
- Quatre assets runtime web : **PASS**.
- Migrations packagées : **43**, dernière migration `0043_network_config_compliance.sql` — **PASS**.
- Import et exécution du benchmark depuis le wheel installé : **PASS**.

## CDC, roadmap et migrations

Le lot EPIC-1506 figurait déjà dans la roadmap et ne modifie aucune exigence fonctionnelle, technique, réglementaire ou architecturale existante. Conformément à la politique de livraison OpenInfra :

- le CDC reste inchangé et n'est pas réémis ;
- la roadmap reste inchangée et n'est pas réémise ;
- aucune migration PostgreSQL n'est ajoutée ;
- la compatibilité ascendante est intégralement préservée.

## Contrôles limités par l'environnement

- `pip-audit --strict --requirement requirements/security-audit.txt` est **non concluant** : la résolution DNS de `pypi.org` est indisponible dans le runner.
- Docker et Podman ne sont pas disponibles ; la recette Compose n'a pas pu être exécutée en conteneurs.
- Aucun serveur PostgreSQL live n'est disponible ; les 43 migrations, adaptateurs et contrats SQL sont validés statiquement et par tests simulés.
- Aucun navigateur E2E n'est fourni ; les contrats DOM/CSS/ARIA, JSX-a11y, tests Node.js et build frontend ont été exécutés.
