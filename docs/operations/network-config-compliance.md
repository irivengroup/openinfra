# Conformité réseau par golden configuration

OpenInfra compare une configuration attendue, versionnée et gouvernée, à la dernière configuration découverte pour le même objet équipement RSOT et la même plateforme.

## Garanties

- aucune écriture automatique sur les équipements ;
- isolation tenant et permissions `network_config.read` / `network_config.write` ;
- observations immuables et idempotentes ;
- documents JSON limités à 1 MiB, 10 000 nœuds et 32 niveaux ;
- rejet des secrets, mots de passe, communautés SNMP, jetons, credentials et clés privées ;
- audit des créations, révisions, retraits, ingestions et évaluations ;
- pagination et sélection de l'observation la plus récente à la date `as_of`.

## Dérives

- `missing` : clé ou élément attendu absent ;
- `unexpected` : clé ou élément non attendu ;
- `mismatch` : valeur différente ;
- `type-mismatch` : type JSON différent.

Les chemins utilisent JSON Pointer. Les chemins ignorés et leurs descendants ne produisent pas de dérive. Les chemins critiques et leurs descendants produisent une sévérité `critical`; les autres écarts sont `warning`.

## Exploitation

```bash
openinfra network-config baseline-upsert --help
openinfra network-config observation-submit --help
openinfra network-config assess --help
```

La remédiation reste une décision opérateur ou un workflow externe explicitement autorisé. Le moteur ne pousse jamais de configuration.
