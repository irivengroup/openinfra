# OpenInfra v0.29.99

OpenInfra v0.29.99 réalise **P16 / EPIC-1605 — SBOM, vulnérabilités et exposition contextualisée**. Le parcours est regroupé sous **Sécurité → SBOM & vulnérabilités** et corrèle les composants CycloneDX/SPDX, les CVE importées, l’exposition réseau et la criticité métier. Le module reste analytique : aucun scan actif ni aucune remédiation automatique n’est exécuté.

## SBOM, vulnérabilités et exposition

Les imports sont versionnés par application, release et environnement, bornés à 10 MiB, normalisés et protégés par empreinte SHA-256. La comparaison des releases reconnaît les mises à niveau d’un même package au lieu de les présenter comme une suppression suivie d’un ajout. Les évaluations de risque expliquent chaque facteur de contexte et peuvent être exportées en JSON ou CSV.

```bash
openinfra sbom import --help
openinfra sbom vulnerability-import --help
openinfra sbom exposure-upsert --help
openinfra sbom assess --help
openinfra sbom compare --help
```

Voir `docs/operations/sbom-vulnerabilities-exposure.md` pour les formats, les règles de confiance, les permissions, la persistance et les procédures d’exploitation.

## GreenOps, énergie et capacité

OpenInfra distingue toujours les mesures observées des estimations. Chaque donnée conserve sa source, sa période, son périmètre, sa méthode et son empreinte d’idempotence. Les rapports utilisent `Decimal`, publient les hypothèses PUE et les facteurs carbone appliqués, puis exposent l’énergie IT, l’énergie totale, les émissions estimées, les anomalies, les prévisions et les scores GreenOps par site, rack, PDU, actif ou application.

Les recommandations de consolidation ou de capacité sont strictement consultatives et portent `requires_human_approval=true`. Elles ne déplacent, n’arrêtent et ne modifient aucune ressource de production.

```bash
openinfra greenops measurement-ingest --tenant default \
  --admin-token "$OPENINFRA_TOKEN" \
  --idempotency-key greenops-par01-20260701 \
  --source-code dcim-meter --kind observed --scope rack \
  --scope-key rack-a01 --site-code par-01 \
  --period-start 2026-07-01T00:00:00+00:00 \
  --period-end 2026-07-02T00:00:00+00:00 --energy-kwh 125.4

openinfra greenops report-generate --tenant default \
  --admin-token "$OPENINFRA_TOKEN" --site-code par-01 \
  --period-start 2026-07-01 --period-end 2026-07-31 \
  --scope site
```

Voir `docs/operations/greenops-energy-capacity.md` pour les unités, les hypothèses, les permissions, les API/CLI, la persistance et les procédures de validation.

## FinOps et coûts

Le parcours **ITAM → FinOps & coûts** consolide les coûts cloud, SaaS, datacenter, énergie, licences, support et contrats. Les imports sont asynchrones, idempotents et contrôlés par empreinte SHA-256. Les allocations utilisent des règles prioritaires et conservent explicitement toute part non attribuable.

Les budgets, anomalies, prévisions, showbacks et chargebacks contrôlés sont disponibles en CLI, API HTTP, OpenAPI et dans les deux portails web. Tous les montants utilisent `Decimal`; une période clôturée est protégée par un digest reproductible. Le chargeback reste consultatif et ne produit aucune écriture comptable ou mutation ITSM.

```bash
openinfra finops import-submit --tenant default --admin-token "$OPENINFRA_TOKEN" \
  --idempotency-key finops-aws-2026-06-0001 --source aws-cur \
  --records-file costs.json

openinfra finops report-generate --tenant default --admin-token "$OPENINFRA_TOKEN" \
  --kind showback --period-start 2026-06-01 --period-end 2026-06-30 \
  --group-by application --currency EUR
```

Voir `docs/operations/finops-costs-showback.md` pour le modèle, les permissions, les règles de clôture, les contrats API/CLI et les procédures d’exploitation.

## Organisation de la navigation

- **IPAM** : adressage, **Conformité réseau** et **Flux réseau** ;
- **Sécurité** : contrôles de sécurité et **Certificats & PKI** ;
- **ITAM** : actifs, contrats, licences et **FinOps & coûts**.

Cette organisation ne modifie aucun endpoint ni identifiant d’opération ; elle évite la dispersion des fonctions transversales dans le premier niveau de navigation.

## Performance volumétrique du graphe RSOT

Le banc intégré génère des graphes synthétiques indexés jusqu’à 5 000 nœuds et mesure quatre scénarios : parcours à un niveau, filtrage par type de relation, analyse SPOF et pagination complète. Les cardinalités sont contrôlées à chaque exécution afin qu’une optimisation incorrecte ne puisse pas améliorer artificiellement les temps.

```bash
PYTHONPATH=src python -m openinfra.quality.dependency_graph_benchmark \
  --nodes 5000 \
  --spof-hubs 100 \
  --samples 3 \
  --warmups 1 \
  --output build/reports/dependency-graph-benchmark.json
```

Le processus retourne un code non nul si un p95 dépasse son seuil. Voir `docs/operations/dependency-graph.md` pour les objectifs, la méthodologie et l’interprétation du rapport.

## Formulaires et documentation API fiabilisés

Les deux portails partagent désormais exactement le même moteur de typage, de validation et de normalisation. Les adresses IP/CIDR, emails, téléphones, codes postaux, adresses MAC, noms DNS, URL, nombres, JSON et listes sont contrôlés avant émission, sans remplacer les validations métier du backend. Un validateur OpenAPI fondé sur un chargeur YAML à clés uniques bloque les doublons de mappings en CI et avant packaging.

## Visualisations d’impact et SPOF

L’analyse utilise les dominateurs enracinés : un objet est classé SPOF lorsque sa suppression rend inaccessibles d’autres objets depuis la racine, dans le sens de dépendance demandé. Les résultats sont bornés, filtrables, paginés et signalent explicitement toute projection tronquée afin de ne jamais présenter une analyse partielle comme exhaustive.

Le portail fournit une vue en couches accessible au clavier, un classement tabulaire des SPOF, un résultat JSON de repli et des exports JSON, CSV ou GraphML. Les mêmes capacités sont disponibles en CLI, API HTTP et OpenAPI avec la permission `rsot.read` et un audit systématique.

Voir `docs/operations/dependency-graph.md` pour les contrats, limites, commandes, exemples d’export et règles d’interprétation.

## Conformité réseau par golden configuration

Les baselines sont versionnées par équipement RSOT et plateforme. Les observations sont immuables, idempotentes et peuvent provenir de SSH, API, NETCONF, RESTCONF, gNMI, Discovery ou import. La comparaison JSON produit des dérives typées, respecte les chemins ignorés et critiques, rejette les secrets et reste strictement en lecture sur les équipements.

Les opérations sont disponibles en CLI, API HTTP, OpenAPI et portail web FR/EN. Voir `docs/operations/network-config-compliance.md` pour les contrats d’exploitation, les permissions, les limites documentaires et la procédure d’évaluation.

## Certificats et PKI

OpenInfra v0.29.90 réalise **P15 / EPIC-1503** avec un inventaire gouverné des certificats X.509 et de leurs endpoints TLS. Les chaînes PEM sont analysées et validées cryptographiquement, les empreintes SHA-256 servent d'identifiants immuables et la gouvernance (propriétaire, environnement, source, objet RSOT) reste révisable et auditée.

La capacité couvre l'import de chaînes leaf-first, le contrôle des liens émetteur/sujet et des signatures, l'inventaire des SAN DNS/IP/email/URI, la détection des certificats expirés ou proches de l'expiration, le contrôle du hostname présenté par les endpoints et les observations idempotentes. Aucun secret de clé privée n'est accepté ni stocké.

Les opérations sont disponibles en CLI, API HTTP, OpenAPI et portail web FR/EN. Voir `docs/operations/certificate-pki.md` pour les règles d'exploitation, les permissions, les seuils, les commandes et les limites de sécurité.

## Graphe de dépendances RSOT

Le moteur de graphe **P15 / EPIC-1501** reste une projection en lecture du RSOT. Il couvre l’exploration du voisinage, la recherche du chemin le plus court et l’analyse d’impact direct/indirect. **EPIC-1505** ajoute la détection des SPOF, les visualisations accessibles et les exports gouvernés sans modifier les objets ni les relations sources.

Les filtres par type de relation et le paramètre historique `as_of` sont disponibles en CLI, API HTTP, OpenAPI et portail web FR/EN. Toutes les consultations nécessitent la permission `rsot.read` et produisent un événement d’audit.

Voir `docs/operations/dependency-graph.md` pour les contrats d’exploitation et les commandes.

## Navigation web responsive

Le portail applique une navigation progressive fondée sur la largeur utile et la capacité réelle de la barre des onze composants :

- **écran large (`>= 1200 px`)** : sidebar persistante et scrollable sous le header fixe ;
- **tablette et portable compact (`768–1199,98 px`)** : sidebar masquée, icônes de composants alignées dans le header et ouverture d’un mégamenu multicolonne reprenant les mêmes contextes et opérations ;
- **mobile (`< 768 px`)** : remplacement de la barre de composants par une icône de menu unique ouvrant une navigation complète, scrollable et accessible au clavier.

La seconde barre conserve sa hauteur initiale tandis que la recherche reste compacte. Le sélecteur EN/FR, Swagger et ReDoc utilisent un gabarit légèrement réduit et restent alignés. Sur écran tactile, les cibles interactives passent automatiquement à 44 px afin de préserver l’accessibilité. Les menus se ferment par bouton, clic sur le backdrop ou touche `Échap`.

Voir `docs/operations/responsive-navigation.md` pour le contrat détaillé et `docs/ui/WEB_ACCESSIBILITY.md` pour la baseline d’accessibilité.

## Nomenclature DCIM des étages et portail multilingue

OpenInfra v0.29.86 remplace la nomenclature d’étage concaténant site et bâtiment par un code local, stable et lisible : `L-01` pour le premier sous-sol, `L00` pour le rez-de-chaussée et `L01` pour le premier étage. Les étages restent générés automatiquement depuis le type et les bornes du bâtiment ; aucune saisie libre de code ou de nom n’est demandée dans les nouveaux parcours.

La migration `0040_dcim_floor_nomenclature.sql` et la migration JSON intégrée réécrivent toutes les références DCIM dépendantes, préservent les noms personnalisés et conservent les anciens codes comme alias de lecture.

Le portail web supporte désormais intégralement le français et l’anglais. La langue est détectée depuis le navigateur ; toute langue non supportée utilise l’anglais. Un sélecteur EN/FR mémorise le choix opérateur. Le même moteur i18n est utilisé par le frontend React et par le portail statique livré dans le package Python.


## Résilience des workers et agents Discovery

OpenInfra v0.29.83 réalise **P14 / EPIC-1406** avec une file de jobs Discovery persistante, idempotente et récupérable après interruption d’un worker ou d’un agent. Un job validé est enregistré avant sa remise à un collector ; il ne peut donc plus être perdu à la suite d’un arrêt brutal entre l’autorisation et l’exécution.

Chaque réservation repose sur un bail expirant et un **jeton de fencing monotone**. Lorsqu’un worker disparaît, un autre peut reprendre le job après expiration du bail ; l’ancien worker ne peut plus terminer ou altérer le traitement avec son jeton périmé. Les échecs suivent une politique de tentatives bornées, puis basculent dans une **DLQ** (Dead-Letter Queue, file de quarantaine) administrable et auditée.

## Capacités livrées

- états persistants `queued`, `leased`, `retry-wait`, `completed` et `dead-letter` ;
- soumission idempotente par tenant et clé métier ;
- réservation atomique concurrente et reprise des baux expirés ;
- jetons de fencing empêchant le double traitement par un worker obsolète ;
- renouvellement de bail, terminaison idempotente et empreinte SHA-256 du résultat ;
- retries bornés, DLQ et rejeu explicite par un administrateur ;
- persistance JSON et PostgreSQL, partitionnée par tenant via la migration `0039_discovery_job_resilience.sql` ;
- CLI, API HTTP, OpenAPI et portail web alignés ;
- audit des soumissions, réservations, reprises, erreurs, mises en DLQ, rejeux et terminaisons ;
- tests domaine, services, concurrence, CLI, HTTP, portail, migration, sécurité et non-perte ;
- runbook `docs/runbooks/DISCOVERY_JOB_RESILIENCE.md`.

La réconciliation multisource v0.29.82 et les corrections DCIM/ITAM antérieures restent compatibles. Le CDC et la roadmap ne sont pas modifiés : EPIC-1406 était déjà défini et aucune nouvelle recommandation n’impacte l’existant.

## Opérations terrain DCIM

Le parcours **DCIM → Opérations terrain** guide les interventions physiques sans introduire de ticketing ITSM natif. Une fiche est générée depuis une cible réellement localisée, enrichie par les dépendances RSOT/Graphe, les flux déclarés et la redondance électrique A/B.

Interfaces principales :

```bash
openinfra dcim field-sheet-list --tenant default --admin-token "$OPENINFRA_TOKEN"
openinfra dcim field-sheet-generate --tenant default --admin-token "$OPENINFRA_TOKEN" \
  --target-type equipment --target-id PAR-SRV-001 \
  --title "Remplacement alimentation" \
  --purpose "Remplacer le bloc et contrôler le service" \
  --owner ops.owner --operator field.operator
```

Les preuves acceptées sont JPEG, PNG, WebP ou PDF, limitées à 2 Mio. Les paquets hors ligne sont limités au tenant et au site autorisés, expirent automatiquement et sont synchronisés uniquement si leur empreinte SHA-256 canonique correspond. Le runbook complet est disponible dans `docs/runbooks/FIELD_OPERATIONS.md`.


- [SBOM, vulnérabilités et exposition contextualisée](docs/operations/sbom-vulnerabilities-exposure.md)
