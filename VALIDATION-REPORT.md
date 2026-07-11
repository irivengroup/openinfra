# OpenInfra v0.30.4 — Rapport de validation

Date : 2026-07-11  
Release : `0.30.4`

## Objet

Correction de la régression visuelle signalée sur le portail Web : plusieurs textes auparavant perçus comme bleu nuit apparaissaient gris foncé. Le correctif couvre le portail React et le runtime statique packagé, sans modifier les fonctions métier, les API, le CDC ou la roadmap.

## Cause racine

Les textes secondaires utilisaient des couleurs calculées par transparence à partir du bleu nuit, par exemple `rgba(0, 27, 65, 0.62)`. Le résultat final dépendait de la surface placée derrière le texte et produisait une teinte grisâtre sur les fonds blancs ou bleu très pâle. Bootstrap pouvait également réintroduire ses couleurs secondaires grises sur certains utilitaires.

## Correctifs validés

- remplacement des mélanges alpha par quatre couleurs opaques et sémantiques :
  - principal : `#001b41` ;
  - secondaire : `#234f7d` ;
  - atténué : `#315d8a` ;
  - subtil : `#3d648d` ;
- alignement des variables Bootstrap de texte secondaire et tertiaire ;
- redéfinition de `text-secondary`, `text-muted` et `text-body-secondary` ;
- placeholders explicitement bleus et opaques ;
- correction de la référence CSS non définie `--openinfra-muted` ;
- parité stricte, octet pour octet, entre le thème React et le thème du runtime packagé ;
- mise à jour des validateurs historiques qui imposaient encore une couleur codée en dur ;
- documentation de la hiérarchie chromatique et de sa politique de contraste.

## Contrastes mesurés

| Niveau | Couleur | Sur blanc | Sur fond de page `#f4f8ff` |
|---|---:|---:|---:|
| Principal | `#001b41` | 17,03:1 | 15,99:1 |
| Secondaire | `#234f7d` | 8,45:1 | 7,93:1 |
| Atténué | `#315d8a` | 6,86:1 | 6,44:1 |
| Subtil | `#3d648d` | 6,17:1 | 5,79:1 |

Tous les niveaux dépassent le seuil WCAG 2.2 AA de 4,5:1 pour le texte normal.

## Résultats

- 985 tests Python réussis ;
- couverture : 35 268 / 35 986 lignes, soit 98,0047796365 % ;
- seuil contractuel de 98 % : PASS ;
- Ruff format et lint : 280 fichiers conformes ;
- mypy strict : 92 modules, PASS ;
- compileall : PASS ;
- Bandit et security gate : PASS ;
- quality gate : PASS ;
- 50 tests frontend Node.js : PASS ;
- ESLint JSX : PASS ;
- WCAG 2.2 AA : PASS ;
- build Vite : PASS ;
- audit npm : 0 vulnérabilité ;
- deux contrats OpenAPI : PASS ;
- six profils d’installation : PASS ;
- validation CDC 4.9.0 / roadmap 2.1.0 : PASS ;
- tests spécifiques de palette, contraste et parité CSS : PASS.

## Contrôle non exécutable localement

`pip-audit` n’a pas pu interroger PyPI en raison d’un échec de résolution DNS de `pypi.org`. Le contrôle reste bloquant dans la CI disposant d’un accès réseau.

## Déploiement

La modification concerne des assets versionnés. Après déploiement, un rechargement forcé du navigateur peut être effectué une seule fois pour éliminer une ressource CSS éventuellement conservée par un proxy ou un cache intermédiaire.
