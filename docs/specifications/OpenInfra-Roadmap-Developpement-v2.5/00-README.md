# OpenInfra — Roadmap de développement 2.5.0

La roadmap 2.5.0 est alignée sur le CDC/SFG/STG 4.12.0 et OpenInfra 0.34.7. Elle conserve les phases P00 à P24 et ajoute un lot prioritaire de complétude contractuelle et d’hygiène du dépôt.

## Incrément P25 prioritaire

- **P25 — Complétude contractuelle et hygiène du dépôt** : registre exhaustif des tests CDC, classification honnête des preuves, résolution des nœuds pytest, couverture des exigences N1, audit contextuel de l’obsolescence et packaging GATE-14.
- **REL-15 — Contractual Completeness** : promotion locale de la version 0.34.7 uniquement avec six contrôles GATE-14, couverture globale minimale de 98 %, artefacts vérifiés et aucune dette active non classifiée.

P25 ferme l’audit demandé après les évolutions prioritaires. Les preuves `partial` et `external` restent explicitement des travaux ou qualifications non équivalents à une validation fonctionnelle complète.

## Références

- CDC actif : `OpenInfra-CDC-SFG-STG-v4.12.0`
- Alignement : `14-alignement-cdc-v4.12.0.csv`
- Release produit : OpenInfra `0.34.7`
- Politique de promotion : `docs/release/contract-completeness-promotion-policy.json`
- Registre : `docs/release/contract-proof-registry-v4.12.csv`
- Seuil de couverture : 98 % minimum

## Validation

```bash
python docs/specifications/OpenInfra-Roadmap-Developpement-v2.5/scripts/validate_roadmap.py
python docs/specifications/OpenInfra-CDC-SFG-STG-v4.12.0/scripts/validate_contract_completeness.py
python scripts/quality_gate.py
```
