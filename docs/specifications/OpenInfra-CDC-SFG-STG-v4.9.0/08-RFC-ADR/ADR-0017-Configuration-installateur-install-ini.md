# ADR-0017 — `install.ini`, configuration runtime canonique et verrou d'installation

## Statut

Accepté.

## Contexte

Les éditions OpenInfra Lite, Pro et Entreprise comportent plusieurs scopes d'installation. Les paramètres varient selon le serveur, le site, la topologie réseau, le mode cluster, le stockage et les intégrations. Un opérateur ne doit pas modifier les scripts ni posséder une expertise approfondie des composants HA pour installer OpenInfra.

Le dossier `installers/` est nécessaire au bootstrap, mais il ne doit pas devenir une dépendance runtime des services OpenInfra après installation.

## Décision

Chaque dossier `installers/setup/<edition>/<scope>/` contient un fichier `install.ini`. Ce fichier constitue le contrat de configuration opérateur d'installation. Les scripts d'installation sont génériques et déterministes.

Après installation, les paramètres utiles issus de `install.ini` et du fichier `.env` sont matérialisés dans `/opt/openinfra/config/openinfra.conf`. Le chemin `/etc/openinfra` est un lien symbolique vers `/opt/openinfra/config`; `/etc/openinfra/openinfra.conf` est donc un chemin compatible vers le fichier réel.

L'installateur crée le verrou masqué `/opt/openinfra/config/.openinfra-installed.lock` après une installation réussie. Les migrations backend sont copiées dans `/opt/openinfra/share/migrations/postgresql`.

## Conséquences positives

- Installation plus simple.
- Automatisation plus fiable.
- Meilleure traçabilité.
- Réduction des erreurs humaines.
- Validation avant changement système.
- Même logique pour Lite, Pro et Entreprise.
- Suppression de la dépendance runtime au dossier `installers/`.
- Chemin compatible `/etc/openinfra` sans seconde source de vérité.
- Protection contre les réinstallations accidentelles.

## Contraintes

- Le schéma `install.ini` doit être versionné.
- Les validations doivent être strictes.
- Les secrets en clair sont interdits.
- Les templates doivent être maintenus avec les installateurs.
- Les tests doivent couvrir chaque édition et scope.
- Les unités systemd doivent utiliser `EnvironmentFile=/etc/openinfra/openinfra.conf`.
- Les écritures runtime doivent cibler `/opt/openinfra/config`.
- Toute réinstallation contrôlée nécessite sauvegarde, validation et rollback explicites.
