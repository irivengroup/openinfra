# OpenInfra v0.29.98 — Rapport de validation

Date de validation : `2026-07-11`  
Release : `0.29.98`  
Périmètre : P16 / EPIC-1604 — GreenOps, énergie, empreinte carbone et capacité

## Résultat global

La livraison ajoute GreenOps sous **DCIM**, sans nouveau composant principal. Les mesures observées restent strictement distinguées des estimations ; les facteurs carbone, hypothèses PUE et données sources sont versionnés et traçables. Les recommandations restent consultatives et exigent une validation humaine.

- Tests Python collectés et validés : **861 PASS** dans **137 fichiers**.
- Tests unitaires : **365 PASS**.
- Tests d'intégration : **492 PASS**.
- Tests d'architecture : **3 PASS**.
- Tests de performance : **1 PASS**.
- Couverture exacte : **98,0026502 %**, soit **30 323 / 30 941** lignes couvertes.
- Seuil bloquant : **98 % PASS**.
- Tests frontend Node.js : **33 PASS**.
- Ruff format et lint : **PASS** sur **234 fichiers**.
- mypy : **PASS** sur **78 modules**.
- Bandit, compilation, gates sécurité et qualité : **PASS**.
- Contrat WCAG 2.2 AA, JSX-a11y, build Vite et audit npm : **PASS**.
- Audit npm production : **0 vulnérabilité**.

La campagne Python a été exécutée par fragments exhaustifs pour éviter les dépassements du runner sous instrumentation Coverage.py. Seuls les fragments terminés avec succès ont produit un fichier de données ; une unique consolidation finale a été utilisée. La valeur de couverture est calculée exactement, sans accepter l'arrondi à l'entier affiché par défaut.

## Organisation de l'interface validée

- **DCIM → GreenOps** : sources, facteurs carbone, politiques, mesures, rapports, anomalies, prévisions, recommandations et scores.
- **IPAM → Conformité réseau / Flux réseau** : classement conservé.
- **Sécurité → Certificats & PKI** : classement conservé.
- **ITAM → FinOps & coûts** : classement conservé.
- Aucune entrée GreenOps autonome de premier niveau.
- Conservation des routes REST, commandes CLI, permissions et identifiants d'opération historiques.

## Fonctionnalités GreenOps validées

- Sources de mesure versionnées et administrables.
- Mesures énergétiques `observed` ou `estimated`, sans requalification silencieuse.
- Périmètres site, rack, PDU, actif et application.
- Périodes timezone-aware et valeurs financières/énergétiques représentées avec `Decimal`.
- Facteurs carbone versionnés par région et période avec source et URI HTTPS.
- Politiques par site : PUE par défaut, coût énergétique, devise, seuils de capacité et minimum d'échantillons.
- PUE mesuré lorsque les énergies IT et totale sont présentes ; estimation politique explicitement signalée sinon.
- Calcul reproductible des émissions CO₂e et du coût énergétique.
- Anomalies d'énergie, prévisions de saturation, scores GreenOps et recommandations de consolidation/capacité.
- Recommandations portant systématiquement `requires_human_approval=true`.
- Rapports reproductibles avec digest des mesures, politique, facteur carbone et périmètre.
- Exports JSON et CSV.
- Idempotence globale par tenant et empreinte SHA-256, y compris entre partitions PostgreSQL temporelles.
- Persistance JSON locale et PostgreSQL transactionnelle.
- Outbox transactionnel pour les événements critiques.
- Aucune mutation automatique de ressource, aucun arrêt, déplacement ou retrait en production.

## Interfaces

### REST

Seize routes sont exposées sous `/api/v1/greenops` :

- sources de mesure : création et liste ;
- politiques : consultation et création/mise à jour ;
- facteurs carbone : création et liste ;
- mesures énergétiques : ingestion et liste ;
- rapports : génération, consultation, liste et export ;
- anomalies, prévisions de capacité, recommandations et scores : listes paginées.

Les deux spécifications OpenAPI passent le parseur YAML strict avec interdiction des clés dupliquées :

- `docs/api/openapi.yaml` ;
- `docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/09-API/OpenAPI/openapi.yaml`.

### CLI

La parité publique est fournie sous `openinfra greenops` pour les sources, facteurs, politiques, mesures, rapports, exports, anomalies, prévisions, recommandations et scores.

### Interface web

- Portail React et portail statique packagé alignés.
- GreenOps regroupé sous DCIM.
- Champs date et date-heure servis par calendriers natifs thémés.
- Validation anticipée des saisies libres.
- Export de rapport téléchargeable.
- Recommandations signalées comme consultatives et soumises à validation humaine.
- Navigation clavier, lecteurs d'écran, contraste, réduction des animations et focus sans épaississement validés.

## Base de données et packaging

- Migration ajoutée : `0047_greenops_energy_capacity.sql`.
- Total attendu et vérifié : **47 migrations PostgreSQL**.
- Partitionnement temporel des mesures et index tenant/site/périmètre/période.
- Registre global d'idempotence par tenant protégeant les partitions contre les doublons ou collisions de contenu.
- Tables dédiées aux sources, facteurs, politiques, mesures, anomalies, prévisions, recommandations, scores, rapports et événements outbox.
- Wheel et sdist construits depuis les sources `0.29.98`.
- Installation du wheel dans une cible vierge et smoke test des points d'entrée.
- Présence contrôlée des **16 routes GreenOps**, des assets web, du benchmark et des **47 migrations**.

## Performance

Benchmark déterministe sur **5 000 nœuds** et **100 SPOF** :

| Scénario | p95 observé | Seuil |
|---|---:|---:|
| Graphe à un niveau | 204,231 ms | 1 500 ms |
| Graphe filtré | 103,704 ms | 1 500 ms |
| Analyse SPOF | 212,647 ms | 5 000 ms |
| Pagination complète SPOF | 521,568 ms | 15 000 ms |

Tous les seuils sont respectés.

## Documentation et traçabilité

- CDC : **828 exigences**, 529 entités de traçabilité, validation documentaire PASS.
- Roadmap : **19 phases**, **115 epics**, **8 gates**, **97 tests**, validation PASS.
- Documentation GreenOps : unités, provenance, PUE, facteurs carbone, permissions, idempotence, API, CLI, exploitation et limites.
- Gate CI GreenOps : domaine, cas limites, service, CLI, HTTP, migration, PostgreSQL et interface web.

## Contrôles non concluants ou indisponibles

- `pip-audit` n'a pas pu interroger `pypi.org` en raison de l'échec de résolution DNS du runner. Aucun résultat de vulnérabilité Python externe n'est donc revendiqué.
- Docker, Podman et PostgreSQL live ne sont pas disponibles dans cet environnement ; les contrats, migrations, mappings PostgreSQL, profils d'installation et smokes natifs correspondants ont toutefois été exécutés.
- Aucun navigateur E2E réel n'est disponible ; les contrats statiques, Node.js, JSX-a11y et WCAG ont été validés.
