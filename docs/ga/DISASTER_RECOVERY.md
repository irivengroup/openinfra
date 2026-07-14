# PRA et PCA

Version cible : `0.33.1`

## Objectifs RPO et RTO

Le RPO et le RTO sont définis par l’organisation et doivent être mesurés. OpenInfra ne déclare pas une conformité PRA/PCA sans exercice réel et preuves horodatées.

- RPO : perte de données maximale acceptable.
- RTO : durée maximale de restauration du service.
- PCA : maintien contrôlé des fonctions prioritaires pendant l’incident.
- PRA : restauration du service après sinistre.

## Sauvegarde et PITR

La cible PostgreSQL doit disposer de sauvegardes de base et d’archives WAL. Avant chaque exercice :

```bash
openinfra database status --root installers/migrations/postgresql
openinfra audit verify-integrity \
  --backend postgresql \
  --tenant default \
  --admin-token "$OPENINFRA_BOOTSTRAP_TOKEN"
```

Conserver la version applicative, le checksum des migrations, le manifeste de release et l’heure de coupure choisie pour le PITR.

## Bascule contrôlée

Le failover PostgreSQL reste manuel et auditable :

1. confirmer la perte du primaire ;
2. mesurer le lag et identifier le standby candidat ;
3. geler les écritures ;
4. promouvoir le standby selon la procédure PostgreSQL de l’organisation ;
5. reconfigurer PgBouncer et les DSN ;
6. vérifier `/ready`, les migrations et l’intégrité d’audit ;
7. réouvrir progressivement le trafic ;
8. reconstruire un nouveau réplica.

Aucune promotion automatique n’est déclenchée par OpenInfra.

## Restauration

Ordre recommandé :

1. provisionner une cible isolée ;
2. restaurer la base puis appliquer le PITR ;
3. restaurer `/opt/openinfra/config` et les références de secrets ;
4. restaurer le stockage d’artefacts ;
5. installer exactement la version indiquée dans le manifeste ;
6. exécuter les migrations uniquement si la base restaurée est antérieure ;
7. contrôler l’intégrité d’audit et les volumes métier ;
8. lancer les smokes ;
9. basculer DNS/VIP après autorisation.

## Exercice de reprise

Chaque exercice doit produire :

- scénario et périmètre ;
- heure de début, heure de restauration et RTO mesuré ;
- point restauré et RPO mesuré ;
- checksums et versions ;
- contrôles d’intégrité ;
- incidents, décisions et actions correctives ;
- signature du responsable de validation.

## PCA dégradé

En cas de perte du réplica, les écritures peuvent continuer sur le primaire si les budgets de connexion restent respectés. En cas de perte d’un worker, les leases expirent et les jobs sont repris avec fencing. En cas de perte du stockage d’artefacts, suspendre les traitements asynchrones concernés plutôt que d’accepter des résultats non vérifiables.

## Certification PRA/PCA

À partir de la version 0.32.9, les éditions Pro et Enterprise peuvent produire une preuve de certification PRA/PCA reproductible. Le dispositif agrège le plan DR actif, un exercice DR, une preuve de sauvegarde/restauration, une preuve PITR et l’attestation des procédures. Les cinq sources sont hachées en SHA-256 et la certification conserve la mesure la plus défavorable pour le RPO, le RTO et l’âge de sauvegarde.

La procédure complète est décrite dans `docs/runbooks/PRA_PCA_CERTIFICATION.md`. Le certificateur est strictement évaluatif : il ne déclenche ni failover, ni promotion PostgreSQL, ni restauration, ni modification DNS/VIP.
