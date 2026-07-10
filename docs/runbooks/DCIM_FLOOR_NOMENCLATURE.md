# Nomenclature des étages DCIM

## Principe

Le bâtiment est la racine de définition des étages. Un opérateur renseigne le type de bâtiment ainsi que les niveaux initial et final ; OpenInfra crée les étages correspondants. Le CRUD manuel des étages reste désactivé afin d'empêcher les incohérences entre le bâtiment et ses dépendances.

Le code d'un étage est local au bâtiment. Le site et le bâtiment sont déjà portés par la hiérarchie et ne sont donc pas répétés dans ce code.

| Niveau physique | Code canonique | Affichage anglais | Affichage français |
|---:|---|---|---|
| -2 | `L-02` | Basement 2 | Sous-sol 2 |
| -1 | `L-01` | Basement 1 | Sous-sol 1 |
| 0 | `L00` | Ground floor | Rez-de-chaussée |
| 1 | `L01` | Level 1 | Étage 1 |
| 12 | `L12` | Level 12 | Étage 12 |
| 100 | `L100` | Level 100 | Étage 100 |

Les bornes supportées sont `-20` à `150`. `L-00` est invalide ; le niveau zéro est toujours `L00`.

## Compatibilité ascendante

Les nouvelles écritures utilisent exclusivement le code canonique. Les références historiques suivantes restent acceptées comme alias de lecture dans le périmètre du bâtiment :

- `<code-site>_<code-bâtiment>_ETG<n>` ;
- `F<n>` ;
- `ETG<n>`.

La migration PostgreSQL `0040_dcim_floor_nomenclature.sql` et la migration automatique du stockage JSON mettent à jour, dans une transaction logique unique :

- les étages ;
- les salles ;
- les zones de salle ;
- les racks ;
- la localisation des équipements.

Les libellés personnalisés sont préservés. Seuls les anciens libellés générés automatiquement sont remplacés par le libellé canonique, puis localisés côté interface web. Les événements d'audit historiques ne sont pas réécrits.

## Procédure de déploiement

1. Sauvegarder PostgreSQL ou le fichier JSON avant la mise à niveau.
2. Appliquer les migrations avec la commande standard OpenInfra.
3. Vérifier que la migration `0040` est marquée comme appliquée.
4. Contrôler un bâtiment contenant des sous-sols, un rez-de-chaussée et plusieurs étages.
5. Vérifier les salles, zones, racks et équipements rattachés.
6. Tester au moins un ancien alias en lecture.

La migration refuse de s'exécuter si deux étages d'un même bâtiment aboutissent au même niveau canonique.
