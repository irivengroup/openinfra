# Services systemd rendus par l'installateur

Les services systemd ne sont pas livrés dans un dossier `deploy/` et ne sont pas déclarés dans `install.ini`. L'installateur les rend selon l'édition et le scope :

- `openinfra.service` : backend et Lite all-in-one.
- `openinfra-web.service` : frontend web Pro/Enterprise.
- `openinfra-agent.service` : agent collector Enterprise.

Les noms de services sont invariants entre éditions. Les ports internes restent gérés par l'installateur : `2006` back/front, `2007` back/agent, `2008` synchronisation cluster.
