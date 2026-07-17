# GATE-09 — Promotion Enterprise Scale-out

Version cible : `0.34.1`

## Objet

`GATE-09` est le gate final de `REL-10 / P20`. Il n'exécute pas une seconde fois les campagnes déjà certifiées : il agrège leurs rapports immuables, vérifie leur version, leur fraîcheur, leur empreinte SHA-256 et leur verdict avant d'autoriser la promotion Enterprise Scale-out.

La promotion exige simultanément :

- les contrats P20 du code courant : PgBouncer/read-routing, pagination curseur/streaming, outbox/workers spécialisés, frontend modulaire/virtualisé, observabilité/capacité et runbooks ;
- une certification Enterprise Capacity valide ;
- une certification Chaos multisite valide ;
- une certification PRA/PCA valide ;
- un audit de sécurité release complet et non offline ;
- un packaging release certifié avec clé de signature de confiance ;
- une décision GA `GO` signée par une clé de confiance.

Aucune preuve n'est acceptée par nom seul. Chaque fichier est copié dans le dossier de preuve, référencé par un chemin relatif et verrouillé par son SHA-256 canonique.

## Exécution locale du contrat P20

```bash
PYTHONPATH=src:. python scripts/validate_scaleout_promotion.py \
  --project-root . \
  --output build/scaleout/p20-contracts.json \
  --enforce
```

## Assemblage

```bash
PYTHONPATH=src:. python scripts/assemble_scaleout_promotion_evidence.py \
  --candidate-id openinfra-0.34.1-enterprise-scaleout \
  --source-commit 0123456789abcdef0123456789abcdef01234567 \
  --p20-contracts build/scaleout/p20-contracts.json \
  --enterprise-capacity build/input/capacity/certification-report.json \
  --multisite-chaos build/input/chaos/certification-report.json \
  --pra-pca build/input/pra-pca/certification-report.json \
  --release-security build/input/security/release-security.json \
  --release-packaging build/input/packaging/openinfra-0.34.1-release-manifest.json \
  --ga-go-no-go build/input/ga/openinfra-0.34.1-go-no-go.json \
  --evidence-root build/scaleout/evidence \
  --output build/scaleout/manifest.json
```

## Certification bloquante

```bash
PYTHONPATH=src:. python scripts/certify_scaleout_promotion.py \
  --policy docs/release/enterprise-scaleout-promotion-policy.json \
  --manifest build/scaleout/manifest.json \
  --evidence-root build/scaleout/evidence \
  --output build/scaleout/certification-report.json \
  --enforce
```

Le code retour est non nul si `scaleout_promotion_certification` est faux. Une preuve périmée doit être régénérée par son workflow source ; elle ne doit jamais être modifiée manuellement.

## Sécurité

- aucun secret n'est placé dans le manifeste ;
- aucun chemin absolu ni traversée `..` n'est accepté lors de la certification ;
- les SHA-256 doivent être en hexadécimal minuscule canonique ;
- le workflow de promotion ne télécharge que des artefacts de runs explicitement fournis ;
- la promotion ne modifie aucune infrastructure : elle produit uniquement une décision auditable.
