# OpenInfra Web v0.29.24

OpenInfra Web est le portail `openinfra-web` API-only. Il sert l'interface React/Bootstrap 5, expose un proxy applicatif `/api/*` vers le backend `openinfra-api` et fournit un dashboard de pilotage aligné sur les domaines CLI.

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


## v0.29.24 — formulaires ITRM historique

- Ajout du formulaire `Restituer une ressource à date`, câblé sur `/v1/itrm/object-as-of`.
- Ajout du formulaire `Audit d’une ressource`, câblé sur `/v1/itrm/object-audit`.
- Le formulaire `Lister les relations` accepte désormais `as_of` pour filtrer les relations valides à une date donnée.
- Les formulaires restent exécutés via BFF server-side, sans token technique saisi ou stocké dans le navigateur.

## v0.29.22 — titlebar dashboard aérée

La zone `Dashboard de pilotage OpenInfra` utilise un espacement vertical responsive pour éviter un rendu compact du titre et du sous-titre. La règle produit `padding-block: clamp(1rem, 2vw, 1.75rem)` est appliquée à `.openinfra-titlebar`, avec un interligne renforcé sur le texte descriptif.

Cette correction est appliquée aux sources React et aux assets runtime servis par `openinfra-web`; elle est verrouillée par `validate_frontend.py` et les tests d’intégration serveur web.

## v0.29.22 — statut BFF sans secret et assainissement auth backend

`openinfra-web` expose désormais `/status`, un statut BFF destiné à l’exploitation. Il indique l’état des formulaires protégés, le trust web/backend server-side, le trust base de données et la présence d’un bearer backend server-side sans jamais sérialiser la valeur du secret. En absence de bearer, le statut retourne une remédiation explicite vers `OPENINFRA_WEB_BACKEND_BEARER_TOKEN` ou `OPENINFRA_BOOTSTRAP_TOKEN`.

Le proxy web assainit aussi les erreurs d’authentification backend : une réponse brute `missing bearer token` issue de l’API n’est pas renvoyée telle quelle au navigateur. L’opérateur reçoit une erreur BFF explicite indiquant que l’authentification backend via `openinfra-web` a échoué.
