# Licence runtime offline

## Modèle de confiance

Chaque installation génère localement une paire Ed25519. La demande d’activation contient la clé publique d’installation et les attributs contractuels, puis elle est signée par l’installation. L’autorité commerciale vérifie cette demande hors ligne et émet un entitlement Ed25519. Seule la clé publique d’autorité est déployée sur le runtime.

La canonicalisation JSON est déterministe. Les UUID, dates UTC, édition, entreprise et quotas sont validés avant toute vérification de signature. Les clés qui ne sont pas Ed25519, les signatures malformées, les autorités non approuvées et les schémas inconnus sont refusés.

## États runtime

- `not_required` : édition Lite ;
- `missing` : identité présente mais aucun entitlement ;
- `active` : entitlement valide ;
- `grace` : expiration atteinte depuis moins de 30 jours ;
- `expired` : grâce terminée ;
- `invalid` : corruption, divergence, signature invalide ou recul d’horloge.

Lorsque `OPENINFRA_LICENSE_ENFORCEMENT=true`, seuls les parcours de diagnostic, activation et renouvellement restent accessibles dans les états bloquants. L’API renvoie HTTP 402 avec un diagnostic structuré, sans matériel secret.

## Persistance et concurrence

La liaison d’installation est immuable. L’activation, le renouvellement, la mise à jour de la dernière horloge observée et le quota d’hôtes sont sérialisés par l’unité de travail. PostgreSQL verrouille l’état avec `SELECT ... FOR UPDATE`. Oracle utilise le stockage documentaire segmenté et accepte explicitement l’état JSON `null` avant bootstrap.

## Exploitation

Les installateurs Pro et Entreprise requièrent l’entreprise, le UUID de licence et le quota d’hôtes, génèrent les clés en `0600` dans un répertoire `0700`, puis produisent la demande d’activation. La clé privée d’autorité demeure hors du système cible. Le runbook canonique est `docs/runbooks/OFFLINE_RUNTIME_LICENSING.md`.
