# OpenInfra v0.29.93 — Rapport de validation

Date de validation : `2026-07-10`  
Release : `0.29.93`  
Périmètre : correction OpenAPI, formulaires typés et rangement du Graphe sous RSOT

## Résultat global

La livraison corrige l’erreur ReDoc causée par cinq chemins DCIM dupliqués dans les deux spécifications OpenAPI. Elle généralise les calendriers et la validation anticipée des formulaires, puis replace les parcours Graphe dans le menu RSOT sans modifier les contrats API ni CLI.

- Tests Python collectés et validés : **745 PASS** dans **105 fichiers**.
- Tests unitaires : **299 PASS**.
- Tests d’intégration : **443 PASS**.
- Tests d’architecture : **3 PASS**.
- Couverture : **98,06648990414033 %**, soit **24 041 / 24 515** instructions couvertes.
- Seuil bloquant : **98 % PASS**.
- Tests frontend Node.js : **28 PASS**.
- Lint frontend, accessibilité JSX, contrat WCAG 2.2 AA et build Vite : **PASS**.
- Audit npm production : **0 vulnérabilité**.

La suite Python a été exécutée par fragments isolés puis consolidée avec Coverage.py. Cette segmentation évite le dépassement de la limite d’exécution des parcours CLI monolithiques, sans omettre de fichier ni de scénario.

## Correction OpenAPI et ReDoc

- Suppression des déclarations dupliquées de `/api/v1/dcim/power-devices`, `/api/v1/dcim/power-circuits`, `/api/v1/dcim/cooling-zones`, `/api/v1/dcim/power-reservations` et `/api/v1/dcim/energy-cooling-capacity`.
- Conservation des déclarations les plus récentes et les plus contraintes.
- Validation des deux copies OpenAPI avec un `SafeLoader` YAML qui refuse toute clé de mapping dupliquée.
- Refus d’une racine OpenAPI invalide et des versions non supportées.
- Gate ajouté dans GitHub Actions avant tests et packaging.
- Tests de non-régression sur les documents réels et sur une fixture volontairement invalide.

## Formulaires typés et validation anticipée

- Champs date rendus par `input[type=date]`.
- Champs date et heure rendus par `input[type=datetime-local]`.
- Calendriers natifs intégrés au thème clair/sombre OpenInfra.
- Normalisation des dates en `YYYY-MM-DD` et des horodatages en ISO 8601 UTC avant appel API.
- Validation anticipée et messages accessibles pour : email, téléphone, code postal contextualisé par pays, IPv4, IPv6, CIDR, MAC, nom DNS/FQDN, URL HTTP(S), nombres, JSON, CSV et texte.
- Rejet des caractères de contrôle et bornes de longueur explicites.
- Support des champs texte longs jusqu’à 262 144 caractères afin de préserver les PEM et configurations volumineuses.
- Moteur partagé byte-identique entre le frontend React et le runtime statique packagé.
- Erreurs exposées avec `aria-invalid`, `setCustomValidity` et `reportValidity`.
- Le focus des champs change uniquement la couleur de bordure : aucune augmentation d’épaisseur, aucun halo et aucune translation.

## Navigation RSOT

- Suppression du composant Graphe autonome dans les deux portails.
- Regroupement sous RSOT : `Exploration`, `Analyse d’impact` et `Exports`.
- Maintien des cinq routes `/api/v1/graph/*` et des commandes `openinfra graph ...`.
- Maintien des alternatives textuelles, tableaux SPOF, navigation clavier et exports JSON/CSV/GraphML.

## Qualité, sécurité et typage

- `ruff format --check src tests scripts docker installers` : **PASS**, 186 fichiers.
- `ruff check src tests scripts docker installers` : **PASS**.
- `mypy src/openinfra` : **PASS**, 64 fichiers source.
- `bandit -q -r src/openinfra` : **PASS**.
- `python -m compileall -q src tests scripts docker installers` : **PASS**.
- `python scripts/security_gate.py --project-root .` : **PASS**.
- `python scripts/quality_gate.py --project-root .` : **PASS**.
- `python scripts/native_runtime_smoke.py --project-root .` : **PASS**.
- `python scripts/validate_enterprise_alignment.py --project-root .` : **PASS**.
- Six profils d’installation Lite/Pro/Entreprise : **PASS**.
- Validation CDC : **PASS**, version 4.8.1, 828 exigences et 628 tests contractuels.
- Validation roadmap : **PASS**, 19 phases, 115 epics, 8 gates et 97 tests.

## Frontend

- `npm --prefix web run lint` : **PASS**.
- `npm --prefix web run a11y` : **PASS**.
- `npm --prefix web run a11y:jsx` : **PASS**.
- `npm --prefix web test` : **28 PASS**.
- `npm --prefix web run build` : **PASS**, Vite 8.1.4.
- `npm --prefix web audit --omit=dev --audit-level=high` : **0 vulnérabilité**.
- `python scripts/validate_frontend.py --project-root .` : **PASS**.
- Parité React/runtime packagé : **PASS**.

## Packaging et smoke tests

- Build wheel `openinfra-0.29.93-py3-none-any.whl` : **PASS**.
- Build sdist `openinfra-0.29.93.tar.gz` : **PASS**.
- Vérification d’artefact : **PASS**.
- Installation du wheel dans une cible vierge hors arbre source : **PASS**.
- Version runtime et métadonnées : `0.29.93` — **PASS**.
- Points d’entrée `openinfra`, `openinfra-api`, `openinfra-web` : **PASS**.
- OpenAPI packagé : **PASS**.
- Cinq routes Graphe, six routes Matrice de flux, sept routes Certificats/PKI et six routes Conformité réseau : **PASS**.
- Quatre assets runtime web, dont `openinfra-form-fields.js` : **PASS**.
- Migrations packagées : **43**, dernière migration `0043_network_config_compliance.sql` — **PASS**.

## CDC, roadmap et migrations

Les recommandations modifient des exigences transversales d’interface et de validation. Le CDC et la roadmap sont donc mis à jour et réémis.

- CDC : compléments API/formulaires et intégration du Graphe au périmètre RSOT.
- Roadmap : renforcement de `EPIC-0102`, `EPIC-0104`, `EPIC-0805` et `EPIC-1505` ; ajout de `REQ-00826`, `REQ-00827`, `REQ-00828` et de leurs tests.
- Migration PostgreSQL : aucune nouvelle migration nécessaire.
- Compatibilité ascendante : routes API, commandes CLI, données et migrations existantes préservées.

## Contrôles limités par l’environnement

- `pip-audit --strict --requirement requirements/security-audit.txt` est **non concluant** : la résolution DNS de `pypi.org` est indisponible dans le runner.
- Docker et Podman ne sont pas disponibles ; la recette Compose n’a pas pu être exécutée en conteneurs.
- Aucun serveur PostgreSQL live n’est disponible ; les 43 migrations, adaptateurs et contrats SQL sont validés statiquement et par tests simulés.
- Aucun navigateur E2E n’est fourni ; les contrats DOM/CSS/ARIA, JSX-a11y, tests Node.js et build frontend ont été exécutés.
