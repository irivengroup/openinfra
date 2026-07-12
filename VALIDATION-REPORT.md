# OpenInfra v0.30.6 — rapport de validation

Date : 2026-07-11

## Périmètre

Cette livraison corrige l'état actif des composants dans le header des portails React et statique. La surface blanche très visible introduite par la couche de design finale est supprimée au profit d'un état translucide, cohérent avec le header bleu nuit et la charte OpenInfra.

## Correctif visuel

- fond actif bleu/cyan translucide : 10,5 % vers 4,5 % d'opacité ;
- suppression de toute carte ou bordure blanche opaque en mode normal ;
- repère inférieur cyan à 42 % d'opacité ;
- libellé actif bleu très clair à 94 % d'opacité globale ;
- icône active cyan clair à 82 % d'opacité ;
- ombre ramenée à une profondeur légère ;
- hover/focus sans surface blanche ;
- modes `prefers-contrast` et `forced-colors` conservés pour l'accessibilité ;
- parité CSS exacte entre le portail React et le runtime statique packagé.

## Contrastes

Le contraste est calculé sur l'extrémité la plus claire du dégradé du header (`#0a5ddb`) :

- libellé actif : supérieur ou égal à 4,5:1 ;
- icône active : supérieure ou égale à 3:1 ;
- le fond translucide n'est pas le seul indicateur : le repère inférieur et `aria-current="page"` complètent l'état actif.

## Tests et qualité

- 991 tests Python collectés et réussis en 163 secondes ;
- couverture globale : 98,01 % ;
- seuil contractuel de 98 % : PASS ;
- 51 tests frontend réussis ;
- Ruff format : 282 fichiers conformes ;
- Ruff lint : PASS ;
- mypy strict : 93 modules, PASS ;
- `compileall` : PASS ;
- Bandit : PASS ;
- security gate : PASS ;
- quality gate : PASS ;
- ESLint JSX : PASS ;
- WCAG 2.2 AA : PASS ;
- build Vite : PASS ;
- audit npm : 0 vulnérabilité ;
- deux contrats OpenAPI : PASS ;
- six profils installateurs : PASS ;
- runtime natif : PASS.

## Tests de non-régression ajoutés

- interdiction d'un fond blanc ou quasi blanc dans les règles actives du header en mode normal ;
- obligation d'utiliser les jetons sémantiques translucides du header ;
- contrôle de l'opacité du libellé et de l'icône ;
- contrôle du contraste WCAG du libellé et du contraste non textuel de l'icône ;
- contrôle de parité des deux feuilles de style.

## Limites d'environnement

- Docker/Podman et PostgreSQL réel ne sont pas disponibles dans l'environnement local ;
- `pip-audit` réseau n'a pas été rejoué, les planchers sécurisés de la version 0.30.5 restent inchangés et le gate demeure bloquant en CI ;
- aucune capture navigateur automatisée n'est revendiquée.

Le CDC 4.9.0 et la roadmap 2.1.0 ne sont pas modifiés : il s'agit d'un correctif visuel sans évolution métier ou architecturale.
