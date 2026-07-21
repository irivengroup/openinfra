# OpenInfra CDC/SFG/STG v4.12.0

Le CDC 4.12.0 est la référence contractuelle consolidée pour OpenInfra Lite, Pro et Entreprise. Il conserve les exigences fonctionnelles et techniques de la version 4.11.0, maintient la licence runtime offline et la canonicalisation RSOT, puis ajoute une gouvernance exhaustive des preuves de validation.

## Incrément contractuel 4.12

- `REQ-00861` impose un registre exhaustif des tests du CDC.
- Chaque test est classé `automated`, `partial` ou `external` sans assimilation des preuves partielles ou externes à une validation fonctionnelle complète.
- Les preuves automatisées référencent des nœuds pytest réels et résolus.
- Les exigences N1 restent toutes classifiées et traçables.
- GATE-14 bloque REL-15 lorsqu’un test, une preuve, un fichier d’évidence ou un contrôle d’hygiène manque.
- Le scanner d’obsolescence ignore uniquement les fichiers qui définissent les règles de détection elles-mêmes ; les sources produit restent intégralement contrôlées.

## Principes invariants

- Clean Architecture, DDD, monolithe modulaire et API-first.
- PostgreSQL comme source transactionnelle principale ; Oracle uniquement pour l’édition Enterprise.
- Aucun ITSM intégré ; connecteurs ITSM externes uniquement.
- Services canoniques : `openinfra.service`, `openinfra-web.service`, `openinfra-agent.service`.
- Installateurs sous `installers/`, configuration `config/install.ini`, migrations pilotées par le backend.
- Données PostgreSQL sous `/data/openinfra/`, avec `/opt/openinfra/data -> /data/openinfra/` et `PGDATA` dimensionné selon l’édition.
- Authentification locale Lite ; LDAP/IPA et RBAC groupe pour Pro/Entreprise.
- Frontend React + Bootstrap 5, accessible WCAG 2.2 AA et consommant exclusivement les API.
- Seuil de couverture globale strictement supérieur ou égal à 98 %.

## Documents d’entrée

- [Delta v4.12](00-Delta-v4.12.md)
- [Delta v4.11 historique](00-Delta-v4.11.md)
- [Index général](00-Index-general.md)
- [Exigences](11-Matrices/Exigences.csv)
- [Tests](11-Matrices/Tests.csv)
- [Traçabilité](11-Matrices/Traceabilite.csv)
- [Matrice GATE-14](11-Matrices/Matrice-completude-contractuelle-v4.12.csv)

## Validation

```bash
python docs/specifications/OpenInfra-CDC-SFG-STG-v4.12.0/scripts/validate_docs.py
python docs/specifications/OpenInfra-CDC-SFG-STG-v4.12.0/scripts/validate_runtime_licensing.py
python docs/specifications/OpenInfra-CDC-SFG-STG-v4.12.0/scripts/validate_rsot_canonical.py
python docs/specifications/OpenInfra-CDC-SFG-STG-v4.12.0/scripts/validate_contract_completeness.py
python scripts/quality_gate.py
```
