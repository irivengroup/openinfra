# Fonctionnel — Policy Engine et conformité continue

Ce document décline le volume V24 dans la vue fonctionnelle du dossier OpenInfra SFG/STG v4.

## Capacités utilisateur

| Fonctionnalité |
|---|
| moteur de règles déclaratif versionné |
| politiques par tenant, site, environnement, criticité, domaine et objet |
| évaluation continue et planifiée |
| exceptions avec justification, expiration et propriétaire |
| preuves d’audit attachées aux constats |
| score conformité par domaine, application, tenant et site |
| webhooks et intégrations SIEM/GRC externes |
| mode simulation avant activation d’une politique |

## Parcours métier principal

1. L’utilisateur authentifié ouvre le périmètre `POLICY`.
2. Le système applique tenant, RBAC, ABAC et filtres de confidentialité.
3. L’utilisateur consulte ou déclenche une opération contrôlée.
4. L’opération produit audit, métriques, événements et éventuels résultats asynchrones.
5. Les résultats sont consultables par API, UI, export asynchrone et matrice de traçabilité.

## Critères d’acceptation fonctionnels

| Critère |
|---|
| une politique possède version, portée, propriétaire, sévérité et critère d’évaluation |
| une exception ne peut pas être permanente sans justification renforcée |
| les résultats d’évaluation sont auditables et exportables |
| le mode simulation ne modifie aucun statut de conformité effectif |

## Interfaces minimales

- Vue liste avec filtres sélectifs et pagination.
- Fiche détail avec historique et audit.
- Vue qualité/conformité lorsque applicable.
- Action de job asynchrone lorsque le traitement peut être long.
- Exports filtrés et exports massifs asynchrones.
- Webhooks configurables.
