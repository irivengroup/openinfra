# OpenInfra v0.29.41

OpenInfra est une solution Python orientée objet pour référentiel d'infrastructure, IPAM/DDI, DCIM, inventaire, import/export, sécurité, éditions Lite/Pro/Enterprise et installateurs autonomes.

**Version courante : 0.29.41 — la recherche globale du header conserve le fallback métier, les camemberts restaurent la palette initiale action/vert, les boutons Swagger/ReDoc ouvrent réellement la documentation du backend API, l’icône ITRM représente désormais un référentiel de référence avec un SVG plein/opaque et le header reste fixe pendant le scroll.**

### v0.29.41 — restauration de la palette initiale des camemberts et documentation API réelle

- Les boutons `Swagger` et `ReDoc` du second header utilisent désormais les URLs `apiDocumentation` publiées par `/config.json` et ouvrent les routes backend `/docs` et `/redoc`, proxifiées par `openinfra-web` si nécessaire.
- `openinfra-web` publie aussi `/docs`, `/swagger`, `/redoc`, `/openapi.yaml` et `/api/v1/openapi.yaml` comme proxy BFF vers `openinfra-api`, avec une CSP adaptée aux viewers Swagger/ReDoc.
- `OPENINFRA_WEB_PUBLIC_API_DOCS_BASE_URL` permet de publier explicitement une origine backend API externe lorsque le portail web et l’API sont exposés séparément.
- Les camemberts du Dashboard reviennent à la palette initiale : bleu action pour les lectures et vert pour les mutations.
- Le duo bleu nuit/fuchsia introduit en 0.29.39 est retiré du gradient et des légendes car trop agressif visuellement.
- Les garde-fous frontend vérifient explicitement que les camemberts n’utilisent plus le fuchsia.
- L’entrée ITRM utilise une icône de référentiel/référence pleine et opaque, homogène avec les autres pictogrammes de composants et plus cohérente avec son rôle de source canonique qu’une icône de tableau générique.
- Le double header est fixe en haut de viewport ; le contenu et le menu latéral scrollent dessous avec un offset dynamique calculé côté runtime.

### v0.29.39 — recherche globale durcie

- Le champ de recherche globale n’affiche plus le détail navigateur brut `Failed to fetch` : l’opérateur voit un message fonctionnel générique et les résultats locaux groupés restent disponibles.
- L’appel backend utilise `apiBaseUrl` fourni par `/config.json`, ce qui respecte `OPENINFRA_WEB_PUBLIC_API_BASE_URL` dans les déploiements avec préfixe API personnalisé. Les liens de documentation API utilisent `apiDocumentation` et peuvent être surchargés avec `OPENINFRA_WEB_PUBLIC_API_DOCS_BASE_URL`.

### v0.29.38 — recherche globale backend groupée par composant

- Le champ de recherche globale du double header appelle `/api/v1/search/global` quand le backend est disponible.
- Les résultats backend sont groupés par composant métier : ITRM, IPAM et Discovery.
- Les composants non accessibles au jeton courant sont ignorés sans fuite de données ; la recherche locale des opérations reste un fallback UX.
- La CLI expose `openinfra search global --tenant ... --admin-token ... --query ...` pour le même contrat applicatif.

### v0.29.37 — double header, recherche globale et retrait des messages permanents

- Le header devient une double barre : navigation produit en haut, recherche globale et accès documentation API dans le second bandeau.
- Le champ de recherche globale est centré, occupe la moitié de l’espace disponible sur desktop et embarque une loupe SVG cohérente avec le thème.
- Les résultats de recherche sont groupés par composant OpenInfra afin de garder une lecture claire lorsque plusieurs domaines correspondent.
- Les boutons `Swagger` et `ReDoc` utilisent les liens backend API publiés par `/config.json` ; par défaut `openinfra-web` proxyfie `/docs` et `/redoc` vers `openinfra-api`, sans réintroduire les contrôles Login/Sign-up supprimés précédemment.
- Les textes permanents précédemment issus d’alertes informatives sont retirés du rendu UI ; seules les alertes `warning/error` caractérisées et `success` post-soumission restent visibles.

### v0.29.36 — openinfra-web contextual alerts only

- Les pages composant n’affichent plus d’alerte informative par défaut pour signaler que le formulaire est typé.
- Les messages permanents hérités des anciennes alertes sont retirés à partir de la v0.29.37.
- Les alertes visibles restent contextuelles : `warning/error` lors d’un problème caractérisé et `success` uniquement après soumission effective d’un formulaire.
- Le validateur frontend et les tests d’intégration verrouillent l’absence d’alerte informative runtime par défaut.

### v0.29.35 — openinfra-web content shadow refinement

- Réduction des ombres portées sur les blocs de contenu : titlebar, cards, métriques, formulaires, synthèses et cartes composants.
- Conservation des effets existants du header principal et du menu latéral afin de ne pas casser la hiérarchie visuelle de navigation.
- Ajout de variables CSS dédiées `--openinfra-content-shadow` et `--openinfra-content-shadow-hover`, afin de séparer les effets de contenu des effets de navigation.
- Les tests et validateurs frontend contrôlent la présence des ombres allégées et empêchent un retour au rendu trop appuyé.

### v0.29.34 — Discovery Enterprise proxy enrollment verification

- Ajout `openinfra discovery proxy-enroll-verify` pour valider localement un fichier généré par `--config-output`.
- La commande reste réservée à l’édition Enterprise et refuse Lite/Pro avant lecture opérationnelle.
- Le validateur contrôle le schéma JSON, `tenant_id`, `name`, `enrolled`, la liste des backends, les URLs backend, les codes HTTP, les réponses JSON et les permissions POSIX `0600`.
- L’option `--allow-partial` permet de transformer un enrôlement backend partiel en avertissement lorsqu’un opérateur doit diagnostiquer une topologie HA sans masquer les erreurs de schéma.
- Correction de dette CLI : `openinfra discovery job-authorize` n’imprime plus deux fois le même document JSON.
- Le portail web affiche désormais le titre d’accueil court `Dashboard`.
- Les métriques et statistiques d’accueil restent strictement limitées à la page Dashboard et ne sont plus reprises dans les pages des composants.

### v0.29.33 — Discovery Enterprise proxy CLI enrollment

- Ajout `openinfra discovery proxy-enroll` pour enrôler un proxy Enterprise directement auprès d’un ou plusieurs backends via API.
- Ajout `openinfra discovery proxy-enroll-local` pour l’enrôlement local dans un backend sélectionné.
- Ajout de `POST /api/v1/discovery/proxy-enrollments` pour un contrat backend dédié à l’enrôlement proxy.
- Alignement domaine/API/CLI pour les types `site-proxy`, `network-proxy`, `datacenter-proxy`.
- Remplacement du thème web basic Bootstrap par une charte visuelle premium : surfaces navy, actions bleu vif, accents cyan, cartes arrondies, focus rings et transitions harmonisées, sans modification de structure de page ni ajout d’asset tiers.

### v0.29.32 — IPAM topologie opérationnelle

- Ajout du graphe IPAM opérationnel via `GET /api/v1/ipam/topology` et `openinfra ipam topology`.
- Consolidation déterministe des noeuds/relations VRF, agrégats, préfixes, plages, adresses, réservations, VLAN groups, VLAN, VXLAN VNI, ASN, BGP peers, observations DNS et baux DHCP.
- Ajout d'un contrôle d'intégrité du graphe pour détecter les arêtes orphelines avant exploitation UI/API/automation.
- Les formulaires restent API-only : aucune validation métier n'est dupliquée côté navigateur ; les invariants restent portés par le domaine et les services applicatifs.

### v0.29.30 — jumeau numérique DCIM initial

- Ajout de `GET /api/v1/dcim/digital-twin` et de `openinfra dcim digital-twin` pour restituer une vue consolidée de salle DCIM.
- Le document retourné `dcim_digital_twin` agrège `summary`, `room_plan`, `racks`, `floor_equipment`, `cables` et `integrity` sans créer de stockage parallèle.
- Chaque rack inclut son occupation, ses équipements, panneaux de brassage, ports, câbles, circuits, réservations, capacité énergie/refroidissement et élévations utilisables.
- Le dashboard ajoute l’opération **Jumeau numérique salle**, alignée sur le contrat backend et servie via le proxy same-origin.
- Le service réutilise les repositories et services DCIM existants ; les règles rack/U, câblage, énergie, refroidissement et intégrité restent centralisées côté domaine/application.

### v0.29.29 — énergie/refroidissement DCIM dans le dashboard et taxonomie ITRM

- Ajout des opérations web `Définir un équipement électrique`, `Définir un circuit électrique`, `Définir une zone de refroidissement`, `Réserver la puissance équipement` et `Capacité énergie/refroidissement`.
- Les formulaires sont alignés sur les contrats backend existants `POST /api/v1/dcim/power-devices`, `POST /api/v1/dcim/power-circuits`, `POST /api/v1/dcim/cooling-zones`, `POST /api/v1/dcim/power-reservations` et `GET /api/v1/dcim/energy-cooling-capacity`.
- Le navigateur ne calcule ni derating, ni redondance A/B, ni marge thermique : ces règles restent portées par le domaine DCIM et le service `DcimEnvironmentService`.
- Le document de découverte API et `docs/api/openapi.yaml` exposent désormais les routes énergie/refroidissement DCIM.
- Les sélecteurs ITRM affichent les libellés humains des catégories et types, tandis que les valeurs normalisées restent internes aux payloads API ; les types génériques obsolètes `physical-server` et `disk` sont retirés.

### v0.29.28 — câblage DCIM dans le dashboard

- Ajout des opérations web `Définir un panneau de brassage`, `Définir un port DCIM` et `Connecter un câble`, alignées sur les contrats backend `POST /api/v1/dcim/patch-panels`, `POST /api/v1/dcim/ports` et `POST /api/v1/dcim/cables`.
- Le formulaire câble expose explicitement les deux endpoints A/B, le média, le statut, le chemin câble en liste CSV, la longueur et le libellé opérateur.
- Les listes de valeurs `owner_type`, `connector`, `medium`, `status` et `rack_face` sont proposées en sélecteurs afin de réduire les erreurs de saisie sans dupliquer les règles métier serveur.
- Le dashboard conserve `Tracer un câble` pour la consultation de bout en bout via `GET /api/v1/dcim/cable-trace`.

### v0.29.27 — élévation rack DCIM dans le dashboard

- Ajout de l’opération web `Élévation rack` alignée sur `GET /api/v1/dcim/rack-elevation`.
- Le formulaire expose les champs métier `Site`, `Bâtiment`, `Salle`, `Rack`, `Face rack` et `Format rendu`.
- Le `Plan de salle` permet désormais de sélectionner explicitement le format `json`, `svg` ou `html`, comme l’API DCIM existante.
- Les champs DCIM de lecture sont marqués requis dans le catalogue runtime afin d’éviter les requêtes incomplètes côté opérateur.

### v0.29.26 — localisation équipement DCIM API/UI

- Ajout de `POST /api/v1/dcim/locations` pour localiser ou relocaliser un équipement DCIM via le service métier existant.
- La réponse publique inclut `asset_tag`, `name`, `tenant_id` et un bloc `location` complet : site, bâtiment, étage, salle, ligne, colonne, zone, rack, face, position U, hauteur U, coordonnées X/Y/Z et chemin humain.
- Le dashboard ajoute le formulaire `Localiser un équipement`, aligné sur le contrat API runtime `/v1/dcim/locations` et protégé par le proxy web same-origin.
- Le document de découverte API expose maintenant `dcim.locations`, afin de rendre le contrat consommable par intégration automatisée.

### v0.29.25 — taxonomie ITRM catégories / types

- Ajout d’un catalogue ITRM structuré par catégories : server, personal-computer, monitor-peripheral, network-device, storage, power-supply, rack-facility, cooling, security-safety, telecom, cloud-virtualization, software-service, cable-connectivity, mobile-iot et other.
- Chaque catégorie expose ses types rattachés, par exemple `server -> rack-server, virtual-machine`, `network-device -> firewall, load-balancer, router, switch` et `storage -> storage-array, hdd, ssd, nvme-drive`.
- Ajout de `GET /api/v1/itrm/resource-taxonomy` et de `openinfra itrm resource-taxonomy`.
- Les créations/modifications ITRM valident la cohérence catégorie/type et enrichissent les objets avec `resource_category` et `resource_type`.
- Le dashboard filtre dynamiquement le champ `Type de ressource` selon la `Catégorie`, via un mécanisme générique réutilisable pour les autres formulaires structurés de la même façon. Les `select` affichent les labels opérateur et transmettent uniquement les valeurs normalisées internes à la solution.

### v0.29.24 — réconciliation gouvernée ITRM

- Ajout de `openinfra itrm reconcile-object` et `POST /api/v1/itrm/reconcile-object`.
- Le mode par défaut produit un plan déterministe : chemins modifiés, conflits, règles obsolètes, version planifiée et attributs résultants.
- L’option `--apply` applique uniquement les plans acceptés ; les conflits bloquants ne provoquent aucun écrasement silencieux.
- Les plans et applications sont tracés dans l’audit objet via `itrm.reconciliation.plan` et `itrm.reconciliation.apply`.

### v0.29.23 — historique ITRM as-of et audit par objet

- Ajout de la restitution `openinfra itrm get-object-as-of` et `GET /api/v1/itrm/object-as-of`.
- Ajout du filtrage temporel des relations via `--as-of` et paramètre query `as_of`.
- Ajout de `openinfra itrm list-object-audit` et `GET /api/v1/itrm/object-audit`.
- Ajout du filtre audit `target_id` pour cibler précisément un objet ou une ressource.
- Ajout des formulaires web ITRM correspondants.

### v0.29.22 — statut BFF web et assainissement des erreurs auth

- `openinfra-web` expose `/status`, un endpoint de diagnostic sans secret indiquant le trust server-side, l’état des formulaires protégés et la configuration bearer backend sous forme `configured` / `not-configured`.
- Le dashboard affiche un indicateur discret `Formulaires protégés` alimenté par `/status`.
- Si le backend renvoie une erreur brute `missing bearer token`, le proxy web retourne une erreur BFF assainie au navigateur.
- La zone titre `Dashboard` conserve l’espacement vertical responsive autour du titre et du sous-titre.

### v0.29.20 — formulaires web fonctionnels et camemberts responsive

- L’accueil `openinfra-web` affiche désormais des métriques par composant : opérations, champs métier, champs obligatoires et mutations.
- Chaque composant ITRM, IPAM, DCIM, Discovery et Sécurité dispose d’un camembert lecture/mutation calculé depuis le catalogue UI.
- Les statistiques restent déterministes, sans accès direct base de données et sans exposition de secret côté navigateur.
- Les formulaires web ciblent les vrais contrats backend `/api/v1/*` via le proxy same-origin `/api/*`.
- `openinfra-web` peut injecter côté serveur un bearer backend via `OPENINFRA_WEB_BACKEND_BEARER_TOKEN` ou `OPENINFRA_BOOTSTRAP_TOKEN`, sans exposition navigateur.
- Les camemberts utilisent `clamp()` pour atteindre 10.5rem en desktop tout en restant adaptés aux écrans mobiles.
- L’accueil ne présente plus l’alerte permanente `Backend prêt` ; les alertes visibles sont réservées aux erreurs et aux soumissions de formulaire.


### v0.29.17 — openinfra-web Bootstrap 5 Dashboard Theme

- Portail `openinfra-web` aligné sur le thème Bootstrap 5 Dashboard.
- Header principal unique adapté aux domaines OpenInfra : Dashboard, ITRM, IPAM, DCIM, Discovery, Sécurité/RBAC et Audit.
- Bootstrap servi localement depuis `interfaces/rendering/static/assets/bootstrap.min.css`.
- Dashboard API-only : aucun DSN PostgreSQL ni secret backend exposé au navigateur.

## v0.29.13 — ITRM, agents proxy Enterprise et dashboard

- Le domaine public `Source of Truth/SOT` est renommé `IT Ressources Management/ITRM`.
- Les chemins primaires deviennent `openinfra itrm *`, `/api/v1/itrm/*`, les rôles `itrm:*` et les permissions `itrm.*`.
- Les anciens alias `openinfra ri *`, `/api/v1/ri/*`, `ri:*`, `openinfra sot *`, `/api/v1/sot/*` et `sot:*` restent compatibles uniquement pour migration ; ils sont signalés comme dépréciés et seront supprimés progressivement au profit de `itrm`.
- `agent` désigne exclusivement un proxy collector Enterprise en topologie étoile ; Lite et Pro collectent depuis les backends servers.
- Les assets web runtime sont déplacés sous `src/openinfra/interfaces/rendering/static`, cohérents avec le domaine présentation/rendering.
- `openinfra-web` devient un dashboard API-only couvrant ITRM, IPAM, DCIM, Discovery, sécurité/RBAC, audit, import/export et runtime.

## v0.29.11 — Runtime post-installation, backend API-only et sécurisation des flux

Cette livraison corrige et verrouille le modèle d'exploitation post-installation :

- `/opt/openinfra/config/openinfra.conf` devient la configuration runtime canonique.
- `/etc/openinfra` est un symlink vers `/opt/openinfra/config`, conservant le chemin compatible `/etc/openinfra/openinfra.conf`.
- `install.ini` et `.env` sont des entrées de bootstrap ; les services ne dépendent plus de `installers/` après installation.
- Les migrations backend sont copiées sous `/opt/openinfra/share/migrations/postgresql`.
- Le verrou `/opt/openinfra/config/.openinfra-installed.lock` empêche les installations multiples non contrôlées.
- Le backend reste API-only pour les opérateurs : pas de login LDAP/IPA direct côté backend.
- Le frontend web porte l'authentification opérateur, y compris LDAP/IPA en Pro/Enterprise.
- Les agents consomment uniquement l'API backend avec leur mécanisme technique d'enrôlement.
- Hors Lite, les échanges frontend-backend, agent-backend et backend-backend imposent TLS 1.3 et mTLS.
- Lite reste strictement local et loopback-only.

Nouvelle commande de contrôle :

```bash
PYTHONPATH=src python -m openinfra.interfaces.cli auth policy \
  --edition enterprise \
  --mode ipa \
  --url ldaps://ipa.example.net \
  --base-dn dc=example,dc=net \
  --bind-dn-ref env:OPENINFRA_IPA_BIND_DN \
  --bind-password-ref env:OPENINFRA_IPA_BIND_PASSWORD
```

## Installateurs autonomes

Les installateurs restent les points d'entrée d'installation réels :

```text
installers/setup/lite/install.py
installers/setup/pro/server/install.py
installers/setup/pro/web/install.py
installers/setup/enterprise/server/install.py
installers/setup/enterprise/web/install.py
installers/setup/enterprise/agent/install.py
```

Chaque installateur déploie son contenu autonome : `src/`, `pyproject.toml`, requirements de production par scope, unité systemd rendue et migrations backend quand le scope gère PostgreSQL.

## Validations principales

```bash
PYTHONPATH=src:. python -m pytest
PYTHONPATH=src:. python scripts/quality_gate.py
PYTHONPATH=src python -m openinfra.interfaces.cli installer validate --root installers
PYTHONPATH=src python -m openinfra.interfaces.cli spec validate --root docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1
python -m build
python scripts/verify_artifact.py dist/*.whl
```

### v0.29.14 — ITRM Quality & Certification

OpenInfra expose maintenant la qualité ITRM comme capacité pilotable :

```bash
openinfra itrm quality-object --tenant default --admin-token "$TOKEN" --key device/example
openinfra itrm quality-summary --tenant default --admin-token "$TOKEN" --kind device
```

Les endpoints primaires sont `/api/v1/itrm/quality/object` et `/api/v1/itrm/quality/summary`. Les alias historiques `/api/v1/sot/...` et `openinfra sot ...` restent disponibles uniquement pour migration et sont dépréciés.
