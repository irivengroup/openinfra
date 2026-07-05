# Fonctionnel — SBOM, vulnérabilités et exposition contextualisée

Ce document décline le volume V22 dans la vue fonctionnelle du dossier OpenInfra SFG/STG v4.

## Capacités utilisateur

| Fonctionnalité |
|---|
| import CycloneDX et SPDX |
| versionnement SBOM par application, image, release et environnement |
| corrélation composant ↔ version ↔ licence ↔ CVE ↔ application ↔ actif |
| exposition contextualisée selon Internet, flux, criticité métier et dépendances |
| priorisation risque selon exploitabilité, criticité, exposition et compensating controls |
| comparaison SBOM entre releases |
| intégration CI/CD par API et webhooks |
| exports conformité et preuves d’audit |

## Parcours métier principal

1. L’utilisateur authentifié ouvre le périmètre `SBOM`.
2. Le système applique tenant, RBAC, ABAC et filtres de confidentialité.
3. L’utilisateur consulte ou déclenche une opération contrôlée.
4. L’opération produit audit, métriques, événements et éventuels résultats asynchrones.
5. Les résultats sont consultables par API, UI, export asynchrone et matrice de traçabilité.

## Critères d’acceptation fonctionnels

| Critère |
|---|
| un SBOM importé conserve format, hash, source, application, release et environnement |
| une vulnérabilité est contextualisée sans remplacer le scanner externe |
| la comparaison de releases liste ajouts, suppressions et changements de versions |
| les imports SBOM sont idempotents et versionnés |

## Interfaces minimales

- Vue liste avec filtres sélectifs et pagination.
- Fiche détail avec historique et audit.
- Vue qualité/conformité lorsque applicable.
- Action de job asynchrone lorsque le traitement peut être long.
- Exports filtrés et exports massifs asynchrones.
- Webhooks configurables.
