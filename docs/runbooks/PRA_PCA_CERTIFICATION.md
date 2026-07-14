# Certification PRA/PCA — P17 / EPIC-1704

OpenInfra certifie les objectifs de continuité à partir de preuves d'exploitation réelles. La certification ne déclenche jamais de bascule, de restauration ou de promotion automatique : elle évalue des artefacts produits par un exercice contrôlé.

## Périmètre

La certification s'applique aux éditions **Pro** et **Enterprise** disposant d'un plan DR actif. Elle agrège cinq sources JSON immuables :

1. le plan DR OpenInfra retourné par l'API ou la CLI ;
2. le dernier exercice DR représentatif ;
3. la preuve de sauvegarde/restauration ;
4. la preuve PITR (Point-In-Time Recovery, restauration à un instant précis) ;
5. l'attestation d'exécution des procédures PRA/PCA.

Chaque source est hachée en SHA-256. Le manifeste final possède lui-même une empreinte déterministe ; toute modification après assemblage invalide la certification.

## Mesures bloquantes

Le **RPO mesuré** est la valeur la plus défavorable entre le lag de réplication observé pendant l'exercice DR et la perte de données mesurée par le PITR.

Le **RTO mesuré** est la valeur la plus défavorable entre le temps de reprise de l'exercice DR et le temps complet de récupération PITR depuis l'incident.

L'âge de sauvegarde retenu est la valeur la plus défavorable entre la mesure de l'exercice DR et l'âge réel de la sauvegarde au moment de l'incident simulé.

La certification est refusée si une mesure dépasse l'objectif du plan, si une restauration/intégrité/chiffrement/consistance n'est pas vérifiée, si le plan est inactif, si l'exercice DR a échoué ou si une étape de procédure est incomplète.

## Format des preuves

### Sauvegarde et restauration

```json
{
  "backup_id": "pgbackrest-20260714T090000Z",
  "backup_completed_at": "2026-07-14T09:00:00+00:00",
  "restore_started_at": "2026-07-14T10:05:00+00:00",
  "restore_completed_at": "2026-07-14T10:20:00+00:00",
  "restore_verified": true,
  "integrity_verified": true,
  "encryption_verified": true
}
```

### PITR

```json
{
  "incident_at": "2026-07-14T10:00:00+00:00",
  "target_recovery_point_at": "2026-07-14T09:59:30+00:00",
  "recovered_point_at": "2026-07-14T09:59:30+00:00",
  "recovery_started_at": "2026-07-14T10:05:00+00:00",
  "recovery_completed_at": "2026-07-14T10:20:00+00:00",
  "consistency_verified": true
}
```

### Procédures

Le fichier doit contenir `owner`, `approved_by`, `reviewed_at` et exactement les dix étapes définies dans `docs/operations/pra-pca-profile.json`, chacune à `true` pour une certification positive.

## Exécution locale

```bash
python scripts/assemble_pra_pca_evidence.py \
  --profile docs/operations/pra-pca-profile.json \
  --edition enterprise \
  --plan build/pra-pca/dr-plan.json \
  --drill build/pra-pca/dr-drill.json \
  --backup-restore build/pra-pca/backup-restore.json \
  --pitr build/pra-pca/pitr.json \
  --procedures build/pra-pca/procedures.json \
  --output build/pra-pca/evidence.json

python scripts/certify_pra_pca.py \
  --evidence build/pra-pca/evidence.json \
  --output build/pra-pca/certification-report.json \
  --enforce
```

## GitHub Actions

Le workflow `PRA/PCA Certification` est manuel, utilise un environnement protégé et un runner dédié `openinfra-pra-pca`. Les cinq preuves sont injectées via les secrets d'environnement suivants :

- `OPENINFRA_PRA_PCA_PLAN_JSON` ;
- `OPENINFRA_PRA_PCA_DRILL_JSON` ;
- `OPENINFRA_PRA_PCA_BACKUP_RESTORE_JSON` ;
- `OPENINFRA_PRA_PCA_PITR_JSON` ;
- `OPENINFRA_PRA_PCA_PROCEDURES_JSON`.

Le rapport et toutes les preuves hachées sont conservés 90 jours. Un résultat négatif bloque le job avec `--enforce`.

## Sécurité et exploitation

- aucun secret applicatif n'est écrit dans le rapport ;
- les preuves d'entrée doivent être expurgées de tout mot de passe, jeton ou clé privée ;
- aucune commande de promotion, failover ou restauration n'est exécutée par le certificateur ;
- la conservation longue durée doit être réalisée dans le système documentaire/audit approuvé par l'organisation ;
- une nouvelle certification est requise après modification majeure de topologie, objectifs RPO/RTO, politique de sauvegarde ou procédure de reprise.
