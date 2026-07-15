# Rapport de validation — OpenInfra Python POO v0.33.5

## Objet de la livraison

La version **0.33.5** regroupe deux évolutions cohérentes et entièrement intégrées :

1. **P21 / REL-11 / EPIC-2104 — Conformité GitOps et dérive observée** ;
2. correction et professionnalisation des **filtres multicritères contextuels** des pages `Gestion de …`.

Cette livraison ne supprime ni ne renomme aucun endpoint public, aucune commande CLI, aucune permission RBAC et aucune opération historique du portail.

## EPIC-2104 — Conformité GitOps et dérive observée

Le référentiel Kubernetes distingue désormais explicitement :

- l'état **attendu** issu de GitOps, immuable et lié à un commit Git complet de 40 ou 64 caractères hexadécimaux ;
- l'état **observé** issu d'un snapshot Kubernetes Discovery immuable ;
- un rapport de conformité déterministe entre ces deux sources.

Les dérives couvertes incluent :

- ressource attendue absente ;
- ressource inattendue ;
- label ou annotation absent/non conforme ;
- propriétaire absent/non conforme ;
- environnement absent, non conforme ou hors politique ;
- attribut attendu absent ou différent.

Le moteur compare uniquement les champs explicitement gouvernés afin d'éviter les faux positifs liés aux données Kubernetes volatiles.

### Sécurité et gouvernance

- aucun secret Git n'est accepté dans les références de dépôt ;
- seuls les schémas de dépôt HTTPS et SSH autorisés sont acceptés ;
- les chemins GitOps sont relatifs et refusent les traversées `..` ;
- les clés sensibles sont refusées dans les métadonnées gouvernées ;
- l'évaluation produit un audit `kubernetes.gitops.assessed` ;
- une dérive produit un événement outbox transactionnel `kubernetes.gitops.drift.detected` ;
- une évaluation conforme ne produit pas d'événement de dérive ;
- **`automatic_remediation=false`** : aucune correction automatique silencieuse du cluster ou de l'état attendu.

### API et CLI

Six routes GitOps sont exposées :

- `GET /api/v1/kubernetes/gitops-states`
- `GET /api/v1/kubernetes/gitops-states/get`
- `GET /api/v1/kubernetes/gitops-states/latest`
- `GET /api/v1/kubernetes/gitops-states/drift`
- `GET /api/v1/kubernetes/gitops-states/latest-drift`
- `POST /api/v1/kubernetes/gitops-states/import`

Les commandes CLI correspondantes sont disponibles :

- `openinfra kubernetes gitops-import`
- `openinfra kubernetes gitops-list`
- `openinfra kubernetes gitops-get`
- `openinfra kubernetes gitops-latest`
- `openinfra kubernetes gitops-drift`
- `openinfra kubernetes gitops-latest-drift`

Swagger/ReDoc classe ces opérations sous **Discovery · Kubernetes et cloud-native**.

## Persistance

Nouvelle migration additive :

- `0056_kubernetes_gitops_drift.sql`

La livraison contient désormais **56 migrations**.

Le modèle GitOps utilise :

- partitionnement par tenant ;
- index de lecture du dernier état attendu ;
- filtres cluster/environnement/propriétaire ;
- pagination par curseur ;
- outbox transactionnelle.

## Filtres multicritères des pages de gestion

Le défaut qui rendait les nouveaux formulaires de filtrage vides est corrigé.

### Comportement

Les critères pertinents au contexte sont désormais **toujours visibles**, même si la liste courante ne permet pas encore de dériver une valeur.

Les critères sont structurés en deux groupes :

1. **Contexte parent** ;
2. **Critères métier**.

La hiérarchie parentale canonique reste :

1. Organisation ;
2. Filiale/Subdivision ;
3. Site ;
4. Bâtiment ;
5. Étage ;
6. Salle ;
7. Ligne/Colonne ;
8. Rack.

Les niveaux non pertinents au type d'objet ne sont pas affichés artificiellement.

Lorsqu'un critère pertinent ne possède aucune valeur disponible, il reste visible avec un état désactivé explicite au lieu de disparaître.

Les données DCIM aplaties héritent désormais, sans mutation de la source, du contexte nécessaire aux filtres, notamment :

- Organisation/Filiale selon la portée ;
- Étage ;
- Ligne ;
- Colonne ;
- Rack.

Les règles de cascade restent strictes : un parent filtre ses descendants mais ne se filtre jamais lui-même ; Ligne et Colonne restent au même niveau et filtrent ensemble le Rack.

### Intégration au thème

Le panneau de filtrage utilise exclusivement les tokens visuels OpenInfra existants :

- surfaces et transparences existantes ;
- bordures et rayons cohérents avec les autres cartes ;
- typographie et hiérarchie visuelle de la page ;
- états focus/disabled accessibles ;
- responsive mobile/tablette conservé.

Comparaison de palette avec v0.33.4 :

- 52 couleurs hexadécimales distinctes avant ;
- 52 couleurs hexadécimales distinctes après ;
- aucune couleur ajoutée ;
- aucune couleur supprimée.

Le comportement approuvé de la sidebar est conservé : le fond du composant racine actif ne change pas au survol ; seuls le texte, l'icône et le chevron utilisent le turquoise prévu.

## Validation exécutée

### Python

- **1 366 tests collectés** ;
- **660/660 tests unitaires et performance : PASS** ;
- **62/62 tests ciblés GitOps, gestion CRUD, OpenAPI, workflows, packaging et runtime frontend : PASS** ;
- nouveau domaine + service GitOps : **506/506 instructions couvertes, 100 %** ;
- Ruff format : **410 fichiers conformes** ;
- Ruff lint : **PASS** ;
- mypy strict : **119 modules conformes** ;
- `compileall` : **PASS**.

### Frontend

- **78/78 tests frontend : PASS** ;
- validation statique frontend : **PASS** ;
- WCAG 2.2 AA : **PASS** ;
- ESLint : **PASS** ;
- build Vite : **PASS** ;
- validation des budgets de chargement : **PASS** ;
- `npm audit --audit-level=high` : **0 vulnérabilité**.

### Sécurité et documentation

- security gate : **PASS** ;
- Bandit sur `src/openinfra` : **PASS**, aucun finding bloquant ;
- OpenAPI produit et OpenAPI CDC : **PASS** ;
- documentation GA 0.33.5 : **PASS** ;
- CDC : **840 exigences / 529 entités** ;
- roadmap v2.2 : **22 phases / 131 epics / 11 gates / 112 tests** ;
- alignement Enterprise : **PASS** ;
- support-readiness : **PASS** ;
- validateurs EPIC-2101, EPIC-2102, EPIC-2103 et EPIC-2104 : **PASS**.

### Packaging et smoke installé

- wheel `openinfra-0.33.5-py3-none-any.whl` : **PASS** ;
- sdist `openinfra-0.33.5.tar.gz` : **PASS** ;
- vérification du contenu des artefacts : **PASS** ;
- smoke du wheel réellement installé hors de l'arbre source : **PASS** ;
- version installée : **0.33.5** ;
- routes Kubernetes installées : **16** ;
- migrations installées : **56** ;
- dernière migration : `0056_kubernetes_gitops_drift.sql` ;
- assets runtime packagés : **20**.

## Limites de l'environnement local

La couverture globale complète du dépôt n'a pas été recalculée dans ce sandbox. Le seuil contractuel global **≥ 98 % reste bloquant dans GitHub Actions**. Le nouveau domaine et service GitOps ont toutefois été mesurés séparément à **100 %**.

`pip-audit --strict -r requirements/runtime.txt` a été lancé mais n'a pas pu joindre `pypi.org` en raison d'un échec de résolution DNS. Ce contrôle n'est donc pas déclaré comme réussi localement et reste exécuté par la CI lorsque le réseau est disponible.

Docker/Docker Compose ne sont pas disponibles dans cet environnement. Les smokes conteneurisés restent donc exécutés par les workflows CI dédiés.

## Documentation de référence

- CDC : **4.9.0**, inchangé ;
- roadmap : **2.2.0**, inchangée ;
- phase : **P21** ;
- release : **REL-11** ;
- epic principal : **EPIC-2104**.

Aucune mise à jour du CDC ou de la roadmap n'est requise : EPIC-2104 est déjà défini dans la roadmap v2.2 et la correction des filtres constitue une amélioration structurelle/UX sans nouvelle exigence métier.
