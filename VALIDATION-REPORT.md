# OpenInfra 0.34.18 — rapport de validation

## Incrément

`TST-RSOTQUAL-048` automatise l’avertissement produit lorsqu’un attribut RSOT est alimenté par une source différente de la source autoritative définie par la gouvernance. Le contrôle est démontré de bout en bout par service applicatif, CLI, API HTTP, synthèse tenant, audit et portails.

Le finding reste rétrocompatible et expose désormais `field`, `actual_source`, `expected_source` et `governance_rule`. Les chemins imbriqués sont résolus sans modifier l’objet RSOT ni son stockage. Le packaging a été durci par une normalisation atomique et déterministe des sdists sous `SOURCE_DATE_EPOCH`.

## Qualification fonctionnelle et autonome

La campagne complète exécutée après toutes les modifications est entièrement verte :

- fichiers de tests Python : **295/295 PASS** ;
- tests Python : **1 687/1 687 PASS** ;
- échecs, erreurs, timeouts et tests ignorés : **0** ;
- base Coverage issue d’une campagne complète réussie : **PASS** ;
- instructions : **50 392** ;
- couvertes : **49 396** ;
- non couvertes : **996** ;
- couverture exacte : **98,023495792983 %**, seuil `>= 98 %` franchi ;
- tests frontend autonomes : **100/100 PASS** ;
- catalogue frontend runtime : **300 opérations uniques** ;
- migrations PostgreSQL/Oracle : **60/60** ;
- compilation Python, sécurité interne, contrats frontend, WCAG 2.2 AA, OpenAPI principal et CDC, documentation GA, CDC 4.12, roadmap 2.5 et GATE-14 : **PASS** ;
- quality gate global : **code 0**.

Le parcours `TST-RSOTQUAL-048` vérifie un attribut imbriqué `hardware.serial_number` gouverné par `inventory.cmdb` alors que l’observation provient de `discovery.snmp`. Le résultat est `warning`, le score d’autorité est dégradé, les métadonnées de gouvernance sont identiques sur toutes les interfaces et la collection `source_objects` reste strictement inchangée.

## Traçabilité GATE-14

- entrées contractuelles : **667** ;
- preuves automatisées : **31** ;
- preuves partielles : **588** ;
- qualifications externes : **48** ;
- sélecteurs pytest résolus : **44** ;
- fichiers d’évidence : **77** ;
- preuves manquantes et exigences N1 non classées : **0**.

## Packaging

- wheel : **reproductible bit à bit** ;
- sdist : **reproductible bit à bit** après normalisation déterministe TAR/PAX/GZIP ;
- contenu strict wheel/sdist : **PASS** ;
- runbook `RSOT_QUALITY_NON_AUTHORITATIVE_SOURCE.md` présent dans les deux distributions ;
- smoke du wheel installé hors arbre source avec le runtime local : **PASS** ;
- smoke strict en environnement vierge : **bloqué**, le registre Python ne fournit pas `defusedxml>=0.7.1` ;
- Twine : **non exécuté**, outil absent.

## Gates externes non exécutables dans l’environnement courant

- Ruff, mypy, Bandit et pip-audit : outils absents ;
- `npm ci` : échec registre HTTP **503**, arbre de dépendances Node non matérialisé ;
- ESLint JSX, Vite et npm audit : non exécutables sans cet arbre ;
- qualifications live PostgreSQL, Oracle 19c, fournisseurs DDI, Docker Compose, systemd et fédération d’identité : plateformes absentes.

## État de promotion

L’incrément 0.34.18 est **fonctionnellement qualifié**. La promotion final-candidate et production reste **NO-GO** tant que les gates externes d’outillage, de registres et d’infrastructure ne sont pas exécutés avec succès dans un environnement approprié.
