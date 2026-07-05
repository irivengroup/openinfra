# OpenInfra — Plan opérationnel 90 jours aligné CDC v4.8.1

## Jours 1 à 15 — Recalage et verrouillage

- Valider la matrice CDC v4.8.1 → roadmap.
- Geler les services systemd canoniques : `openinfra.service`, `openinfra-web.service`, `openinfra-agent.service`.
- Interdire explicitement `ancien service backend obsolète` dans la CI documentaire et packaging.
- Valider les limites Lite/Pro/Entreprise.
- Geler la structure `installers/` hors `src`.

## Jours 16 à 30 — Socle engineering

- Créer repository, CI/CD, conventions, architecture hexagonale et API baseline.
- Créer contrôles qualité : lint, type check, tests, sécurité, packaging et validation docs.
- Démarrer le modèle d’éditions et de feature gates.

## Jours 31 à 45 — Installateurs et install.ini

- Créer les templates `config/install.ini` par scope.
- Implémenter validation stricte des paramètres : FQDN, IP, mask, VIP, gateway, DNS, édition, scope, LVM, PGDATA.
- Ajouter dry-run, plan d’impact, logs, rollback.
- Ajouter installation automatique des dépendances.

## Jours 46 à 60 — Runtime et stockage

- Livrer `openinfra.service`, `openinfra-web.service`, `openinfra-agent.service`.
- Implémenter LVM applicatif `/opt/openinfra/` pour all-in-one/server/web et l’exclure du scope enterprise/agent.
- Implémenter LVM PostgreSQL `/data/openinfra/`.
- Créer symlink `/opt/openinfra/data -> /data/openinfra/`.
- Initialiser PGDATA sous `/data/openinfra/`.

## Jours 61 à 75 — PostgreSQL et migrations

- Ajouter migrations backend versionnées.
- Garantir que seul le backend applique les migrations.
- Livrer PostgreSQL géré mono-nœud puis base HA.
- Ajouter sauvegarde/PITR initiale.

## Jours 76 à 90 — Edition Alpha et validation

- Valider Lite all-in-one minimal.
- Valider Pro server/web séparés minimal.
- Valider Enterprise server/web/agent minimal.
- Exécuter tests packaging, services, install.ini, PGDATA, migrations et édition gates.
