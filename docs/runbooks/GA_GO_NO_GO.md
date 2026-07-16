# Décision Go/No-Go GA OpenInfra

Version cible : `0.33.9`

## Objectif

Le gate `GATE-07` consolide les critères business, techniques, sécurité, support et exploitation exigés par `EPIC-1805`. Il ne déduit jamais un GO à partir d'une preuve absente, périmée, non signée ou produite hors de la topologie attendue.

## Preuves obligatoires

Le fichier `docs/release/ga-go-no-go-policy.json` définit un catalogue fermé : validation technique, capacité Enterprise, sécurité de release, packaging, documentation GA, préparation opérationnelle, préparation support et préparation business.

Chaque rapport est référencé par son chemin relatif et son empreinte SHA-256 dans le manifeste candidat. Les preuves trop anciennes, futures, invalides ou correspondant à une autre version sont refusées.

## Approbations

Les rôles `product-owner`, `engineering-owner`, `security-owner`, `operations-owner` et `support-owner` doivent chacun fournir une déclaration JSON signée par Ed25519. La clé publique doit être autorisée pour le rôle dans une politique de confiance externe au dépôt.

La déclaration contient exactement : `schema_version`, `release_version`, `candidate_id`, `role`, `approver`, `decision`, `signed_at` et `comment`. La valeur `decision` doit être `approve`.

## Risques

Tout risque `critical` ou `high` encore ouvert ou accepté bloque la GA. Un risque de sévérité inférieure peut être accepté uniquement avec responsable, mesure de maîtrise et date d'expiration future.

## Exécution locale non certifiante

Une exécution locale peut produire un NO-GO signé par une clé éphémère :

```powershell
python scripts/ga_go_no_go.py `
  --manifest artifacts/ga/candidate.json `
  --policy docs/release/ga-go-no-go-policy.json `
  --trust-policy artifacts/ga/trust-policy.json `
  --evidence-root artifacts/ga `
  --output artifacts/ga/openinfra-0.33.9-go-no-go.json `
  --ephemeral-signing-key
```

Une clé éphémère n'est jamais autorisée à produire un GO.

## Décision officielle

La clé privée de décision est fournie par `OPENINFRA_RELEASE_SIGNING_PRIVATE_KEY_B64`. La politique de confiance est injectée depuis le coffre de secrets et ne doit pas être commitée.

```powershell
python scripts/ga_go_no_go.py `
  --manifest artifacts/ga/candidate.json `
  --policy docs/release/ga-go-no-go-policy.json `
  --trust-policy artifacts/ga/trust-policy.json `
  --evidence-root artifacts/ga `
  --output artifacts/ga/openinfra-0.33.9-go-no-go.json `
  --enforce-go
```

La commande retourne `1` pour un NO-GO et `2` pour une erreur de validation. Le rapport, sa signature et la clé publique de vérification doivent être archivés ensemble.

## État de la version 0.33.9

Le mécanisme de décision est opérationnel. La GA reste en NO-GO tant que le modèle de support d'`EPIC-1806`, les preuves de capacité et de sécurité exécutées sur l'infrastructure cible, les exercices PITR/failover et toutes les approbations signées ne sont pas disponibles.
