# Fonctionnel — Field Operations et mobilité datacenter

Ce document décline le volume V19 dans la vue fonctionnelle du dossier OpenInfra SFG/STG v4.

## Capacités utilisateur

| Fonctionnalité |
|---|
| génération de fiche d’intervention depuis équipement, rack, câble, PDU ou certificat |
| affichage chemin physique complet avec site, bâtiment, salle, ligne, colonne, X/Y/Z, rack, face et U |
| QR code et code-barres pour actif, rack, PDU, câble et emplacement |
| mode mobile avec consultation offline contrôlée |
| checklists de manipulation et validations avant/après |
| photos avant/après et preuves rattachées à l’actif |
| verrou logique d’intervention hors ITSM pour éviter manipulations concurrentes |
| avertissement sur dépendances critiques, flux, alimentation et SPOF avant intervention |

## Parcours métier principal

1. L’utilisateur authentifié ouvre le périmètre `FIELD`.
2. Le système applique tenant, RBAC, ABAC et filtres de confidentialité.
3. L’utilisateur consulte ou déclenche une opération contrôlée.
4. L’opération produit audit, métriques, événements et éventuels résultats asynchrones.
5. Les résultats sont consultables par API, UI, export asynchrone et matrice de traçabilité.

## Critères d’acceptation fonctionnels

| Critère |
|---|
| une fiche terrain ne peut pas être générée si la localisation obligatoire est incomplète |
| le mode offline ne stocke que le périmètre autorisé et expire automatiquement |
| les preuves d’intervention sont immuables après validation |
| le verrou d’intervention ne bloque pas la lecture ni la découverte automatique |

## Interfaces minimales

- Vue liste avec filtres sélectifs et pagination.
- Fiche détail avec historique et audit.
- Vue qualité/conformité lorsque applicable.
- Action de job asynchrone lorsque le traitement peut être long.
- Exports filtrés et exports massifs asynchrones.
- Webhooks configurables.
