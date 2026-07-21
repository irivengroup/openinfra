# Identité fédérée, Team Sync et Oracle

## Principes

PostgreSQL reste la persistance transactionnelle par défaut. Oracle est un backend optionnel réservé à l’édition Entreprise, sélectionné explicitement et isolé derrière les mêmes ports applicatifs et frontières `UnitOfWork`. Les dépendances Oracle ne sont pas installées lorsque PostgreSQL est utilisé.

L’authentification SAML 2.0 valide les assertions et signatures côté serveur. Les certificats, endpoints IdP, attributs et mappings groupes-vers-rôles proviennent exclusivement de `openinfra.conf` et de références de secrets. Le client ACS ne transmet que `SAMLResponse` et éventuellement `RelayState`.

LDAP/IPA avancé prend en charge LDAPS ou StartTLS, autorités de certification, bases utilisateurs/groupes distinctes, attributs configurables, pagination, limites, timeouts, referrals contrôlés et groupes imbriqués avec profondeur maximale.

Team Sync prend en charge LDAP, OAuth, Auth Proxy signé HMAC et Okta. Chaque source possède ses identités et appartenances gérées ; une synchronisation ne supprime pas une identité locale ni une appartenance détenue par une autre source. La pagination HTTP reste sur l’origine HTTPS configurée.

## Production sans Docker

Le déploiement de production utilise l’installateur natif, `/opt/openinfra/config/openinfra.conf`, des fichiers secrets protégés et les unités systemd `openinfra-runtime-secrets`, `openinfra-migrate`, `openinfra`, `openinfra-web` et `openinfra-team-sync`. Docker n’est pas une dépendance de production.

La migration 0058 segmente l’état documentaire Oracle par collection métier avec version optimiste indépendante et reprise idempotente depuis le document global historique.
