# Volume V28 — Authentification LDAP/IPA, RBAC groupes, compte système et FS LVM dédié

## 1. Objectif

Ce volume définit les exigences de sécurité et d'installation liées à l'identité, aux droits applicatifs, au compte système OpenInfra et au stockage local dédié.

La conception distingue trois catégories d'identité :

1. les utilisateurs humains, authentifiés localement ou via LDAP/IPA selon l'édition ;
2. les groupes d'enterprise, synchronisés ou résolus depuis LDAP/IPA ;
3. le compte système Linux `openinfra`, créé par root et utilisé par les services applicatifs.

## 2. Authentification par édition

| Édition | Auth locale | LDAP/LDAPS | IPA/FreeIPA | RBAC groupes | Remarques |
|---|---:|---:|---:|---:|---|
| Lite | oui | non | non | local uniquement | Mode autonome limité |
| Pro | oui | oui | oui | oui | Connexion à annuaire enterprise |
| Entreprise | oui | oui | oui | oui | Multi-tenant, groupes, rôles et politiques avancées |

L'authentification LDAP/IPA ne doit jamais devenir un prérequis pour l'installation Lite.

## 3. LDAP/IPA

Les éditions Pro et Entreprise doivent prendre en charge :

- LDAP simple bind sur TLS lorsque nécessaire ;
- LDAPS ;
- StartTLS si explicitement configuré ;
- FreeIPA/IPA ;
- recherche utilisateur par attribut configurable ;
- recherche groupe par attribut configurable ;
- appartenance directe ;
- appartenance indirecte et groupes imbriqués si supportés par l'annuaire ;
- cache d'identité borné ;
- invalidation de cache ;
- test de connectivité intégré ;
- test de mapping groupes/rôles ;
- audit des authentifications ;
- audit des refus ;
- audit des changements de mapping.

## 4. RBAC et groupes

Le RBAC doit permettre de mapper les groupes LDAP/IPA vers les rôles OpenInfra :

- `OpenInfra-SuperAdmin` ;
- `OpenInfra-Admin` ;
- `OpenInfra-Operator` ;
- `OpenInfra-ReadOnly` ;
- rôles personnalisés ;
- rôles par tenant ;
- rôles par site ;
- rôles par domaine fonctionnel.

Un utilisateur peut obtenir plusieurs rôles par appartenance à plusieurs groupes. Les conflits de permissions doivent être résolus selon une politique explicite : la permission la plus restrictive prime lorsqu'une interdiction explicite existe.

## 5. Compte système `openinfra`

Toutes les éditions doivent créer un compte système local :

| Attribut | Valeur par défaut |
|---|---|
| Utilisateur | `openinfra` |
| Groupe primaire | `openinfra` |
| Home | `/opt/openinfra/` |
| Shell | `/usr/sbin/nologin` ou équivalent |
| Création | par root pendant l'installation |
| Usage | exécution des services et commandes OpenInfra |

Le compte `openinfra` doit disposer des droits suffisants pour exécuter toutes les commandes OpenInfra prévues par l'édition installée, sans disposer d'un accès root global.

## 6. Privilèges contrôlés

Les droits élevés éventuels doivent être accordés par :

- sudoers root-owned avec mode `0440` ;
- commandes strictement qualifiées par chemin absolu ;
- wrappers OpenInfra signés ou vérifiés ;
- interdiction de shell arbitraire ;
- interdiction de wildcard dangereux ;
- journalisation des élévations ;
- validation CI des règles sudoers ;
- refus si le fichier sudoers est modifiable par le compte `openinfra`.

## 7. Filesystem LVM dédié

L'installateur doit créer un filesystem dédié avant le déploiement des composants applicatifs.

Valeurs par défaut obligatoires :

```yaml id="ae6lyu"
storage:
  vgname: rootvg
  lvname: openinfra_lv
  lv_size: 2GB
  mountpoint: /opt/openinfra/
  filesystem: xfs
```

L'installateur doit permettre de surcharger ces valeurs dans un fichier de réponses validé.

## 8. Idempotence stockage

L'installation doit être idempotente :

- si le VG existe, il est réutilisé après contrôle ;
- si le LV existe, sa taille et son montage sont vérifiés ;
- si le mountpoint existe, son propriétaire, ses permissions et son origine de montage sont vérifiés ;
- aucune suppression ou recréation destructive n'est autorisée sans option explicite ;
- toute non-conformité bloquante produit un rapport d'erreur exploitable.

## 9. Permissions filesystem

Les permissions minimales sont :

- propriétaire : `openinfra:openinfra` ;
- mode recommandé : `0750` sur `/opt/openinfra/` ;
- secrets : `0640` ou plus restrictif ;
- répertoires runtime sensibles : `0750` ;
- logs : écriture contrôlée et rotation ;
- sauvegarde avant modification destructive ;
- SELinux/AppArmor pris en compte si actif.

## 10. Critères d'acceptation

L'exigence est acceptée uniquement si :

- Pro et Entreprise authentifient des utilisateurs via LDAP/IPA ;
- les groupes LDAP/IPA se mappent vers des rôles OpenInfra ;
- Lite reste installable sans LDAP/IPA ;
- le compte système `openinfra` est créé par root ;
- les services OpenInfra s'exécutent sous `openinfra` lorsque applicable ;
- le filesystem LVM dédié est créé et monté sur `/opt/openinfra/` ;
- les valeurs par défaut `rootvg`, `openinfra_lv`, `2GB` sont appliquées en absence de surcharge ;
- l'installation est rejouable sans destruction ;
- les migrations backend restent appliquées uniquement par le scope backend ;
- les contrôles de sécurité refusent tout sudoers permissif ou modifiable par `openinfra`.
