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

## Delta v0.29.14 — RI Quality & Certification

La phase P09 ajoute la certification qualité RI : score par objet, synthèse tenant, détection des attributs obligatoires manquants, fraîcheur, source non autoritative, RBAC `ri.quality.read`, audit `ri.quality.*`, API `/api/v1/ri/quality/*` et commandes CLI `openinfra ri quality-*`.

## Delta v0.29.15 — openinfra-web Bootstrap 5 Dashboard Theme

Le portail `openinfra-web` adopte le thème officiel Bootstrap 5 Dashboard comme base de rendu et le header principal unique Bootstrap adapté aux domaines OpenInfra. Les items génériques du template sont remplacés par les domaines opérationnels réels : Dashboard, RI, IPAM, DCIM, Discovery et Sécurité/RBAC/Audit.

Les assets Bootstrap 5 sont servis localement depuis `src/openinfra/interfaces/rendering/static/assets/bootstrap.min.css`. Aucun CDN externe n'est requis au runtime, ce qui préserve la politique CSP stricte, l'exploitation offline et l'absence d'exposition de secrets.

Le dashboard reste API-only : le navigateur consomme uniquement `/api/*` via `openinfra-web`, sans accès direct à PostgreSQL, sans DSN, sans secret backend et sans lecture du fichier runtime `openinfra.conf`.
## Delta v0.29.16 — openinfra-web formulaires métier, trust server-side et accordéons

Le portail `openinfra-web` ne doit plus afficher un champ générique `Attributs` ni demander un token API technique à l'opérateur. Chaque formulaire web présente les variables métier attendues par l'API/CLI : numéro de série, constructeur, modèle, site, bâtiment, salle, ligne, colonne, rack, IP de management, source autoritative, tags, scopes collector, empreinte certificat, etc.

La navigation latérale devient le point de pilotage principal : `Dashboard` reste une entrée directe, tandis que RI, IPAM, DCIM, Discovery et Sécurité/RBAC/Audit sont des accordéons avec transitions `fade`. Les opérations anciennement affichées dans une zone de menu interne à la page sont déplacées dans ces accordéons et le menu interne est supprimé. L'UI ne doit pas afficher les méthodes HTTP aux opérateurs.

Le trust `openinfra-web` ↔ backend est server-side : le navigateur ne transmet pas de token technique et `openinfra-web` ne relaie pas l'en-tête `Authorization` venant du navigateur. Les références DSN/credentials PostgreSQL propres au service web sont déclarées dans `[web_database]`, matérialisées dans `/opt/openinfra/config/openinfra.conf`, et jamais exposées au navigateur.

