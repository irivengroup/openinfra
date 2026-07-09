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
