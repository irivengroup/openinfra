# OpenInfra 0.34.21 — rapport de validation

## Incrément

OpenInfra 0.34.21 corrige l’incomplétude observable du catalogue de migrations dans les livrables. Jusqu’à 0.34.20, les migrations étaient principalement accessibles à l’intérieur de la source, du wheel ou du sdist et le vérificateur d’artefacts ne contrôlait qu’un sous-ensemble de fichiers nommés en dur. Le bundle ne permettait donc pas d’auditer directement et exhaustivement les deux catalogues.

Le correctif comprend :

- une archive autonome `openinfra-0.34.21-migrations.zip` exposée directement sous `artifacts/migrations` ;
- **60 migrations PostgreSQL** et **60 migrations Oracle**, plus le manifeste Oracle ;
- un manifeste unifié avec la version, les bornes `0001`/`0060` et le SHA-256 de chaque migration des deux moteurs ;
- une validation stricte des noms, de la contiguïté, de la parité PostgreSQL/Oracle et du manifeste Oracle ;
- une comparaison exhaustive du wheel et du sdist avec les catalogues sources ;
- une génération reproductible sous `SOURCE_DATE_EPOCH`, atomique et bloquante dans la CI ;
- des tests de corruption, omission, divergence de hash, rupture d’ordre et nettoyage après échec.

Aucun fichier SQL, schéma de base de données, contrat API/CLI/RBAC ni élément de la charte graphique approuvée n’a été modifié.

## Qualification fonctionnelle et autonome

La campagne finale exécutée après les modifications est verte :

- fichiers de tests Python : **298/298 PASS** ;
- tests Python : **1 711/1 711 PASS** ;
- échecs, erreurs et tests ignorés : **0** ;
- stratégie : isolation par fichier, 298 fragments Coverage combinés uniquement après réussite ;
- instructions : **50 621** ;
- couvertes : **49 625** ;
- non couvertes : **996** ;
- couverture exacte : **98,03243713083504 %**, seuil `>= 98 %` franchi ;
- tests frontend autonomes : **100/100 PASS** ;
- contrat frontend statique et WCAG 2.2 AA : **PASS** ;
- OpenAPI principal et CDC : **PASS** ;
- sécurité interne, documentation GA et compilation Python : **PASS** ;
- migrations PostgreSQL/Oracle : **60/60**, parité stricte : **PASS** ;
- quality gate global : **code 0**.

## Intégrité des migrations et du packaging

- catalogue PostgreSQL source : **60 fichiers**, `0001` à `0060` ;
- catalogue Oracle source : **60 fichiers**, `0001` à `0060` ;
- parité des noms PostgreSQL/Oracle : **PASS** ;
- manifeste Oracle : **PASS** ;
- archive autonome : **123 fichiers** — README, manifeste unifié, 120 SQL et manifeste Oracle ;
- comparaison SHA-256 source/wheel/sdist : **PASS** ;
- reconstruction du wheel depuis le sdist extrait : **PASS** ;
- corruption, omission, migration inattendue et divergence de hash : **bloquantes et testées** ;
- archive de migrations incluse directement dans le bundle : **obligatoire et vérifiée**.

## Gates externes non exécutables dans l’environnement courant

- Ruff, mypy, Bandit, Twine et pip-audit : outils absents ;
- Vite : dépendance Node non matérialisée dans l’environnement ;
- npm audit : registre npm indisponible, réponse HTTP 503 ;
- Docker Engine/Compose : indisponible dans l’environnement de qualification ;
- qualifications live PostgreSQL, Oracle 19c, fournisseurs DDI, systemd et fédération d’identité : plateformes absentes.

## État de promotion

L’incrément 0.34.21 et son catalogue de migrations sont **fonctionnellement qualifiés — GO**. La promotion final-candidate et production reste **NO-GO** jusqu’à l’exécution réussie des gates externes d’outillage et d’infrastructure.
