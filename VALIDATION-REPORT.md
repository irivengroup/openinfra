# OpenInfra v0.29.97 — Rapport de validation

Date de validation : `2026-07-11`  
Release : `0.29.97`  
Périmètre : P16 / EPIC-1603 — FinOps, coûts et showback ; rationalisation de la navigation

## Résultat global

La livraison ajoute un domaine FinOps complet sous **ITAM**, sans créer de composant principal supplémentaire. Elle réorganise également les fonctions transverses pour conserver une interface cohérente : **Conformité réseau** et les flux sont rattachés à **IPAM**, tandis que les certificats et la PKI sont rattachés à **Sécurité**. Les routes, commandes CLI, permissions et identifiants d'opération historiques restent compatibles.

- Tests Python collectés et validés : **811 PASS** dans **129 fichiers**.
- Tests unitaires : **329 PASS**.
- Tests d'intégration : **478 PASS**.
- Tests d'architecture : **3 PASS**.
- Tests de performance : **1 PASS**.
- Couverture exacte : **98,0219556 %**, soit **28 841 / 29 423** lignes couvertes.
- Seuil bloquant : **98 % PASS**.
- Tests frontend Node.js : **30 PASS**.
- Ruff format et lint : **PASS** sur **223 fichiers**.
- mypy : **PASS** sur **75 modules**.
- Bandit, compilation, gates sécurité et qualité : **PASS**.
- Contrat WCAG 2.2 AA, JSX-a11y, build Vite et audit npm : **PASS**.
- Audit npm production : **0 vulnérabilité**.

La campagne Python a été exécutée par fragments exhaustifs pour éviter les dépassements du runner sur certains parcours CLI/HTTP instrumentés. Chaque fragment publié a terminé avec succès. Les données Coverage.py ont ensuite été consolidées par union ; le taux indiqué utilise la valeur exacte, et non l'arrondi à l'entier affiché par défaut.

## Navigation validée

- **IPAM → Conformité réseau** : baselines, observations et évaluations de conformité réseau.
- **IPAM → Flux déclarés / Flux observés / Conformité des flux**.
- **Sécurité → Inventaire PKI / Endpoints TLS / Conformité PKI**.
- **ITAM → Règles d'allocation / Imports & coûts / Budgets & périodes / Showback-chargeback / Prévisions & anomalies**.
- Suppression des entrées principales autonomes `flows`, `network-config`, `certificates` et `finops`.
- Conservation de toutes les routes REST, commandes CLI, permissions et identifiants d'opération existants.

## Fonctionnalités FinOps validées

- Montants financiers représentés exclusivement avec `Decimal`.
- Catégories cloud, SaaS, datacenter, énergie, licences, support et contrats.
- Jobs d'import idempotents, annulables et auditables.
- Empreinte SHA-256 liant la clé d'idempotence au contenu importé.
- Règles d'allocation ordonnées par priorité et dimension.
- Bucket explicite `financial-quality/unallocated` pour les coûts non attribuables.
- Budgets et seuils d'alerte.
- Détection d'anomalies de coût, dont les hausses par rapport à l'historique comparable.
- Prévisions fondées sur douze périodes historiques au maximum.
- Groupement par tenant, actif, application, service métier, propriétaire, centre de coûts, environnement, dépendance et tags.
- Identifiants de tags canoniques sous la forme `clé:valeur`.
- Showback informatif et chargeback calculé sans écriture comptable de production.
- Clôture de périodes financières avec digest des sources.
- Rapports reproductibles JSON/CSV.
- Persistance JSON locale et PostgreSQL transactionnelle.
- Outbox transactionnel et événements contractuels.
- Rejet récursif des clés de métadonnées sensibles.

## Interfaces

### REST

Dix-huit routes sont exposées sous `/api/v1/finops` :

- règles d'allocation : création et liste ;
- imports : soumission, consultation, liste, exécution et annulation ;
- coûts normalisés : liste filtrée ;
- budgets : création/mise à jour et liste ;
- périodes financières : clôture et liste ;
- rapports : génération, consultation, liste et export ;
- anomalies et prévisions : listes filtrées.

Les deux spécifications OpenAPI passent le parseur YAML strict avec interdiction des clés dupliquées :

- `docs/api/openapi.yaml` ;
- `docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/09-API/OpenAPI/openapi.yaml`.

### CLI

La parité publique est fournie sous `openinfra finops` pour les règles, imports, coûts, budgets, périodes, rapports, exports, anomalies et prévisions.

### Interface web

- Portail React et portail statique packagé alignés.
- Champs date servis par calendriers natifs thémés.
- Validation anticipée des saisies libres.
- Navigation regroupée sous les composants parents.
- Focus formulaire sans épaississement du contour.
- Contrats clavier, lecteurs d'écran, contraste et réduction des animations validés.

## Base de données et packaging

- Migration ajoutée : `0046_finops_costs_showback.sql`.
- Total attendu et vérifié : **46 migrations PostgreSQL**.
- Tables et index dédiés aux règles, imports, coûts, allocations, budgets, périodes, rapports, anomalies, prévisions et événements outbox.
- Contraintes de tenant, devise, montants, périodes, états et idempotence.
- Wheel et sdist construits depuis les sources `0.29.97`.
- Installation du wheel dans une cible vierge et smoke test des points d'entrée.
- Présence contrôlée des **18 routes FinOps**, des assets web, du benchmark et des **46 migrations**.

## Performance

Benchmark déterministe sur **5 000 nœuds** et **100 SPOF** :

| Scénario | p95 observé | Seuil |
|---|---:|---:|
| Graphe à un niveau | 201,743 ms | 1 500 ms |
| Graphe filtré | 99,102 ms | 1 500 ms |
| Analyse SPOF | 207,275 ms | 5 000 ms |
| Pagination complète SPOF | 546,770 ms | 15 000 ms |

Tous les seuils sont respectés.

## Contrôles non concluants ou indisponibles

- `pip-audit` n'a pas pu interroger `pypi.org` en raison de l'échec de résolution DNS du runner. Aucun résultat de vulnérabilité Python externe n'est donc revendiqué.
- Docker, Podman et PostgreSQL live ne sont pas disponibles dans cet environnement ; les contrats, migrations, mappings, profils d'installation et smokes natifs correspondants ont toutefois été exécutés.
- Aucun navigateur E2E réel n'est disponible ; les contrats statiques, Node.js, JSX-a11y et WCAG ont été validés.
