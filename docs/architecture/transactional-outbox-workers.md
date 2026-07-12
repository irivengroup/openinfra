# Outbox transactionnelle et workers spécialisés

OpenInfra 0.31.1 complète le périmètre fonctionnel de **P20 / EPIC-2003** sans extraction prématurée en microservices. Le plan de contrôle reste un monolithe modulaire ; la file durable et l’outbox pilotent quatre spécialisations indépendantes — reporting, imports, graphes et RAG — tout en réutilisant les services métier existants et leurs règles d’autorisation.

## Invariants

- La création d’un job, l’événement d’outbox et l’audit sont validés dans la même unité de travail PostgreSQL ou JSON.
- Une clé d’idempotence est unique par tenant.
- Un claim incrémente simultanément le compteur de tentative et le jeton de fencing.
- Seul le détenteur du lease et du jeton courant peut renouveler, terminer ou échouer un traitement.
- Les retries sont bornés ; l’épuisement place le job ou l’événement en DLQ (`dead-letter`).
- Le rejeu d’une DLQ exige `async.admin` et réinitialise le compteur sans remettre le jeton de fencing à zéro.
- Les payloads et résultats volumineux ne sont jamais stockés dans PostgreSQL : seules les métadonnées immuables, le SHA-256, la taille, le type MIME et la clé objet sont persistés.

## États

`queued → leased → completed`

`queued|retry-wait → leased → retry-wait → … → dead-letter`

Un lease expiré peut être repris avec un jeton supérieur. Si la dernière tentative expire, l’élément passe directement en DLQ. Un worker obsolète ne peut donc pas finaliser le travail après reprise.

## Persistance

La migration additive `0054_async_outbox_workers.sql` crée `async_jobs` et `outbox_events`, leurs contraintes, l’unicité d’idempotence et les index de claim, reprise, DLQ et pagination. PostgreSQL utilise `FOR UPDATE SKIP LOCKED` afin que plusieurs workers puissent réclamer des éléments concurrents sans double traitement.

Le backend JSON conserve les mêmes invariants sous verrou réentrant et sauvegarde atomique du document.

## Artefacts

Deux adaptateurs sont fournis :

- `LocalArtifactStore` : stockage content-addressed, écriture temporaire, `fsync`, renommage atomique et contrôle de traversée de chemin ;
- `S3ArtifactStore` : API S3 compatible, AWS Signature V4, HTTPS obligatoire par défaut, métadonnées SHA-256/taille et vérification intégrale à la lecture.

La clé est déterministe : `<tenant>/<purpose>/<préfixe-hash>/<sha256>.<extension>`. Une réécriture du même contenu est idempotente.

## Workers spécialisés

- `reporting` exécute `reporting.async-queue-health` et produit l’état des files ;
- `imports` exécute `imports.dataset` et `imports.bulk-dataset` depuis un artefact source externe ;
- `graph` exécute `graph.traverse`, `graph.impact`, `graph.path`, `graph.spof` et `graph.export` ;
- `rag` exécute `rag.sync-rsot`, `rag.document-import` et `rag.answer-export`.

Chaque worker réclame exclusivement sa spécialisation, lit son payload externalisé, appelle le service métier existant, externalise le résultat, termine le job avec le fencing token courant et génère l’événement d’outbox correspondant. Toute erreur suit le même cycle retry/DLQ sans logique parallèle propre au worker.

Le dispatcher d’outbox publie chaque événement vers un `OutboxPublisher`. Le publisher fichier livré est un sink déterministe pour intégration et reprise locale ; un bus externe peut implémenter le même port sans modifier le domaine.

## Sécurité

Permissions dédiées : `async.read`, `async.submit`, `async.worker`, `async.admin`. Les rôles `async:reader`, `async:operator`, `async:worker` et `async:admin` appliquent le moindre privilège. Aucun secret S3 n’est persisté dans les jobs, audits, fichiers JSON ou réponses API.
