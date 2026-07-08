### v0.29.53 — exports massifs streaming par chunks signés

- Ajout `openinfra export artifact-chunk` pour lire un artefact exporté signé par offset/taille bornée.
- Ajout `GET /api/v1/exports/artifact-chunk` retournant `content_base64`, `chunk_sha256`, `next_offset`, `final_chunk` et métadonnées d’artefact après vérification SHA-256 + HMAC-SHA256 complète.
- Ajout de l’opération portail `Imports / Exports > Chunk export signé`.
- OpenAPI, discovery, CDC et roadmap alignés sur P13 / EPIC-1302.
- Non-régression : le téléchargement complet `/api/v1/exports/artifact` et `openinfra export artifact` restent inchangés.

# OpenInfra Web v0.29.52

OpenInfra Web est le portail `openinfra-web` API-only. Il sert l'interface React/Bootstrap 5, expose un proxy applicatif `/api/*` vers le backend `openinfra-api` et fournit un dashboard aligné sur les domaines CLI.

## Contrat fonctionnel

Le dashboard doit permettre de piloter les composantes OpenInfra sans accès direct aux backends techniques :

- IT Ressources Management (ITRM) : objets, relations, versions et gouvernance via `/api/v1/itrm/*`.
- IPAM/DDI : recherche, capacité, réservations, conflits et assistants.
- DCIM : salles, racks, câbles, énergie, refroidissement et localisation.
- Discovery : collecte locale backend en Lite/Pro et agents proxy collectors Enterprise.
- Identité/RBAC/Sécurité : tokens, identité effective, groupes, rôles et politiques d'accès.
- Audit/Import/Export/Runtime : événements, intégrité, exports, imports et statut schéma.

Les anciens chemins `/api/v1/sot/*` et la commande `openinfra sot` restent des alias de compatibilité ; l'UI et la documentation utilisent ITRM comme contrat primaire.

## Contrat runtime

- Le navigateur consomme `/api/*` sur la même origine que `openinfra-web`.
- `openinfra-web` relaie les appels vers `OPENINFRA_WEB_BACKEND_URL`.
- Les assets runtime sont fournis depuis `src/openinfra/interfaces/rendering/static`, domaine présentation/rendering.
- Le frontend ne reçoit jamais de DSN PostgreSQL, de mot de passe LDAP/IPA, de clé privée ou de jeton d'enrôlement agent.
- Hors Lite, `OPENINFRA_WEB_BACKEND_URL` doit être HTTPS, sauf environnement Docker de validation explicitement marqué `OPENINFRA_WEB_ALLOW_INSECURE_BACKEND=true`.
- Le RBAC effectif reste appliqué côté backend à chaque appel API.

## Sémantique Discovery

Dans OpenInfra, `agent` signifie exclusivement proxy collector Enterprise, similaire aux capsules Satellite :

- Enterprise : agents proxy collectors autorisés en topologie étoile vers les backends servers.
- Lite/Pro : aucun agent distribué ; les backends servers exécutent directement les collectes autorisées.
- Agentless : aucun agent n'est installé sur les équipements découverts.

## Docker Compose

Le service Compose `openinfra-web` dépend de `api:8080`, écoute par défaut sur `127.0.0.1:2006` et sert `/health`, `/ready`, `/status`, `/config.json` et les assets web.

## Installation native

L'unité `openinfra-web.service` lance `openinfra-web` depuis le virtualenv géré par l'installateur et lit sa configuration via `EnvironmentFile=/etc/openinfra/openinfra.conf`, chemin compatible pointant vers `/opt/openinfra/config/openinfra.conf`.


## v0.29.52 — Imports / Exports et progression import massif

Le portail expose désormais le composant **Imports / Exports** avec l’opération **Progression import massif**. Cette opération appelle `GET /api/v1/imports/bulk-progress` via le proxy same-origin et demande uniquement le `job_id` du traitement bulk à inspecter.

Le navigateur n’analyse pas le fichier source importé et ne recalcule pas les métriques : il affiche le document consolidé par le backend à partir des checkpoints et du rapport bulk persistés. Les champs exposés couvrent le statut du job, la prochaine ligne à traiter, les compteurs de lignes valides/invalides, les créations/mises à jour, les batches terminés, l’indicateur de reprise `resumable` et la disponibilité du rapport final.

Cette opération est présente dans la source React, dans le runtime statique et dans `scripts/validate_frontend.py`, ce qui maintient la parité entre développement frontend et assets embarqués.


## v0.29.50 — administration éditions et quotas

Le module **Sécurité/RBAC/Audit** expose désormais les opérations d'administration des éditions dans le portail web :

- **Politiques éditions et quotas** : lecture du catalogue Lite/Pro/Enterprise via `GET /api/v1/editions/policies` ;
- **Vérifier une capacité édition** : contrôle d'une capability telle que `distributed_discovery_agents` via `GET /api/v1/editions/feature-check` ;
- **Vérifier un quota édition** : contrôle d'un quota runtime tel que `user` ou `discovery_collector` via `GET /api/v1/editions/quota-check`.

Le navigateur reste un client de consultation/opération : il ne réimplémente pas les règles de licence, les quotas ni les décisions de feature gate. Les décisions restent produites par `EditionQueryService` côté backend, protégées par le RBAC API lorsque l'authentification est active. Les mêmes opérations sont présentes dans le runtime statique, dans la source React et dans le validateur frontend afin de préserver la parité build/runtime.

## v0.29.47 — badge édition dans le header principal

Le header principal affiche l’édition runtime juste après le logo `OpenInfra`, via le badge `openinfra-edition-badge`. Ce badge conserve le gabarit Bootstrap existant : aucune surcharge de padding, taille de police, hauteur ou largeur minimale n’est ajoutée. Seul le fond visuel devient un dégradé fuchsia/action afin de distinguer clairement l’édition.

La titlebar du contenu ne reprend plus l’édition et n’affiche plus le mode d’authentification. Le mode reste présent dans `/config.json` pour le comportement applicatif, mais il n’est plus exposé comme indication permanente dans l’interface opérateur.

## v0.29.46 — accessibilité navigation et recherche

Le portail expose maintenant un contrat d’accessibilité vérifiable pour les parcours critiques :

- un lien d’évitement `Aller au contenu principal` pointe vers `#openinfra-main-content` ;
- la navigation du header et de la sidebar marque l’élément actif avec `aria-current` ;
- chaque accordéon de composant relie son bouton et son panneau via `aria-controls` et `aria-labelledby` ;
- la recherche globale est déclarée comme champ de recherche/combobox, ses résultats comme listbox et chaque résultat comme option ;
- les mises à jour de recherche et de résultat sont annoncées avec `aria-live` ;
- après sélection depuis la recherche globale, le focus est déplacé vers le contenu principal pour éviter de piéger l’opérateur dans le header fixe.

Ces règles sont présentes dans la source React, dans les assets runtime servis par `openinfra-web`, dans `scripts/validate_frontend.py` et dans les tests d’intégration web.

## v0.29.31 — formulaires IPAM Enterprise++

Le module IPAM du dashboard expose désormais les opérations opérateur suivantes : rechercher dans l’IPAM, afficher le dashboard IPAM, définir une VRF, définir un agrégat, définir un préfixe, définir une plage, enregistrer une adresse, allouer une adresse, utiliser l’assistant de réservation, calculer la capacité, lister les préfixes, afficher les bindings réseau, définir VLAN/VXLAN/ASN/BGP, observer DNS/DHCP, détecter les conflits et générer une prévisualisation DDI.

Les champs sont typés et ciblent les vrais contrats `/api/v1/ipam/*`. Les règles d'allocation, de conflit et de cohérence réseau restent exclusivement dans les services backend.

## v0.29.30 — jumeau numérique DCIM initial

Le dashboard expose désormais l’opération **Jumeau numérique salle** adossée à `GET /api/v1/dcim/digital-twin`. Le formulaire demande Site, Bâtiment et Salle, puis relaie la requête via le proxy same-origin sans exposer de jeton technique au navigateur.

La réponse agrège une vue opérateur cohérente : synthèse de salle, plan 2D, racks, équipements localisés, équipements au sol, panneaux, ports, câbles, capacité énergie/refroidissement, réservations et contrôles d’intégrité. Le navigateur ne reconstruit pas le jumeau numérique : il affiche le document consolidé par le backend.

## v0.29.29 — énergie/refroidissement DCIM dans le dashboard

Le dashboard expose désormais les opérations **Définir un équipement électrique**, **Définir un circuit électrique**, **Définir une zone de refroidissement**, **Réserver la puissance équipement** et **Capacité énergie/refroidissement**. Ces formulaires appellent exclusivement les contrats backend existants `POST /api/v1/dcim/power-devices`, `POST /api/v1/dcim/power-circuits`, `POST /api/v1/dcim/cooling-zones`, `POST /api/v1/dcim/power-reservations` et `GET /api/v1/dcim/energy-cooling-capacity` via le proxy same-origin.

Les champs opérateur couvrent la chaîne électrique A/B, les capacités en watts, le derating, le calibre disjoncteur, la zone froid/chaud, les températures soufflage/retour et la puissance attendue par actif. Le navigateur reste un client de saisie : les règles de capacité, redondance, derating, réservation et marge thermique restent centralisées côté backend.

## v0.29.28 — câblage DCIM dans le dashboard

Le dashboard expose désormais les opérations **Définir un panneau de brassage**, **Définir un port DCIM** et **Connecter un câble**. Ces formulaires appellent exclusivement les contrats backend existants `POST /api/v1/dcim/patch-panels`, `POST /api/v1/dcim/ports` et `POST /api/v1/dcim/cables` via le proxy same-origin ; aucun calcul de compatibilité connecteur/média, d’occupation de port ou de conflit d’endpoint n’est réimplémenté côté navigateur.

Les champs opérateur couvrent les endpoints A/B, le type propriétaire, le connecteur, le média, le statut, le chemin câble, la longueur et le libellé. Le champ **Chemin câble** utilise une saisie CSV transformée en liste `path_segments` avant soumission au backend.

## v0.29.27 — élévation rack DCIM dans le dashboard

Le dashboard expose désormais l’opération **Élévation rack** adossée à `GET /api/v1/dcim/rack-elevation`. Le formulaire couvre le site, le bâtiment, la salle, le rack, la face `front/rear` et le format de rendu `json/svg/html`. L’opération réutilise le proxy API same-origin et le service de visualisation DCIM existant : aucune logique de placement ni d’occupation U n’est recalculée côté navigateur.

Le formulaire **Plan de salle** expose également le choix du format de rendu `json/svg/html`, afin de rendre la parité dashboard/API explicite pour les plans 2D.

## v0.29.26 — localisation équipement DCIM API/UI

Le dashboard expose l’opération **Localiser un équipement** adossée à `POST /api/v1/dcim/locations`. Le formulaire couvre l’identification d’actif, la salle, la ligne, la colonne, le rack, la face, la position U, la hauteur U et les coordonnées XYZ optionnelles. L’appel passe par le proxy API existant et conserve les validations métier DCIM côté serveur.

## v0.29.25 — taxonomie ITRM et filtres dynamiques

Le formulaire `Créer / mettre à jour une ressource` sépare désormais la `Catégorie` et le `Type de ressource`. La catégorie pilote dynamiquement la liste des types compatibles : un serveur propose notamment `Rack server`, `Hypervisor host` et `Virtual machine`, tandis qu’un équipement réseau propose `Switch`, `Router`, `Firewall`, `Load balancer` ou `Wireless access point`.

Les listes déroulantes affichent les libellés métier (`Rack server`, `Firewall`, `Storage array`, etc.) mais conservent les valeurs techniques normalisées (`rack-server`, `firewall`, `storage-array`) dans les payloads envoyés à l’API. Les types génériques obsolètes `physical-server` et `disk` ne sont plus proposés.

Le même mécanisme de formulaire est générique : tout champ `select` peut déclarer une dépendance `optionsByField` vers un autre champ et fournir une table `optionsMap`. Les futurs objets structurés catégorie/type des autres composants peuvent donc réutiliser ce comportement sans logique spécifique au composant.

## v0.29.16 — Bootstrap 5 Dashboard Theme

Le portail utilise le thème Bootstrap 5 Dashboard comme structure principale : header sombre principal unique, sidebar gauche, métriques runtime et zone centrale d'opérations. Le header Bootstrap est adapté aux domaines OpenInfra : Dashboard, ITRM, IPAM, DCIM, Discovery et Sécurité.

Les styles Bootstrap sont fournis localement par `src/openinfra/interfaces/rendering/static/assets/bootstrap.min.css`; aucun CDN externe n'est nécessaire. Le fichier `openinfra-web.css` ne contient que les adaptations produit OpenInfra.

## v0.29.16 — formulaires métier typés, trust server-side et navigation accordéon

Le dashboard ne présente plus de champ générique `Attributs`. Les formulaires exposent directement les variables métier attendues par l'API et par le CLI : numéro de série, constructeur, modèle, site, bâtiment, salle, ligne, colonne, rack, IP de management, source autoritative, tags, scopes collector, empreinte certificat, endpoint mTLS, etc.

L'opérateur ne saisit pas de token API technique dans le navigateur. `openinfra-web` agit comme BFF server-side : il établit le trust applicatif avec le backend, retire tout `Authorization` transmis par le navigateur et utilise exclusivement ses paramètres runtime serveur. Les références DSN/credentials PostgreSQL du service web sont déclarées dans `install.ini` sous `[web_database]`, matérialisées dans `/opt/openinfra/config/openinfra.conf` et jamais exposées dans `/config.json` ni dans les assets statiques.

Le panneau latéral devient le menu principal. `Dashboard` reste une entrée directe ; ITRM, IPAM, DCIM, Discovery et Sécurité/RBAC/Audit sont des accordéons avec transition `fade`. Les opérations précédemment affichées dans une zone interne de la page sont déplacées dans ces accordéons. L'UI n'affiche pas les méthodes HTTP aux opérateurs.

## v0.29.17 — header principal unique

Le second bandeau Bootstrap de recherche/actions a été retiré du header web. Le dashboard conserve uniquement le header sombre principal et la sidebar accordéon comme navigation opérationnelle. Les boutons `Login` et `Sign-up` ne sont plus affichés dans le header ; l’authentification opérateur reste portée par le flux applicatif web et non par des contrôles techniques visibles dans le bandeau.


## v0.29.18 — statistiques d’accueil par composant

L’accueil du dashboard affiche maintenant une synthèse de chaque composant métier : ITRM, IPAM, DCIM, Discovery et Sécurité/RBAC/Audit. Chaque carte expose les métriques calculées depuis le catalogue UI : nombre d’opérations, nombre de champs métier, champs obligatoires et mutations.

Un camembert par composant représente la répartition fonctionnelle lecture/mutation sans afficher les méthodes HTTP à l’opérateur. Cette vue est déterministe, ne consomme aucun accès base direct et ne fait transiter aucun secret dans le navigateur.

## v0.29.20 — formulaires fonctionnels, bearer backend server-side et camemberts responsives

Les formulaires du dashboard sont désormais alignés sur les vrais contrats backend `/api/v1/*` servis via le proxy same-origin `/api/*`. Les chemins IPAM utilisent notamment `/v1/ipam/ui-search`, `/v1/ipam/allocate`, `/v1/ipam/capacity` et `/v1/ipam/conflicts`; Discovery envoie les champs attendus `version`, `endpoint_url`, `requested_scope` et `target`.

Pour les runtimes backend authentifiés, `openinfra-web` peut injecter côté serveur un bearer backend via `OPENINFRA_WEB_BACKEND_BEARER_TOKEN`, avec fallback contrôlé sur `OPENINFRA_BOOTSTRAP_TOKEN`. Ce secret n’est jamais sérialisé dans `/config.json`, dans les assets JavaScript/CSS ou dans les formulaires navigateur. Un `Authorization` fourni par le navigateur n’est pas relayé automatiquement.

En runtime Docker, une valeur vide de `OPENINFRA_WEB_BACKEND_BEARER_TOKEN` est traitée comme absente : `openinfra-web` utilise alors `OPENINFRA_BOOTSTRAP_TOKEN`. Si aucun bearer server-side n’est disponible pour une route API protégée, le proxy retourne une erreur de configuration BFF explicite plutôt que de propager l’erreur backend brute `missing bearer token` au navigateur.

Les camemberts du dashboard d’accueil sont doublés et adaptatifs : `--openinfra-pie-size` utilise `clamp(8rem, 14vw, 10.5rem)` en desktop/tablette et une règle mobile dédiée en dessous de 576 px.


## v0.29.23 — formulaires ITRM historique

- Ajout du formulaire `Restituer une ressource à date`, câblé sur `/v1/itrm/object-as-of`.
- Ajout du formulaire `Audit d’une ressource`, câblé sur `/v1/itrm/object-audit`.
- Le formulaire `Lister les relations` accepte désormais `as_of` pour filtrer les relations valides à une date donnée.
- Les formulaires restent exécutés via BFF server-side, sans token technique saisi ou stocké dans le navigateur.

## v0.29.22 — titlebar dashboard concise

La zone `Dashboard` utilise un espacement vertical responsive pour éviter un rendu compact du titre et du sous-titre. La règle produit `padding-block: clamp(1rem, 2vw, 1.75rem)` est appliquée à `.openinfra-titlebar`, avec un interligne renforcé sur le texte descriptif.

Cette correction est appliquée aux sources React et aux assets runtime servis par `openinfra-web`; elle est verrouillée par `validate_frontend.py` et les tests d’intégration serveur web.

## v0.29.22 — statut BFF sans secret et assainissement auth backend

`openinfra-web` expose désormais `/status`, un statut BFF destiné à l’exploitation. Il indique l’état des formulaires protégés, le trust web/backend server-side, le trust base de données et la présence d’un bearer backend server-side sans jamais sérialiser la valeur du secret. En absence de bearer, le statut retourne une remédiation explicite vers `OPENINFRA_WEB_BACKEND_BEARER_TOKEN` ou `OPENINFRA_BOOTSTRAP_TOKEN`.

Le proxy web assainit aussi les erreurs d’authentification backend : une réponse brute `missing bearer token` issue de l’API n’est pas renvoyée telle quelle au navigateur. L’opérateur reçoit une erreur BFF explicite indiquant que l’authentification backend via `openinfra-web` a échoué.


## IPAM topologie opérationnelle

Le dashboard expose `Topologie opérationnelle IPAM` sur `/v1/ipam/topology`. Le formulaire conserve `tenant_id` côté BFF et accepte un filtre VRF optionnel ; le backend produit le graphe consolidé et le navigateur ne recalcule pas les invariants IPAM.


## v0.29.33 — charte graphique premium Bootstrap 5

Le portail conserve exactement sa structure existante : header principal unique, sidebar accordéon, zone centrale de formulaires, cartes de métriques et panneau résultat. La couche visuelle basic Bootstrap est remplacée par une charte premium appliquée uniquement par CSS compatible Bootstrap 5 : surfaces navy, boutons bleu vif, accents cyan, fonds soft blue, cartes arrondies, ombres maîtrisées, focus rings visibles et transitions légères.

Aucun logo, image ou composant tiers n’est importé. Les classes Bootstrap existantes restent utilisables ; les adaptations sont portées par `openinfra-web.css` et `openinfra-theme.css`, ce qui préserve le contrat HTML/React et le runtime offline.

## Discovery Enterprise proxy enrollment CLI

La version 0.29.33 ajoute l’enrôlement direct des proxies Discovery Enterprise en CLI. `openinfra discovery proxy-enroll` poste vers un ou plusieurs backends via `POST /api/v1/discovery/proxy-enrollments` et refuse Lite/Pro avant tentative d’enrôlement. `openinfra discovery proxy-enroll-local` couvre le cas backend local sélectionné. Le dashboard conserve l’administration Discovery API-only existante ; les secrets restent côté backend/BFF et ne sont pas demandés au navigateur.

## v0.29.37 — Double barre et recherche globale

Le header `openinfra-web` est structuré en deux barres complémentaires. La première conserve la navigation produit et l’identité OpenInfra. La seconde expose une recherche globale centrée, dimensionnée à 50 % de l’espace disponible sur desktop, avec icône SVG loupe intégrée et effets de focus/hover alignés sur la charte navy/bleu/cyan.

La recherche porte sur les composants, opérations, méthodes, chemins API et champs exposés par le dashboard. Lorsque plusieurs composants correspondent, les résultats sont groupés par composant afin d’éviter une liste globale non contextualisée. Chaque résultat sélectionne directement l’opération concernée et ouvre le composant associé dans le menu latéral.

Le second bandeau expose aussi les actions `Swagger` et `ReDoc`. Depuis la v0.29.41, ces actions ne sont plus de simples liens statiques : elles consomment les URLs `apiDocumentation` publiées par `/config.json` et ouvrent les routes backend API réelles `/docs` et `/redoc`. Par défaut, `openinfra-web` proxyfie ces routes vers `openinfra-api`; si le portail et l’API sont publiés sur des origines séparées, `OPENINFRA_WEB_PUBLIC_API_DOCS_BASE_URL` peut publier explicitement l’origine documentaire backend. Les anciens contrôles `Login`, `Sign-up` et la recherche locale `Search OpenInfra operations` restent interdits.

Les textes permanents précédemment issus des alertes informatives ne sont plus rendus sur les pages composant. Le composant conserve son titre, son sous-titre, le formulaire métier et le panneau résultat ; les alertes restent réservées aux erreurs/warnings caractérisés et au succès après soumission effective.



## v0.29.42 — header fixe, ombre renforcée et scroll aligné

Le double header reste fixe en haut du viewport et porte l’ombre principale de séparation via `--openinfra-header-shadow`. Cette ombre est volontairement plus prononcée que `--openinfra-content-shadow` et `--openinfra-content-shadow-hover`, réservées aux cartes, formulaires et blocs de contenu. La hiérarchie visuelle est donc claire : le header est prioritaire, les cartes restent légères.

Le scroll du contenu commence juste sous le header, sans recouvrement ni marge artificielle. Les assets appliquent `padding-top: var(--openinfra-fixed-header-height)` au `body`, `scroll-padding-top` au document et recalculent la hauteur réelle du header après rendu et lors des redimensionnements. Le menu latéral reste sticky avec `top: var(--openinfra-fixed-header-height)`.

L’ombre basse du second bandeau est supprimée afin que l’effet soit porté par le header complet `openinfra-header-stack` sur toute la largeur de la page.

## v0.29.41 — Liens Swagger/ReDoc branchés sur le backend API

Le header ne pointe plus vers des routes statiques supposées du portail. Le navigateur lit `apiDocumentation.swaggerUrl` et `apiDocumentation.redocUrl` depuis `/config.json`. En mode BFF standard, ces URLs restent same-origin (`/docs`, `/redoc`) et `openinfra-web` les proxyfie vers `openinfra-api`. En mode exposition séparée, `OPENINFRA_WEB_PUBLIC_API_DOCS_BASE_URL` permet de publier une origine backend API explicite.

Les routes `/docs`, `/swagger`, `/redoc`, `/openapi.yaml` et `/api/v1/openapi.yaml` sont donc servies par le backend API réel, pas par un placeholder UI. La CSP du proxy web autorise uniquement les sources nécessaires aux viewers Swagger UI et ReDoc sur ces pages documentaires.

## v0.29.37 — Alertes contextuelles uniquement

Les pages composant n’affichent plus d’alerte informative au chargement. Depuis la v0.29.37, les messages permanents précédemment issus de ces alertes sont également retirés du rendu afin d’éviter toute aide statique redondante. Les alertes dans la zone principale sont réservées aux situations actionnables : erreur/warning caractérisé ou succès après soumission effective.

La non-régression est portée par `scripts/validate_frontend.py` et par `tests/integration/test_openinfra_web.py`, qui interdisent `alert alert-info`, `role="note"` et le retour des textes permanents hérités des anciennes alertes dans les sources UI runtime.

## v0.29.35 — Discovery proxy enrollment verification

La validation locale des fichiers d’enrôlement proxy Enterprise est portée par la CLI `openinfra discovery proxy-enroll-verify`. Le dashboard ne demande toujours aucun secret d’enrôlement proxy au navigateur : les opérations sensibles restent côté CLI/backend, tandis que le portail conserve uniquement les workflows API Discovery déjà exposés.

La même livraison simplifie le titre de la page d’accueil en `Dashboard` et isole les métriques/cartes d’accueil dans cette page uniquement. Lorsqu’un opérateur ouvre ITRM, IPAM, DCIM, Discovery ou Sécurité, la zone centrale affiche seulement le titre du composant, son sous-titre contextuel, le formulaire métier et le résultat éventuel.


## v0.29.41 — restauration des couleurs initiales des camemberts

Les camemberts de l’accueil reviennent à la palette initiale plus confortable : `--openinfra-action` pour les lectures et `--openinfra-green` pour les mutations. Le duo bleu nuit/fuchsia est retiré du gradient et des pastilles de légende afin de réduire la fatigue visuelle signalée.

Les mêmes garde-fous sont appliqués aux sources React et aux assets runtime servis par `openinfra-web` : le fuchsia ne doit plus être utilisé par les camemberts du Dashboard.

## v0.29.41 — icône ITRM référentiel/référence

L’entrée ITRM du header, du menu latéral et des cartes de composants utilise désormais une icône de référentiel/référence pleine et opaque. Cette icône remplace le pictogramme tableau générique afin de matérialiser le rôle d’ITRM comme référentiel canonique des ressources, relations, versions et règles de gouvernance tout en restant conforme à la densité visuelle des autres pictogrammes de composants.

Les sources React et les assets runtime exposent le même nom d’icône `reference`, contrôlé par le validateur frontend et les tests d’intégration web.

## v0.29.39 — Recherche globale tolérante

La recherche globale du double header construit son appel depuis `apiBaseUrl` exposé par `/config.json`. Les déploiements qui personnalisent `OPENINFRA_WEB_PUBLIC_API_BASE_URL` n’ont donc plus de chemin `/api` figé dans l’asset JavaScript.

Si le backend ou le proxy BFF est temporairement indisponible, le navigateur n’expose pas l’erreur technique brute telle que `Failed to fetch`. Le panneau de résultats affiche un message fonctionnel générique et conserve le fallback local des opérations, toujours groupé par composant.

## v0.29.38 — Recherche globale backend

La recherche globale du double header appelle `GET /api/v1/search/global` avec `tenant_id`, `query` et `limit`. Quand le backend répond, les résultats métiers sont affichés par composant : ITRM, IPAM et Discovery. Chaque entrée expose un libellé, une description, un type et une route API ouvrable depuis le panneau résultat.

Si le backend est indisponible, si le jeton courant ne permet pas la recherche ou si la requête est trop courte, le portail conserve un fallback local sur les opérations déjà connues. Cette dégradation contrôlée évite une page vide tout en empêchant l’affichage de données non autorisées.

## Header fixe et navigation

Le portail `openinfra-web` conserve le double header en position fixe. La hauteur réelle du header est mesurée côté runtime et publiée dans `--openinfra-fixed-header-height` afin que le contenu principal et le menu latéral scrollent sous le bandeau sans recouvrement. Le menu latéral reste sticky sous ce header et conserve son propre scroll vertical lorsque la liste des composants dépasse la hauteur disponible.


## v0.29.45 — sidebar accordéon sans masquage

La version 0.29.45 corrige le comportement du panneau latéral lorsque plusieurs composants et opérations sont affichés. Un composant ouvert en accordéon reste dans le flux vertical, repousse les composants inférieurs vers le bas et n’utilise plus de plafond `max-height` fixe susceptible de masquer une partie de ses opérations.

Le scroll reste porté par `.openinfra-sidebar`, borné sous le header fixe. Les règles `overflow-y: auto`, `overflow-x: hidden`, `overscroll-behavior: contain` et `scrollbar-gutter: stable` garantissent une navigation latérale longue sans chevauchement ni saut de largeur lors de l’apparition de la barre de défilement.

## v0.29.43 — continuité UI

La version 0.29.43 ne modifie pas le contrat visuel du portail web. Les évolutions portent sur le backend ITAM, les API, la CLI, la persistance et la documentation contractuelle. Les garde-fous frontend existants restent exécutés afin de vérifier l’absence de régression sur le double header, la recherche globale, les liens Swagger/ReDoc et les composants du Dashboard.


## v0.29.45 — ITAM visible dans Dashboard/header/sidebar/recherche

Le portail expose ITAM comme composant de premier niveau : carte Dashboard, entrée header, accordéon sidebar et recherche globale. L’icône `asset` est un SVG plein/opaque cohérent avec les autres composants. Les boutons Swagger/ReDoc conservent leur branchement backend mais leur taille est réduite de moitié pour préserver l’équilibre du double header.


## v0.29.49 — badge édition fuchsia très foncé

Le badge d’édition conserve sa position après le logo OpenInfra et son gabarit Bootstrap `badge`. Son fond utilise maintenant un dégradé fuchsia très foncé `#2a0015 → #4b001f → #6a1430`, avec une ombre prune cohérente, afin de tendre vers un ton chaud/bruné sans devenir marron ni revenir au bleu Bootstrap.

## v0.29.48 — badge édition fuchsia effectif

Le badge d’édition reste placé immédiatement après le logo OpenInfra. Il conserve la classe Bootstrap `badge` pour préserver son gabarit, mais n’utilise plus `text-bg-primary` afin de supprimer l’héritage bleu. Le fond est appliqué par `badge.openinfra-edition-badge` avec un dégradé fuchsia dédié.

## v0.29.51 — ITAM licences logicielles

Le composant **IT Asset Management** expose désormais les opérations web suivantes, toujours via les endpoints backend `/api/v1` réels :

- lecture d’une licence logicielle par référence ;
- rapport de conformité licence à date ;
- déclaration/mise à jour d’une licence logicielle ;
- mise à jour de la quantité assignée.

Les formulaires restent typés métier : produit, éditeur, référence licence, référence contrat, métrique, quantités, période de droit, statut, propriétaire et notes. Aucune logique de conformité n’est dupliquée côté navigateur ; le navigateur délègue au service applicatif ITAM.
