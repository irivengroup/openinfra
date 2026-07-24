# Guide API

Version cible : `0.34.21`

## Découverte des contrats

- Swagger UI : `http://127.0.0.1:2006/swagger`
- ReDoc : `http://127.0.0.1:2006/redoc`
- OpenAPI brut : `http://127.0.0.1:8080/openapi.yaml`
- Contrat versionné : `docs/api/openapi.yaml`

Contrôles publics :

- `GET /health`
- `GET /ready`
- `GET /metrics`
- `GET /api/v1/version`

## Authentification

Les opérations protégées utilisent un bearer. Dans le lab Docker, sa valeur est générée dans le volume secret interne et récupérée explicitement :

```bash
OPENINFRA_TOKEN="$(python scripts/docker_environment.py bootstrap-token)"
curl -fsS \
  -H "Authorization: Bearer $OPENINFRA_TOKEN" \
  "http://127.0.0.1:8080/api/v1/dcim/sites?tenant_id=default"
unset OPENINFRA_TOKEN
```

Sous PowerShell :

```powershell
$OpenInfraToken = python scripts/docker_environment.py bootstrap-token
$headers = @{ Authorization = "Bearer $OpenInfraToken" }
Invoke-RestMethod -Uri "http://127.0.0.1:8080/api/v1/dcim/sites?tenant_id=default" -Headers $headers
Remove-Variable OpenInfraToken
```

Le jeton n’est jamais placé dans l’URL ni stocké dans `.env`.

## Pagination et idempotence

Les collections non bornées utilisent un curseur opaque. Le client doit transmettre le curseur retourné sans le décoder ni le modifier. Un curseur est lié au tenant, aux filtres et au tri.

Les mutations rejouables utilisent une clé d’idempotence stable par opération métier. Une clé ne doit pas être réutilisée pour un payload différent.

Exemple de collection : `GET /api/v1/async/jobs`.

## Erreurs

| Code | Sens | Action client |
|---:|---|---|
| 400 | saisie ou payload invalide | corriger la requête |
| 401 | jeton absent, expiré ou invalide | renouveler l’authentification |
| 403 | permission ou périmètre insuffisant | demander le rôle adéquat |
| 404 | ressource inexistante dans le périmètre | vérifier identifiant et tenant |
| 409 | conflit, quota ou état incompatible | relire l’état avant décision |
| 429 | limite de concurrence | appliquer un backoff borné |
| 500 | erreur interne | conserver l’identifiant de corrélation et alerter l’exploitation |
| 503 | dépendance non prête | rejouer avec backoff après vérification `/ready` |

## Exemples vérifiés

Version :

```powershell
curl.exe -fsS http://127.0.0.1:8080/api/v1/version
```

Recherche globale :

```powershell
curl.exe -fsS `
  -H "Authorization: Bearer $OpenInfraToken" `
  "http://127.0.0.1:8080/api/v1/search/global?tenant_id=default&query=firewall&limit=5"
```

Sites DCIM :

```powershell
curl.exe -fsS `
  -H "Authorization: Bearer $OpenInfraToken" `
  "http://127.0.0.1:8080/api/v1/dcim/sites?tenant_id=default"
```

Jobs asynchrones :

```powershell
curl.exe -fsS `
  -H "Authorization: Bearer $OpenInfraToken" `
  "http://127.0.0.1:8080/api/v1/async/jobs?tenant_id=default&limit=100"
```
