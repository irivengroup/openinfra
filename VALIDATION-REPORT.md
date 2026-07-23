# OpenInfra 0.34.19 — rapport de validation

## Incrément

OpenInfra 0.34.19 corrige l’échec de build Compose déclenché lorsqu’une ressource déclarée dans le contrat de packaging n’est pas matérialisée dans l’arbre Docker. Le contrôle strict n’est pas supprimé ni contourné.

Le correctif comprend :

- `COPY docs ./docs` afin d’aligner durablement le contexte Docker sur l’arborescence documentaire distribuée ;
- `scripts/validate_docker_build_context.py`, exécuté avant `pip install` et dans GitHub Actions ;
- croisement déterministe entre les sources `force-include`, les fichiers réellement présents et les instructions `COPY` précédant le packaging ;
- diagnostic structuré `missing_sources` / `uncovered_sources` ;
- prévalidation transactionnelle du backend de build avant toute copie sous `src/openinfra` ;
- `.dockerignore` versionné et embarqué dans le sdist ;
- documentation, tests et CI synchronisés.

Aucune migration, aucune rupture API/CLI/RBAC, aucune suppression fonctionnelle et aucune modification de la charte graphique approuvée n’ont été introduites.

## Qualification fonctionnelle et autonome

La campagne finale exécutée après toutes les modifications est entièrement verte :

- fichiers de tests Python : **296/296 PASS** ;
- tests Python : **1 692/1 692 PASS** ;
- échecs, erreurs, timeouts et tests ignorés : **0** ;
- stratégie : exécution isolée de chaque fichier, quatre workers supervisés, puis combinaison de **296 fragments Coverage** ;
- instructions : **50 392** ;
- couvertes : **49 396** ;
- non couvertes : **996** ;
- couverture exacte : **98,023495792983 %**, seuil `>= 98 %` franchi ;
- tests frontend autonomes : **100/100 PASS** ;
- catalogue frontend runtime : **300 opérations uniques** ;
- migrations PostgreSQL/Oracle : **60/60** ;
- compilation Python, sécurité interne, contrats frontend, WCAG 2.2 AA, OpenAPI principal et CDC, documentation GA, CDC 4.12, roadmap 2.5 et GATE-14 : **PASS** ;
- quality gate global : **code 0**.

## Régression Docker et packaging

- ressources `force-include` requises : **29** ;
- ressources absentes : **0** ;
- ressources non couvertes par le Dockerfile : **0** ;
- construction du wheel depuis l’arbre source : **PASS** ;
- construction du wheel depuis le sdist extrait : **PASS** ;
- présence de `docs/runbooks/RSOT_QUALITY_NON_AUTHORITATIVE_SOURCE.md` dans le sdist et le wheel : **PASS** ;
- absence de staging partiel lorsqu’une source est manquante : **PASS** ;
- nettoyage du staging après build réussi : **PASS**.

## Traçabilité GATE-14

- entrées contractuelles : **667** ;
- preuves automatisées : **31** ;
- preuves partielles : **588** ;
- qualifications externes : **48** ;
- sélecteurs pytest résolus : **44** ;
- fichiers d’évidence : **77** ;
- preuves manquantes et exigences N1 non classées : **0**.

## Gates externes non exécutables dans l’environnement courant

- Ruff, mypy, Bandit, Twine et pip-audit : outils absents ;
- ESLint JSX, Vite et npm audit : arbre de dépendances Node complet non matérialisé ;
- Docker Engine/Compose : indisponible dans l’environnement de qualification, donc le build d’image réel reste à confirmer sur la plateforme cible ;
- qualifications live PostgreSQL, Oracle 19c, fournisseurs DDI, systemd et fédération d’identité : plateformes absentes.

Le smoke de packaging reproduisant précisément l’étape fautive du Dockerfile (`pip wheel` depuis le contexte source puis depuis le sdist extrait) est vert.

## État de promotion

L’incrément 0.34.19 est **fonctionnellement qualifié**. La promotion final-candidate et production reste **NO-GO** tant que les gates externes d’outillage et d’infrastructure ne sont pas exécutés avec succès dans un environnement approprié.
