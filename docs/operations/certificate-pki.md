# Exploitation des certificats et de la PKI

## Objectif

Le module **Certificats et PKI** maintient un inventaire gouverné des certificats X.509 sans conserver de clé privée. Il permet d'importer une chaîne PEM, d'inventorier ses propriétés cryptographiques, de rattacher le certificat feuille à un objet RSOT, d'observer les endpoints qui le présentent et d'évaluer les échéances ainsi que la cohérence hostname/SAN.

Le module ne remplace pas une autorité de certification, un HSM ou un gestionnaire de secrets. Il ne génère, ne signe, ne renouvelle et ne déploie aucun certificat automatiquement.

## Modèle de sécurité

- `certificate.read` : consultation de l'inventaire, des endpoints et des évaluations.
- `certificate.write` : import, révision de gouvernance, retrait et ingestion d'observations.
- rôles fournis : `certificate:reader` et `certificate:operator` ;
- isolation stricte par tenant ;
- empreinte SHA-256 comme identité immuable ;
- journal d'audit pour chaque mutation et évaluation ;
- refus des chaînes de plus de 16 certificats ;
- refus des certificats dupliqués dans une même chaîne ;
- absence de stockage de clé privée ou de contenu applicatif transporté par TLS.

Un bundle contenant `BEGIN PRIVATE KEY`, `BEGIN RSA PRIVATE KEY`, `BEGIN EC PRIVATE KEY` ou une autre clé privée doit être rejeté en amont et ne doit jamais être utilisé comme entrée opérateur.

## Import d'une chaîne PEM

La chaîne doit être fournie dans l'ordre **certificat feuille, intermédiaires, racine**. OpenInfra vérifie :

1. le décodage X.509 de chaque bloc PEM ;
2. la continuité entre `issuer` du certificat courant et `subject` du certificat suivant ;
3. la signature cryptographique de chaque certificat par la clé publique de son émetteur ;
4. l'unicité des empreintes ;
5. la cohérence des périodes de validité et des métadonnées.

Exemple CLI :

```bash
openinfra certificate import \
  --backend postgresql \
  --tenant tenant-a \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --actor alice \
  --pem-file /secure/input/portal-chain.pem \
  --owner platform-team \
  --environment production \
  --source internal-pki \
  --object-key application/portal
```

Le fichier PEM doit être lu depuis un emplacement protégé. Il ne doit contenir que des certificats publics.

## Inventaire et retrait

```bash
openinfra certificate list \
  --backend postgresql \
  --tenant tenant-a \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --limit 100

openinfra certificate get \
  --backend postgresql \
  --tenant tenant-a \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --fingerprint <sha256>

openinfra certificate retire \
  --backend postgresql \
  --tenant tenant-a \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --actor alice \
  --fingerprint <sha256>
```

Le retrait est logique. L'enregistrement, ses versions de gouvernance, ses observations et son audit restent consultables.

## Observation des endpoints

Une observation décrit uniquement les métadonnées TLS utiles : protocole, hôte, port, service, empreinte présentée, date, collecteur, version TLS et suite cryptographique.

```bash
openinfra certificate endpoint-observe \
  --backend postgresql \
  --tenant tenant-a \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --actor tls-scanner \
  --idempotency-key 'scanner-par-01:portal.example.net:443:20260710T120000Z' \
  --protocol https \
  --host portal.example.net \
  --port 443 \
  --service openinfra-portal \
  --certificate-fingerprint <sha256> \
  --observed-at 2026-07-10T12:00:00Z \
  --source active-scan \
  --collector scanner-par-01 \
  --tls-version TLSv1.3 \
  --cipher TLS_AES_256_GCM_SHA384
```

La même clé d'idempotence et la même charge retournent l'observation existante. Une charge différente avec la même clé produit un conflit explicite.

## Évaluation des certificats

```bash
openinfra certificate assess \
  --backend postgresql \
  --tenant tenant-a \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --critical-days 14 \
  --warning-days 30 \
  --limit 100
```

Ordre des états :

1. `retired` ;
2. `not-yet-valid` ;
3. `expired` ;
4. `critical` lorsque l'échéance est dans le seuil critique ;
5. `warning` lorsque l'échéance est dans le seuil d'avertissement ;
6. `healthy`.

L'évaluation signale également :

- les liens de chaîne absents de l'inventaire ;
- les endpoints dont le hostname ne correspond ni au SAN DNS/IP ni au CN de secours ;
- le nombre d'endpoints rattachés à chaque certificat.

Les wildcards DNS ne correspondent qu'à un seul label, par exemple `*.example.net` couvre `portal.example.net`, mais pas `api.portal.example.net`.

## Limites de charge

Une évaluation charge au maximum :

- 5 000 certificats ;
- 10 000 observations d'endpoints ;
- pages internes de 500 éléments.

Les curseurs non progressifs ou cycliques provoquent une erreur explicite afin d'éviter une boucle infinie.

## PostgreSQL

La migration `0042_certificate_pki_inventory.sql` crée :

- `certificate_inventory` ;
- `certificate_endpoint_observations` ;
- 16 partitions hash par table et par tenant ;
- contraintes d'intégrité et unicités tenant-aware ;
- index sur expiration, propriétaire, rattachement RSOT, sujet, SAN, endpoints et temps d'observation ;
- index BRIN pour les observations temporelles volumineuses.

## Procédure d'incident

En cas d'import rejeté :

1. ne pas contourner la validation cryptographique ;
2. vérifier l'ordre leaf-first ;
3. vérifier que chaque intermédiaire est présent ;
4. vérifier que le bundle ne contient aucune clé privée ;
5. comparer les sujets, émetteurs et algorithmes ;
6. corriger la chaîne à la source, puis réimporter.

En cas d'expiration critique :

1. identifier le propriétaire et les endpoints concernés ;
2. renouveler le certificat dans la PKI autorisée ;
3. déployer selon le processus de changement applicable ;
4. réobserver les endpoints ;
5. retirer l'ancien certificat uniquement après confirmation du basculement.
