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
