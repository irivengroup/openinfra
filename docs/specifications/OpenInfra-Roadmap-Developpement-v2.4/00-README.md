# OpenInfra — Roadmap de développement 2.4.0

La roadmap 2.4.0 est alignée sur le CDC/SFG/STG 4.10.0 et OpenInfra 0.34.5. Elle conserve intégralement les phases P00 à P22 de la roadmap 2.2.0 et ajoute un lot prioritaire transverse consacré au licensing runtime offline.

## Incrément P23 prioritaire

- **P23 — Licence runtime offline Pro/Entreprise** : identité d’installation Ed25519, autorité hors ligne, entitlements liés à l’entreprise et au quota d’hôtes, persistance JSON/PostgreSQL/Oracle, période de grâce de 30 jours, blocage fail-closed, interfaces CLI/API, installateurs, notifications opérateur et qualification GATE-12.
- **REL-13 — Offline Runtime Licensing** : promotion de la version 0.34.5 uniquement avec sept preuves GATE-12, couverture globale minimale de 98 %, artefacts contrôlés et absence de clé privée d’autorité.

P23 est classée prioritaire par rapport à la poursuite normale des phases historiques. Elle ne supprime ni ne replanifie les fonctions déjà engagées : elle ajoute un mécanisme commercial et de sécurité transversal compatible avec les trois backends.

## Références

- CDC actif : `OpenInfra-CDC-SFG-STG-v4.11.0`
- Alignement : `14-alignement-cdc-v4.11.0.csv`
- Release produit : OpenInfra `0.34.5`
- Politique de promotion : `docs/release/offline-runtime-licensing-promotion-policy.json`
- Seuil de couverture : 98 % minimum

## Validation

```bash
python docs/specifications/OpenInfra-Roadmap-Developpement-v2.3/scripts/validate_roadmap.py
python docs/specifications/OpenInfra-CDC-SFG-STG-v4.11.0/scripts/validate_runtime_licensing.py
python scripts/validate_enterprise_alignment.py
```
