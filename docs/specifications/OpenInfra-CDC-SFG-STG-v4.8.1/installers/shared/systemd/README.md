# Services systemd rendus par l'installateur

Les services systemd ne sont pas livrés dans un dossier `deploy/` et ne sont pas déclarés dans `install.ini`. L'installateur les rend selon l'édition et le scope :

- `openinfra.service` : backend et Lite all-in-one.
- `openinfra-web.service` : frontend web Pro/Enterprise.
- `openinfra-agent.service` : agent collector Enterprise.

Les noms de services sont invariants entre éditions. Les ports internes restent gérés par l'installateur : `2006` back/front, `2007` back/agent, `2008` synchronisation cluster.

Toutes les unités utilisent `EnvironmentFile=/etc/openinfra/openinfra.conf`. Ce chemin est volontairement stable pour systemd, mais `/etc/openinfra` est un lien symbolique vers `/opt/openinfra/config`; le fichier réel est donc `/opt/openinfra/config/openinfra.conf`.

Les unités ne doivent pas dépendre du dossier `installers/` après installation. Les migrations backend sont appliquées pendant l'installation depuis `/opt/openinfra/share/migrations/postgresql`, jamais depuis un `ExecStartPre` systemd.
