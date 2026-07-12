# Runbook — workers asynchrones et outbox

## Configuration

Mode local :

```ini
OPENINFRA_ASYNC_ARTIFACT_BACKEND=filesystem
OPENINFRA_ARTIFACT_ROOT=/data/openinfra/artifacts
```

Mode S3 compatible :

```ini
OPENINFRA_ASYNC_ARTIFACT_BACKEND=s3
OPENINFRA_S3_ENDPOINT=https://objects.example.tld
OPENINFRA_S3_BUCKET=openinfra-artifacts
OPENINFRA_S3_REGION=eu-west-3
OPENINFRA_S3_ACCESS_KEY=<injecté par le gestionnaire de secrets>
OPENINFRA_S3_SECRET_KEY=<injecté par le gestionnaire de secrets>
OPENINFRA_S3_VERIFY_TLS=true
OPENINFRA_S3_TIMEOUT_SECONDS=30
```

Les identifiants doivent provenir du gestionnaire de secrets ou de l’environnement systemd. Ne jamais les écrire dans `openinfra.conf` distribué, un dépôt Git ou une image.

## Exploitation

Déposer un artefact source puis soumettre un traitement :

```bash
openinfra async artifact-put --backend postgresql --tenant default \
  --admin-token "$OPENINFRA_TOKEN" --actor operator \
  --file inventory.csv --purpose imports-source --media-type text/csv

openinfra async job-submit --backend postgresql --tenant default \
  --admin-token "$OPENINFRA_TOKEN" --specialization imports \
  --operation imports.dataset --idempotency-key import-20260712-01 \
  --payload-file import-request.json
```

Exécuter une itération de worker puis une publication d’outbox :

```bash
openinfra async worker-run-once --backend postgresql --tenant default \
  --admin-token "$OPENINFRA_TOKEN" --specialization imports --worker-id imports-01
openinfra async outbox-dispatch-once --backend postgresql --tenant default \
  --admin-token "$OPENINFRA_TOKEN" --worker-id outbox-01 \
  --output-directory /var/lib/openinfra/outbox-published
```

Consulter l’état :

```bash
openinfra async metrics --backend postgresql --tenant default --admin-token "$OPENINFRA_TOKEN"
openinfra async jobs --backend postgresql --tenant default --admin-token "$OPENINFRA_TOKEN" --status dead-letter
openinfra async outbox-events --backend postgresql --tenant default --admin-token "$OPENINFRA_TOKEN" --status dead-letter
```

## Reprise

1. Vérifier l’expiration du lease et l’identité du worker.
2. Ne jamais modifier manuellement `lease_token`.
3. Corriger la cause du défaut.
4. Rejouer uniquement une DLQ avec `job-replay` ou `outbox-replay` et un rôle `async:admin`.
5. Contrôler les audits `async.*`, les métriques et l’artefact produit.

## Sauvegarde et restauration

Sauvegarder ensemble `async_jobs`, `outbox_events`, `audit_events` et le stockage d’artefacts. Après restauration, lancer les workers avec de nouveaux identifiants ; les leases expirés seront repris avec un jeton de fencing supérieur. Ne jamais purger un événement non terminé. Les artefacts orphelins ne peuvent être supprimés qu’après comparaison avec toutes les références persistées et une période de rétention validée.

## Alertes recommandées

- croissance continue de `dead-letter` ;
- plus ancien `queued` ou `retry-wait` au-delà du SLO ;
- leases expirés récurrents pour un même worker ;
- taux de retry élevé ;
- échec S3, divergence SHA-256 ou indisponibilité du bucket ;
- backlog outbox non publié.

## Spécialisations et rôles

| Spécialisation | Opérations | Rôle recommandé |
|---|---|---|
| `reporting` | `reporting.async-queue-health` | `async:reporting-worker` |
| `imports` | `imports.dataset`, `imports.bulk-dataset` | `async:import-worker` |
| `graph` | `graph.traverse`, `graph.impact`, `graph.path`, `graph.spof`, `graph.export` | `async:graph-worker` |
| `rag` | `rag.sync-rsot`, `rag.document-import`, `rag.answer-export` | `async:rag-worker` |

Exécuter chaque spécialisation avec une identité de service distincte. Ne pas partager les tokens workers entre processus ni leur attribuer le rôle `admin`.
