# Promotion REL-15 — GATE-14

## Objet

GATE-14 qualifie la complétude contractuelle d’OpenInfra 0.34.27. Il ne transforme pas une preuve documentaire ou une qualification à exécuter sur infrastructure réelle en validation fonctionnelle complète.

## Commande

```bash
openinfra-gate14 \
  --project-root . \
  --candidate-id openinfra-0.34.27-candidate \
  --source-commit "$(git rev-parse HEAD)" \
  --output artifacts/gate14-report.json \
  --enforce
```

## Contrôles

1. `CDC-TRACEABILITY` : CDC 4.12.0, 861 exigences, 667 tests et 861 traces.
2. `ROADMAP-ALIGNMENT` : roadmap 2.5.0, P25, REL-15, EPIC-2501 à EPIC-2504 et GATE-14.
3. `PROOF-REGISTRY` : classification exhaustive et métriques exactes.
4. `PYTEST-AUTOMATION` : 35 preuves automatisées et 48 sélecteurs pytest résolus.
5. `EVIDENCE-CLASSIFICATION` : 584 preuves partielles, 48 externes, 83 fichiers distincts et aucune exigence N1 non classifiée.
6. `REPOSITORY-HYGIENE` : sources actives, packaging, secrets, alias et chemins obsolètes contrôlés.

## Interprétation

- `automated` signifie qu’un test pytest réel est directement rattaché au test contractuel.
- `partial` signifie qu’une partie de l’acceptation est couverte ou qu’une preuve statique existe ; le reste demeure à vérifier.
- `external` signifie qu’une plateforme réelle, un tiers ou une charge représentative est indispensable.

La promotion production reste NO-GO tant que les preuves externes requises ne sont pas exécutées et associées au véritable commit de publication.

## Résilience du pipeline et artefacts de diagnostic

Le toolchain de qualité est déterministe : Ruff `0.15.22` et mypy `2.2.0` sont installés depuis `requirements/dev.txt`, puis contrôlés par `scripts/validate_quality_toolchain.py` avant toute analyse.

Les étapes `Ruff format check`, `Ruff lint`, `Strict typing` et `Python bytecode compilation` sont séparées. Les trois premières écrivent leurs journaux sous `artifacts/quality/` avec `set -o pipefail`, de sorte que la journalisation ne transforme jamais un échec en succès.

En cas d’échec avant la production du rapport ou des distributions, le workflow publie `openinfra-gate14-diagnostics-<run-id>` avec le contexte CI et les journaux disponibles. L’absence de `dist/` ou de `web/dist/` n’ajoute pas une seconde erreur. L’artefact immuable final reste, lui, strictement limité aux exécutions réussies et conserve `if-no-files-found: error`.
