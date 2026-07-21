# V32 — Canonicalisation RSOT définitive

## Objectif

Retirer les alias ITRM, RI et SOT de toutes les surfaces actives sans supprimer les fonctions métier du composant RSOT.

## Périmètre

- CLI : seule la commande `openinfra rsot` est enregistrée ;
- API : seules les routes `/api/v1/rsot/*` sont servies et annoncées ;
- RBAC : seuls les rôles `rsot:*` sont acceptés ;
- éditions : seule la capacité `core_rsot` est reconnue ;
- Python : services, commandes et modèles utilisent le préfixe `Rsot` ;
- packaging : aucun module de compatibilité ITRM/RI n’est livré ;
- documentation : un guide de migration fournit les remplacements exacts.

## Acceptation

Le gate GATE-13 valide six contrôles fermés, la suite historique reste verte et la couverture globale demeure supérieure ou égale à 98 %.
