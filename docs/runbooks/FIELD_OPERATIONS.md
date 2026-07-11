# Runbook — Field Operations mobile/offline

## Objet

Field Operations guide les interventions physiques sur les ressources DCIM sans réimplémenter un outil ITSM. Le module produit une fiche contrôlée, vérifie la localisation, expose les risques techniques, collecte des preuves avant/après et permet un travail hors ligne limité au périmètre autorisé.

L’interface est rangée sous **DCIM → Opérations terrain**. Les routes HTTP restent sous `/api/v1/field-*` et les commandes sous `openinfra dcim field-*`.

## Modèle de sécurité

Trois permissions distinctes sont appliquées :

- `field.read` : consultation des fiches, preuves et QR ;
- `field.write` : création, verrouillage, exécution, preuve et clôture ;
- `field.sync` : création, lecture et synchronisation des paquets hors ligne.

Les règles tenant, RBAC et ABAC de site sont évaluées avant chaque opération. Les rôles intégrés `field:reader`, `field:operator` et `admin` portent les permissions correspondantes. Aucun paquet hors ligne ne peut élargir le tenant ou le site de la fiche source.

## Cibles prises en charge

- équipement ;
- rack ;
- câble DCIM ;
- équipement électrique/PDU ;
- certificat, à condition d’indiquer une cible physique de localisation.

Une fiche n’est jamais générée si le chemin physique requis est incomplet. Le chemin peut contenir site, bâtiment, étage, salle, ligne, colonne, zone, rack, face, position U et coordonnées X/Y/Z.

## Parcours nominal

1. Générer la fiche depuis une cible DCIM existante.
2. Lire les avertissements de sécurité : lien RSOT, impact Graphe/SPOF, flux déclarés, alimentation A/B.
3. Vérifier le QR ou le code-barres sur site.
4. Acquérir un verrou logique idempotent avec durée de vie bornée.
5. Démarrer l’intervention.
6. Renseigner toutes les étapes obligatoires de checklist.
7. Attacher puis valider au moins une preuve `before` et une preuve `after`.
8. Clôturer l’intervention ; le verrou est libéré dans la même transaction.

La clôture est refusée si le verrou actif n’appartient pas à la fiche, si une étape obligatoire n’est pas acceptée ou si les preuves validées avant/après sont absentes.

## Preuves

Formats autorisés :

- `image/jpeg` ;
- `image/png` ;
- `image/webp` ;
- `application/pdf`.

La taille maximale est de **2 Mio par preuve**. Le contenu base64 est décodé strictement, son type MIME est contrôlé et une empreinte SHA-256 est enregistrée. Après validation, l’objet métier ne permet plus de modifier le contenu, le nom, la légende ou l’empreinte.

Exemple CLI :

```bash
openinfra dcim field-evidence-attach \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN" \
  --sheet-id "$SHEET_ID" \
  --phase before \
  --media-type image/jpeg \
  --file ./avant.jpg \
  --caption "Câblage et voyants avant intervention"
```

## Verrou logique

Le verrou évite deux manipulations concurrentes sur une même cible. Il ne bloque ni les consultations ni les collectes automatiques. Sa clé d’idempotence permet de rejouer sans duplication une demande réseau. Sa durée est comprise entre 60 secondes et 24 heures.

Un verrou expiré n’autorise pas le démarrage ou la clôture. Une libération répétée est idempotente.

## Mode hors ligne

Le paquet contient uniquement :

- la fiche et son état courant ;
- les métadonnées de preuve sans contenu binaire ;
- le tenant et le site autorisés ;
- une version de schéma ;
- une empreinte SHA-256 du JSON canonique.

La durée de vie est comprise entre 5 minutes et 7 jours. Une synchronisation est acceptée uniquement si le paquet est encore valide, non déjà révoqué et si l’empreinte client correspond à l’empreinte canonique. Les clés d’idempotence évitent les doublons.

## Persistance PostgreSQL

La migration `0044_field_operations_mobile_offline.sql` crée :

- `field_operation_sheets` ;
- `field_evidence` ;
- `intervention_locks` ;
- `offline_sync_packages` ;
- `field_event_outbox`.

Les tables sont partitionnées par hash du tenant en 16 partitions. Les index couvrent les listes par site/statut, les cibles, les preuves, les verrous actifs, l’expiration des paquets et l’outbox non publiée. La migration est additive et ne contient aucun `DROP`.

## Audit et événements

Chaque écriture critique produit un audit et, dans la même transaction, un événement outbox : génération, démarrage, checklist, preuve attachée/validée, verrouillage/libération, création/synchronisation hors ligne, clôture ou annulation.

Les événements ne contiennent jamais le contenu binaire des preuves ni le jeton d’authentification.

## Diagnostic

```bash
openinfra dcim field-sheet-list \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN" \
  --site PAR1

openinfra dcim field-offline-list \
  --tenant default \
  --admin-token "$OPENINFRA_TOKEN"
```

Pour un échec :

1. vérifier le tenant, les permissions et la politique ABAC du site ;
2. vérifier que la cible DCIM existe et possède une localisation complète ;
3. contrôler le statut de la fiche et le verrou actif ;
4. contrôler les étapes obligatoires et les preuves validées ;
5. vérifier l’expiration et l’empreinte du paquet hors ligne ;
6. consulter les audits `field.*` et l’outbox `field_event_outbox`.

## Sauvegarde et restauration

Les données JSON suivent la sauvegarde atomique du document OpenInfra. En PostgreSQL, les cinq tables sont incluses dans la sauvegarde globale et le PITR. Une restauration ciblée doit préserver les couples `(tenant_id, id)` ainsi que l’ordre temporel des audits et événements outbox.
