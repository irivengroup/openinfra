# Exploitation — corrélation sécurité Kubernetes

## Prérequis

La corrélation nécessite :

1. un snapshot Kubernetes importé ;
2. des images déclarées dans les ressources `workload` ou `pod` ;
3. des SBOM déjà importés pour les images à contextualiser ;
4. des certificats déjà présents dans l’inventaire PKI lorsqu’une ressource déclare une empreinte.

Les secrets ne sont jamais lus. Seules leurs références sont acceptées à l’import du snapshot.

## Exemple de ressource workload

```json
{
  "kind": "workload",
  "uid": "deploy-api",
  "name": "api",
  "namespace": "production",
  "images": [
    {
      "reference": "registry.example/openinfra/api:1.0.0",
      "digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "sbom_document_ids": ["11111111-1111-4111-8111-111111111111"]
    }
  ],
  "secret_refs": [
    "vault://openinfra/production/api/password",
    "kubernetes-secret://production/api-runtime"
  ]
}
```

Après validation, la référence Vault n’est jamais restituée en clair. Le snapshot conserve un affichage `vault://***` et une empreinte irréversible de la référence.

## API

Snapshot précis :

```text
GET /api/v1/kubernetes/topologies/security?tenant_id=default&snapshot_id=<uuid>
```

Dernier snapshot du cluster :

```text
GET /api/v1/kubernetes/topologies/latest-security?tenant_id=default&cluster_key=cluster-par-01
```

Authentification : `Authorization: Bearer <token>`.

## CLI

```bash
openinfra kubernetes security \
  --tenant default \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --snapshot-id "<uuid>"
```

```bash
openinfra kubernetes latest-security \
  --tenant default \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --cluster-key cluster-par-01
```

## Lecture du rapport

Les compteurs importants sont :

- `images_without_sbom` : images sans SBOM corrélé ;
- `active_vulnerability_count` : findings non mitigés et non faux positifs ;
- `critical_vulnerability_count` : findings actifs de priorité critique ;
- `unknown_certificate_count` : empreintes non présentes dans l’inventaire PKI ;
- `unhealthy_certificate_count` : certificats expirés, critiques, en avertissement, futurs ou retirés ;
- `secret_reference_count` : références de secrets, sans résolution de valeur ;
- `correlation_truncated` : une borne de protection a limité la corrélation.

## Réponse opérationnelle recommandée

- une image sans SBOM doit déclencher la production/import du SBOM, pas une déduction heuristique ;
- une vulnérabilité critique doit être traitée dans le workflow de risque SBOM existant ;
- un certificat inconnu doit être importé ou investigué dans l’inventaire PKI ;
- un certificat non sain doit être renouvelé selon les procédures PKI ;
- une référence de secret ne doit jamais être remplacée par une valeur en clair dans le snapshot.

La corrélation est strictement en lecture et ne remédie automatiquement à aucun de ces écarts.
