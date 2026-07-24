# Runbook — certification du packaging OpenInfra

## Préparer une clé Ed25519

La clé doit être générée et conservée hors du dépôt :

```bash
openssl genpkey -algorithm ED25519 -out openinfra-release-signing.pem
base64 -w 0 openinfra-release-signing.pem
```

La valeur base64 est enregistrée dans le secret GitHub `OPENINFRA_RELEASE_SIGNING_PRIVATE_KEY_B64`.

## Audit certifiant

```bash
export OPENINFRA_RELEASE_SIGNING_PRIVATE_KEY_B64='<base64-du-pem>'
SOURCE_DATE_EPOCH="$(git log -1 --pretty=%ct)"
python scripts/release_packaging_audit.py \
  --project-root . \
  --output-dir artifacts/release-packaging \
  --source-date-epoch "$SOURCE_DATE_EPOCH" \
  --signing-key-from-env \
  --enforce
```

## Audit local non certifiant

```bash
python scripts/release_packaging_audit.py \
  --project-root . \
  --output-dir artifacts/release-packaging-local \
  --source-date-epoch 1700000000 \
  --ephemeral-signing-key
```

Le rapport doit alors contenir `release_packaging_certification=false` et signaler que l'identité de signature est éphémère.

## Construire et vérifier le catalogue autonome des migrations

```bash
SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1700000000}"
python scripts/build_migration_catalog.py \
  --project-root . \
  --output-dir artifacts/migrations \
  --source-date-epoch "$SOURCE_DATE_EPOCH" \
  --json
```

L’archive `openinfra-$(cat VERSION)-migrations.zip` doit contenir exactement 60 fichiers SQL PostgreSQL, 60 fichiers SQL Oracle, `oracle/manifest.json`, `MIGRATIONS-MANIFEST.json` et un README. Le manifeste unifié donne le SHA-256 de chaque migration et les bornes `0001` à `0060`.

## Vérifier les artefacts

```bash
cd artifacts/release-packaging
sha256sum --check "openinfra-$(cat ../../VERSION)-SHA256SUMS.txt"
```

La signature peut être vérifiée avec le module OpenInfra :

```bash
python - <<'PYTHON'
from pathlib import Path
from openinfra.quality.release_packaging import ReleaseSignatureVerifier

version = Path("../../VERSION").read_text(encoding="utf-8").strip()
manifest = Path(f"openinfra-{version}-release-manifest.json")
ReleaseSignatureVerifier.verify(
    manifest.with_suffix(manifest.suffix + ".pub"),
    manifest,
    manifest.with_suffix(manifest.suffix + ".sig"),
)
PYTHON
```

## Rollback applicatif

1. Arrêter les services OpenInfra.
2. Restaurer le wheel ou l'arbre applicatif de la version précédente.
3. Exécuter l'installateur concerné avec `--rollback` lorsque des sauvegardes `.openinfra-rollback` existent.
4. Si une migration de schéma incompatible a été appliquée, restaurer PostgreSQL depuis PITR/sauvegarde cohérente.
5. Redémarrer puis exécuter les sondes `/health`, `/ready` et le smoke fonctionnel.

Exemple hors production :

```bash
python installers/setup/enterprise/server/install.py \
  --rollback \
  --target-root /mnt/openinfra-recovery \
  --json
```
