# OpenInfra v0.29.94

OpenInfra v0.29.94 industrialise les performances du graphe RSOT avec un benchmark volumétrique reproductible, des mesures p50/p95, des seuils CI bloquants et un rapport JSON exploitable.

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
