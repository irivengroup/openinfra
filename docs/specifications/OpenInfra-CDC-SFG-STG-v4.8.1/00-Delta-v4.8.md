## Delta v0.29.36 — alertes web contextuelles uniquement

- Ajout de `REQ-00776` et `TST-WEB-079` : les pages composant `openinfra-web` ne doivent plus afficher d’alerte informative par défaut pour expliquer le caractère typé des formulaires.
- Les textes permanents hérités des anciennes alertes informatives sont retirés du rendu UI à partir de la v0.29.37.
- Les alertes de contenu sont réservées aux erreurs/warnings caractérisés et au succès post-soumission de formulaire.

- Ajout REQ-00773 pour la vérification locale CLI des fichiers d’enrôlement proxy Discovery Enterprise.
- Ajout TST-DISCOVERY-076 pour valider édition Enterprise, schéma, résultats backend, permissions 0600 et mode --allow-partial.
- Ajout REQ-00771 pour l’enrôlement CLI direct des proxies Discovery Enterprise auprès des backends.
- Ajout TST-DISCOVERY-074 pour valider édition Enterprise, refus Lite/Pro, API dédiée et CLI local/distant.
- Ajout REQ-00770 pour la topologie opérationnelle IPAM consolidée.
- Ajout TST-IPAM-073 pour valider API, CLI, dashboard, OpenAPI et intégrité du graphe IPAM.
## Delta v0.29.31 — IPAM Enterprise++ dashboard

- Ajout REQ-00769 pour l'exposition des opérations IPAM Enterprise++ dans le dashboard.
- Ajout TST-IPAM-072 pour valider la parité frontend, les routes backend réelles et la découverte API IPAM.
- Les valeurs et invariants IPAM restent gérés par les services backend ; le navigateur ne duplique pas les règles métier.

## Delta v0.29.30 — jumeau numérique DCIM initial

- Ajout de `REQ-00768` et `TST-DCIM-071` : jumeau numérique DCIM initial exposé par API, CLI et dashboard via `GET /api/v1/dcim/digital-twin`, consolidant plan salle, racks, équipements, panneaux, ports, câbles et capacité énergie/refroidissement.
- Le document `dcim_digital_twin` agrège `summary`, `room_plan`, `racks`, `floor_equipment`, `cables` et `integrity` sans créer de stockage parallèle.
- Les règles métier restent portées par les services DCIM existants : occupation rack, câblage, capacité énergie/refroidissement et intégrité.

## Delta v0.29.29 — énergie/refroidissement DCIM dans le dashboard

- Ajout de `REQ-00767` et `TST-ITRM-070` : les sélecteurs ITRM affichent les libellés métier tout en conservant les valeurs internes normalisées ; les types obsolètes `physical-server` et `disk` sont retirés de la taxonomie.

- Ajout de `REQ-00766` et `TST-DCIM-069` : opérations énergie/refroidissement DCIM exposées dans le dashboard via les contrats existants `POST /api/v1/dcim/power-devices`, `POST /api/v1/dcim/power-circuits`, `POST /api/v1/dcim/cooling-zones`, `POST /api/v1/dcim/power-reservations` et `GET /api/v1/dcim/energy-cooling-capacity`.
- Ajout des champs opérateur chaîne électrique A/B, capacité watts, derating, calibre disjoncteur, rôle de zone, températures soufflage/retour et puissance attendue.
- Publication explicite des routes énergie/refroidissement dans le document de découverte API et OpenAPI afin de verrouiller la parité API/UI.

## Delta v0.29.28 — câblage DCIM dans le dashboard

- Ajout de `REQ-00765` et `TST-DCIM-068` : opérations de câblage DCIM exposées dans le dashboard via les contrats existants `POST /api/v1/dcim/patch-panels`, `POST /api/v1/dcim/ports` et `POST /api/v1/dcim/cables`.
- Ajout des champs opérateur endpoints A/B, connecteur, média, statut, chemin câble, longueur et libellé pour documenter le chemin de bout en bout.
- Conservation des validations métier côté service DCIM : compatibilité connecteur/média, existence des ports, occupation des endpoints et chemin obligatoire restent contrôlés par le backend.

## Delta v0.29.27 — élévation rack DCIM dans le dashboard

- Ajout de l’exigence `REQ-00764` pour exposer l’élévation rack DCIM dans `openinfra-web` via le contrat existant `GET /api/v1/dcim/rack-elevation`.
- Ajout du test `TST-DCIM-067` couvrant la présence du formulaire web, les champs `Face rack` et `Format rendu`, la route backend réelle et la validation frontend.
- Ajout du choix de format `json/svg/html` au formulaire `Plan de salle` afin d’aligner explicitement les rendus API et dashboard.

## Delta v0.29.26 — localisation équipement DCIM API/UI

- Ajout de l’exigence `REQ-00763` pour exposer la localisation et relocalisation d’équipement DCIM par `POST /api/v1/dcim/locations` et formulaire web.
- Ajout du test `TST-DCIM-066` couvrant API, payload public, dashboard et non-régression des contraintes rack/U.

## Delta v0.29.25 — taxonomie ITRM catégories / types

- Ajout du catalogue ITRM catégories/types couvrant les ressources datacenter.
- Ajout du filtrage dynamique Catégorie -> Type de ressource dans le dashboard.
- Ajout de la validation backend des couples catégorie/type et du mécanisme générique optionsByField/optionsMap.

# Delta v4.8.0 — Configuration installateur `./config/install.ini`

## Décision

Chaque dossier d'installation OpenInfra doit embarquer un fichier de configuration canonique `./config/install.ini`.
Ce fichier est l'unique point d'ajustement opérateur pour les paramètres dépendant du serveur, du site, du réseau, de l'édition et du scope.

## Règles obligatoires

- Le fichier doit être localisé dans `installers/<edition>/<scope>/config/install.ini`.
- Le fichier doit exister pour chaque installateur livré.
- L'installateur doit refuser tout démarrage sans fichier `install.ini` valide.
- L'opérateur ne modifie pas les scripts d'installation pour adapter le serveur.
- L'installateur doit fournir une commande de validation et une commande de dry-run.
- Les secrets en clair sont interdits dans `install.ini`.
- Les valeurs sensibles sont référencées via Vault, SOPS, variable d'environnement ou fichier protégé.
- Le backend canonique reste `openinfra.service`.
- Le frontend reste `openinfra-web.service`.
- Les agents de discovery restent `openinfra-agent.service`.
- Le scope backend/server applique toutes les migrations backend.
- Les scopes web et agent ne doivent jamais appliquer de migrations.

## Paramètres serveur attendus

Le fichier doit permettre de renseigner ou surcharger :

- FQDN ;
- IP ;
- masque ;
- VIP ;
- passerelle ;
- DNS ;
- site ;
- région ;
- rôle du nœud ;
- mode cluster ;
- mode réplication ;
- stockage applicatif ;
- stockage PostgreSQL ;
- authentification LDAP/IPA pour Pro/Entreprise ;
- endpoint API pour le frontend ;
- endpoint central pour les agents.

## Acceptation

L'exigence est acceptée si tous les dossiers `installers/<edition>/<scope>/` livrés contiennent `config/install.ini`, si la validation échoue proprement en cas de valeur incohérente et si les tests vérifient les profils Lite, Pro et Entreprise.

## Delta v0.29.14 — ITRM Quality & Certification

La phase P09 ajoute la certification qualité ITRM : score par objet, synthèse tenant, détection des attributs obligatoires manquants, fraîcheur, source non autoritative, RBAC `itrm.quality.read`, audit `itrm.quality.*`, API `/api/v1/itrm/quality/*` et commandes CLI `openinfra itrm quality-*`.

## Delta v0.29.15 — openinfra-web Bootstrap 5 Dashboard Theme

Le portail `openinfra-web` adopte le thème officiel Bootstrap 5 Dashboard comme base de rendu et le header principal unique Bootstrap adapté aux domaines OpenInfra. Les items génériques du template sont remplacés par les domaines opérationnels réels : Dashboard, ITRM, IPAM, DCIM, Discovery et Sécurité/RBAC/Audit.

Les assets Bootstrap 5 sont servis localement depuis `src/openinfra/interfaces/rendering/static/assets/bootstrap.min.css`. Aucun CDN externe n'est requis au runtime, ce qui préserve la politique CSP stricte, l'exploitation offline et l'absence d'exposition de secrets.

Le dashboard reste API-only : le navigateur consomme uniquement `/api/*` via `openinfra-web`, sans accès direct à PostgreSQL, sans DSN, sans secret backend et sans lecture du fichier runtime `openinfra.conf`.
## Delta v0.29.16 — openinfra-web formulaires métier, trust server-side et accordéons

Le portail `openinfra-web` ne doit plus afficher un champ générique `Attributs` ni demander un token API technique à l'opérateur. Chaque formulaire web présente les variables métier attendues par l'API/CLI : numéro de série, constructeur, modèle, site, bâtiment, salle, ligne, colonne, rack, IP de management, source autoritative, tags, scopes collector, empreinte certificat, etc.

La navigation latérale devient le point de pilotage principal : `Dashboard` reste une entrée directe, tandis que ITRM, IPAM, DCIM, Discovery et Sécurité/RBAC/Audit sont des accordéons avec transitions `fade`. Les opérations anciennement affichées dans une zone de menu interne à la page sont déplacées dans ces accordéons et le menu interne est supprimé. L'UI ne doit pas afficher les méthodes HTTP aux opérateurs.

Le trust `openinfra-web` ↔ backend est server-side : le navigateur ne transmet pas de token technique et `openinfra-web` ne relaie pas l'en-tête `Authorization` venant du navigateur. Les références DSN/credentials PostgreSQL propres au service web sont déclarées dans `[web_database]`, matérialisées dans `/opt/openinfra/config/openinfra.conf`, et jamais exposées au navigateur.


## Delta v0.29.19 — ITRM et alertes dashboard

Le composant public d’inventaire est exposé sous `IT Ressources Management/ITRM`. Les contrats primaires sont `openinfra itrm *`, `/api/v1/itrm/*`, les rôles `itrm:*` et les permissions `itrm.*`. Les alias historiques `ri` et `sot` restent compatibles uniquement pour migration et sont signalés comme dépréciés afin d’être supprimés progressivement.

Le dashboard d’accueil ne doit plus afficher d’alerte succès permanente `Backend prêt`. L’état backend reste visible dans la sidebar, tandis que les alertes de contenu sont réservées aux erreurs et aux soumissions de formulaire réussies.
## Delta v0.29.20 — formulaires web fonctionnels et camemberts responsives

- Ajout de REQ-00752 : les formulaires openinfra-web doivent être réellement câblés sur les contrats backend `/api/v1/*`, avec chemins et champs obligatoires alignés.
- Ajout de REQ-00753 : le proxy web peut injecter côté serveur un bearer backend optionnel sans exposition navigateur.
- Ajout de REQ-00754 : les camemberts du dashboard d’accueil sont doublés et rendus responsives par CSS `clamp()`.
- Ajout de TST-WEB-055, TST-WEB-056 et TST-WEB-057 pour verrouiller les régressions formulaire, sécurité BFF et responsive charts.


## Delta v0.29.22 — aération de la titlebar dashboard

- Ajout de REQ-00755 : la titlebar du dashboard d’accueil doit disposer d’un espacement vertical responsive autour du titre et du sous-titre.
- Ajout de TST-WEB-058 : validation frontend et tests d’intégration inspectent les assets CSS runtime pour verrouiller `padding-block: clamp(1rem, 2vw, 1.75rem)`.
- Ajout de REQ-00756 et TST-WEB-059 : le bearer backend server-side doit rester effectif lorsque `OPENINFRA_WEB_BACKEND_BEARER_TOKEN` est vide mais `OPENINFRA_BOOTSTRAP_TOKEN` est défini, et le navigateur ne doit plus recevoir d’erreur brute `missing bearer token`.
## Delta v0.29.22 — statut BFF web sans secret

- Ajout de REQ-00757 et TST-WEB-060 : `openinfra-web` expose `/status` sans secret pour diagnostiquer le trust BFF et l’état des formulaires protégés.
- Le proxy web assainit toute erreur backend brute `missing bearer token` avant retour navigateur.

## Delta v0.29.23 — historique ITRM as-of et audit par objet

- Ajout de REQ-00758 : ITRM expose la restitution historique `as-of` des objets, le filtrage temporel des relations et l’audit par objet.
- Ajout de TST-ITRM-061 : tests service, API, CLI et repositories pour verrouiller `get-object-as-of`, `object-as-of`, `object-audit`, `target_id` audit et `as_of` sur les relations.
- Les snapshots existants restent compatibles ; aucune migration destructive n’est requise.

## Delta v0.29.24 — réconciliation gouvernée ITRM

- Ajout de REQ-00759 : ITRM expose une réconciliation gouvernée en dry-run et apply contrôlé.
- Ajout de TST-ITRM-062 : tests service, API, CLI, frontend et audit pour verrouiller `reconcile-object`, `/api/v1/itrm/reconcile-object`, conflits non autoritatifs et application autoritative.
- Les mises à jour non autoritatives rejetées ne sont jamais appliquées ; les plans et applications sont auditables par objet.
- v0.29.33 : ajout de la charte graphique premium openinfra-web, appliquée par CSS Bootstrap 5 compatible sans modification de structure ni import d’asset tiers.
- Ajout REQ-00775 pour l’allègement des ombres de contenu openinfra-web sans modification du header ni du menu latéral.

- La recherche globale du header interroge le backend à partir de la v0.29.38 et regroupe les résultats métiers ITRM, IPAM et Discovery.

### REQ-00786 — Panneau latéral accordéon sans masquage

Le panneau latéral openinfra-web doit ouvrir les accordéons de composants dans le flux vertical. Un composant ouvert repousse les composants inférieurs vers le bas, sans superposition et sans plafond de hauteur susceptible de masquer des opérations. Le scroll reste porté par la sidebar sous le header fixe.

## Delta v0.29.50 — administration éditions et quotas API/UI

- Ajout de REQ-00793 : le portail openinfra-web et l’API HTTP exposent en lecture les politiques d’édition, les décisions de capacité et les décisions de quota runtime.
- Ajout de TST-WEB-094 : validation discovery, OpenAPI, routes HTTP protégées par `security:admin`, opérations web Sécurité/RBAC/Audit et parité CLI/API.
- Les règles métier restent centralisées dans `EditionQueryService` ; le navigateur ne duplique aucune règle de licence, quota ou feature gate.
