# Mise à niveau

Version cible : `0.34.2`

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

La version de l’image applicative est résolue automatiquement depuis `VERSION` par `scripts/docker_environment.py`, qui génère un override Compose temporaire et le supprime après exécution. Aucune clé `OPENINFRA_IMAGE_TAG` ne doit être ajoutée au `.env`.

Arrêter sans supprimer les volumes :

```powershell
python scripts/docker_environment.py down
```

Reconstruire et redémarrer avec les valeurs runtime internes :

```powershell
python scripts/docker_environment.py up
```

## Validation

```powershell
python scripts/docker_environment.py status
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
