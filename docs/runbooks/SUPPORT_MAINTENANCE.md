# Runbook support, maintenance et cycle de vie

## Objectif

Ce runbook rend opérationnel EPIC-1806. Il décrit la qualification d’un incident, l’escalade, la préparation d’un patch, la maintenance planifiée, la migration et la production de la preuve `support-readiness` consommée par GATE-07. Les objectifs de temps sont stockés dans `docs/release/support-maintenance-policy.json` afin d’être contrôlés automatiquement et révisés de manière traçable.

## Qualification d’un incident

1. Identifier l’édition, la version, l’environnement et le périmètre affecté.
2. Vérifier `/health`, `/ready`, `/metrics`, PostgreSQL, PgBouncer et les workers.
3. Collecter des logs bornés, horodatés et expurgés.
4. Classer S1 à S4 selon impact, urgence, contournement et intégrité.
5. Assigner un propriétaire et l’heure de prochaine mise à jour.
6. Escalader immédiatement tout risque de sécurité, perte de données ou panne multi-site.

```powershell
openinfra version
docker compose --env-file .env --profile observability ps
docker compose --env-file .env logs --tail=200 postgres pgbouncer-primary migrate api web
curl.exe -f http://127.0.0.1:8080/health
curl.exe -f http://127.0.0.1:8080/ready
curl.exe -f http://127.0.0.1:8080/metrics
```

## Escalade

L1 assure l’accueil, la vérification des prérequis et la collecte. L2 prend les défauts reproductibles, les migrations et les contournements. L3 regroupe engineering, SRE et sécurité pour les défaillances complexes. Le rôle incident-command est obligatoire pour S1 Enterprise, impact multi-clients, suspicion d’exfiltration ou publication d’un avis de sécurité. Les décisions sont consignées avec heure UTC, auteur, action et preuve.

## Préparation d’un patch

Un patch doit partir d’une branche supportée, conserver la compatibilité ascendante et contenir un test de non-régression. La livraison inclut wheel, sdist, archive source, SBOM, checksums, signatures, rapport de sécurité et commandes Compose. Les scans de dépendances, Bandit, Ruff, mypy, couverture, tests frontend et smoke du wheel installé sont bloquants. Un correctif de sécurité doit aussi indiquer les versions affectées, la mitigation et les conditions de mise à niveau.

## Maintenance planifiée

Avant la fenêtre, vérifier la sauvegarde, le point de restauration, l’espace disque, le tag d’image et le plan de rollback. Arrêter la stack sans supprimer les volumes, construire les images, appliquer les migrations puis démarrer les services. Ne jamais utiliser `--volumes` pendant une mise à niveau normale.

```powershell
docker compose --env-file .env --profile observability down --remove-orphans
docker compose --env-file .env build --no-cache migrate api web
docker compose --env-file .env --profile observability up -d
docker compose --env-file .env --profile observability ps
```

La validation post-maintenance contrôle la version exécutée, les endpoints, les migrations, l’authentification, un parcours web et un traitement asynchrone. En cas d’échec, arrêter la progression, conserver les preuves, restaurer selon le plan approuvé et ne pas modifier manuellement le schéma.

## Migration et rollback

Une montée N-1 vers N est directe. N-2 vers N est réalisée en deux étapes avec validation intermédiaire. Une version plus ancienne nécessite un plan spécifique. La sauvegarde et le rollback sont obligatoires. Le rollback applicatif n’est autorisé que si le schéma reste compatible ; sinon une restauration PostgreSQL ou PITR validée est requise. Les procédures détaillées se trouvent dans `docs/ga/UPGRADE.md` et `docs/ga/DISASTER_RECOVERY.md`.

## Production de la preuve support-readiness

Pour une validation locale signée avec une clé éphémère :

```powershell
python scripts/support_readiness.py `
  --project-root . `
  --output artifacts/ga/evidence/support-readiness.json `
  --ephemeral-key `
  --enforce
```

Pour une release officielle, fournir une clé Ed25519 d’organisation avec `--signing-key` ou la variable `OPENINFRA_RELEASE_SIGNING_PRIVATE_KEY_B64`. Le rapport, sa signature et la clé publique doivent être conservés avec les autres preuves GATE-07. Une clé éphémère valide l’intégrité technique mais ne remplace pas la politique de confiance de promotion.

## Revue périodique

La politique est revue à chaque version mineure, après incident S1, après changement réglementaire, après modification des canaux de support et au minimum tous les six mois. Toute modification des objectifs doit mettre à jour le JSON, la documentation, les tests, la CI et la preuve signée.
