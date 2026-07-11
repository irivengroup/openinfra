# OpenInfra v0.29.95 — Rapport de validation

Date de validation : `2026-07-11`  
Release : `0.29.95`  
Périmètre : P16 / EPIC-1601 — opérations terrain mobiles et synchronisation hors ligne

## Résultat global

La livraison ajoute un parcours complet d'opérations terrain rattaché à **DCIM → Opérations terrain**. Elle couvre la génération de fiches depuis les objets DCIM, l'identification QR/code-barres, les checklists avant/après, les preuves horodatées, les avertissements d'impact, les verrous logiques et la synchronisation hors ligne contrôlée. Les contrats REST, CLI, interface web, persistance JSON et PostgreSQL sont alignés.

- Tests Python collectés et validés : **773 PASS** dans **106 fichiers**.
- Tests unitaires : **315 PASS**.
- Tests d'intégration : **454 PASS**.
- Tests d'architecture : **3 PASS**.
- Tests de performance : **1 PASS**.
- Couverture : **98,0228 %**, soit **25 829 / 26 350** lignes couvertes.
- Seuil bloquant : **98 % PASS**.
- Tests frontend Node.js : **30 PASS**.
- Lint frontend, accessibilité JSX, contrat WCAG 2.2 AA et build Vite : **PASS**.
- Audit npm production : **0 vulnérabilité**.

La suite Python a été exécutée par fragments exhaustifs puis consolidée avec Coverage.py. Les fichiers comportant des parcours CLI longs ont été isolés afin d'éviter la limite d'exécution du runner, sans omettre de test ni de scénario.

## Fonctionnalités validées

- Génération d'une fiche terrain depuis un équipement, rack, câble, alimentation, panneau de brassage ou certificat.
- Résolution de la localisation physique depuis les dépendances DCIM.
- QR/code-barres signé logiquement et comparaison en temps constant.
- Verrou logique idempotent, propriétaire, expiration TTL et libération contrôlée.
- Démarrage, annulation et clôture selon une machine d'états explicite.
- Checklists avant et après intervention avec contrôle des étapes obligatoires.
- Preuves JPEG, PNG, WebP ou PDF, limitées à 2 MiB, décodage Base64 strict et empreinte SHA-256.
- Avertissements issus du graphe RSOT : impact, SPOF, flux déclarés et analyse tronquée.
- Contrôle de redondance électrique A/B du rack avant intervention.
- Paquet hors ligne canonique borné au tenant et au site, expirant et protégé par SHA-256.
- Synchronisation idempotente avec détection des conflits et conservation de la traçabilité.
- Événements critiques publiés dans un outbox transactionnel PostgreSQL.
- Aucune fonction ITSM native : l'orchestration de tickets demeure externe.

## Interfaces

### REST

Dix-sept routes Field Operations sont exposées sous `/api/v1/dcim/field-operations`, couvrant consultation, génération, verrouillage, démarrage, checklist, preuves, paquet hors ligne, synchronisation, clôture, annulation et libération.

Les deux contrats OpenAPI sont validés par un parseur YAML strict refusant les clés dupliquées :

- `docs/api/openapi.yaml` ;
- `docs/specifications/OpenInfra-CDC-SFG-STG-v4.8.1/09-API/OpenAPI/openapi.yaml`.

### CLI

La hiérarchie publique reste rattachée au DCIM :

```bash
openinfra dcim field-generate
openinfra dcim field-show
openinfra dcim field-lock
openinfra dcim field-start
openinfra dcim field-checklist
openinfra dcim field-evidence
openinfra dcim field-offline-package
openinfra dcim field-sync
openinfra dcim field-close
openinfra dcim field-cancel
openinfra dcim field-release
```

### Interface web

- Entrée unique **DCIM → Opérations terrain**.
- Aucun nouveau composant principal dispersé dans le header ou la sidebar.
- Navigation au clavier, libellés, erreurs et états accessibles.
- Formulaires React et portail statique packagé alignés.
- Import de preuves limité aux types et tailles autorisés.
- Affichage des avertissements avant toute transition critique.

## Persistance et migration

- Repository JSON pour l'exploitation locale et les tests déterministes.
- Repository PostgreSQL transactionnel pour la production.
- Migration `0044_field_operations_mobile_offline.sql`.
- Nombre total de migrations packagées : **44**.
- Tables partitionnées et indexées pour fiches, checklists, preuves, verrous, synchronisations et outbox.
- Contraintes de tenant, site, état, unicité et intégrité explicites.
- L'outbox utilise l'horodatage métier `occurred_at` ; le contrôle qualité continue d'imposer `created_at` aux seules requêtes visant `audit_events`.

## CI/CD

Les workflows GitHub Actions vérifient désormais :

- la migration `0044` et le total de 44 migrations ;
- les 17 routes Field Operations dans le wheel installé ;
- les nouveaux modules domaine, application et mapping ;
- les contrats CLI, HTTP, PostgreSQL, OpenAPI et frontend ;
- l'absence de régression du gate de schéma `audit_events` ;
- le build, l'installation isolée et les smoke tests de l'artefact.

## Qualité, sécurité et typage

- `ruff format --check src tests scripts docker installers` : **PASS**.
- `ruff check src tests scripts docker installers` : **PASS**.
- `mypy src/openinfra` : **PASS**, 69 fichiers source.
- `bandit -q -r src/openinfra` : **PASS**.
- `python -m compileall -q src tests scripts docker installers` : **PASS**.
- Validation OpenAPI stricte des deux spécifications : **PASS**.
- `python scripts/security_gate.py --project-root .` : **PASS**.
- `python scripts/quality_gate.py --project-root .` : **PASS**.
- `python scripts/native_runtime_smoke.py --project-root .` : **PASS**.
- `python scripts/validate_enterprise_alignment.py --project-root .` : **PASS**.
- Six profils d'installation Lite/Pro/Entreprise : **PASS**.
- Validation CDC : **PASS**, version 4.8.1, 828 exigences et 628 tests contractuels.
- Validation roadmap : **PASS**, 19 phases, 115 epics, 8 gates et 97 tests.

## Frontend

- `npm --prefix web run lint` : **PASS**.
- `npm --prefix web run a11y` : **PASS**.
- `npm --prefix web run a11y:jsx` : **PASS**.
- `npm --prefix web test` : **30 PASS**.
- `npm --prefix web run build` : **PASS**, Vite 8.1.4.
- `npm --prefix web audit --omit=dev --audit-level=high` : **0 vulnérabilité**.
- `python scripts/validate_frontend.py --project-root .` : **PASS**.
- Parité React/runtime packagé : **PASS**.

## Packaging et smoke tests

- Build wheel `openinfra-0.29.95-py3-none-any.whl` : **PASS**.
- Build sdist `openinfra-0.29.95.tar.gz` : **PASS**.
- Vérification d'artefact : **PASS**.
- Installation du wheel dans une cible vierge hors arbre source : **PASS**.
- Version runtime et métadonnées : `0.29.95` — **PASS**.
- Points d'entrée `openinfra`, `openinfra-api`, `openinfra-web` : **PASS**.
- OpenAPI packagé : **PASS**.
- Routes packagées : 5 Graphe, 6 Matrice de flux, 7 Certificats/PKI, 6 Conformité réseau et **17 Opérations terrain** — **PASS**.
- Quatre assets runtime web : **PASS**.
- Migrations packagées : **44**, dernière migration `0044_field_operations_mobile_offline.sql` — **PASS**.
- Import et exécution du benchmark Graphe depuis le wheel installé : **PASS**.

## CDC et roadmap

L'EPIC-1601 et ses exigences figuraient déjà dans le CDC et la roadmap de référence. L'implémentation ne crée pas de nouvelle exigence fonctionnelle, réglementaire ou architecturale au-delà de ce périmètre planifié. Conformément à la politique de livraison OpenInfra :

- le CDC reste inchangé et n'est pas réémis ;
- la roadmap reste inchangée et n'est pas réémise ;
- la migration PostgreSQL `0044` est incluse dans la livraison applicative ;
- la compatibilité ascendante des interfaces existantes est préservée.

## Contrôles limités par l'environnement

- `pip-audit --strict --requirement requirements/security-audit.txt` est **non concluant** : la résolution DNS de `pypi.org` est indisponible dans le runner.
- Docker et Podman ne sont pas disponibles ; la recette Compose n'a pas pu être exécutée en conteneurs.
- Aucun serveur PostgreSQL live n'est disponible ; la migration, les repositories et les transactions sont validés statiquement et par tests d'intégration simulés.
- Aucun navigateur E2E n'est fourni ; les contrats DOM/CSS/ARIA, JSX-a11y, tests Node.js et build frontend ont été exécutés.
