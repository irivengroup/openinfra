# OpenInfra v0.29.31

OpenInfra est une solution Python orientée objet pour référentiel d'infrastructure, IPAM/DDI, DCIM, inventaire, import/export, sécurité, éditions Lite/Pro/Enterprise et installateurs autonomes.

**Version courante : 0.29.31 — P11/IPAM expose dans le dashboard les opérations Enterprise++ VRF, agrégats, préfixes, plages, adresses, VLAN/VXLAN, ASN/BGP, observations DNS/DHCP, DDI, conflits, capacité et allocation/réservation.**

### v0.29.31 — IPAM Enterprise++ dashboard et découverte API

- Ajout des formulaires IPAM avancés dans le dashboard : VRF, agrégats, préfixes, plages, adresses, VLAN groups, VXLAN VNI, VLAN, ASN, BGP peers, observations DNS/DHCP, DDI preview, assistant de réservation, allocation, capacité, bindings et conflits.
- Ajout de la section IPAM dans le document de découverte API racine afin d'exposer les contrats REST IPAM déjà disponibles.
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
- La zone titre `Dashboard de pilotage OpenInfra` conserve l’espacement vertical responsive autour du titre et du sous-titre.

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

## v0.29.13 — ITRM, agents proxy Enterprise et dashboard de pilotage

- Le domaine public `Source of Truth/SOT` est renommé `IT Ressources Management/ITRM`.
- Les chemins primaires deviennent `openinfra itrm *`, `/api/v1/itrm/*`, les rôles `itrm:*` et les permissions `itrm.*`.
- Les anciens alias `openinfra ri *`, `/api/v1/ri/*`, `ri:*`, `openinfra sot *`, `/api/v1/sot/*` et `sot:*` restent compatibles uniquement pour migration ; ils sont signalés comme dépréciés et seront supprimés progressivement au profit de `itrm`.
- `agent` désigne exclusivement un proxy collector Enterprise en topologie étoile ; Lite et Pro collectent depuis les backends servers.
- Les assets web runtime sont déplacés sous `src/openinfra/interfaces/rendering/static`, cohérents avec le domaine présentation/rendering.
- `openinfra-web` devient un dashboard de pilotage API-only couvrant ITRM, IPAM, DCIM, Discovery, sécurité/RBAC, audit, import/export et runtime.

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
