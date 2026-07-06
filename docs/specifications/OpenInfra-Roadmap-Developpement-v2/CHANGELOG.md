## v2 / OpenInfra 0.29.19

- Renommage transversal ITRM : CLI/API/RBAC/frontend primaires en `itrm`, alias `ri` et `sot` compatibles et dépréciés progressivement.
- Ajout de la validation des alertes dashboard contextuelles : suppression de l’alerte succès permanente `Backend prêt` sur l’accueil.

## v2 / OpenInfra 0.29.19

- Ajout `TST-P08-WEB-COMPONENT-STATS` : validation du dashboard d’accueil avec métriques et camemberts par composant.

# CHANGELOG — OpenInfra Roadmap

## v2.0.0

- Alignement sur OpenInfra CDC/SFG/STG v4.8.1 corrigé.
- Ajout des phases dédiées éditions, installateurs, systemd, LVM/PGDATA, LDAP/IPA, multisite et synchronisation quasi temps réel.
- Mise à jour des releases macro.
- Ajout de 114 epics.
- Ajout de la matrice `14-alignement-cdc-v4.8.1.csv`.
- Ajout du plan de livraison par édition.
- Ajout du plan installateurs par scope.
- Ajout du plan LVM/PGDATA par édition.
- Correction explicite : `openinfra.service` remplace tout modèle `ancien service backend obsolète`.
- Ajout des validations spécifiques à `install.ini`, PGDATA `/data/openinfra/` et tailles par édition.

## v1.0.0

- Roadmap initiale alignée CDC v4.0.0.

## 0.29.14

- P09 initialisée par ITRM Quality & Certification.
- Ajout du pilotage qualité/certification ITRM dans CLI, API et dashboard web.
- Ajout de la permission `itrm.quality.read` et des audits `itrm.quality.*`.

## 0.29.15

- P08 renforcé : `openinfra-web` adopte le thème Bootstrap 5 Dashboard et le header principal unique adapté aux domaines OpenInfra.
- Bootstrap 5 est servi localement dans le domaine présentation/rendering, sans CDN runtime.
- Ajout du test roadmap de parité UI Bootstrap/API-only.

## 0.29.16

- P08 web renforcé : formulaires métier typés sans champ générique Attributs.
- Navigation sidebar en accordéons avec transitions fade ; suppression du menu d'opérations interne.
- Trust `openinfra-web` ↔ backend server-side ; aucun token API demandé à l'opérateur.
- Cible `install.ini` `[web_database]` ajoutée pour les références DSN/credentials PostgreSQL du service web.
