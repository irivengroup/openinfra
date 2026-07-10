# OpenInfra v0.29.88

## Graphe de dépendances RSOT

OpenInfra v0.29.88 renforce **P08 / EPIC-0805** avec une baseline d’accessibilité WCAG 2.2 AA appliquée à toutes les pages et aux deux runtimes web. La navigation clavier, les lecteurs d’écran, les annonces dynamiques, les formulaires, le contraste, les couleurs forcées et la réduction des mouvements sont intégrés au contrat de livraison. Les états actif/survol du header sont désormais plus discrets, les angles moins perceptibles et les transitions bounce/fade respectent `prefers-reduced-motion`. Le moteur de graphe **P15 / EPIC-1501** reste intégralement préservé.

Les opérateurs disposent de trois fonctions complémentaires : exploration du voisinage d'un objet, recherche du chemin le plus court et analyse d'impact direct/indirect. Les filtres par type de relation et le paramètre historique `as_of` sont disponibles en CLI, API HTTP, OpenAPI et portail web FR/EN. Toutes les consultations nécessitent la permission `rsot.read` et produisent un événement d'audit.

Voir `docs/operations/dependency-graph.md` pour les contrats d'exploitation et les commandes.

## Navigation web responsive

Le portail applique une navigation progressive fondée sur la largeur utile et la capacité réelle de la barre des dix composants :

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
