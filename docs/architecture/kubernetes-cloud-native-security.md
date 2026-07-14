# Architecture — corrélation sécurité Kubernetes et cloud-native

## Objectif

EPIC-2103 relie l’inventaire Kubernetes immuable aux référentiels sécurité déjà présents dans OpenInfra. La capacité est une **projection en lecture seule** : elle ne duplique ni les SBOM, ni les findings, ni l’inventaire PKI et ne résout jamais un secret.

Le rapport produit la chaîne suivante :

`workload/pod → image OCI → SBOM → findings contextualisés`

et, lorsque la ressource le déclare :

`ressource Kubernetes → empreinte certificat → actif PKI → état de santé`

`ressource Kubernetes → référence de secret → fournisseur + empreinte irréversible`

## Modèle de référence

### Images

Une ressource `workload` ou `pod` peut déclarer jusqu’à 64 images. Chaque référence contient :

- la référence OCI ;
- éventuellement un digest `sha256` ;
- éventuellement jusqu’à 32 identifiants de documents SBOM déjà importés.

La corrélation SBOM fonctionne par identifiant explicite et par métadonnées SBOM (`image_reference`, `image_references`, `container_image`, `container_images`, `image_digest`, `image_digests`, `container_image_digest`). Aucune heuristique basée uniquement sur un nom d’application n’est utilisée.

### Certificats

Les ressources compatibles déclarent uniquement des empreintes SHA-256. Le rapport consulte l’inventaire PKI existant et expose :

- présence ou absence de l’actif ;
- cycle de vie ;
- santé à la date d’observation du snapshot ;
- jours restants ;
- propriétaire et environnement.

Aucun certificat n’est importé implicitement par la corrélation.

### Secrets référencés

Les valeurs de secrets sont interdites. Les seules entrées acceptées sont des références utilisant un schéma approuvé :

- `vault://` ;
- `sops://` ;
- `kms://` ;
- `kubernetes-secret://namespace/name` ;
- `external-secret://` ;
- `aws-secrets-manager://` ;
- `azure-key-vault://` ;
- `gcp-secret-manager://`.

Pour les fournisseurs externes, OpenInfra conserve uniquement :

- le fournisseur ;
- un affichage masqué tel que `vault://***` ;
- le SHA-256 de la référence d’origine.

La référence externe en clair n’est donc pas persistée. La référence native `kubernetes-secret://namespace/name` peut rester visible car elle identifie un objet Kubernetes et ne contient pas le contenu du Secret.

## Compatibilité ascendante

Les nouveaux champs de sécurité sont omis de la sérialisation lorsqu’ils sont vides. Cette règle préserve bit pour bit le payload canonique des snapshots historiques et donc leurs empreintes créées par les versions 0.33.0 à 0.33.2.

Aucune migration supplémentaire n’est nécessaire : la migration `0055_kubernetes_topology_inventory.sql` stocke déjà le snapshot de ressources sous forme JSON immuable.

## Bornes et déterminisme

La projection applique les bornes suivantes :

- 2 000 documents SBOM parcourus ;
- 512 références directes de documents SBOM ;
- 10 000 findings de vulnérabilité ;
- 64 images, 64 certificats et 64 références de secrets par ressource.

Un curseur cyclique provenant d’un repository SBOM est refusé. Si une borne de volume est atteinte, `correlation_truncated=true` l’indique explicitement.

Le rapport final possède une empreinte SHA-256 canonique calculée sur les ressources corrélées et les compteurs de synthèse.

## Sécurité

La capacité respecte les principes suivants :

- RBAC Kubernetes en lecture ;
- isolation stricte par tenant ;
- aucune résolution de secret ;
- aucune copie de contenu de Secret ;
- aucune mutation de SBOM, finding ou certificat ;
- aucune correction automatique d’une vulnérabilité ou d’un certificat ;
- aucune écriture dans le cluster Kubernetes.
