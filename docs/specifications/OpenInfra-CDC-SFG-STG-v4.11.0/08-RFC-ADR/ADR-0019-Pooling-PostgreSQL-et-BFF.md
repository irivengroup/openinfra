# ADR-0019 — Pooling PostgreSQL et BFF

## Statut
Accepté — CDC 4.9.0, OpenInfra 0.30.0.

## Contexte
Ouvrir une connexion PostgreSQL ou HTTP par requête augmente la latence et peut saturer PostgreSQL, les sockets et la mémoire.

## Décision
Chaque worker possède un pool PostgreSQL borné et un client HTTP persistant. Le produit `workers × max_size` ne doit jamais dépasser le budget global alloué au service. Toute acquisition est temporisée. Les connexions défectueuses sont invalidées et les métriques d’attente, saturation et timeout sont exposées.

PgBouncer en mode transaction est obligatoire pour les topologies Pro HA et Entreprise. Les migrations et opérations d’administration utilisent un rôle et un pool séparés. Le BFF utilise keep-alive, streaming, limites de corps et timeouts connect/read/write/pool distincts.

## Conséquences
- réduction de la latence de connexion ;
- protection de `max_connections` ;
- dimensionnement explicite par édition ;
- tests d’épuisement, timeout, reprise et arrêt propre obligatoires.
