# Simulation de changement et planification de migration

## Finalité

Le moteur P16 / EPIC-1602 évalue un changement proposé sur une projection en lecture du RSOT. Il produit des constats et un plan consultatif. Il ne doit jamais :

- modifier un objet ou une relation RSOT ;
- réserver ou modifier une ressource IPAM/DCIM ;
- appliquer une règle réseau, DNS ou pare-feu ;
- exécuter une vague de migration ;
- créer un changement ITSM natif.

Les champs `production_mutation`, `execution_allowed`, `execution_order` et `itsm_native_change_created` restent explicitement à `false` dans les résultats concernés.

## Changements typés

| Type | Contrat minimal |
|---|---|
| `equipment-move` | `after` contient au moins `site`, `building`, `room`, `rack` ou `u_position` |
| `equipment-add` | la cible n’existe pas dans le RSOT et `before` est vide |
| `equipment-remove` | la cible existe et `after` est vide |
| `equipment-outage` | la cible existe et `after` est vide |
| `vlan-change` | `after.vlan` ou `after.vlan_id` |
| `vrf-change` | `after.vrf` ou `after.vrf_name` |
| `subnet-change` | `after.subnet` ou `after.prefix`, préfixe IP valide |
| `dns-change` | `after.dns_name`, `after.resolver` ou `after.record` |
| `firewall-change` | `after.policy`, `after.action` ou `after.rule` |
| `pdu-outage` | la cible existe et `after` est vide |

Un scénario contient de 1 à 100 changements et jusqu’à 50 hypothèses normalisées par changement. Les états `before` et `after` sont bornés à 64 Kio chacun.

## Exemple d’entrée

```json
[
  {
    "kind": "equipment-move",
    "target_key": "server:par-001",
    "before": {"site": "par1", "rack": "r01"},
    "after": {
      "site": "par2",
      "rack": "r20",
      "power_watts": 400,
      "cooling_kw": 0.5,
      "monthly_cost": 250
    },
    "assumptions": ["La capacité du rack cible est réservée"]
  }
]
```

## CLI

```bash
openinfra simulation create \
  --backend postgresql --postgres-dsn "$OPENINFRA_POSTGRES_DSN" \
  --tenant default --admin-token "$OPENINFRA_TOKEN" \
  --actor architect@example.com \
  --name "Migration ERP vers PAR2" \
  --description "Comparer le déplacement du serveur ERP vers le site secondaire." \
  --owner architecture.team \
  --idempotency-key simulation-erp-par2-0001 \
  --site par1 --environment production --criticality high \
  --changes-file changes.json

openinfra simulation list --tenant default --admin-token "$OPENINFRA_TOKEN"
openinfra simulation get --tenant default --admin-token "$OPENINFRA_TOKEN" --scenario-id "$SCENARIO_ID"
openinfra simulation run --tenant default --admin-token "$OPENINFRA_TOKEN" --scenario-id "$SCENARIO_ID"
openinfra simulation reports --tenant default --admin-token "$OPENINFRA_TOKEN" --scenario-id "$SCENARIO_ID"
openinfra simulation report --tenant default --admin-token "$OPENINFRA_TOKEN" --report-id "$REPORT_ID"
openinfra simulation compare --tenant default --admin-token "$OPENINFRA_TOKEN" \
  --left-report-id "$LEFT_REPORT_ID" --right-report-id "$RIGHT_REPORT_ID"
openinfra simulation comparisons --tenant default --admin-token "$OPENINFRA_TOKEN"
```

## API HTTP

Les neuf routes sont publiées sous `/api/v1` :

- `GET /simulation-scenarios`
- `GET /simulation-scenarios/get`
- `POST /simulation-scenarios/create`
- `POST /simulation-scenarios/run`
- `POST /simulation-scenarios/cancel`
- `GET /impact-reports`
- `GET /impact-reports/get`
- `GET /scenario-comparisons`
- `POST /scenario-comparisons/create`

Toutes exigent un Bearer token et un `tenant_id`. La pagination utilise un curseur opaque lié au tenant et aux filtres.

## Analyse produite

Le rapport agrège :

- dépendances directes et indirectes du graphe RSOT ;
- services métier potentiellement affectés ;
- flux réseau déclarés associés aux objets ;
- contrôles VLAN/VRF/sous-réseau/DNS/pare-feu ;
- delta de puissance, refroidissement, coût mensuel et unités de rack ;
- risques avant/après ;
- score global de préparation et preuves manquantes ;
- groupes d’affinité ;
- dépendances bloquantes ;
- vagues ordonnées à titre consultatif ;
- indicateur `truncated` lorsque la limite `max_nodes` est atteinte.

Un résultat tronqué ne doit jamais être présenté comme exhaustif. Augmenter `max_nodes` dans la limite de 5 000 ou réduire le périmètre de la simulation.

## Sécurité et rôles

Permissions :

- `simulation.read` : consultation des scénarios, rapports et comparaisons ;
- `simulation.write` : création, annulation et comparaison ;
- `simulation.execute` : génération d’un rapport ;
- `simulation.admin` : administration réservée.

Rôles dédiés : `simulation:reader`, `simulation:operator`, `simulation:admin`. Le rôle `admin` conserve l’ensemble des permissions. Toutes les transitions sont auditées et publiées dans l’outbox transactionnel.

## Persistance et volumétrie

La migration `0045_simulation_migration_planning.sql` crée quatre tables partitionnées par hash du tenant en 16 partitions : scénarios, rapports, comparaisons et outbox. Les recherches principales disposent d’index B-tree, GIN JSONB et BRIN temporels.

Les rapports sont immuables. Une nouvelle exécution avec un nouvel état d’entrée produit un nouveau rapport ; une répétition avec le même scénario terminé et la même empreinte retourne le rapport existant.

## Sauvegarde, restauration et purge

Les tables sont incluses dans la sauvegarde PostgreSQL OpenInfra standard. Pour une restauration cohérente, restaurer scénarios, rapports, comparaisons, outbox et `audit_events` dans la même fenêtre transactionnelle.

La purge doit être pilotée par la politique de rétention et exécutée dans cet ordre : comparaisons, rapports, scénarios, événements outbox publiés. Ne jamais supprimer un rapport référencé par une comparaison. Les événements non publiés (`published_at IS NULL`) ne doivent pas être purgés.

## Diagnostic

1. Vérifier l’existence et le tenant de chaque `target_key`.
2. Contrôler que l’état `before` correspond au RSOT courant.
3. Vérifier les permissions `simulation.*` du token.
4. Examiner `failure_reason` si le scénario est `failed`.
5. Contrôler `truncated`, `max_depth` et `max_nodes`.
6. Vérifier l’outbox et l’audit sur l’identifiant du scénario.
7. Relancer le scénario échoué après correction de l’entrée ; aucune mutation de production n’a eu lieu.
