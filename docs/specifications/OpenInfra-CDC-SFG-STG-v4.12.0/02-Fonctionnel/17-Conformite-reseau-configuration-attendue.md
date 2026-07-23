# Fonctionnel — Conformité réseau et configuration attendue

Ce document décline le volume V17 dans la vue fonctionnelle du dossier OpenInfra SFG/STG v4.

## Capacités utilisateur

| Fonctionnalité |
|---|
| définition de golden configurations par constructeur, modèle, rôle, site et environnement |
| contrôle conformité AAA, NTP, SNMP, syslog, TACACS/RADIUS, BGP, OSPF, VRF, VLAN et ACL |
| parsing sécurisé des configurations collectées |
| détection de drift par règle, section et criticité |
| historique des configurations découvertes avec chiffrement si nécessaire |
| rapports de conformité par équipement, site et domaine réseau |
| suggestions de remédiation non exécutées automatiquement |
| intégration avec matrice de flux et policy engine |

## Parcours métier principal

1. L’utilisateur authentifié ouvre le périmètre `NCFG`.
2. Le système applique tenant, RBAC, ABAC et filtres de confidentialité.
3. L’utilisateur consulte ou déclenche une opération contrôlée.
4. L’opération produit audit, métriques, événements et éventuels résultats asynchrones.
5. Les résultats sont consultables par API, UI, export asynchrone et matrice de traçabilité.

## Critères d’acceptation fonctionnels

| Critère |
|---|
| une dérive identifie règle, équipement, section, preuve et criticité |
| les configurations sensibles sont protégées contre exposition de secrets |
| les remédiations proposées sont séparées de toute exécution automatique |
| les règles de conformité sont versionnées et auditables |

## Interfaces minimales

- Vue liste avec filtres sélectifs et pagination.
- Fiche détail avec historique et audit.
- Vue qualité/conformité lorsque applicable.
- Action de job asynchrone lorsque le traitement peut être long.
- Exports filtrés et exports massifs asynchrones.
- Webhooks configurables.
