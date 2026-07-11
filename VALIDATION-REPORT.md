# OpenInfra v0.29.99 — Rapport de validation

Date de validation : `2026-07-11`  
Release : `0.29.99`  
Périmètre : P16 / EPIC-1605 — SBOM, vulnérabilités et exposition contextualisée

## Résultat global

La livraison ajoute la gestion analytique des nomenclatures logicielles sous **Sécurité → SBOM & vulnérabilités**, sans nouveau composant principal. Elle importe et versionne les SBOM CycloneDX/SPDX, corrèle les composants avec des vulnérabilités, contextualise le risque par l'exposition et la criticité métier, compare les releases et exporte les résultats sans scan actif ni remédiation automatique.

- Tests Python collectés et validés : **886 PASS** dans **145 fichiers**.
- Tests unitaires : **375 PASS**.
- Tests d'intégration : **507 PASS**.
- Tests d'architecture : **3 PASS**.
- Tests de performance : **1 PASS**.
- Couverture exacte : **98,0029677 %**, soit **31 702 / 32 348** lignes couvertes.
- Seuil bloquant : **98 % PASS**.
- Tests frontend Node.js : **36 PASS**.
- Ruff format et lint : **PASS** sur **246 fichiers**.
- mypy : **PASS** sur **82 modules**.
- Bandit, compilation, gates sécurité et qualité : **PASS**.
- Contrat WCAG 2.2 AA, JSX-a11y, build Vite et audit npm : **PASS**.
- Audit npm production : **0 vulnérabilité**.

La campagne Python a été exécutée par fragments exhaustifs afin d'éviter les dépassements du runner sous instrumentation Coverage.py. Seuls les fragments terminés avec succès ont été consolidés. La couverture est contrôlée sur sa valeur exacte et non sur l'arrondi affiché par défaut.

## Organisation de l'interface validée

- **Sécurité → Certificats & PKI / SBOM & vulnérabilités**.
- **IPAM → Conformité réseau / Flux réseau**.
- **RSOT → Graphe / Simulation & migrations**.
- **ITAM → FinOps & coûts**.
- **DCIM → GreenOps / Opérations terrain**.
- Aucune entrée SBOM autonome de premier niveau.
- Conservation des routes, commandes CLI, permissions et identifiants historiques.

## Fonctionnalités SBOM validées

- Import CycloneDX JSON et SPDX JSON, limité à 10 MiB.
- Validation stricte des structures, URI, PURL, CVE, empreintes SHA-256 et métadonnées sensibles.
- Versionnement immuable des documents par tenant, application et release.
- Idempotence par clé et empreinte du contenu.
- Inventaire des composants, licences, dépendances et références externes.
- Import de vulnérabilités avec CVSS, sévérité, dates, références et versions corrigées.
- Contextes d'exposition : environnement, exposition Internet, criticité métier, actifs et services liés.
- Calcul reproductible d'un score contextualisé et d'une priorité de traitement.
- Statuts de constat audités, sans remédiation automatique.
- Comparaison de releases distinguant ajout, suppression et changement de version.
- Identité de comparaison fondée sur le package, sans confondre une mise à niveau avec une suppression suivie d'un ajout.
- Exports JSON et CSV.
- Persistance JSON locale et PostgreSQL transactionnelle.
- Outbox transactionnel pour les événements critiques.
- Aucune capacité de scan actif, d'exploitation ou de correction automatique.

## Interfaces

### REST

Quatorze routes sont exposées sous `/api/v1/sbom` pour :

- import, liste et consultation des documents SBOM ;
- import et liste des vulnérabilités ;
- création, liste et consultation des contextes d'exposition ;
- évaluation, liste et export du risque contextualisé ;
- création, liste et consultation des comparaisons de releases.

Les deux spécifications OpenAPI passent le parseur YAML strict avec interdiction des clés dupliquées :

- `docs/api/openapi.yaml` ;
- `docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/09-API/OpenAPI/openapi.yaml`.

### CLI

La parité publique est fournie sous `openinfra sbom` pour l'import, l'inventaire, les vulnérabilités, l'exposition, l'évaluation du risque, les exports et les comparaisons.

### Interface web

- Portail React et portail statique packagé alignés.
- SBOM regroupé sous Sécurité.
- Dates de publication/modification CVE servies par calendriers natifs thémés.
- Validation anticipée des saisies libres et fichiers importés.
- Export de risque téléchargeable.
- Résultats présentés comme analytiques, sans scan actif ni action de remédiation.
- Navigation clavier, lecteurs d'écran, contraste, réduction des animations et focus sans épaississement validés.

## Base de données et packaging

- Migration ajoutée : `0048_sbom_vulnerabilities_exposure.sql`.
- Total attendu : **48 migrations PostgreSQL**.
- Tables et index dédiés aux documents, composants, vulnérabilités, expositions, constats, comparaisons et événements outbox.
- Isolation stricte par tenant.
- Wheel et sdist construits depuis les sources `0.29.99`.
- Installation du wheel dans une cible vierge et smoke test des points d'entrée.
- Présence contrôlée des **14 routes SBOM**, des assets web, du benchmark et des **48 migrations**.

## Performance

Benchmark déterministe sur **5 000 nœuds** et **100 SPOF** :

| Scénario | p95 observé | Seuil |
|---|---:|---:|
| Graphe à un niveau | 198,469 ms | 1 500 ms |
| Graphe filtré | 103,718 ms | 1 500 ms |
| Analyse SPOF | 208,318 ms | 5 000 ms |
| Pagination complète SPOF | 524,216 ms | 15 000 ms |

Tous les seuils sont respectés.

## Documentation et traçabilité

- CDC et roadmap inchangés : l'EPIC-1605 et ses exigences étaient déjà définis.
- Documentation SBOM : formats, limites, identité des composants, scoring, exposition, permissions, idempotence, API, CLI et limites de responsabilité.
- Gate CI SBOM : domaine, cas limites, service, CLI, HTTP, migration, PostgreSQL et interface web.

## Contrôles non concluants ou indisponibles

- `pip-audit` n'a pas pu interroger `pypi.org` en raison d'un échec de résolution DNS du runner. Aucun résultat de vulnérabilité Python externe n'est revendiqué.
- Docker, Podman et PostgreSQL live ne sont pas disponibles dans cet environnement ; les contrats, migrations, mappings PostgreSQL, profils d'installation et smokes natifs correspondants ont été exécutés.
- Aucun navigateur E2E réel n'est disponible ; les contrats statiques, Node.js, JSX-a11y et WCAG ont été validés.
