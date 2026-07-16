# Rapport de validation — OpenInfra Python POO v0.33.12

## Objet

La version **0.33.12** retire `OPENINFRA_BOOTSTRAP_TOKEN` du contrat `.env` et confie intégralement sa gestion au runtime OpenInfra.

Le jeton est généré par un CSPRNG, conservé dans un volume Docker dédié, lu via un fichier protégé et jamais injecté dans l'environnement d'un conteneur. Les anciens `.env` sont migrés automatiquement et idempotemment.

## Architecture

- Service one-shot `runtime-secrets` exécuté en root uniquement pour initialiser le volume et affecter le propriétaire runtime `10001:10001`.
- Secret stocké dans `/run/openinfra/secrets/bootstrap-token`.
- Répertoire `0700`, fichier `0400`, refus des liens symboliques et validation stricte du format.
- Écriture atomique avec `fsync`, remplacement atomique et nettoyage des temporaires.
- Montages en lecture seule pour `auth-bootstrap`, `openinfra-web` et le smoke runtime.
- Le token persiste lors de `down/up` et est régénéré après `reset --volumes`.
- `EnvFileManager` supprime toute ligne héritée `OPENINFRA_BOOTSTRAP_TOKEN` sans toucher aux autres valeurs.
- Consultation opérateur explicite via `python scripts/docker_environment.py bootstrap-token`.

## Compatibilité

- PostgreSQL reste le backend par défaut.
- Aucune migration SQL ajoutée.
- Aucun endpoint métier ni permission RBAC supprimé.
- Les options CLI `--token-file` et Web `--backend-bearer-token-file` sont intégrées sans exposer le secret au navigateur.
- Le thème et les assets CSS ne sont pas modifiés.

## Validations exécutées

| Contrôle | Résultat |
|---|---:|
| Tests unitaires runtime secrets | 5/5 PASS |
| Contrats Docker runtime et migration `.env` | 13/13 PASS |
| Contrats Web/BFF | 20/20 PASS |
| Test CLI `--token-file` | 1/1 PASS |
| Ruff format | PASS |
| Ruff lint | PASS |
| mypy ciblé | PASS |
| Bandit ciblé | PASS |
| Build wheel et sdist | PASS |
| Installation wheel hors dépôt | PASS |
| Smoke commande `openinfra-runtime-secrets` | PASS |

L'exécution groupée de certains fichiers d'intégration reste sujette aux sous-processus persistants déjà connus dans la base. Les périmètres directement impactés ont donc été exécutés séparément et sont tous verts.

Docker n'est pas disponible dans l'environnement de construction : le démarrage réel des conteneurs n'est pas revendiqué localement. Les contrats Compose et l'orchestration sont couverts par les tests automatisés.
