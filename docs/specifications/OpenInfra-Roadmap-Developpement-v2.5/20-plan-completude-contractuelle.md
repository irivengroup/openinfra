# Plan P25 — Complétude contractuelle et hygiène du dépôt

## Registre

Le registre `docs/release/contract-proof-registry-v4.12.csv` contient une ligne pour chacun des 667 tests du CDC 4.12.0. Les identifiants supplémentaires ou dupliqués sont bloquants.

## Niveaux de preuve

- `automated` : au moins un sélecteur pytest réel et résolu ;
- `partial` : preuve documentaire, statique ou ciblée utile, mais insuffisante pour revendiquer une validation fonctionnelle complète ;
- `external` : qualification dépendant d’une infrastructure ou d’un tiers réel, conservée en NO-GO production tant qu’elle n’est pas exécutée.

## Audit contextuel

Le scanner parcourt les sources actives, les scripts, les installateurs, le frontend et les référentiels actifs. Les seuls fichiers ignorés sont les définitions de règles exactes, dont les chemins sont eux-mêmes contrôlés. Aucun répertoire produit n’est exclu globalement.

## Sortie

GATE-14 produit un rapport JSON atomique et exige six contrôles verts. La couverture globale reste supérieure ou égale à 98 %, le wheel et le sdist sont vérifiés, puis le smoke est exécuté depuis une installation isolée.
