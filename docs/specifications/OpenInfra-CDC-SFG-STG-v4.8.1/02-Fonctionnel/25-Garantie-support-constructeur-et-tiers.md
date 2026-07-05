# Garantie, support constructeur et support tiers

## Objectif

Garantir que tout équipement physique possède des informations obligatoires de garantie et de support constructeur, tout en permettant à l'entreprise de souscrire un support tiers séparé sans altérer les informations constructeur initiales.

## Exigences fonctionnelles

- La fiche d'un équipement physique doit afficher la garantie constructeur.
- La fiche d'un équipement physique doit afficher le support constructeur initial.
- La fiche peut afficher un ou plusieurs contrats de support tiers.
- Le support tiers est complémentaire et séparé du support constructeur.
- Le support tiers ne doit jamais écraser le support constructeur.
- Une importation, discovery ou synchronisation ITSM ne doit jamais supprimer ou masquer les données constructeur.
- Les données constructeur peuvent être corrigées uniquement par une action autorisée, auditée et explicitement typée comme correction de donnée constructeur.
- Les dates, niveaux de service, références contrat, constructeur et sources doivent être historisés.

## Modèle logique

Entités obligatoires :

- `physical_asset` ;
- `manufacturer_warranty` ;
- `manufacturer_support` ;
- `third_party_support_contract` ;
- `support_provider` ;
- `support_source_evidence` ;
- `support_conflict`.

## Comportement en cas de divergence

Si une source externe propose de remplacer une donnée constructeur par une donnée tiers, OpenInfra doit :

1. refuser l'écrasement automatique ;
2. créer un conflit ;
3. conserver les deux valeurs ;
4. afficher la source et la date ;
5. exiger une résolution autorisée ;
6. journaliser la décision.

## Critères d'acceptation

- Aucun équipement physique ne peut être certifié complet sans garantie constructeur et support constructeur.
- Un support tiers peut être ajouté sans modifier le support constructeur.
- Les API d'import refusent l'écrasement silencieux.
- L'UI affiche clairement les blocs `Constructeur` et `Tiers`.
- Les connecteurs ITSM respectent la même séparation.

