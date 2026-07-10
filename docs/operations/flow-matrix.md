# Matrice de flux OpenInfra

## Objet

La matrice de flux compare les politiques réseau déclarées aux communications réellement observées. Elle ne déploie aucune règle de pare-feu et ne modifie pas le RSOT : elle produit une vue de conformité gouvernée, tenant-aware et auditée.

## Modèle de données

Une **déclaration** décrit un flux attendu ou interdit avec :

- un code métier stable ;
- une source et une destination sélectionnées par `any`, `object:<clé RSOT>` ou `cidr:<réseau>` ;
- un protocole parmi `any`, `tcp`, `udp`, `sctp`, `icmp`, `icmpv6`, `esp`, `ah` et `gre` ;
- une plage de ports de destination lorsque le protocole la permet ;
- une décision `allow` ou `deny` ;
- une priorité comprise entre 0 et 1000 ;
- un propriétaire, une justification et une période de validité ;
- un cycle de vie `active` ou `retired`.

Une **observation** est une preuve immuable issue de NetFlow, sFlow, IPFIX, d'un journal de pare-feu, d'un journal applicatif, d'un import ou d'une saisie manuelle contrôlée. L'idempotence repose sur la paire tenant/clé d'idempotence et sur une empreinte SHA-256 canonique. Une même clé avec une charge différente est refusée.

## Résultats de comparaison

| Statut | Signification | Traitement recommandé |
|---|---|---|
| `compliant` | Une observation correspond à une déclaration active `allow`. | Conserver comme preuve de conformité. |
| `denied-observed` | Une observation correspond à une déclaration active `deny`. | Investiguer immédiatement et corriger le contrôle réseau ou la source du trafic. |
| `undeclared-observed` | Une observation ne correspond à aucune déclaration active. | Qualifier le besoin, créer une déclaration gouvernée ou bloquer le flux. |
| `declared-unobserved` | Une déclaration `allow` active n'a aucune observation sur la fenêtre. | Vérifier l'utilité, la supervision et la possibilité de retirer la règle. |

La sélection d'une déclaration est déterministe : priorité métier, spécificité des sélecteurs et ordre stable. Les déclarations retirées ou hors période ne participent pas à la comparaison.

## Bornes de sécurité et de performance

- fenêtre maximale : 31 jours ;
- maximum chargé par comparaison : 5 000 déclarations et 10 000 observations ;
- pagination obligatoire pour les listes ;
- détection des curseurs cycliques ou non progressifs ;
- isolation stricte par tenant ;
- permissions `flow.read` et `flow.write` ;
- index PostgreSQL sur périodes, sources, endpoints, objets RSOT et audit ;
- partitionnement hash sur le tenant via `0041_flow_matrix.sql`.

## Commandes CLI

```bash
openinfra flow declaration-upsert --help
openinfra flow declaration-list --help
openinfra flow declaration-retire --help
openinfra flow observation-submit --help
openinfra flow observation-list --help
openinfra flow matrix --help
```

Toutes les commandes requièrent un tenant et un jeton approprié. Les dates sont fournies au format ISO 8601 avec fuseau horaire.

## API HTTP

Les routes sont documentées dans `docs/api/openapi.yaml` :

- `GET /api/v1/flows/declarations` ;
- `POST /api/v1/flows/declarations/upsert` ;
- `POST /api/v1/flows/declarations/retire` ;
- `GET /api/v1/flows/observations` ;
- `POST /api/v1/flows/observations/submit` ;
- `GET /api/v1/flows/matrix`.

## Runbook d'exploitation

1. Déclarer les flux autorisés et interdits avec propriétaire et justification vérifiables.
2. Collecter les observations depuis des sources approuvées ; ne jamais inclure de secrets ou de charge applicative sensible.
3. Comparer une fenêtre courte et stable, puis traiter en priorité `denied-observed` et `undeclared-observed`.
4. Vérifier les règles `declared-unobserved` avant retrait ; l'absence d'observation n'est pas une preuve suffisante d'inutilité.
5. Retirer une déclaration au lieu de la supprimer afin de conserver l'historique.
6. Consulter les événements d'audit pour toute création, révision, retraite, ingestion ou comparaison.

## Confidentialité

La matrice stocke uniquement les métadonnées nécessaires à la conformité : endpoints, protocole, port, compteurs, période et références RSOT. Elle ne stocke pas le contenu des paquets. Les politiques de rétention et de minimisation doivent être adaptées aux obligations de l'organisation.
