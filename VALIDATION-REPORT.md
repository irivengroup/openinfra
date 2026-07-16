# Rapport de validation — OpenInfra Python POO v0.33.10

## Objet de la livraison

La version **0.33.10** clôt le jalon **P21 / EPIC-2106** et livre le gate bloquant **GATE-10** pour la promotion de **REL-11 Kubernetes & Cloud-native**.

La promotion repose sur un catalogue fermé de sept preuves immuables :

1. EPIC-2101 — topologie Kubernetes et mapping physique ;
2. EPIC-2102 — exposition réseau et dépendances ;
3. EPIC-2103 — corrélation sécurité, images, SBOM, certificats et références de secrets ;
4. EPIC-2104 — conformité GitOps et dérives ;
5. EPIC-2105 — capacité cluster/namespace ;
6. EPIC-2106 — qualification runtime multi-cluster ;
7. EPIC-2106 — contrat projet et industrialisation.

Aucune migration PostgreSQL, route métier, commande CLI métier, permission RBAC ou modification de thème n’est introduite. La chaîne reste à **56 migrations**, avec `0056_kubernetes_gitops_drift.sql` comme dernière migration.

## Implémentation livrée

### Certification GATE-10

Le moteur `openinfra.quality.cloud_native_promotion` :

- vérifie l’exactitude du catalogue de preuves ;
- contrôle la version OpenInfra, la fraîcheur et les types de rapports ;
- recalcule chaque SHA-256 avant certification ;
- refuse les chemins absolus, traversées de répertoire et preuves hors racine ;
- bloque la promotion sur preuve absente, altérée, périmée ou incohérente ;
- produit un rapport déterministe autorisant ou refusant REL-11.

Le workflow `.github/workflows/cloud-native-promotion.yml` construit les sept preuves, exécute les tests de régression, assemble le manifeste immuable, applique GATE-10 et publie les preuves avec une rétention de 90 jours.

### Qualification runtime multi-cluster

La qualification locale réelle a exécuté :

- **3 clusters** ;
- **50 256 ressources qualifiées** ;
- un snapshot au plafond contractuel de **50 000 ressources** ;
- un budget maximal de **30 secondes**.

Résultat mesuré : **1,023399 seconde**, statut `passed`.

Les probes ont confirmé :

- fingerprints déterministes ;
- mapping physique valide ;
- read model de capacité valide ;
- rejet du matériel secret en clair ;
- rejet des références inter-namespace interdites ;
- rejet des chemins physiques orphelins.

La certification finale contient **7/7 critères passés**, aucun bloqueur et `authorized_for_cloud_native_release=true`.

### Durcissement de l’installateur autonome

Le déploiement des scopes `all-in-one` et `web` exclut désormais systématiquement :

- `node_modules/` ;
- `dist/` ;
- caches Vite ;
- rapports de couverture ;
- fichiers de log.

Cette correction empêche l’embarquement de dépendances de développement, réduit fortement le payload offline et préserve un comportement déterministe même lorsque l’arbre source a déjà exécuté `npm ci` et `npm run build`.

Le test installateur correspondant passe de **21,1 s à 2,3 s** dans l’environnement local tout en vérifiant la présence des sources Web nécessaires et l’absence des artefacts interdits.

## Validation exécutée

### Tests Python

| Périmètre | Résultat |
|---|---:|
| Unitaires | inclus dans le lot de 674 tests |
| Architecture | inclus dans le lot de 674 tests |
| Performance | inclus dans le lot de 674 tests |
| Lot unitaires + architecture + performance | **674/674 PASS** |
| Intégration, tous les 167 fichiers | **714/714 PASS** |
| Total Python exécuté | **1 388/1 388 PASS** |
| Tests ciblés Kubernetes/GATE-10 | **105/105 PASS** |
| Contrats GATE-10 spécifiques | **9/9 PASS** |

Les fichiers d’intégration ont été instrumentés dans des processus isolés afin d’éviter la contamination d’état entre scénarios CLI/installateur et d’agréger une couverture déterministe.

### Couverture

- lignes couvertes : **43 708 / 44 686** ;
- lignes manquantes : **978** ;
- couverture exacte : **97,811395 %** ;
- affichage Coverage.py et seuil contractuel : **98 %** ;
- `coverage report --fail-under=98` : **PASS** ;
- aucune exclusion supplémentaire ni réduction du seuil.

### Qualité statique et sécurité

- `compileall` : **PASS** ;
- Ruff format sur `src tests scripts docker installers` : **PASS** ;
- Ruff lint : **PASS** ;
- mypy strict : **121 modules source conformes** ;
- Bandit sur `src/openinfra` : **PASS**, aucun finding bloquant ;
- `scripts/security_gate.py` : **PASS** ;
- `scripts/quality_gate.py` : **PASS** ;
- GATE-10 local : **CERTIFIED**.

### Frontend

- tests Node : **79/79 PASS** ;
- ESLint : **PASS** ;
- contrôles JSX et accessibilité : **PASS** ;
- WCAG 2.2 AA : **PASS** ;
- build Vite sous budgets : **PASS** ;
- bundle initial : **2 556 octets bruts / 1 264 octets gzip** ;
- chunks dynamiques : **13** ;
- `npm audit --audit-level=high` : **0 vulnérabilité** ;
- `npm audit --omit=dev --audit-level=high` : **0 vulnérabilité**.

### Packaging et smoke installé

- wheel `openinfra-0.33.10-py3-none-any.whl` : **PASS** ;
- sdist `openinfra-0.33.10.tar.gz` : **PASS** ;
- `scripts/verify_artifact.py` sur les deux artefacts : **PASS** ;
- sdist : **975 entrées**, sans `node_modules` ni `web/dist` ;
- installation du wheel avec `--no-deps` hors arbre source : **PASS** ;
- smoke du wheel installé : **PASS** ;
- version installée : **0.33.10** ;
- migrations installées : **56** ;
- routes Kubernetes : **16** ;
- assets runtime : **20** ;
- gate cloud-native installé : **GATE-10**.

### Documentation et contrats

- validateur EPIC-2101 : **PASS** ;
- validateur EPIC-2102 : **PASS** ;
- validateur EPIC-2103 : **PASS** ;
- validateur EPIC-2104 : **PASS** ;
- validateur EPIC-2105 : **PASS** ;
- validateur EPIC-2106 : **PASS** ;
- assemblage du manifeste à sept preuves : **PASS** ;
- vérification de l’intégrité SHA-256 : **PASS** ;
- documentation GA et frontend : **PASS** ;
- OpenAPI produit et CDC : **PASS**.

## Non-régression visuelle

Le thème n’a pas été modifié. Le fichier `web/src/openinfra-theme.css` conserve l’empreinte validée :

```text
fb7feabe378613ac41efb18db94b0d95a8faa916b6f782c9fd0ea2b0d8e9fcf4
```

Aucune couleur, surface, transparence, règle de survol ou structure visuelle n’a été changée.

## Validations dépendantes de l’environnement

- Le binaire Docker n’est pas disponible dans l’environnement courant. Les contrats du contexte Docker minimal, de Compose et des services runtime sont testés, mais le démarrage réel des conteneurs reste à confirmer sur un hôte Docker ou dans GitHub Actions.
- `pip-audit --strict --requirement requirements/security-audit.txt` a été exécuté, mais n’a pas pu résoudre `pypi.org` (`Temporary failure in name resolution`). Aucun résultat d’audit de vulnérabilités Python n’est donc revendiqué localement ; les contrôles Bandit, Security Gate et audits npm sont, eux, exécutés et verts.

## Documentation de planification

Le **CDC 4.9.0** et la **roadmap v2.2** restent inchangés : EPIC-2106, GATE-10 et REL-11 y étaient déjà planifiés. Cette livraison implémente le jalon existant sans nouvelle exigence fonctionnelle, réglementaire ou architecturale.
