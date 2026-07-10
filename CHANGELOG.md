## v0.29.85 — Nomenclature DCIM des étages et portail FR/EN

- Abandon de la concaténation site/bâtiment dans les codes et noms d’étage.
- Nouvelle nomenclature locale au bâtiment : `L-01`, `L00`, `L01`, `L02`…
- Migration JSON automatique et migration PostgreSQL `0040_dcim_floor_nomenclature.sql` couvrant étages, salles, zones, racks et équipements.
- Compatibilité de lecture avec les alias historiques `<site>_<bâtiment>_ETG<n>`, `F<n>` et `ETG<n>`.
- Préservation des noms d’étage personnalisés et refus des collisions de niveaux.
- Internationalisation complète de l’interface web en français et anglais.
- Détection via `navigator.languages`, puis `navigator.language`, avec fallback anglais.
- Sélecteur EN/FR persistant et moteur i18n identique pour React et le portail packagé.
- Localisation des composants, opérations, formulaires, états, pays, continents, taxonomie et étages sans modification des valeurs API.
- Priorité garantie au runtime web packagé afin qu’un `web/dist` React incomplet ne masque jamais les assets contractuels Python.
- Mise à jour du CDC et de la roadmap, cette recommandation modifiant l’existant.

## v0.29.84 — Correctif CI DCIM et runtime GitHub Actions Node.js 24

- Correction du smoke `DCIM physical model` : réutilisation du code d’étage canonique produit par `define-room`.
- Correction préventive du smoke `DCIM cabling and energy foundation`, affecté par le même écart.
- Ajout de tests de non-régression sur le chaînage `define-room` → `locate`/`define-rack`.
- Migration de `actions/checkout` vers `v6`, `actions/setup-python` vers `v6` et `actions/setup-node` vers `v6`.
- Durcissement du gate de sécurité : refus explicite des actions JavaScript encore liées au runtime Node.js 20.
- Aucune migration PostgreSQL ; aucune modification du CDC ni de la roadmap.

## v0.29.83 — Résilience des workers et agents Discovery

- Ajout d’une file de jobs Discovery persistante avec états explicites et isolation tenant.
- Soumission idempotente, réservation atomique et récupération des baux expirés après crash worker.
- Ajout d’un jeton de fencing monotone empêchant les écritures d’un ancien propriétaire de bail.
- Renouvellement de bail, terminaison idempotente et contrôle de l’empreinte SHA-256 du résultat.
- Retries bornés, mise en DLQ et rejeu administré avec journal d’audit.
- Persistance JSON et PostgreSQL ; `FOR UPDATE SKIP LOCKED` pour les workers concurrents.
- Ajout de la migration additive `0039_discovery_job_resilience.sql`, partitionnée et indexée.
- Exposition complète par service, CLI, API HTTP, OpenAPI et portail web.
- Ajout des tests de crash/reprise, concurrence, non-perte, DLQ, CLI/API, migration et sécurité.
- Ajout d’un gate GitHub Actions dédié à EPIC-1406.
- CDC et roadmap inchangés, l’incrément étant déjà prévu sans nouvelle recommandation impactante.

## v0.29.82 — Réconciliation Discovery multisource gouvernée

- Ajout des preuves Discovery immuables, identifiées par UUID et empreinte SHA-256 canonique.
- Validation stricte des payloads JSON, limite de 1 MiB et refus des clés susceptibles de contenir des secrets.
- Calcul déterministe des scores confiance/fraîcheur/complétude et du score global pondéré.
- Détection des conflits par chemin d’attribut, conservation de toutes les variantes et idempotence par signature.
- Résolution complète et justifiée des conflits sans écriture automatique dans le RSOT.
- Persistance JSON et PostgreSQL partitionnée par tenant, indexée et paginée.
- Ajout de la migration PostgreSQL additive `0038_discovery_multisource_reconciliation.sql`.
- Exposition service, CLI, API HTTP, OpenAPI et portail web.
- Ajout des tests domaine, service, CLI, API, web, migration, sécurité et non-régression RSOT.
- Alignement de la version frontend sur 0.29.82 et ajout d’un job CI Node.js dédié au lint, aux tests et au build Vite.

## v0.29.81 — Profils Discovery virtualisation, Kubernetes et cloud

- Ajout du référentiel Discovery des profils VMware, Proxmox, Hyper-V, Kubernetes, AWS, Azure, GCP et OpenStack.
- Secrets référencés exclusivement en `vault://` et masqués dans les sorties publiques.
- Endpoints HTTPS obligatoires pour les connecteurs on-premises et OpenStack ; cloud public compatible sans endpoint local.
- Limites de concurrence et rate limit bornées.
- CRUD service, CLI, API HTTP et portail web.
- Ajout de la migration PostgreSQL additive `0037_discovery_integration_profiles.sql`.
- Aucun scan réseau ni écriture RSOT n’est exécuté par ce référentiel.

## v0.29.80 — Adresse complète sites DCIM, organisations et partenaires ITAM

- Correction effective de l’exposition DCIM site : les formulaires, CLI et API exigent rue, code postal, email et téléphone à la création.
- Conservation du pays comme valeur ISO alpha-2 avec affichage du nom seul dans les sélecteurs web et libellé `Pays`.
- Complément de l’adresse des organisations ITAM avec code postal et téléphone obligatoires.
- Clarification : les codes/noms d’étage générés sont calculés par OpenInfra à partir des attributs réels du modèle, sans imposer de noms de variables internes.
- Complément de l’adresse des partenaires ITAM avec code postal obligatoire.
- Ajout de la migration PostgreSQL additive `0036_site_organization_addresses.sql`.
- Ajout des tests service, CLI/API/Web, migration et documentation.
