# Fonctionnel — Certificats, PKI et secrets référencés

Ce document décline le volume V16 dans la vue fonctionnelle du dossier OpenInfra SFG/STG v4.

## Capacités utilisateur

| Fonctionnalité |
|---|
| inventaire TLS depuis réseau, load balancers, ingress Kubernetes, cloud, fichiers et APIs externes |
| corrélation certificat ↔ endpoint ↔ application ↔ propriétaire ↔ service métier |
| suivi expiration, algorithme, taille de clé, SAN, autorité émettrice et chaîne de confiance |
| détection certificats expirés, faibles, auto-signés, doublons ou non conformes |
| référencement de secrets Vault/SOPS/Kubernetes Secrets sans exposition du secret brut |
| notifications webhooks et rapports avant expiration |
| historique des certificats et comparaison entre renouvellements |
| score de risque certificat selon exposition et criticité métier |

## Parcours métier principal

1. L’utilisateur authentifié ouvre le périmètre `CERT`.
2. Le système applique tenant, RBAC, ABAC et filtres de confidentialité.
3. L’utilisateur consulte ou déclenche une opération contrôlée.
4. L’opération produit audit, métriques, événements et éventuels résultats asynchrones.
5. Les résultats sont consultables par API, UI, export asynchrone et matrice de traçabilité.

## Critères d’acceptation fonctionnels

| Critère |
|---|
| aucun secret brut n’est renvoyé par API ou export |
| un certificat critique expirant sous seuil génère un événement et une alerte |
| la chaîne de certification est historisée et vérifiable |
| les scans certificats sont asynchrones, bornés et auditables |

## Interfaces minimales

- Vue liste avec filtres sélectifs et pagination.
- Fiche détail avec historique et audit.
- Vue qualité/conformité lorsque applicable.
- Action de job asynchrone lorsque le traitement peut être long.
- Exports filtrés et exports massifs asynchrones.
- Webhooks configurables.
