# Gouvernance de la documentation GA

OpenInfra 0.32.2 traite la documentation comme un artefact de release vérifiable. Le corpus `docs/ga/` est séparé des spécifications contractuelles et des runbooks historiques afin de fournir un parcours exploitable par rôle sans dupliquer le CDC.

## Invariants

- chaque guide déclare la version cible ;
- le manifeste `documentation-manifest.json` fixe les documents et sections obligatoires ;
- les commandes CLI citées doivent exister dans le parser installé ;
- les opérations HTTP citées doivent exister dans le contrat OpenAPI ;
- les liens relatifs restent confinés au dépôt et doivent se résoudre ;
- les blocs de code sont équilibrés et utilisent un langage de fence autorisé ;
- les marqueurs de contenu inachevé rendent la validation non conforme ;
- le wheel embarque le corpus GA afin qu’une installation hors source conserve les procédures ;
- le rapport de validation porte une empreinte SHA-256 du contenu contrôlé.

## Séparation des responsabilités

- `docs/ga/` : procédures et parcours de production par rôle ;
- `docs/runbooks/` : détails techniques spécialisés ;
- `docs/architecture/` : décisions et invariants ;
- `docs/api/openapi.yaml` : contrat HTTP public ;
- `docs/specifications/` : exigences, architecture cible et roadmap ;
- `VALIDATION-REPORT.md` : preuves réellement exécutées pour la livraison.

## Gate de release

Le validateur est exécuté dans la CI générale, dans un workflow dédié et dans le quality gate local. Une dérive de version, de commande, de route ou de lien bloque la promotion. Le rapport JSON est conservé comme preuve de release pendant 90 jours dans GitHub Actions.

## Compatibilité

L’ajout du corpus GA est purement documentaire et de packaging. Il ne modifie ni le schéma PostgreSQL, ni les routes, ni les permissions, ni la CLI, ni la charte graphique.
