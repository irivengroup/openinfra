# ADR-0021 — Licence runtime offline Ed25519

- **Statut** : Accepté
- **Version** : CDC 4.10.0

## Contexte

Les installations OpenInfra peuvent être durablement isolées d’Internet. La licence doit rester vérifiable localement, être liée à l’entreprise et au nombre d’hôtes, et ne jamais nécessiter la présence de la clé privée d’autorité sur le site client.

## Décision

OpenInfra utilise des signatures Ed25519 et une enveloppe JSON canonicalisée. L’installation signe sa demande avec une clé locale ; l’autorité commerciale émet hors ligne un entitlement signé avec une clé privée chiffrée. Le runtime embarque uniquement le trust bundle public.

L’état commercial est séparé des politiques fonctionnelles d’édition. Lite est exemptée. Pro et Entreprise deviennent fail-closed lorsque l’enforcement est activé. La période de grâce est fixée à 30 jours et ne peut pas être prolongée par recul de l’horloge.

## Conséquences

- validation déterministe sans réseau ;
- rotation possible du trust bundle public ;
- persistance versionnée et migration 0059 ;
- contrôle transactionnel du quota ;
- API HTTP 402 et CLI diagnostiquables ;
- GATE-12 obligatoire avant REL-13 ;
- sauvegarde des clés d’installation et du document d’activation requise.

## Alternatives rejetées

- appel périodique à un serveur de licence : incompatible avec les intranets isolés ;
- secret HMAC partagé : compromet toutes les installations si un client est extrait ;
- clé privée d’autorité embarquée : permettrait l’émission frauduleuse et est interdite.
