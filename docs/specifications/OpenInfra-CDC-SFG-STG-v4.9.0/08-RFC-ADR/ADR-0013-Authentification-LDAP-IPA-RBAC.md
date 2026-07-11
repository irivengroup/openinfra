# ADR-0013 — Authentification opérateur LDAP/IPA côté frontend et RBAC OpenInfra

## Statut

Accepté.

## Contexte

Les enterprises utilisent fréquemment LDAP, Active Directory ou FreeIPA/IPA pour centraliser les identités et groupes. OpenInfra Pro et Entreprise doivent s'intégrer à ces référentiels sans embarquer d'ITSM, sans déléguer l'autorisation applicative à l'annuaire et sans faire du backend un portail de login opérateur.

## Décision

OpenInfra Pro et Entreprise prennent en charge LDAP/LDAPS et IPA/FreeIPA uniquement dans le scope web/frontend pour l'authentification des opérateurs. Les groupes externes sont mappés vers des groupes et rôles OpenInfra. Le RBAC reste géré par OpenInfra.

Le backend expose une API. Il n'authentifie pas directement chaque opérateur humain par LDAP/IPA. Il valide des jetons applicatifs, applique les politiques RBAC effectives, journalise les décisions de permission et sert les clients autorisés : frontend web et agents.

## Conséquences

- Le frontend devient le point d'authentification opérateur.
- Le backend reste API-only pour les opérateurs : validation de jetons, RBAC, audit et application des permissions.
- LDAP/IPA est interdit côté backend et côté Lite.
- Les groupes externes doivent être audités et mappés explicitement vers des groupes/rôles OpenInfra.
- Les secrets de bind sont gérés uniquement par référence `env:`, `file://`, `vault://`, `sops://` ou `kms://`.
- Lite reste indépendante de LDAP/IPA et strictement locale.
