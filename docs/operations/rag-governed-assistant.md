# Assistant RAG gouverné OpenInfra

## Objectif

Le module **RSOT → Assistant gouverné** recherche dans un index documentaire contrôlé, puis produit une réponse extractive accompagnée de citations. Il ne remplace pas le RSOT, ne modifie aucune ressource et ne peut déclencher aucune action d’infrastructure.

## Modèle de sécurité

Chaque document porte une liste non vide de permissions OpenInfra. L’isolation est appliquée dans cet ordre :

1. tenant ;
2. état actif du document ;
3. permissions exigées par le document ;
4. recherche et classement des fragments autorisés seulement.

Le filtrage intervient **avant** la génération de la réponse. Une source interdite ne peut donc apparaître ni dans les citations ni dans le texte généré. Les permissions dédiées sont `rag.read`, `rag.write`, `rag.import`, `rag.export`, `rag.query` et `rag.admin`.

## Génération et citations

Le moteur par défaut `openinfra-extractive-rag-v1` est local, déterministe et sans appel réseau. Une réponse `answered` exige au moins une citation. En l’absence de contexte autorisé suffisamment pertinent, le statut est `insufficient-context` et aucune citation n’est retournée.

L’audit conserve l’empreinte SHA-256 de la question, le statut, le nombre de citations et le niveau de confiance. Il ne conserve pas la question en clair dans les métadonnées d’audit.

## Sources et versionnement

Les sources prises en charge sont : `rsot`, `runbook`, `policy`, `documentation` et `other`. Une révision crée une nouvelle version immuable et désactive la version précédente. La synchronisation RSOT indexe une projection JSON en lecture seule ; elle n’écrit jamais dans le référentiel source.

## Imports et exports volumineux

Les jobs `document-import` et `answer-export` sont idempotents, bornés et exécutés par lots. Un job interrompu reste relançable à partir de `processed_count`. Les exports JSON ou CSV sont vérifiés par SHA-256 et téléchargés via la route d’artefact.

## Commandes principales

```bash
openinfra rag document-upsert --help
openinfra rag sync-rsot --help
openinfra rag ask --help
openinfra rag job-create --help
openinfra rag job-run --help
openinfra rag artifact --help
```

## API

Les 13 routes sont publiées sous `/api/v1/rag`. Le bearer token est obligatoire. Les charges JSON sont validées avant persistance, les métadonnées refusent récursivement les clés sensibles et les curseurs restent bornés par les contrats de pagination.

## Limites opérationnelles

- pas de modèle externe par défaut ;
- pas de scan de fichiers binaires ;
- pas d’exécution de commande ;
- pas de remédiation automatique ;
- pas de mutation RSOT/DCIM/IPAM ;
- résultat dépendant exclusivement des sources actives et autorisées.
