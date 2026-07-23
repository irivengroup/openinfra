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


## Implémentation incrémentale v0.29.43

OpenInfra v0.29.43 introduit le profil de support ITAM `asset_support_profile` pour un équipement physique. Ce profil contient obligatoirement la garantie constructeur et le support constructeur initial, puis accepte des contrats de support tiers séparés.

Règles de gestion :

- la garantie constructeur et le support constructeur sont créés ensemble lors de l’enregistrement initial ;
- toute tentative de modifier ces informations par un nouvel enregistrement divergent est rejetée ;
- un contrat de support tiers ne peut être ajouté que si le profil constructeur existe déjà ;
- un contrat tiers est identifié par fournisseur et référence de contrat ;
- un contrat tiers n’écrase jamais les champs constructeur ;
- chaque opération est auditée.

Interfaces exposées :

- `GET /api/v1/itam/support-profile` ;
- `POST /api/v1/itam/support-profile/manufacturer` ;
- `POST /api/v1/itam/support-profile/third-party` ;
- `openinfra itam register-manufacturer-support` ;
- `openinfra itam add-third-party-support` ;
- `openinfra itam support-profile`.

Persistance :

- backend JSON : collection `asset_support_profiles` ;
- backend PostgreSQL : migration `0027_itam_asset_support_profiles.sql`, table partitionnée par `tenant_id`, index d’échéance garantie, index GIN des contrats tiers et index d’audit dédié.
