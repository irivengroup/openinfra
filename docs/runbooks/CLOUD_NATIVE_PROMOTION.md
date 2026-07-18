# Promotion Kubernetes & Cloud-native — GATE-10

## Objet

GATE-10 autorise la promotion de `REL-11` uniquement lorsque les preuves des EPIC-2101 à EPIC-2106 sont complètes, récentes, cohérentes avec la version OpenInfra candidate et épinglées par SHA-256.

La certification ne modifie aucun cluster Kubernetes, aucun objet RSOT/DCIM et aucun état GitOps. Elle produit un verdict en lecture seule.

## Preuves obligatoires

1. inventaire et topologie physique EPIC-2101 ;
2. expositions et dépendances réseau EPIC-2102 ;
3. corrélation sécurité EPIC-2103, sans secret en clair ;
4. dérive GitOps EPIC-2104, sans remédiation automatique ;
5. capacité cluster/namespace EPIC-2105 ;
6. qualification runtime EPIC-2106 avec au moins trois clusters et un snapshot de 50 000 ressources ;
7. contrat projet EPIC-2106 : CI bloquante, runbook, packaging et chaîne de migrations inchangée.

## Exécution locale

```bash
python scripts/validate_kubernetes_topology.py --project-root . --output build/cloud-native/topology.json --enforce
python scripts/validate_kubernetes_exposure.py --project-root . --output build/cloud-native/exposure.json --enforce
python scripts/validate_kubernetes_security.py --project-root . --output build/cloud-native/security.json --enforce
python scripts/validate_kubernetes_gitops.py --project-root . --output build/cloud-native/gitops.json --enforce
python scripts/validate_kubernetes_capacity.py --project-root . --output build/cloud-native/capacity.json --enforce
python scripts/run_cloud_native_qualification.py --clusters 3 --resources 50000 --max-seconds 30 --output build/cloud-native/runtime.json --enforce
python scripts/validate_cloud_native_promotion.py --project-root . --output build/cloud-native/qualification.json --enforce
```

Utiliser ensuite un SHA-1 Git complet et lowercase :

```bash
python scripts/assemble_cloud_native_promotion_evidence.py \
  --candidate-id "openinfra-$(cat VERSION)-$(git rev-parse HEAD)" \
  --source-commit "$(git rev-parse HEAD)" \
  --topology build/cloud-native/topology.json \
  --exposure build/cloud-native/exposure.json \
  --security build/cloud-native/security.json \
  --gitops build/cloud-native/gitops.json \
  --capacity build/cloud-native/capacity.json \
  --runtime build/cloud-native/runtime.json \
  --qualification build/cloud-native/qualification.json \
  --evidence-root build/cloud-native/evidence \
  --output build/cloud-native/manifest.json

python scripts/certify_cloud_native_promotion.py \
  --policy docs/release/cloud-native-promotion-policy.json \
  --manifest build/cloud-native/manifest.json \
  --evidence-root build/cloud-native/evidence \
  --output build/cloud-native/certification-report.json \
  --enforce
```

## Conditions de rejet

La certification est rejetée si :

- une des sept preuves manque ;
- un hash SHA-256 diffère ;
- un chemin sort du répertoire de preuves ;
- une preuve est trop ancienne ou datée dans le futur ;
- la version ne correspond pas à la version installée ;
- le benchmark n’atteint pas trois clusters ou 50 000 ressources ;
- un secret peut être ingéré, une référence inter-namespace est acceptée ou un mapping physique orphelin est accepté ;
- la remédiation GitOps automatique est activée ;
- la chaîne PostgreSQL ne contient plus exactement 58 migrations terminant par `0058_oracle_document_shards.sql`, après la preuve historique `0056_kubernetes_gitops_drift.sql`.

## Exploitation et rollback

GATE-10 est un mécanisme de décision sans mutation. Un rejet ne nécessite aucun rollback applicatif : corriger la preuve ou la régression, régénérer toutes les preuves depuis le même commit, puis relancer la certification. Ne jamais réutiliser une preuve produite par un autre commit ou une autre version.
