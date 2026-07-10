# OpenInfra v0.29.92 — Rapport de validation

Date de validation : `2026-07-10`  
Release : `0.29.92`  
Périmètre : `P15 / EPIC-1505 — visualisations d’impact et détection des SPOF`

## Résultat global

La livraison étend le graphe de dépendances RSOT existant avec une détection déterministe des points uniques de défaillance (SPOF), des visualisations accessibles et des exports gouvernés. Elle reste strictement en lecture seule sur le RSOT, ne crée aucune seconde source de vérité et n’applique aucune remédiation automatique.

- Tests Python collectés et validés : **742 PASS** dans **103 fichiers**.
- Tests unitaires : **299 PASS**.
- Tests d’intégration : **440 PASS**.
- Tests d’architecture : **3 PASS**.
- Couverture globale exacte : **98,001223740567 %** — `24 025 / 24 515` lignes couvertes.
- Seuil bloquant : **98 % PASS**.
- Tests frontend Node.js : **23 PASS**.
- Lint frontend, accessibilité JSX, contrat WCAG 2.2 AA et build Vite : **PASS**.
- `npm audit --audit-level=high` : **0 vulnérabilité**.

La suite Python complète a été exécutée par fragments isolés, puis les données de couverture ont été consolidées. Cette segmentation évite le dépassement de la limite d’exécution observé lors des parcours CLI monolithiques, sans omettre de fichier ni de scénario.

## Détection des SPOF et visualisations d’impact

Garanties validées :

- analyse par dominateurs enracinés sur une projection bornée du graphe RSOT ;
- directions `outgoing`, `incoming` et `both` ;
- prise en compte des chemins alternatifs avant de qualifier un objet de SPOF ;
- exclusion de la racine des candidats ;
- classement déterministe par nombre d’objets affectés, profondeur et clé ;
- impact direct, ratio d’impact, agrégats par type et catégorie, échantillon borné ;
- filtres de candidats par type d’objet, catégorie, type de ressource et statut ;
- limites strictes sur les filtres, la profondeur, le volume, l’échantillon et le seuil d’impact ;
- pagination par curseur opaque lié à l’empreinte complète de la requête ;
- rejet des curseurs invalides, falsifiés, négatifs ou hors jeu de résultats ;
- signalement `complete=false` lorsque la projection est tronquée par `max_nodes` ;
- gestion déterministe des cycles, boucles, nœuds déconnectés et relations hors projection ;
- exports JSON, CSV normalisé et GraphML ;
- annotations SPOF optionnelles dans les exports ;
- écriture CLI atomique via fichier temporaire puis remplacement ;
- permission existante `rsot.read`, isolation tenant et événements d’audit ;
- aucune migration de base de données et aucune écriture sur les équipements.

## Interfaces

- CLI : `openinfra graph spof` et `openinfra graph export`.
- HTTP : `GET /api/v1/graph/spof` et `GET /api/v1/graph/export`.
- OpenAPI : paramètres, bornes, formats, authentification et réponses binaires documentés.
- Portail React et runtime packagé : opérations SPOF/export en parité FR/EN.
- Visualisation en couches avec navigation clavier et liste textuelle équivalente.
- Classement tabulaire des SPOF avec rang, impact total/direct, ratio et échantillon.
- Résultat JSON brut toujours disponible comme repli.
- Téléchargements navigateur JSON, CSV et GraphML via URL d’objet révoquée après usage.
- Correction du rendu des booléens par défaut dans le runtime statique : une valeur `true` est désormais sélectionnée comme telle.

## Qualité, sécurité et typage

- `python -m compileall -q src tests scripts docker installers` : **PASS**.
- `ruff format --check src tests scripts docker installers` : **PASS**, 184 fichiers.
- `ruff check src tests scripts docker installers` : **PASS**.
- `mypy src/openinfra` avec les dépendances runtime : **PASS**, 64 modules source.
- `bandit -q -r src/openinfra` : **PASS**.
- `python scripts/security_gate.py --project-root .` : **PASS**.
- `python scripts/quality_gate.py` : **PASS**.
- `python scripts/native_runtime_smoke.py --project-root .` : **PASS**.
- Six profils d’installation Lite/Pro/Enterprise : **PASS**.
- Alignement Enterprise : **PASS**.
- Architecture POO et séparation domaine/application/infrastructure/interfaces : **PASS**.

## Frontend

- `npm --prefix web run lint` : **PASS**.
- `npm --prefix web run a11y` : **PASS**.
- `npm --prefix web run a11y:jsx` : **PASS**.
- `npm --prefix web test` : **23 PASS**.
- `npm --prefix web run build` : **PASS**, Vite 8.1.4.
- `npm --prefix web audit --audit-level=high` : **0 vulnérabilité**.
- `python scripts/validate_frontend.py --project-root .` : **PASS**.
- Parité React/runtime packagé, responsive, lecteurs d’écran, couleurs forcées et réduction des mouvements : **PASS**.

## CI/CD

Le workflow GitHub Actions conserve les gates existants et intègre le nouveau lot :

- formatage et lint de `src`, `tests`, `scripts`, `docker` et `installers` ;
- compilation Python ;
- typage strict ;
- Bandit et gate de sécurité ;
- tests domaine, services, CLI, HTTP, OpenAPI, web et non-régression SPOF ;
- couverture bloquante à 98 % ;
- lint, accessibilité, tests Node.js, audit npm et build Vite ;
- build wheel/sdist, vérification d’artefact et smoke d’installation du wheel.

## Packaging et smoke tests

- Wheel : `openinfra-0.29.92-py3-none-any.whl` — **PASS**.
  - SHA-256 : `f94cb6c7f609b5c1ccc3611500b6f8f580b329d96004c3abaab99cd97d7cba3a`
- Sdist : `openinfra-0.29.92.tar.gz` — **PASS**.
  - SHA-256 : `75e99be2868b03c5bcb751d7b77bda270503cb63909734b9c4847cfcd630c479`
- Vérification d’artefact incluant le domaine et le service du graphe : **PASS**.
- Installation du wheel dans une cible vierge hors arbre source : **PASS**.
- Version runtime et métadonnées : `0.29.92` — **PASS**.
- Trois points d’entrée console : **PASS**.
- OpenAPI packagé : **PASS**.
- Cinq routes Graphe, six routes Matrice de flux, sept routes Certificats/PKI et six routes Conformité réseau : **PASS**.
- Trois assets web runtime : **PASS**.
- Migrations packagées : **43**, dernière migration `0043_network_config_compliance.sql` — **PASS**.
- Wheel et sdist sans cache, `node_modules`, `web/dist`, couverture ni artefact de build imbriqué : **PASS**.

## CDC, roadmap et migrations

`EPIC-1505` était déjà défini dans la roadmap fournie. L’évolution n’introduit aucune nouvelle exigence fonctionnelle, réglementaire ou architecturale hors de ce périmètre et ne modifie aucun schéma persistant.

- CDC : inchangé et non réémis.
- Roadmap : inchangée et non réémise.
- Migration PostgreSQL : aucune nouvelle migration requise.
- Compatibilité ascendante : routes, commandes et comportements existants préservés.

## Contrôles limités par l’environnement

- `pip-audit --strict --requirement requirements/security-audit.txt` a été lancé mais reste **non concluant** : la résolution DNS de `pypi.org` est indisponible dans le runner.
- Aucun exécutable Docker ou Podman n’est disponible ; la recette Compose n’a pas pu être rejouée.
- Aucun client ni serveur PostgreSQL live n’est disponible ; les 43 migrations, adaptateurs et contrats SQL restent couverts statiquement et par tests simulés.
- Aucun harnais E2E navigateur n’est fourni dans l’environnement ; les contrats DOM/CSS/ARIA, JSX-a11y, tests Node.js et build frontend ont été exécutés.
