# OpenInfra v0.29.101 — Rapport de validation

Date de validation : `2026-07-11`  
Release : `0.29.101`  
Périmètre : P16 / EPIC-1606 — assistant RAG gouverné, cité et cloisonné par permissions

## Résultat global

- Tests Python collectés et validés : **914 PASS** dans **157 fichiers**.
- Tests unitaires : **385 PASS**.
- Tests d'intégration : **525 PASS**.
- Tests d'architecture : **3 PASS**.
- Tests de performance : **1 PASS**.
- Couverture exacte : **98,0068810 %**, soit **33 044 / 33 716** lignes couvertes.
- Seuil bloquant : **98 % PASS**.
- Tests frontend Node.js : **39 PASS**.
- Ruff format et lint : **PASS** sur **262 fichiers Python**.
- mypy strict : **PASS** sur **86 modules**.
- Bandit, compilation, gates sécurité et qualité : **PASS**.
- OpenAPI strict sans clé YAML dupliquée : **PASS** sur les deux spécifications.
- Contrat WCAG 2.2 AA, JSX-a11y, build Vite et audit npm : **PASS**.
- Audit npm production : **0 vulnérabilité**.

## Contrats RAG validés

- Documents tenant-aware, versionnés et désactivables sans suppression destructive.
- Synchronisation RSOT en lecture seule avec import, mise à jour, idempotence et désactivation des projections obsolètes.
- Filtrage tenant et permissions **avant** la recherche et avant la génération de réponse.
- Recherche lexicale déterministe et générateur extractif local, sans appel à un service externe.
- Citations obligatoires pour toute réponse au statut `answered`.
- Statut `insufficient-context` sans citation lorsque les sources autorisées sont insuffisantes.
- Audit des consultations par empreinte SHA-256 sans persistance de la question en clair.
- Jobs d'import/export idempotents, paginés, relançables et contrôlés par empreinte d'artefact.
- Rejet récursif des métadonnées contenant des clés sensibles.
- Aucune action destructive, aucune mutation RSOT/DCIM/IPAM et aucune remédiation automatique.
- Dépôts JSON local et PostgreSQL transactionnel avec outbox pour les événements critiques.
- Rejet des curseurs, payloads, artefacts et données persistées invalides ou corrompus.

## Interfaces et packaging

- Parcours regroupé sous **RSOT → Assistant gouverné / Index de connaissances / Imports-exports RAG**.
- **13 routes REST** sous `/api/v1/rag`.
- Parité CLI sous `openinfra rag`.
- Portail React et portail statique packagé alignés.
- Migration ajoutée : `0049_rag_governed_assistant.sql`.
- Total packagé : **49 migrations PostgreSQL**.
- Wheel et sdist `0.29.101` construits avec succès.
- Vérification du contenu du wheel et du sdist : **PASS**.
- Installation du wheel dans une cible vierge : **PASS**.
- Smoke installé : version, 13 routes RAG, routes historiques, 49 migrations, quatre assets runtime et trois points d'entrée publics : **PASS**.

## Performance

Benchmark exécuté depuis le wheel installé sur **5 000 nœuds** et **100 SPOF** :

| Scénario | p95 observé | Seuil |
|---|---:|---:|
| Graphe à un niveau | 220,538 ms | 1 500 ms |
| Graphe filtré | 107,114 ms | 1 500 ms |
| Analyse SPOF | 203,438 ms | 5 000 ms |
| Pagination SPOF complète | 514,475 ms | 15 000 ms |

Tous les seuils passent.

## Limites de l'environnement

- `pip-audit -r requirements/security-audit.txt` n'a pas pu interroger `pypi.org` en raison d'un échec de résolution DNS du runner.
- Docker, Podman, PostgreSQL live et un navigateur E2E complet ne sont pas disponibles dans l'environnement courant.
- Les contrats statiques, les doubles PostgreSQL déterministes, les six profils d'installation, le runtime natif et le package installé ont néanmoins été validés.

Le CDC et la roadmap restent inchangés : l'EPIC-1606 et ses exigences y étaient déjà définis.
