# Audit de sécurité de release — P18 / EPIC-1802

## Objectif

Le gate de sécurité de release produit une preuve versionnée et bloque toute promotion lorsqu'un contrôle requis échoue, manque ou n'a pas été exécuté. Une exécution locale partielle ne vaut jamais certification de release.

Le rapport final est écrit dans `build/reports/release-security.json`. Les sorties de chaque outil sont conservées dans `build/security-evidence/`, après redaction des secrets connus. Chaque preuve possède une empreinte SHA-256 et le rapport contient un digest global déterministe des résultats.

## Chaîne de confiance du scanner de conteneurs

Les contrôles filesystem et image utilisent Trivy 0.72.0 épinglé par digest OCI `sha256:cffe3f5161a47a6823fbd23d985795b3ed72a4c806da4c4df16266c02accdd6f`. Le tag lisible est conservé avec le digest afin de garantir à la fois traçabilité et immutabilité.

## Contrôles obligatoires

1. `repository-secrets-and-workflows` : secrets committés, durcissement des workflows et séparation dépendances runtime/dev.
2. `sast-bandit` : analyse statique Python.
3. `rbac-authentication-regression` : tests RBAC, authentification locale/externe et refus d'accès.
4. `python-dependency-audit` : dépendances Python connues vulnérables.
5. `frontend-dependency-audit` : dépendances Node avec seuil `moderate`.
6. `container-filesystem-scan` : vulnérabilités, secrets et mauvaises configurations du dépôt.
7. `container-image-scan` : vulnérabilités, secrets et mauvaises configurations de l'image finale.
8. `dynamic-http-security-probe` : sonde HTTP réelle sur API et web démarrés.

La certification `release_security_certification=true` n'est possible que si les huit contrôles sont présents et réussis. Le mode `--offline` produit volontairement un rapport incomplet et non certifiant.

## Préparation du lab Docker

```bash
python scripts/docker_environment.py init
```

Cette commande crée ou met à niveau `.env` avec des permissions `0600`. Elle génère notamment :

- `OPENINFRA_POSTGRES_PASSWORD` ;
- `OPENINFRA_POSTGRES_REPLICATION_PASSWORD` ;
- `OPENINFRA_READ_CONSISTENCY_SECRET` ;
- `OPENINFRA_BOOTSTRAP_TOKEN` ;
- `OPENINFRA_PGADMIN_PASSWORD` ;
- `OPENINFRA_GRAFANA_ADMIN_PASSWORD`.

Les valeurs existantes non vides sont conservées. Les clés absentes ou les secrets obligatoires vides sont complétés atomiquement.

## Exécution complète

```bash
npm ci --prefix web --ignore-scripts --no-audit --no-fund
python -m pip install -e '.[postgresql]'
python -m pip install --requirement requirements/dev.txt
python scripts/docker_environment.py init

docker compose --env-file .env build api
docker compose --env-file .env up -d postgres migrate auth-bootstrap api web

python scripts/release_security_audit.py \
  --project-root . \
  --output build/reports/release-security.json \
  --evidence-dir build/security-evidence \
  --image-ref "openinfra/runtime:$(cat VERSION)" \
  --api-base-url http://127.0.0.1:8080 \
  --web-base-url http://127.0.0.1:2006 \
  --enforce

docker compose --env-file .env down --volumes --remove-orphans
```

Sous PowerShell, remplacer `$(cat VERSION)` par :

```powershell
$version = Get-Content VERSION -Raw
$version = $version.Trim()
```

Puis utiliser `--image-ref "openinfra/runtime:$version"`.

## Sonde DAST

La sonde vérifie au minimum :

- `/health`, `/ready` et `/metrics` sur l'API ;
- refus HTTP `401` d'une route métier protégée sans bearer ;
- `/health` sur le portail web ;
- `X-Content-Type-Options: nosniff` ;
- `Referrer-Policy: no-referrer` ;
- présence d'une Content Security Policy.

Exécution isolée :

```bash
python scripts/security_http_probe.py \
  --api-base-url http://127.0.0.1:8080 \
  --web-base-url http://127.0.0.1:2006
```

## Mode local sans réseau

```bash
python scripts/release_security_audit.py \
  --project-root . \
  --output build/reports/release-security-offline.json \
  --evidence-dir build/security-evidence-offline \
  --image-ref "openinfra/runtime:$(cat VERSION)" \
  --api-base-url http://127.0.0.1:8080 \
  --web-base-url http://127.0.0.1:2006 \
  --offline
```

Ce mode exécute les contrôles locaux disponibles, marque les contrôles réseau `not-run`, fixe `complete=false` et interdit toute certification.

## CI de release

Le workflow `.github/workflows/release-security.yml` s'exécute sur les tags `v*` et manuellement. Il :

- installe les dépendances verrouillées ;
- génère l'environnement privé ;
- construit l'image de release ;
- démarre une topologie DAST réelle ;
- exécute le gate complet avec `--enforce` ;
- collecte les logs et preuves ;
- publie un artefact de sécurité conservé 90 jours ;
- arrête et supprime le lab ;
- échoue si le rapport n'est pas certifié.

## Interprétation du rapport

Champs principaux :

- `release_security_certification` : résultat bloquant global ;
- `complete` : tous les contrôles ont réellement été exécutés ;
- `offline_mode` : indique une exécution non certifiante ;
- `controls` : statut, durée, commande, code retour et empreintes des preuves ;
- `evidence_digest_sha256` : digest global de l'ensemble des résultats ;
- `failures` : liste explicite des contrôles en échec, indisponibles ou non exécutés.

Aucune dérogation silencieuse n'est supportée. Une acceptation de risque doit être traitée dans un processus de gouvernance distinct, documenté et approuvé avant de relancer le gate avec des dépendances ou configurations corrigées.
