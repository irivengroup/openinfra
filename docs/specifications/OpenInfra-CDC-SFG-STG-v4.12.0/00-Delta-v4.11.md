# Delta CDC v4.11.0 — Canonicalisation RSOT définitive

Ce delta remplace la période de compatibilité temporaire des alias ITRM, RI et SOT par leur retrait définitif, conformément à la décision produit. Les capacités métier RSOT, les permissions `rsot.*`, les routes `/api/v1/rsot/*` et la commande `openinfra rsot` sont conservées.

## Décisions contractuelles

- `openinfra itrm`, `openinfra ri` et `openinfra sot` sont supprimés et rejetés par la CLI.
- `/api/v1/itrm/*`, `/api/v1/ri/*` et `/api/v1/sot/*` retournent HTTP 404.
- les rôles `itrm:*`, `ri:*`, `sot:*` et les capacités `core_ri`, `core_sot`, `core_*resources_inventory` sont supprimés ;
- les modules Python de compatibilité ITRM/RI sont retirés du source, du wheel et du sdist ;
- les services, commandes et modèles qualité utilisent exclusivement le préfixe `Rsot` ;
- les migrations historiques restent immuables ; seules les surfaces actives sont concernées ;
- un guide de migration fournit les remplacements exacts.

## Compatibilité assumée

La suppression des alias est une rupture explicitement demandée. Les intégrations doivent migrer vers `rsot` avant déploiement de 0.34.6. Aucune fonctionnalité métier n’est supprimée.
