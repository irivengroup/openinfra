# OpenInfra Web v0.29.13

OpenInfra Web est le portail `openinfra-web` API-only. Il sert l'interface React/Bootstrap 5, expose un proxy applicatif `/api/*` vers le backend `openinfra-api` et fournit un dashboard de pilotage aligné sur les domaines CLI.

## Contrat fonctionnel

Le dashboard doit permettre de piloter les composantes OpenInfra sans accès direct aux backends techniques :

- Ressources Inventory (RI) : objets, relations, versions et gouvernance via `/api/v1/ri/*`.
- IPAM/DDI : recherche, capacité, réservations, conflits et assistants.
- DCIM : salles, racks, câbles, énergie, refroidissement et localisation.
- Discovery : collecte locale backend en Lite/Pro et agents proxy collectors Enterprise.
- Identité/RBAC/Sécurité : tokens, identité effective, groupes, rôles et politiques d'accès.
- Audit/Import/Export/Runtime : événements, intégrité, exports, imports et statut schéma.

Les anciens chemins `/api/v1/sot/*` et la commande `openinfra sot` restent des alias de compatibilité ; l'UI et la documentation utilisent RI comme contrat primaire.

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

Le service Compose `openinfra-web` dépend de `api:8080`, écoute par défaut sur `127.0.0.1:2006` et sert `/health`, `/ready`, `/config.json` et les assets web.

## Installation native

L'unité `openinfra-web.service` lance `openinfra-web` depuis le virtualenv géré par l'installateur et lit sa configuration via `EnvironmentFile=/etc/openinfra/openinfra.conf`, chemin compatible pointant vers `/opt/openinfra/config/openinfra.conf`.
