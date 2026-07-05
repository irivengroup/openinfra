# Volume 25 — Editions, Packaging, Installateurs et Alignement Entreprise

## 25.1 But du volume

Ce volume formalise les éditions OpenInfra, les règles de packaging, les installateurs, les services systemd, les agents, l'interface web, les quotas, les licences/abonnements, les connecteurs ITSM externes et les critères d'acceptation multi-éditions.

## 25.2 Editions supportées

### OpenInfra Lite

OpenInfra Lite est l'édition monolithique pour petits environnements, lab, POC maîtrisé ou usage local.

Caractéristiques obligatoires :

- profil haute performance : non ;
- architecture : monolithique ;
- profil PostgreSQL : low ;
- séparation backend/frontend : non ;
- clustering PostgreSQL : non ;
- clustering frontend : non ;
- architecture distribuée discovery par agents régionaux : non ;
- clustering agents : non ;
- concurrence multithreading : non ;
- asynchrone : non ;
- autodiscovery local : oui ;
- autodiscovery via agent distant : non ;
- abonnements/licences : non ;
- équipements max : 200 ;
- subnets/VLAN max : 20 ;
- réservations IP/DNS max : 200 ;
- utilisateurs max : 5.

Installateur attendu :

- `openinfra-lite-installer` : installateur all-in-one unique.

Services systemd autorisés :

- `openinfra.service` uniquement pour l'all-in-one Lite.

### OpenInfra Pro

OpenInfra Pro est l'édition de production intermédiaire pour PME, équipes infra ou périmètres datacenter non distribués.

Caractéristiques obligatoires :

- profil haute performance : oui ;
- architecture : backend/frontend séparés ;
- profil PostgreSQL : medium ;
- clustering PostgreSQL : oui en option, désactivé par défaut ;
- clustering frontend : non ;
- architecture distribuée discovery par agents régionaux : non ;
- clustering agents : non ;
- concurrence multithreading : non ;
- asynchrone : oui ;
- autodiscovery local : oui ;
- autodiscovery via agent distant : non ;
- abonnements/licences : oui ;
- connecteurs ITSM externes : oui ;
- équipements max : 5 000 ;
- subnets/VLAN max : 100 ;
- réservations IP/DNS max : 5 000 ;
- utilisateurs max : 100.

Installateurs attendus :

- `openinfra-pro-server-installer` ;
- `openinfra-pro-web-installer` ;
- `openinfra-pro-worker-installer` ;
- `openinfra-pro-db-installer` si PostgreSQL managé par OpenInfra ;
- `openinfra-pro-itsm-connectors-installer` si connecteurs installés séparément.

Services systemd autorisés :

- `openinfra.service` ;
- `openinfra-web.service` ;
- `openinfra-worker.service` ;
- `openinfra-scheduler.service` ;
- `openinfra-connector.service`.

### OpenInfra Entreprise

OpenInfra Entreprise est l'édition grands comptes, multi-sites, multi-régions, très haute volumétrie et architecture distribuée.

Caractéristiques obligatoires :

- profil haute performance : oui ;
- architecture : backend/frontend séparés ;
- profil PostgreSQL : large, conçu pour plus de 10 000 000 000 d'entrées ;
- clustering PostgreSQL : oui en option, désactivé par défaut ;
- clustering frontend : oui ;
- architecture discovery distribuée par agents régionaux : oui ;
- clustering agents : oui ;
- concurrence multithreading : oui ;
- asynchrone : oui ;
- autodiscovery local : oui ;
- autodiscovery via agent distant : oui ;
- abonnements/licences : oui ;
- connecteurs ITSM externes : oui ;
- équipements max : illimité ;
- subnets/VLAN max : illimité ;
- réservations IP/DNS max : illimité ;
- utilisateurs max : illimité.

Installateurs attendus :

- `openinfra-enterprise-server-installer` ;
- `openinfra-enterprise-web-installer` ;
- `openinfra-enterprise-agent-installer` ;
- `openinfra-enterprise-worker-installer` ;
- `openinfra-enterprise-scheduler-installer` ;
- `openinfra-enterprise-db-installer` si PostgreSQL managé par OpenInfra ;
- `openinfra-enterprise-itsm-connectors-installer` ;
- `openinfra-enterprise-observability-installer` ;
- `openinfra-enterprise-ha-installer`.

Services systemd autorisés :

- `openinfra.service` ;
- `openinfra-web.service` ;
- `openinfra-agent.service` ;
- `openinfra-worker.service` ;
- `openinfra-scheduler.service` ;
- `openinfra-connector.service` ;
- `openinfra-exporter.service`.

## 25.3 Règle de nommage systemd

Les noms systemd ne doivent jamais contenir le nom de l'édition.

Interdit :

- `openinfra-lite.service` ;
- `openinfra-pro-server.service` ;
- `openinfra-enterprise-server.service` ;
- `openinfra-proxy.service` ;
- `openinfra-proxy-worker.service`.

Autorisé :

- `openinfra.service` pour le backend API, PostgreSQL géré, les migrations et le monolithe Lite ;
- `openinfra-web.service` pour l'interface web ;
- `openinfra-agent.service` pour les collecteurs de découverte distribués ;
- `openinfra-worker.service` pour les traitements asynchrones ;
- `openinfra-scheduler.service` pour la planification ;
- `openinfra-connector.service` pour les connecteurs externes ;
- `openinfra-exporter.service` pour les métriques.

L'édition active est déterminée par configuration signée, licence/abonnement lorsque applicable et feature gates, jamais par le nom du service.

## 25.4 Agents d'autodiscovery

Les agents sont de simples collecteurs d'informations destinés à alimenter la base centrale via l'API backend. Ils ne sont pas une Source of Truth locale.

Un agent doit :

- être rattaché à une édition Entreprise ;
- posséder une identité forte ;
- communiquer en mTLS avec `backend API` ;
- recevoir ses jobs depuis le backend ;
- publier des observations signées ;
- respecter rate limiting, fenêtres horaires et limites de périmètre ;
- ne jamais écrire directement dans PostgreSQL ;
- ne jamais exposer d'API d'administration non authentifiée ;
- être idempotent, relançable et observable.

## 25.5 Frontend React + Bootstrap 5

Le frontend OpenInfra est une interface web React + Bootstrap 5.

Il doit :

- consommer exclusivement l'API backend ;
- couvrir toutes les fonctionnalités disponibles en CLI lorsque l'utilisateur a les droits requis ;
- ne jamais se connecter directement à PostgreSQL ;
- ne jamais embarquer de logique d'autorisation finale ;
- appliquer RBAC/ABAC côté affichage mais laisser l'autorisation définitive au backend ;
- exposer les modules Source of Truth, DCIM, ITAM, IPAM, Discovery, Dependency Mapping, sécurité, gouvernance, qualité, support constructeur, licences et connecteurs ;
- supporter le mode responsive ;
- utiliser Bootstrap 5 pour layout, composants et cohérence visuelle ;
- respecter accessibilité, pagination, recherche, filtres, exports asynchrones et traces d'audit.

## 25.6 Connecteurs ITSM externes

Les éditions Pro et Entreprise doivent pouvoir se connecter aux solutions ITSM les plus connues, sans intégrer l'ITSM.

Connecteurs minimaux :

- ServiceNow ;
- Jira Service Management ;
- GLPI ;
- Freshservice ;
- Zendesk ;
- Zammad ;
- Redmine ;
- OTRS/Znuny.

Capacités autorisées :

- synchronisation de CI vers ITSM externe ;
- enrichissement de tickets externes avec contexte OpenInfra ;
- lien entre ticket externe et actif OpenInfra ;
- consultation de liens de tickets depuis une fiche actif ;
- webhooks sortants ;
- webhooks entrants validés ;
- mapping de champs ;
- dry-run de synchronisation ;
- reprise sur erreur ;
- audit de synchronisation ;
- limitation de débit ;
- contrôle par RBAC.

Capacités interdites :

- création d'un moteur de tickets natif ;
- gestion de files d'incidents native ;
- moteur SLA de tickets ;
- portail utilisateur support ;
- workflow ITIL de changement intégré ;
- assignation de tickets interne ;
- escalade de tickets interne.

## 25.7 Support constructeur et support tiers

Tout équipement physique doit contenir :

- garantie constructeur ;
- support constructeur initial ;
- dates de début et fin ;
- niveau de service constructeur ;
- identifiant contrat constructeur si disponible ;
- constructeur ;
- source de l'information ;
- preuve ou référence documentaire ;
- statut de validité.

Un support tiers peut être associé, mais il doit être stocké dans une entité distincte et ne doit jamais écraser les détails constructeur.

## 25.8 Feature gates et quotas

Les capacités par édition doivent être pilotées par feature gates déclaratifs.

Les feature gates doivent être :

- versionnés ;
- signés ;
- auditables ;
- testés ;
- lisibles par CLI/API/UI ;
- appliqués côté backend ;
- compatibles avec les migrations ;
- refusés en cas de contournement.

Les quotas doivent être appliqués côté backend, avec messages explicites et audit.

## 25.9 Critères d'acceptation

Le volume est accepté si :

- les trois éditions sont documentées ;
- les quotas sont testables ;
- les services systemd ne contiennent jamais le nom de l'édition ;
- le suffixe `-server` est utilisé pour le backend ;
- le suffixe `-agent` est utilisé pour les collecteurs discovery ;
- l'interface web React + Bootstrap 5 consomme exclusivement l'API ;
- les connecteurs ITSM sont disponibles en Pro et Entreprise ;
- Lite ne contient aucun connecteur ITSM ;
- aucune fonctionnalité ITSM native n'est introduite ;
- support constructeur et support tiers sont séparés ;
- les tests multi-éditions valident la matrice de capacités.

