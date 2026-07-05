# Delta v4.8.0 — Configuration installateur `./config/install.ini`

## Décision

Chaque dossier d'installation OpenInfra doit embarquer un fichier de configuration canonique `./config/install.ini`.
Ce fichier est l'unique point d'ajustement opérateur pour les paramètres dépendant du serveur, du site, du réseau, de l'édition et du scope.

## Règles obligatoires

- Le fichier doit être localisé dans `installers/<edition>/<scope>/config/install.ini`.
- Le fichier doit exister pour chaque installateur livré.
- L'installateur doit refuser tout démarrage sans fichier `install.ini` valide.
- L'opérateur ne modifie pas les scripts d'installation pour adapter le serveur.
- L'installateur doit fournir une commande de validation et une commande de dry-run.
- Les secrets en clair sont interdits dans `install.ini`.
- Les valeurs sensibles sont référencées via Vault, SOPS, variable d'environnement ou fichier protégé.
- Le backend canonique reste `openinfra.service`.
- Le frontend reste `openinfra-web.service`.
- Les agents de discovery restent `openinfra-agent.service`.
- Le scope backend/server applique toutes les migrations backend.
- Les scopes web et agent ne doivent jamais appliquer de migrations.

## Paramètres serveur attendus

Le fichier doit permettre de renseigner ou surcharger :

- FQDN ;
- IP ;
- masque ;
- VIP ;
- passerelle ;
- DNS ;
- site ;
- région ;
- rôle du nœud ;
- mode cluster ;
- mode réplication ;
- stockage applicatif ;
- stockage PostgreSQL ;
- authentification LDAP/IPA pour Pro/Entreprise ;
- endpoint API pour le frontend ;
- endpoint central pour les agents.

## Acceptation

L'exigence est acceptée si tous les dossiers `installers/<edition>/<scope>/` livrés contiennent `config/install.ini`, si la validation échoue proprement en cas de valeur incohérente et si les tests vérifient les profils Lite, Pro et Entreprise.
