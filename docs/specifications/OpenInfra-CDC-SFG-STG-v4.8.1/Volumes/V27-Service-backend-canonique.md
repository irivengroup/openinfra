# Volume 27 — Service backend canonique et simplification systemd

## 27.1 Objectif

Ce volume formalise la simplification du modèle systemd OpenInfra : le backend applicatif, le bootstrap PostgreSQL géré, l'application des migrations et l'orchestration de démarrage sont portés par un service unique `openinfra.service`.

## 27.2 Règle de conception

Le scope d'installation `server` reste autorisé comme périmètre d'installateur, car il distingue clairement le backend du frontend et des agents. En revanche, ce scope ne doit pas créer de service systemd backend supplémentaire.

Rôles canoniques :

- `openinfra.service` : backend/API, PostgreSQL géré, migrations, orchestration applicative et mode Lite all-in-one.
- `openinfra-web.service` : frontend React + Bootstrap 5 consommant exclusivement l'API backend.
- `openinfra-agent.service` : collecteurs d'auto discovery alimentant la base centrale via l'API backend.
- `openinfra-worker.service` : traitements longs lorsque séparés du backend.
- `openinfra-scheduler.service` : planification.
- `openinfra-connector.service` : connecteurs externes.
- `openinfra-exporter.service` : métriques.

## 27.3 Exigences fonctionnelles

- Toute installation backend Pro ou Entreprise doit installer `openinfra.service`.
- Toute installation Lite doit utiliser `openinfra.service` comme service all-in-one.
- Le backend doit déployer les dépendances PostgreSQL requises lorsque PostgreSQL est géré par OpenInfra.
- Le backend doit appliquer toutes les migrations backend avant démarrage final.
- Les scopes `web` et `agent` ne doivent jamais appliquer les migrations backend.
- L'état des migrations doit être consultable depuis la CLI, l'API et l'interface web selon les droits RBAC.

## 27.4 Critères d'acceptation

- Les matrices systemd et installateurs ne déclarent qu'un seul service backend canonique : `openinfra.service`.
- Une installation Pro backend démarre `openinfra.service` et non un service backend distinct.
- Une installation Entreprise backend cluster démarre plusieurs instances `openinfra.service` derrière le load balancer ou la VIP selon le design retenu.
- Les migrations sont exécutées une seule fois de manière idempotente, avec verrou applicatif et rapport de preuve.
- Le frontend consomme l'API exposée par le backend et ne dépend pas du nom d'une édition.
- Les agents publient les observations vers l'API backend et n'écrivent jamais directement dans PostgreSQL.

## Modèle backend API-only et clients autorisés

Le service backend expose l'API OpenInfra et applique les politiques d'autorisation effectives. Il n'est pas un portail de login opérateur LDAP/IPA. Les clients autorisés sont :

- le frontend web, chargé de l'authentification opérateur et de la présentation ;
- les agents techniques enrôlés, chargés de la collecte et de la remontée d'observations ;
- les autres nœuds backend dans les topologies clusterisées.

Le backend valide les jetons applicatifs, applique RBAC/ABAC, journalise les refus et décisions sensibles, et refuse tout chemin de contournement qui tenterait d'utiliser LDAP/IPA directement sur un scope backend. Tous les flux réseau hors Lite utilisent TLS 1.3 et mTLS.

## Complément v0.29.15 — thème Bootstrap 5 du portail web

`openinfra-web.service` doit servir un dashboard Bootstrap 5 complet basé sur le modèle Dashboard officiel et sur un header principal unique adapté à OpenInfra. Les composants visibles doivent permettre le pilotage réel des domaines exposés par l'API backend : Dashboard, IT Ressources Management, IPAM, DCIM, Discovery, Sécurité/RBAC, Audit et Runtime.

Les fichiers statiques appartiennent au domaine présentation/rendering et sont empaquetés sous `src/openinfra/interfaces/rendering/static`. Le runtime doit charger Bootstrap localement depuis `assets/bootstrap.min.css`, puis le thème OpenInfra depuis `assets/openinfra-web.css`.
