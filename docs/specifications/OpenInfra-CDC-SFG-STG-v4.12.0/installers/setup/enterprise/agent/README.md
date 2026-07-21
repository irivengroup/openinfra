# Installateur OpenInfra Entreprise — agent Discovery

Ce scope installe le collecteur `openinfra-agent.service`. L'agent publie ses preuves vers le backend Entreprise et ne possède aucun accès direct à PostgreSQL.

## Préconditions

- endpoint HTTPS/VIP, FQDN, IP, masque, passerelle et DNS validés ;
- jeton d'enrôlement fourni par référence `OPENINFRA_AGENT_ENROLLMENT_TOKEN` ;
- certificats TLS 1.3/mTLS et CA présents ;
- flux réseau Discovery explicitement autorisés selon le moindre privilège.

## Résultat attendu

L'agent est installé sous `/opt/openinfra/`, enrôlé par API, exécuté par un compte système non-root et activé via `openinfra-agent.service`. Aucun secret n'est matérialisé dans `install.ini` et aucune migration backend n'est appliquée.

## Validation et rollback

Le dry-run vérifie l'identité, les certificats, l'endpoint, les permissions et les dépendances. En cas d'échec, l'enrôlement incomplet est révoqué et la configuration précédente est restaurée sans altérer les preuves déjà publiées.
