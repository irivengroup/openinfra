# OpenInfra v0.32.6 — rapport de validation

Date : 2026-07-14

## Objet

Cette livraison implémente P18 / EPIC-1801 : benchmarks Enterprise Scale reproductibles pour les six familles de charge contractuelles API, IPAM, imports, Discovery, base de données et graphes. Elle étend sans rupture le mécanisme de certification de capacité Enterprise livré précédemment et conserve les contrôles de release P18 déjà présents.

## Fonctionnalités livrées

- profil de capacité Enterprise v2 avec six familles de benchmark obligatoires ;
- runner HTTP asynchrone HTTPS, strictement GET/read-only, avec pool persistant et concurrence bornée ;
- suite orchestrée des six workloads avec configuration externe des chemins représentatifs ;
- mesures p95, p99, taux d'erreur, débit, volume de réponses et distribution des statuts HTTP ;
- intégration des résultats et de leurs empreintes SHA-256 dans la preuve de certification de capacité ;
- refus de `capacity_certification=true` si un benchmark requis est absent ou dépasse les seuils ;
- workflow Enterprise Capacity étendu et secret protégé pour les chemins de benchmark ;
- documentation d'architecture et runbook d'exploitation alignés ;
- compatibilité ascendante de lecture des anciennes preuves de profil v1.

## Compatibilité et impact

- aucune migration PostgreSQL ;
- aucune rupture d'API métier ou de CLI publique ;
- aucune dépendance runtime ajoutée ;
- aucune modification CSS, graphique ou du thème ;
- aucune suppression de fonctionnalité existante ;
- les preuves historiques de profil v1 restent lisibles ;
- une certification officielle avec profil v2 exige désormais les six familles de benchmark.

## Validations exécutées

- tests Python collectés : **1 223** ;
- suites unitaires et performance : **581 tests réussis** ;
- intégration : **133 fichiers de tests réussis** en processus isolés ;
- module modifié `capacity_certification.py` : **284 / 284 instructions couvertes, 100 %** ;
- Ruff format, périmètre CI `src tests scripts docker installers` : **348 fichiers conformes** ;
- Ruff lint, même périmètre CI : **PASS** ;
- mypy strict : **107 modules conformes** ;
- compileall `src tests scripts docker installers` : **PASS** ;
- `scripts/security_gate.py` : **PASS** ;
- Bandit complet `src/openinfra` : **PASS, 0 résultat** sur **95 309 lignes de code analysées** ;
- validation frontend : **PASS** ;
- validation documentation GA : **10 documents, 33 commandes CLI, 7 opérations API, version 0.32.6** ;
- support-readiness : **PASS**, trois profils de support ;
- six profils installateur autonome : **PASS** ;
- alignement Enterprise : **PASS** ;
- runtime natif : **PASS** ;
- tests frontend : **60 réussis** ;
- ESLint : **PASS** ;
- build Vite : **PASS** ;
- npm audit niveau high : **0 vulnérabilité** ;
- build sdist + wheel `openinfra 0.32.6` : **PASS** ;
- vérification des artefacts : **PASS** ;
- smoke du wheel installé : **PASS**, version **0.32.6**, **54 migrations** et contrats runtime/GA/release présents.

## Couverture globale et quality gate

La suite complète monolithique et une seconde tentative de collecte de couverture par processus parallèles ont dépassé la fenêtre d'exécution du sandbox, sans échec fonctionnel observé avant interruption. La couverture globale exacte de cette révision n'est donc pas déclarée comme exécutée localement.

La base v0.32.5 validée était à **98,00398220299402 % (39 869 / 40 681)**. Le principal module de production modifié par EPIC-1801 passe de 222 à 284 instructions et les **284 instructions sont couvertes à 100 %** par la suite dédiée. Le seuil contractuel global reste bloquant à **98 %** dans la CI GitHub ; la promotion de la release est interdite si ce gate échoue.

Le `quality_gate.py` global a été exécuté jusqu'à son étape finale. Tous les contrôles structurels et sous-gates précédents ont terminé avec succès ; le processus retourne **RC=1 uniquement sur `coverage report --fail-under=98`**, car la base `.coverage` locale est issue de la tentative de collecte interrompue et ne représente que 55 % du code. Ce taux partiel n'est pas une mesure de la couverture réelle de la suite complète.

## Limites de l'environnement

Docker n'est pas installé dans le sandbox. Le build Compose réel, les smokes conteneurs, Trivy et le DAST doivent être exécutés par les workflows bloquants de release.


Aucun benchmark Enterprise officiel n'a été exécuté contre une infrastructure représentative, car il nécessite la topologie protégée, les données de charge et les secrets d'organisation. La livraison fournit le moteur, le profil, les preuves et le workflow nécessaires ; une certification officielle doit exécuter le profil v2 avec `duration_scale=1` sur la plateforme de référence.
