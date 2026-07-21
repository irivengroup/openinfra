---
projet: OpenInfra
type_document: SFG/STG-CCTP-CdCF
version: 3.0.0
date: 2026-07-02
statut: Validé
classification: Interne / Consultation intégrateurs
---

# API et intégrations

## Principes API

- Toutes les APIs sont versionnées.
- Les listes volumineuses imposent cursor pagination.
- La limite maximale est stricte et configurée par endpoint.
- Les tris autorisés sont limités aux colonnes indexées.
- Les filtres obligatoires sont imposés sur les endpoints massifs.
- Les exports volumineux sont asynchrones.
- Les mutations critiques exigent une `Idempotency-Key`.
- Les erreurs sont normalisées.
- Les webhooks sont signés.
- GraphQL impose profondeur et complexité maximales.

## Livrables

- `OpenAPI/openapi.yaml`
- `GraphQL/schema.graphql`
- SDK Python et Go dans les phases de développement.
- Collection de tests contractuels API.


## Extension API v4 — domaines fonctionnels avancés

Les ressources suivantes deviennent obligatoires dans l’API REST et visibles dans le contrat OpenAPI lorsque le module est activé :

| Domaine | Ressources minimales |
|---|---|
| Gouvernance | `/data-domains`, `/authoritative-sources`, `/certification-campaigns` |
| Qualité | `/quality-rules`, `/quality-findings`, `/reconciliation-jobs` |
| Flux | `/flow-rules`, `/flow-observations`, `/flow-impact-reports` |
| Certificats | `/certificates`, `/certificate-endpoints`, `/secret-references` |
| Conformité réseau | `/golden-configs`, `/config-snapshots`, `/config-drifts` |
| FinOps | `/cost-records`, `/budgets`, `/showback-reports` |
| Field Operations | `/field-operation-sheets`, `/qr-codes`, `/field-evidence` |
| Simulation | `/simulation-scenarios`, `/impact-reports`, `/migration-waves` |
| GreenOps | `/energy-measurements`, `/carbon-estimates`, `/sustainability-reports` |
| SBOM | `/sbom-documents`, `/vulnerabilities`, `/exposure-contexts` |
| Kubernetes | `/kubernetes-clusters`, `/kubernetes-workloads`, `/gitops-states` |
| Policy Engine | `/policy-rules`, `/policy-evaluations`, `/policy-findings` |

Toutes ces APIs appliquent pagination cursor-based, filtres sélectifs, tri indexé, rate limiting, audit, RBAC/ABAC et exports asynchrones pour volumes importants.


## Extension v4.6 — LDAP/IPA, RBAC groupes et installation système

L'API backend doit exposer, pour Pro et Entreprise, des endpoints d'administration sécurisés permettant :

- tester la connectivité LDAP/IPA ;
- valider les filtres utilisateur et groupe ;
- simuler un mapping groupe vers rôle ;
- consulter les permissions effectives ;
- auditer les connexions ;
- consulter l'état du compte système et du stockage LVM via endpoints d'administration réservés.

Ces endpoints sont interdits à l'édition Lite sauf consultation locale strictement nécessaire.

## v0.29.59 — rollback conflict-aware des imports massifs

OpenInfra ajoute `REQ-00802` pour couvrir le rollback opérable des imports massifs appliqués : dry-run par défaut, restauration versionnée RSOT, mise en retrait sans suppression physique, détection de conflits et publication CLI/API/OpenAPI/discovery/portail web.

## v0.29.60 — guides migration données

`GET /api/v1/imports/migration-guide` retourne un guide structuré par source avec template, étapes, contrôles requis, rollback et critères de succès. L’endpoint ne modifie pas RSOT.

## v0.29.61 — discovery locale Lite/Pro

Ajout `POST /api/v1/discovery/local-plan` pour générer un plan dry-run de discovery locale Lite/Pro sans agent, sans scan réseau exécuté et sans mutation RSOT.
