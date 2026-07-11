# OpenInfra v0.29.102 — Rapport de validation

Date de validation : `2026-07-11`  
Release : `0.29.102`  
Périmètre : P17 / EPIC-1701 — pilotage multisite centralisé Pro, RBAC par site et rapports consolidés DCIM

## Résultat global

- Tests Python collectés et validés : **929 PASS**.
- Tests unitaires : **388 PASS**.
- Tests d’intégration : **537 PASS**.
- Tests d’architecture : **3 PASS**.
- Tests de performance : **1 PASS**.
- Couverture exacte : **98,0020999825 %**, soit **33 601 / 34 286** lignes couvertes.
- Seuil bloquant : **98 % PASS**.
- Tests frontend Node.js : **42 PASS**.
- Ruff format et lint : **PASS** sur **271 fichiers Python**.
- mypy strict : **PASS** sur **88 modules source**.
- Compilation Python : **PASS**.
- Bandit SAST, gate secrets/CI et gate qualité interne : **PASS**.
- OpenAPI strict sans clé YAML dupliquée : **PASS** sur les deux spécifications.
- Contrats frontend statique/React, WCAG 2.2 AA, JSX-a11y et build Vite : **PASS**.
- Validation des six profils d’installation et du runtime natif : **PASS**.

## Contrats multisites validés

- Feature gate `centralized_multisite` disponible en **Pro** et **Enterprise**, refusée en **Lite**.
- Combinaison des permissions globales et des affectations locales `viewer`, `operator` ou `admin`.
- Contournement de la portée locale réservé à la permission explicite `multisite.admin`.
- Création, révision et révocation non destructives des affectations avec audit transactionnel.
- Pagination complète des affectations : **501 sites** validés sans troncature au premier lot de 500.
- Refus d’inspecter ou de générer un rapport pour une autre identité sans permission globale.
- Rejet atomique d’une sélection contenant un site inconnu ou non autorisé ; aucun rapport partiel.
- Rapports immuables agrégeant bâtiments, étages, salles, racks/châssis et équipements depuis le DCIM.
- Limite explicite de 500 sites par rapport et validation stricte des dates timezone-aware.
- Persistance JSON et PostgreSQL, requêtes paramétrées, contraintes d’intégrité et index d’audit.
- Aucun agent régional, proxy collector ou mécanisme distribué Enterprise activé en édition Pro.

## Interfaces et packaging

- Parcours regroupé sous **DCIM → Pilotage multisite**.
- **7 routes REST** sous `/api/v1/multisite`.
- Parité CLI sous `openinfra multisite`.
- Parité des formulaires typés entre le portail React et le runtime statique packagé.
- Traductions FR/EN des opérations, champs et niveaux d’accès.
- Migration ajoutée : `0050_pro_centralized_multisite.sql`.
- Total packagé : **50 migrations PostgreSQL**.
- Toutes les migrations ont été chargées, validées et rendues ; la migration `0050` a également été rendue via la CLI.
- Wheel et sdist `0.29.102` construits avec succès.
- Vérification du contenu du wheel et du sdist : **PASS**.
- Installation du wheel dans une cible vierge : **PASS**.
- Smoke installé : version, 7 routes multisites, routes historiques, 50 migrations, quatre assets runtime et trois points d’entrée publics : **PASS**.

## Performance

Benchmark volumétrique exécuté sur **5 000 nœuds** et **100 SPOF** :

| Scénario | p95 observé | Seuil | Résultat |
|---|---:|---:|---|
| Graphe à un niveau | 221,445 ms | 1 500 ms | PASS |
| Graphe filtré | 102,830 ms | 1 500 ms | PASS |
| Analyse SPOF | 207,662 ms | 5 000 ms | PASS |
| Pagination SPOF complète | 540,820 ms | 15 000 ms | PASS |

La pagination multisite a en complément été validée fonctionnellement au-delà de la taille maximale d’une page repository.

## Limites de l’environnement

- `pip-audit --strict -r requirements/security-audit.txt` n’a pas pu interroger `pypi.org` en raison d’un échec de résolution DNS du runner. Le gate reste bloquant dans GitHub Actions.
- Docker et Podman ne sont pas installés dans l’environnement courant ; les smokes Compose ne peuvent pas être exécutés localement.
- Aucun cluster PostgreSQL réel ni navigateur E2E complet n’est disponible. Les adaptateurs PostgreSQL sont couverts par des doubles transactionnels déterministes, les migrations par les validateurs structurels, et les portails par les contrats Node/JSX/accessibilité et le build de production.

Le CDC et la roadmap restent inchangés : P17 / EPIC-1701 et ses exigences étaient déjà définis, sans nouvelle recommandation fonctionnelle, technique, réglementaire ou architecturale à intégrer.
