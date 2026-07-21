# Recommandations de placement DCIM

## Objectif

La commande et l’API de recommandation de placement évaluent les racks actifs d’une salle afin de proposer des emplacements compatibles avec les contraintes physiques, électriques et thermiques déclarées. L’opération est en lecture seule sur la capacité : elle ne réserve ni unité de rack, ni circuit, ni puissance. Elle écrit uniquement un événement d’audit `dcim.placement.recommended`.

## Contrat fonctionnel

Un candidat est retenu uniquement lorsque toutes les conditions suivantes sont satisfaites :

- un bloc contigu d’unités U est libre sur une face utilisable ;
- le rack est actif et appartient à la salle et, le cas échéant, à la zone demandée ;
- la puissance résiduelle du rack, lorsqu’une limite est définie, couvre la demande ;
- un circuit unique ou deux circuits A/B indépendants disposent chacun de la puissance demandée ;
- le rack est affecté à une zone de refroidissement existante ;
- la capacité thermique résiduelle de cette zone couvre la charge déclarée.

Les équipements et panneaux de brassage existants sont tous comptabilisés par face. Les racks dépourvus de métrologie électrique ou thermique suffisante sont refusés de façon explicite, sans hypothèse optimiste.

## Classement déterministe

Les candidats sont classés selon l’ordre stable suivant :

1. plus faible gaspillage d’unités U dans le bloc libre ;
2. plus grande marge minimale sur les circuits sélectionnés ;
3. plus grande marge thermique ;
4. plus grande marge de puissance du rack ;
5. code du rack, face et unité de départ.

Le nombre de résultats est borné entre 1 et 100. Plusieurs faces compatibles d’un même rack peuvent être proposées, tandis que `compatible_rack_count` reste un nombre de racks uniques.

## Interface CLI

```bash
openinfra dcim recommend-placement \
  --backend postgresql \
  --tenant acme \
  --site PAR1 \
  --building BAT-A \
  --room SALLE-01 \
  --u-height 4 \
  --required-power-watts 1200 \
  --required-cooling-watts 1000 \
  --required-power-feeds 2 \
  --preferred-face front \
  --zone COLD-A \
  --limit 10
```

Pour JSON, ajouter `--data /chemin/etat.json`. Pour Oracle, l’édition Enterprise et une licence valide restent obligatoires.

## Interface HTTP

```bash
curl -fsS -G 'https://openinfra.example/api/v1/dcim/placement-recommendations' \
  -H 'Authorization: Bearer <token>' \
  --data-urlencode 'tenant_id=acme' \
  --data-urlencode 'site=PAR1' \
  --data-urlencode 'building=BAT-A' \
  --data-urlencode 'room=SALLE-01' \
  --data-urlencode 'u_height=4' \
  --data-urlencode 'required_power_watts=1200' \
  --data-urlencode 'required_cooling_watts=1000' \
  --data-urlencode 'required_power_feeds=2' \
  --data-urlencode 'preferred_face=front' \
  --data-urlencode 'zone=COLD-A' \
  --data-urlencode 'limit=10'
```

L’API exige la permission `dcim:locate`, déjà utilisée pour les opérations de localisation DCIM. Les erreurs d’authentification retournent HTTP 401 et les entrées invalides ou hiérarchies absentes HTTP 400.

## Motifs de rejet

Le champ `rejected_by_reason` peut contenir :

- `rack_not_active` ;
- `zone_mismatch` ;
- `insufficient_contiguous_u` ;
- `insufficient_rack_power` ;
- `insufficient_power_circuit` ;
- `insufficient_redundant_power` ;
- `missing_cooling_zone_assignment` ;
- `missing_cooling_capacity` ;
- `insufficient_cooling_capacity`.

Ces compteurs facilitent la remédiation opérationnelle sans exposer de secrets ni de données d’un autre tenant.

## Exploitation

1. Maintenir les emplacements, panneaux de brassage, circuits, réservations et zones de refroidissement à jour.
2. Exécuter une recommandation avant toute demande de changement.
3. Faire valider le candidat par l’équipe datacenter.
4. Réserver explicitement la puissance et enregistrer le placement via les opérations DCIM existantes.
5. Rejouer le rapport de capacité après installation.

La recommandation n’est jamais une réservation et ne protège donc pas contre deux opérateurs choisissant simultanément le même emplacement. La réservation métier demeure une étape distincte et transactionnelle.

## Complexité et limites

L’évaluation parcourt les racks d’une seule salle, leurs équipements, panneaux, circuits et réservations. Le paramètre `limit` borne la sérialisation des réponses, tandis que le filtrage hiérarchique et par tenant limite le périmètre lu. Pour les salles très volumineuses, conserver les index de persistance livrés et surveiller la latence HTTP au moyen de l’observabilité OpenInfra.

## Validation

```bash
pytest -q tests/integration/test_dcim_energy_cooling_services.py
python scripts/validate_openapi.py docs/api/openapi.yaml
python scripts/validate_openapi.py docs/specifications/OpenInfra-CDC-SFG-STG-v4.12.0/09-API/OpenAPI/openapi.yaml
npm test --prefix web
npm run lint --prefix web
```
