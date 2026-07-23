# Assistant RAG gouverné — preuve TST-FUNC-0010

## Objectif

Ce runbook qualifie le parcours bout-en-bout de l’assistant RAG (*Retrieval-Augmented Generation*, génération augmentée par recherche) sur le référentiel RSOT. Une réponse qualifiée doit citer les objets sources réellement utilisés et ne doit jamais modifier les données RSOT, DCIM, ITAM ou IPAM sans un mécanisme de validation explicite distinct.

## Garanties contractuelles

Chaque réponse `RagAnswer` expose :

- `citations` : fragments documentaires classés et autorisés ;
- `source_objects` : références RSOT dédupliquées avec clé objet, URI `openinfra:rsot/...`, document, fragment et score ;
- `governance.mode=read-only` ;
- `governance.source_data_mutation_performed=false` ;
- `governance.change_validation_required=true` ;
- `governance.execution_capabilities=[]`.

La persistance d’une réponse et de son audit n’est pas une mutation du référentiel source. Le test contractuel compare l’empreinte SHA-256 des collections `source_objects`, `source_object_snapshots` et `source_relations` avant et après les requêtes service, CLI et HTTP.

## Sécurité

- filtrage tenant et permissions avant génération ;
- aucune commande système, requête réseau de génération ou remédiation automatique ;
- aucune route `/v1/rag/execute`, `/v1/rag/remediate`, `/v1/rag/apply` ou `/v1/rag/mutate` ;
- question absente des métadonnées d’audit en clair ;
- journalisation du nombre d’objets sources et de la politique de non-mutation ;
- réponses `answered` impossibles sans citation.

## Parcours opératoire

1. créer ou mettre à jour les objets RSOT par les interfaces gouvernées existantes ;
2. synchroniser l’index en lecture seule avec `openinfra rag sync-rsot` ;
3. interroger avec `openinfra rag ask` ou `POST /api/v1/rag/query` ;
4. vérifier les tables de citations et d’objets sources dans les portails ;
5. traiter toute demande de modification via une opération métier distincte, autorisée et validée — jamais via la réponse RAG.

## Validation ciblée

```bash
PYTHONPATH=src python -m pytest -q --no-cov \
  tests/integration/test_contract_functional_rag_assistant.py \
  tests/integration/test_rag_services.py \
  tests/integration/test_rag_cli.py \
  tests/integration/test_rag_http_api.py
node --test web/tests/rag.test.mjs web/tests/rag-governance.test.mjs
python scripts/validate_openapi.py \
  docs/api/openapi.yaml \
  docs/specifications/OpenInfra-CDC-SFG-STG-v4.12.0/09-API/OpenAPI/openapi.yaml
```
