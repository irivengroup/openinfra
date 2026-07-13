# Certification du packaging de release — EPIC-1803

OpenInfra 0.32.1 introduit un gate de packaging fermé qui valide une release avant publication. Le gate ne se limite pas à la présence d'un wheel : il construit deux fois les distributions dans des environnements temporels identiques, compare les octets, vérifie leur contenu, exécute les six installateurs, prouve le rollback transactionnel, génère un SBOM SPDX 2.3, signe le manifeste et réinstalle le wheel dans un environnement Python vierge.

## Invariants

- `SOURCE_DATE_EPOCH`, `PYTHONHASHSEED=0` et `TZ=UTC` rendent la construction déterministe.
- Le wheel et le sdist issus des deux builds doivent avoir le même nom et le même SHA-256.
- Le manifeste de release référence chaque artefact par taille et SHA-256.
- Le SBOM SPDX est déterministe et recense les dépendances de production Python et frontend.
- La signature est Ed25519, détachée et vérifiée avant certification.
- Une clé éphémère permet les tests locaux mais interdit la certification.
- Les six profils installateur doivent annoncer `transactional_rollback=true` et restaurer réellement un fichier antérieur.
- Le wheel doit être installable avec ses dépendances runtime dans un environnement Python vierge et passer `pip check` puis le smoke installé.

## Frontière de confiance

La clé privée n'est jamais stockée dans le dépôt ni dans les artefacts. La CI reçoit un PEM Ed25519 encodé en base64 via le secret GitHub `OPENINFRA_RELEASE_SIGNING_PRIVATE_KEY_B64`. Seule la clé publique est publiée avec la signature.

La signature atteste le manifeste. Le manifeste atteste le wheel, le sdist et le SBOM. `SHA256SUMS` permet un contrôle indépendant avec les outils système.

## Rollback

Le gate valide le mécanisme de rollback des six installateurs sur un arbre cible isolé. Les migrations PostgreSQL restent forward-only : lorsqu'un retour de schéma est requis, la procédure de rollback impose la restauration d'une sauvegarde/PITR cohérente plutôt qu'une migration descendante implicite.
