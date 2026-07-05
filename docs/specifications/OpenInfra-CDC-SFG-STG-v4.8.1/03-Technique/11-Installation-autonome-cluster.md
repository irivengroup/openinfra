# Installation autonome cluster

## Principe

L'installation cluster OpenInfra doit être pilotée par un moteur d'orchestration idempotent. L'opérateur renseigne un inventaire réseau minimal. L'installateur effectue ensuite les actions de préparation, installation, configuration, validation et preuve.

## Inventaire réseau minimal

```yaml
cluster:
  edition: enterprise
  scope: server
  vip: 192.0.2.100
  mask: 255.255.255.0
  gateway: 192.0.2.1
  dns:
    - 192.0.2.53
    - 192.0.2.54
nodes:
  - fqdn: oi-server-01.example.net
    ip: 192.0.2.11
  - fqdn: oi-server-02.example.net
    ip: 192.0.2.12
  - fqdn: oi-server-03.example.net
    ip: 192.0.2.13
```

Aucune information de mot de passe, token ou secret n'est attendue dans cet inventaire. Les secrets techniques sont générés par l'installateur et stockés dans le mécanisme sécurisé de l'environnement.

## Phases autonomes

1. Préflight système.
2. Vérification DNS direct et inverse.
3. Vérification connectivité inter-nœuds.
4. Installation des dépendances.
5. Configuration des comptes techniques.
6. Génération des certificats.
7. Configuration firewall.
8. Configuration systemd.
9. Bootstrap cluster.
10. Déploiement backend, frontend ou agent selon scope.
11. Exécution des migrations pour le scope backend.
12. Démarrage contrôlé.
13. Tests health/readiness.
14. Test de bascule si cluster.
15. Rapport final.

## Règles d'idempotence

Chaque étape doit être réexécutable sans produire de doublon, corruption, écrasement de configuration utilisateur ou régression. Une étape déjà conforme est marquée `conforme` dans le rapport.

## Dry-run et plan d'impact

Chaque installateur doit supporter un mode dry-run qui produit :

- dépendances à installer ;
- services à créer ;
- ports à ouvrir ;
- fichiers à écrire ;
- migrations à appliquer ;
- risques bloquants ;
- actions nécessitant privilèges élevés.

Le dry-run ne doit pas modifier l'état de la machine.

## Rollback

Le rollback doit restaurer l'état précédent pour :

- fichiers de configuration ;
- unités systemd ;
- règles firewall ;
- certificats générés non utilisés ;
- migrations non validées selon politique de migration ;
- services créés pendant une installation échouée.

Les migrations destructives doivent être interdites sans sauvegarde et stratégie de retour documentée.

## Prérequis et rollback runtime

Le dry-run doit exposer les prérequis exécutables nécessaires à l'installation. En installation native, `systemctl` est obligatoire pour rendre effectifs les services. Pour les scopes backend/all-in-one, le gestionnaire de paquets correspondant à la famille Linux détectée est obligatoire lorsque PostgreSQL doit être déployé.

L'installateur doit démarrer ou redémarrer l'unité OpenInfra cible après succès complet. Un service ne doit pas être lancé si la copie du payload, l'installation Python, le bootstrap PostgreSQL ou les migrations backend échouent.

Le rollback doit être automatique sur échec et restaurer les chemins remplacés pendant la tentative. Un mode manuel doit restaurer les sauvegardes résiduelles lorsque l'exécution a été interrompue par un arrêt externe du processus.
