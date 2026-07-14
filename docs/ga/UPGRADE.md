# Mise à niveau

Version cible : `0.32.8`

## Précontrôles

```powershell
python scripts/docker_environment.py status
curl.exe -f http://127.0.0.1:8080/ready
```

```bash
openinfra version
openinfra database status --root installers/migrations/postgresql
```

Vérifier aussi l’absence de jobs critiques en cours, l’état de la DLQ, le lag du réplica, l’espace disque et le manifeste SHA-256 de la nouvelle release.

## Sauvegarde

Avant toute modification :

- sauvegarder PostgreSQL et vérifier la restauration sur cible isolée ;
- archiver `.env` ou `/opt/openinfra/config` dans un coffre sécurisé ;
- sauvegarder le stockage d’artefacts ;
- conserver le wheel, le sdist, le manifeste et la clé publique de la version courante ;
- enregistrer les versions des images et dépendances externes.

## Déploiement

Mettre à jour le fichier `.env` sans écraser les secrets :

```powershell
python scripts/docker_environment.py init
```

Définir la version cible :

```powershell
python -c "from pathlib import Path; p=Path('.env'); rows=p.read_text(encoding='utf-8').splitlines(); p.write_text('\n'.join('OPENINFRA_IMAGE_TAG=0.32.8' if row.startswith('OPENINFRA_IMAGE_TAG=') else row for row in rows) + '\n', encoding='utf-8')"
```

Arrêter sans supprimer les volumes :

```powershell
docker compose --env-file .env --profile observability down --remove-orphans
```

Reconstruire les images applicatives :

```powershell
docker compose --env-file .env build --no-cache migrate api web
```

Redémarrer :

```powershell
docker compose --env-file .env --profile observability up -d
```

## Validation

```powershell
docker compose --env-file .env --profile observability ps
curl.exe -f http://127.0.0.1:8080/health
curl.exe -f http://127.0.0.1:8080/ready
curl.exe -f http://127.0.0.1:2006/health
python scripts/docker_environment.py validate
```

```bash
openinfra version
openinfra database status --root installers/migrations/postgresql
```

Contrôler également les métriques, les logs, l’authentification, un parcours en lecture, une mutation idempotente et un job asynchrone.

## Retour arrière

Le code et la configuration peuvent revenir à la version précédente uniquement si le schéma reste compatible. Les migrations PostgreSQL sont forward-only : une restauration de schéma exige une sauvegarde ou un PITR cohérent.

Procédure :

1. fermer le trafic ;
2. arrêter la version nouvelle ;
3. restaurer la base si le schéma ou les données l’exigent ;
4. restaurer configuration et artefacts ;
5. redéployer l’image ou le wheel précédent vérifié ;
6. lancer les contrôles de santé et d’intégrité ;
7. documenter l’incident et empêcher une nouvelle promotion avant correction.
