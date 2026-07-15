# Rapport de validation — OpenInfra Python POO v0.33.4

## Objet de la livraison

La version **0.33.4** normalise les critères parents utilisés dans les pages et formulaires de gestion selon l'ordre canonique suivant, uniquement lorsque le niveau est pertinent pour l'objet concerné :

1. Organisation ;
2. Filiale/Subdivision ;
3. Site ;
4. Bâtiment ;
5. Étage ;
6. Salle ;
7. Ligne/Colonne ;
8. Rack.

L'évolution complète la gestion CRUD unifiée de la v0.33.2 sans modifier les contrats API/CLI, les permissions RBAC, les migrations PostgreSQL ou la palette graphique.

## Architecture et intégration

Le code de l'expérience de gestion fait désormais partie de l'arborescence permanente du projet :

```text
web/src/management/
├── context-hierarchy.js
├── operation-schema.js
└── resources.js
```

Le runtime packagé conserve son équivalent :

```text
src/openinfra/interfaces/rendering/static/assets/management/
├── context-hierarchy.js
└── resources.js
```

Les anciens chemins restent disponibles comme façades de compatibilité afin de ne casser aucun import historique.

Le référentiel partagé fournit :

- l'ordre canonique des contextes parents ;
- l'identification des ancêtres stricts d'un niveau ;
- l'ordre stable des champs de formulaire ;
- les options de filtres en cascade ;
- l'invalidation des descendants après changement d'un parent ;
- la suppression des sélections devenues invalides après rechargement des données ;
- le filtrage des valeurs Ligne/Colonne lorsqu'elles sont stockées sous forme de collections.

Les sélecteurs DCIM du runtime respectent désormais la chaîne de dépendance physique. Un niveau courant ne se filtre jamais lui-même : par exemple, le Site sélectionné contraint les Bâtiments mais le sélecteur Site reste libre de proposer les autres sites autorisés. Ligne et Colonne, de même rang, restent indépendantes ; elles contraignent toutes deux le Rack.

Les formulaires conservent la décision métier existante : les étages sont générés par le Bâtiment et ne deviennent pas un CRUD autonome.

## Compatibilité

- aucun endpoint API supprimé ou renommé ;
- aucune commande CLI supprimée ou renommée ;
- aucune migration PostgreSQL ajoutée ;
- **55 migrations** conservées, dernière : `0055_kubernetes_topology_inventory.sql` ;
- compatibilité des anciens imports web maintenue par façades ;
- comportement du thème et de la sidebar active inchangé.

## Validation exécutée

### Tests

- collecte Python : **1 337 tests** ;
- unitaires et performance : **645/645 PASS** ;
- intégration directement impactée : **81/81 PASS** ;
- frontend Node.js : **76/76 PASS**.

Le périmètre d'intégration ciblé couvre notamment :

- gestion CRUD unifiée ;
- runtime web ;
- chargement frontend ;
- accessibilité ;
- hiérarchie et modèle physique DCIM ;
- cycle de vie des sites ;
- documentation GA ;
- transport ASGI.

### Qualité statique

- Ruff format : **397 fichiers conformes** ;
- Ruff lint : **PASS** ;
- mypy strict : **116 modules conformes** ;
- `compileall` : **PASS**.

### Frontend et accessibilité

- contrat statique du portail : **PASS** ;
- WCAG 2.2 AA : **PASS** ;
- ESLint JSX : **PASS** ;
- build Vite : **PASS** ;
- budget initial : **2 556 octets JavaScript brut / 1 262 octets gzip** pour le shell initial ;
- `npm audit --audit-level=high` : **0 vulnérabilité**.

### Sécurité et conformité release

- `security_gate.py` : **PASS** ;
- Bandit sur `src/openinfra` : **PASS**, aucun finding bloquant ;
- OpenAPI produit : **PASS** ;
- OpenAPI CDC : **PASS** ;
- documentation GA 0.33.4 : **PASS** ;
- CDC 4.9.0 : **840 exigences / 529 entités — PASS** ;
- roadmap v2.2 : **22 phases / 131 epics / 11 gates / 112 tests — PASS** ;
- alignement Enterprise : **PASS** ;
- support-readiness : **PASS** ;
- six profils installateur : **PASS** ;
- PRA/PCA : **PASS** ;
- observabilité multisite : **PASS** ;
- chaos multisite : **PASS** ;
- GATE-09 Scale-out : **PASS** ;
- validateurs Kubernetes EPIC-2101, 2102 et 2103 : **PASS**.

### Packaging

- wheel `openinfra-0.33.4-py3-none-any.whl` : **PASS** ;
- sdist `openinfra-0.33.4.tar.gz` : **PASS** ;
- vérification du contenu des artefacts : **PASS** ;
- smoke du wheel réellement installé hors de l'arbre source : **PASS** ;
- runtime installé : **20 assets**, **10 routes Kubernetes**, **55 migrations**.

Le premier environnement virtuel de smoke ne disposait pas de `uvicorn`. Après installation du fichier `requirements/runtime.txt` déclaré par le projet, le wheel installé a passé l'intégralité du smoke hors de l'arbre source.

## Non-régression visuelle

Aucune modification du thème ou de la palette n'a été introduite.

Le CSS source, le CSS runtime packagé et le CSS de la v0.33.3 ont le même SHA-256 :

```text
0ef8f1665af70a0d2ac2b07a9de30ec33b7851e00b1731d2c709fbf9a801220e
```

Le comportement précédemment approuvé reste inchangé : le fond du composant racine actif de la sidebar ne varie pas au survol ; seuls le texte, l'icône et le chevron utilisent le turquoise prévu.

## Limites locales

La suite globale complète `tests/architecture + tests/integration` n'a pas été intégralement réexécutée dans ce sandbox. Le périmètre directement impacté est couvert par **81 tests d'intégration**, complétés par **645 tests unitaires/performance** et **76 tests frontend**.

La couverture globale **>= 98 %** n'a pas été recalculée localement et reste bloquante dans GitHub Actions.

`pip-audit --strict -r requirements/runtime.txt` a été lancé mais n'a pas pu interroger `pypi.org` en raison d'un échec de résolution DNS du sandbox.

Docker n'étant pas disponible dans l'environnement courant, les smokes Docker Compose restent délégués à la CI.

## Documentation et planification

- `docs/ui/MANAGEMENT_CONTEXT_HIERARCHY.md` documente la règle et les dépendances ;
- README, changelog et traçabilité sont alignés sur la v0.33.4 ;
- **CDC 4.9.0 inchangé** ;
- **roadmap v2.2 inchangée** : l'évolution est structurelle et ergonomique, sans nouvelle exigence métier ni nouvel epic.
