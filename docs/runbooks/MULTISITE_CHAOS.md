# EPIC-1706 — Chaos multisite

## Objectif

Valider qu'une topologie OpenInfra Enterprise multisite reste en dégradation contrôlée et revient à son état nominal sans corruption après six classes de panne : réseau, site, agent, base de données, saturation de file et frontend.

La campagne est destructive par nature. Elle s'exécute uniquement sur une topologie de validation représentative, depuis un runner GitHub Actions dédié et protégé par l'environnement `multisite-chaos-certification`.

## Architecture du test

OpenInfra ne contient aucun accès fournisseur d'infrastructure ni aucune commande shell libre. Le runner de campagne utilise un port externe, `OPENINFRA_MULTISITE_CHAOS_HARNESS`, dont le chemin doit être absolu, exécutable, non symbolique et non modifiable par le groupe ou les autres utilisateurs.

Le harness reçoit uniquement les opérations suivantes :

```text
<harness> preflight --scenario all
<harness> inject --scenario <scenario>
<harness> recover --scenario <scenario>
<harness> verify-recovered --scenario <scenario>
```

Chaque appel retourne un objet JSON sur stdout. Le harness est spécifique à l'infrastructure de test et doit implémenter les six scénarios, dans cet ordre :

```text
network-partition
site-loss
agent-loss
database-loss
queue-saturation
frontend-loss
```

Le `preflight` retourne :

```json
{
  "status": "ok",
  "supported_scenarios": [
    "network-partition",
    "site-loss",
    "agent-loss",
    "database-loss",
    "queue-saturation",
    "frontend-loss"
  ]
}
```

Une injection réussie retourne au minimum :

```json
{
  "status": "ok",
  "scenario": "network-partition",
  "fault_observed": true,
  "corruption_detected": false,
  "acknowledged_work_lost": false
}
```

La vérification après récupération retourne au minimum :

```json
{
  "status": "ok",
  "scenario": "network-partition",
  "rollback_verified": true,
  "corruption_detected": false,
  "acknowledged_work_lost": false
}
```

## Mesures

Pour chaque scénario, le runner :

1. calcule le SHA-256 du endpoint d'intégrité en lecture seule ;
2. demande l'injection de panne ;
3. sonde le endpoint de santé pendant la fenêtre définie dans `docs/operations/multisite-chaos-profile.json` ;
4. mesure disponibilité et taux d'erreur ;
5. demande systématiquement la récupération dans un bloc de nettoyage ;
6. attend le retour du service ;
7. exige la vérification du rollback par le harness ;
8. recalcule le SHA-256 du endpoint d'intégrité ;
9. refuse de poursuivre la campagne si la récupération ou le rollback échoue.

L'endpoint d'intégrité doit être déterministe et strictement en lecture seule. Il doit représenter un jeu stable de données de référence et ne doit contenir ni timestamp courant, ni compteur volatile, ni ordre non déterministe.

## Critères bloquants

La certification échoue si l'une des conditions suivantes est vraie :

- la panne n'est pas observée ;
- la dégradation n'est pas contrôlée ;
- la récupération échoue ;
- le rollback n'est pas vérifié ;
- le SHA-256 d'intégrité change ;
- une corruption est signalée ;
- un travail acquitté est perdu ;
- le temps de récupération dépasse l'objectif du scénario ;
- la disponibilité est inférieure à l'objectif ;
- le taux d'erreur dépasse l'objectif ;
- une preuve est absente, dupliquée ou altérée.

## Exécution

La campagne officielle est lancée manuellement par `.github/workflows/multisite-chaos.yml`. Le runner doit exposer `OPENINFRA_MULTISITE_CHAOS_HARNESS` et le secret `OPENINFRA_MULTISITE_CHAOS_BEARER_TOKEN` lorsque les endpoints nécessitent une authentification.

Les rapports bruts, le manifeste d'évidence et le rapport de certification sont conservés 90 jours par GitHub Actions.

## Sécurité

- aucune commande shell provenant d'un secret ou d'un fichier JSON n'est exécutée ;
- le harness est appelé avec une liste d'arguments fixe et `shell=False` ;
- les URLs de santé et d'intégrité doivent être en HTTPS ;
- la campagne s'arrête après une récupération non vérifiée afin d'éviter l'empilement de pannes ;
- le workflow ne s'exécute jamais depuis `pull_request_target` ;
- les artefacts ne contiennent aucun bearer token.
