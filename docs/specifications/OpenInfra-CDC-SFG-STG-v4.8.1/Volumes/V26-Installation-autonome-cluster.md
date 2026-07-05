# Volume 26 — Installation autonome, cluster bootstrap, dépendances et migrations

## 1. Objectif

OpenInfra doit disposer d'installateurs industriels capables d'installer chaque édition et chaque scope sans exiger une expertise cluster de l'opérateur.

L'installateur doit transformer un inventaire réseau minimal en installation complète, validée, observable et exploitable.

## 2. Entrées opérateur minimales

Pour un mode cluster, l'opérateur fournit uniquement :

- FQDN de chaque nœud ;
- IP de chaque nœud ;
- masque réseau ;
- VIP du cluster concerné ;
- passerelle ;
- DNS primaire ;
- DNS secondaire si disponible.

Les autres éléments sont générés, calculés, installés ou validés automatiquement par l'installateur : comptes techniques, certificats internes, secrets locaux, règles firewall, services systemd, dépendances OS, configuration HA, poolers, health checks, bootstrap PostgreSQL, migrations, rapports et rollback.

## 3. Structure obligatoire des installateurs

Dans le dépôt logiciel cible, les installateurs doivent être situés hors de `src/` :

```text
openinfra/
├── src/
│   └── openinfra/
├── migrations/
│   └── versions/
├── installers/
│   ├── lite/
│   │   └── all-in-one/
│   ├── pro/
│   │   ├── server/
│   │   └── web/
│   ├── enterprise/
│   │   ├── server/
│   │   ├── web/
│   │   └── agent/
│   └── shared/
│       ├── dependencies/
│       ├── systemd/
│       ├── migrations/
│       ├── network/
│       ├── security/
│       └── validation/
```

Cette séparation évite de mélanger le code applicatif avec le packaging, le bootstrap système, les scripts de cluster et les assets d'exploitation.

## 4. Installateurs par édition et scope

### OpenInfra Lite

Un seul installateur suffit :

- `installers/setup/lite/`

Il installe un mode monolithique local, sans cluster backend, sans cluster frontend, sans agent distant, sans asynchronisme distribué.

### OpenInfra Pro

Installateurs obligatoires :

- `installers/setup/pro/server/`
- `installers/setup/pro/web/`

Le backend peut utiliser PostgreSQL standalone ou PostgreSQL cluster optionnel. Le frontend est séparé et consomme l'API backend.

### OpenInfra Entreprise

Installateurs obligatoires :

- `installers/setup/enterprise/server/`
- `installers/setup/enterprise/web/`
- `installers/setup/enterprise/agent/`

L'édition Entreprise supporte le clustering backend, frontend, PostgreSQL et agents d'auto discovery.

## 5. Installation automatique des dépendances

Chaque installateur doit :

- détecter la distribution Linux ;
- vérifier la version minimale supportée ;
- configurer les dépôts nécessaires ;
- installer les paquets OS ;
- installer les runtimes ;
- installer les composants HA selon le scope ;
- configurer SELinux ou AppArmor sans désactivation globale ;
- configurer firewalld, nftables ou équivalent ;
- activer les services systemd ;
- vérifier les versions installées ;
- produire un rapport de conformité.

Si une dépendance critique ne peut pas être installée, l'installation doit s'arrêter avant toute modification destructive et produire une erreur explicite.

## 6. Backend et migrations

L'installateur backend `server` doit déployer toutes les migrations applicatives et base de données.

Exigences :

- migrations versionnées ;
- migrations rejouables ;
- migrations idempotentes lorsque possible ;
- verrou applicatif de migration ;
- sauvegarde ou snapshot avant migration critique ;
- exécution dans l'ordre strict ;
- contrôle du schéma final ;
- journal de migration ;
- rollback documenté ;
- blocage du démarrage backend si migration incomplète ;
- rapport de preuve.

Le frontend et l'agent ne doivent jamais appliquer de migrations base de données.

## 7. Bootstrap cluster autonome

Le mode cluster doit configurer automatiquement :

- réseau local du cluster ;
- VIP ;
- bascule VIP ;
- health checks ;
- HAProxy ou équivalent ;
- PgBouncer si PostgreSQL est géré ;
- Patroni si PostgreSQL cluster est géré ;
- etcd ou Consul si requis ;
- certificats TLS internes ;
- services systemd ;
- probes applicatives ;
- routage lecture/écriture ;
- rapports de validation.

## 8. Frontend React + Bootstrap 5

Le frontend doit être installé comme interface web indépendante dans les éditions Pro et Entreprise.

Il doit :

- servir les assets React compilés ;
- utiliser Bootstrap 5 ;
- consommer exclusivement l'API backend ;
- ne jamais se connecter à PostgreSQL ;
- exposer toutes les fonctionnalités disponibles en CLI lorsque l'édition les autorise ;
- respecter RBAC/ABAC via le backend ;
- être clusterisable en édition Entreprise.

## 9. Agents d'auto discovery

Les agents sont de simples collecteurs d'information. Ils alimentent la base centrale via l'API backend, directement ou via la chaîne sécurisée définie par l'architecture.

Ils ne doivent pas héberger de logique métier autoritative et ne doivent pas écrire directement dans PostgreSQL.

## 10. Critères d'acceptation

L'installation autonome est acceptée uniquement si :

- les installateurs sont hors de `src/` ;
- les dépendances sont installées automatiquement ;
- le mode cluster se configure à partir des paramètres réseau minimaux ;
- le backend applique toutes les migrations ;
- les services systemd ont des noms invariants ;
- le frontend consomme seulement l'API ;
- les agents utilisent le suffixe `-agent` ;
- la VIP bascule en cas de panne ;
- les health checks sont opérationnels ;
- un rapport d'installation complet est généré ;
- le rollback est possible avant démarrage final ;
- les tests d'acceptation automatisés passent.
