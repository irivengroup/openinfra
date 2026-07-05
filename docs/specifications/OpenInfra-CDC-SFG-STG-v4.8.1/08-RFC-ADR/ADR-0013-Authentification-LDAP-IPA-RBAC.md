# ADR-0013 — Authentification LDAP/IPA et RBAC par groupes pour Pro/Entreprise

## Statut

Accepté.

## Contexte

Les enterprises utilisent fréquemment LDAP, Active Directory ou FreeIPA/IPA pour centraliser les identités et groupes. OpenInfra Pro et Entreprise doivent s'intégrer à ces référentiels sans embarquer d'ITSM ni déléguer l'autorisation applicative à l'annuaire.

## Décision

OpenInfra Pro et Entreprise prennent en charge LDAP/LDAPS et IPA/FreeIPA. Les groupes externes sont mappés vers des rôles OpenInfra. Le RBAC reste géré par OpenInfra.

## Conséquences

- Le backend devient l'unique point d'intégration annuaire.
- Les groupes externes doivent être audités et mappés explicitement.
- Les secrets de bind sont gérés par le mécanisme de secrets retenu.
- Lite reste indépendante de LDAP/IPA.
