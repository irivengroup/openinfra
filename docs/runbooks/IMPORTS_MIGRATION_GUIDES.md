# Guides opérables de migration données

OpenInfra v0.29.60 expose des guides structurés de migration pour les sources historiques **Device42**, **NetBox**, **Nautobot**, **GLPI** et **CSV générique**.

Ces guides ne développent pas de connecteur source supplémentaire et ne mutent jamais RSOT. Ils fournissent un cadre opérable avant migration : template de mapping, étapes d’extraction/profilage/remédiation/chargement/rollback, contrôles requis, contrôles rollback et critères de succès.

## Surfaces exposées

- CLI : `openinfra import migration-guide --source <device42|netbox|nautobot|glpi|csv>`
- API : `GET /api/v1/imports/migration-guide?source=<source>`
- Discovery : `imports.migration_guide`
- OpenAPI : `/api/v1/imports/migration-guide`
- Portail web : `Imports / Exports > Guide migration données`

## Garde-fous

- `native_ticketing_enabled=false`.
- `rsot_authoritative=true`.
- Aucune écriture RSOT n’est réalisée par la lecture du guide.
- Le chargement réel reste porté par `openinfra import bulk-dataset`.
- Le rollback réel reste porté par `openinfra import bulk-rollback`, en dry-run par défaut.
- Les exports source doivent être archivés hors OpenInfra avec checksum afin de garantir la reproductibilité.

## Flux recommandé

1. Lire le template avec `migration-template`.
2. Lire le guide avec `migration-guide`.
3. Exécuter `migration-plan` sur un export figé.
4. Corriger les colonnes requises manquantes et les écarts de mapping.
5. Charger via `bulk-dataset --apply` uniquement après validation opérateur.
6. Préparer le rollback via `bulk-rollback` sans `--apply`.
7. Appliquer le rollback uniquement en cas de validation des actions et absence de conflit.

## Exemple

```bash
openinfra import migration-guide \
  --source netbox

openinfra import migration-plan \
  --tenant default \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --source netbox \
  --file /var/lib/openinfra/migrations/netbox-devices.csv \
  --format csv
```

## Critères d’acceptation

- Le guide retourne un template compatible avec la source sélectionnée.
- Les étapes sont ordonnées et auditables par l’opérateur.
- Les contrôles requis et rollback sont explicites.
- Le plan de migration est validé avant toute mutation.
- RSOT reste la source canonique après migration.
