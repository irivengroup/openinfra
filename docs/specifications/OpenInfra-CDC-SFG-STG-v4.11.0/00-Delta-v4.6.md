# Delta v4.6.0 — Authentification LDAP/IPA, RBAC groupes, compte système et filesystem LVM dédié

## Décisions intégrées

La version 4.6.0 ajoute des exigences obligatoires relatives à l'authentification enterprise et au socle système d'installation.

## Authentification Pro et Entreprise

Les éditions OpenInfra Pro et OpenInfra Entreprise doivent prendre en charge l'authentification LDAP et FreeIPA/IPA. Cette capacité inclut :

- connexion LDAP/LDAPS ;
- connexion FreeIPA/IPA ;
- mapping groupes LDAP/IPA vers rôles OpenInfra ;
- RBAC applicatif basé sur groupes ;
- synchronisation contrôlée des groupes ;
- résolution d'appartenance directe et indirecte ;
- cache d'identité borné et invalidable ;
- audit des connexions, refus et changements de mapping ;
- mode break-glass local strictement contrôlé.

L'édition Lite conserve une authentification locale simplifiée et ne doit pas dépendre de LDAP/IPA.

## Compte système OpenInfra

Toutes les éditions doivent créer à l'installation, par root, un compte système canonique :

- utilisateur : `openinfra` ;
- groupe primaire : `openinfra` ;
- compte non interactif ;
- shell : `/usr/sbin/nologin` ou équivalent distribution ;
- propriétaire de l'arborescence applicative ;
- autorisé à exécuter toutes les commandes OpenInfra nécessaires au fonctionnement, à l'administration applicative et aux opérations contrôlées ;
- sans privilège root global ;
- droits système accordés uniquement via sudoers restreint, wrappers contrôlés ou capacités Linux nécessaires.

## Filesystem LVM dédié

Toutes les éditions doivent créer et monter un filesystem dédié pour OpenInfra lors de l'installation.

Valeurs par défaut :

| Paramètre | Valeur par défaut |
|---|---|
| Volume group | `rootvg` |
| Logical volume | `openinfra_lv` |
| Mountpoint | `/opt/openinfra/` |
| Taille LV | `2GB` |
| Type FS recommandé | `xfs`, surchargeable en `ext4` si la distribution ou la politique enterprise l'impose |

L'installateur doit être idempotent : il détecte un VG, LV, FS ou mountpoint déjà existant, vérifie leur conformité et refuse toute opération destructive sans option explicite et auditée.

## Impacts

- Nouveau volume documentaire : `V28-Authentification-LDAP-IPA-RBAC-Compte-systeme-FS-LVM.md`.
- Nouveaux documents techniques : authentification LDAP/IPA, compte système, filesystem LVM.
- Nouvelles matrices : authentification, RBAC groupes, compte système, LVM, sudoers contrôlés.
- Nouvelles exigences `REQ-00583` à `REQ-00642`.
- Nouveaux tests `TST-AUTH-001` à `TST-AUTH-018`, `TST-SYS-001` à `TST-SYS-014`, `TST-LVM-001` à `TST-LVM-014`.
