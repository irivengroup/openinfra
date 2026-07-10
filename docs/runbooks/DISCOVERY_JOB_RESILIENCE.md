# Runbook — Résilience des jobs Discovery

## Objet

Ce runbook couvre l’exploitation de la file persistante des jobs Discovery : diagnostic des baux, reprise après crash, gestion des tentatives, traitement de la DLQ et vérification de l’absence de perte ou de double exécution.

## États opérationnels

| État | Signification | Action attendue |
|---|---|---|
| `queued` | Job prêt à être réservé | Aucune si les collectors consomment normalement |
| `leased` | Job attribué à un worker jusqu’à `leased_until` | Vérifier le heartbeat et renouveler le bail pendant l’exécution |
| `retry-wait` | Échec temporaire, nouvelle tentative planifiée | Examiner `last_error` et `next_attempt_at` |
| `completed` | Résultat validé et empreinte enregistrée | État terminal, aucune relance automatique |
| `dead-letter` | Nombre maximal de tentatives atteint | Diagnostic obligatoire avant rejeu administré |

## Contrôles courants

Lister les jobs en attente :

```bash
openinfra discovery job-list \
  --data /var/lib/openinfra/state.json \
  --tenant default \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --status queued \
  --limit 100
```

Lister la DLQ :

```bash
openinfra discovery job-list \
  --data /var/lib/openinfra/state.json \
  --tenant default \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --status dead-letter \
  --limit 100
```

Consulter un job précis :

```bash
openinfra discovery job \
  --data /var/lib/openinfra/state.json \
  --tenant default \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --job-id "$JOB_ID"
```

## Reprise après crash d’un worker

1. Ne pas modifier manuellement le job.
2. Vérifier `leased_until`, `lease_owner`, `lease_token` et `attempt_count`.
3. Redémarrer ou remplacer le worker.
4. Après expiration du bail, le prochain `job-claim` reprend atomiquement le job et incrémente `lease_token`.
5. Si le bail expiré correspond déjà à la dernière tentative autorisée, le job est basculé atomiquement en `dead-letter` au lieu d’être repris.
6. Vérifier dans l’audit que la reprise contient `reclaimed_after_crash=true` ou que la mise en DLQ automatique est tracée.
7. Toute tentative de terminaison avec l’ancien jeton doit être rejetée.

Exemple de reprise :

```bash
openinfra discovery job-claim \
  --data /var/lib/openinfra/state.json \
  --tenant default \
  --collector-id "$COLLECTOR_ID" \
  --certificate-fingerprint "$COLLECTOR_CERT_SHA256" \
  --worker-id worker-par1-recovery \
  --lease-seconds 120
```

## Renouvellement d’un bail

Le worker doit renouveler le bail avant `leased_until`. Il doit réutiliser exactement le `lease_token` reçu lors de la réservation.

```bash
openinfra discovery job-renew \
  --data /var/lib/openinfra/state.json \
  --tenant default \
  --collector-id "$COLLECTOR_ID" \
  --certificate-fingerprint "$COLLECTOR_CERT_SHA256" \
  --job-id "$JOB_ID" \
  --worker-id "$WORKER_ID" \
  --lease-token "$LEASE_TOKEN" \
  --lease-seconds 120
```

Un refus pour jeton périmé signifie que le job a déjà été repris. Le worker concerné doit abandonner immédiatement son résultat local.

## Déclaration d’échec et DLQ

Déclarer un échec temporaire :

```bash
openinfra discovery job-fail \
  --data /var/lib/openinfra/state.json \
  --tenant default \
  --collector-id "$COLLECTOR_ID" \
  --certificate-fingerprint "$COLLECTOR_CERT_SHA256" \
  --job-id "$JOB_ID" \
  --worker-id "$WORKER_ID" \
  --lease-token "$LEASE_TOKEN" \
  --error "timeout SSH vers la cible" \
  --retry-delay-seconds 60
```

Lorsque `attempt_count` atteint `max_attempts`, le job passe automatiquement en `dead-letter`.

Avant rejeu :

1. qualifier la cause racine ;
2. corriger le collector, le réseau, la cible ou la référence de secret ;
3. confirmer que le périmètre et la cible sont toujours autorisés ;
4. conserver la preuve du diagnostic dans l’outil d’exploitation ;
5. exécuter le rejeu avec un compte `security:admin`.

```bash
openinfra discovery job-replay \
  --data /var/lib/openinfra/state.json \
  --tenant default \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --actor ops-recovery \
  --job-id "$JOB_ID"
```

Le rejeu remet le job en `queued`, réinitialise son compteur de tentatives et conserve la progression du jeton de fencing.

## Terminaison idempotente

Le résultat doit être sérialisé de manière canonique avant calcul de son SHA-256. La même empreinte peut être soumise plusieurs fois ; une empreinte différente pour un job déjà terminé est rejetée.

```bash
openinfra discovery job-complete \
  --data /var/lib/openinfra/state.json \
  --tenant default \
  --collector-id "$COLLECTOR_ID" \
  --certificate-fingerprint "$COLLECTOR_CERT_SHA256" \
  --job-id "$JOB_ID" \
  --worker-id "$WORKER_ID" \
  --lease-token "$LEASE_TOKEN" \
  --result-hash "$RESULT_SHA256"
```

## Vérifications PostgreSQL

La réservation concurrente utilise `FOR UPDATE SKIP LOCKED`. Les requêtes de diagnostic sont en lecture seule :

```sql
SELECT status, count(*)
FROM discovery_jobs
WHERE tenant_id = :tenant_id
GROUP BY status
ORDER BY status;
```

```sql
SELECT id, collector_id, lease_owner, lease_token, leased_until, attempt_count, max_attempts
FROM discovery_jobs
WHERE tenant_id = :tenant_id
  AND status = 'leased'
  AND leased_until < now()
ORDER BY leased_until;
```

Ne jamais mettre à jour directement `status`, `lease_token`, `attempt_count` ou les dates de bail. Utiliser exclusivement le service, la CLI ou l’API afin de préserver les contraintes, le fencing et l’audit.

## Critères de retour à la normale

- aucun bail expiré durablement sans reprise ;
- aucune croissance non expliquée de `dead-letter` ;
- chaque job soumis est présent dans un état terminal ou récupérable ;
- aucun `job_id` n’est traité simultanément avec deux jetons valides ;
- les événements d’audit de claim, retry, DLQ, replay et completion sont présents ;
- les collectors utilisent une empreinte de certificat enregistrée et active.
