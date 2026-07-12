const moduleDefinition = {
  "id": "rsot",
  "label": "RSOT (Ressource Source of Truth)",
  "shortLabel": "RSOT",
  "icon": "reference",
  "operations": [
    {
      "id": "rsot-taxonomy",
      "label": "Catalogue catégories / types",
      "path": "/v1/rsot/resource-taxonomy",
      "method": "GET",
      "fields": []
    },
    {
      "id": "rsot-list",
      "label": "Lister les objets RSOT",
      "path": "/v1/rsot/objects",
      "method": "GET",
      "fields": [
        "Catégorie",
        "Type de ressource",
        "Tag",
        "Limite"
      ]
    },
    {
      "id": "rsot-upsert",
      "label": "Créer / mettre à jour une ressource",
      "path": "/v1/rsot/objects",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Clé RSOT",
        "Catégorie",
        "Type de ressource",
        "Nom affiché",
        "Source autoritative",
        "Numéro de série",
        "Constructeur accrédité",
        "Modèle",
        "Site",
        "Bâtiment",
        "Salle",
        "Ligne salle",
        "Colonne salle",
        "Rack",
        "IP de management",
        "État cycle de vie",
        "Tags"
      ]
    },
    {
      "id": "rsot-as-of",
      "label": "Restituer une ressource à date",
      "path": "/v1/rsot/object-as-of",
      "method": "GET",
      "fields": [
        "Clé RSOT",
        "Date ISO-8601"
      ]
    },
    {
      "id": "rsot-object-audit",
      "label": "Audit d’une ressource",
      "path": "/v1/rsot/object-audit",
      "method": "GET",
      "fields": [
        "Clé RSOT",
        "Limite"
      ]
    },
    {
      "id": "rsot-reconcile",
      "label": "Réconcilier une ressource",
      "path": "/v1/rsot/reconcile-object",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Clé RSOT",
        "Source entrante",
        "Catégorie",
        "Type de ressource",
        "Nom affiché cible",
        "Numéro de série",
        "Constructeur accrédité",
        "Modèle",
        "Site",
        "Rack",
        "Tags",
        "Appliquer le plan"
      ]
    },
    {
      "id": "graph-traverse",
      "label": "Explorer le graphe de dépendances",
      "path": "/v1/graph/traverse",
      "method": "GET",
      "fields": [
        {
          "name": "root_key",
          "label": "Clé racine",
          "required": true
        },
        {
          "name": "direction",
          "label": "Direction",
          "type": "select",
          "options": [
            "outgoing",
            "incoming",
            "both"
          ],
          "defaultValue": "both"
        },
        {
          "name": "max_depth",
          "label": "Profondeur maximale",
          "type": "number",
          "defaultValue": "3"
        },
        {
          "name": "max_nodes",
          "label": "Nombre maximal de nœuds",
          "type": "number",
          "defaultValue": "500"
        },
        {
          "name": "relation_type",
          "label": "Type de relation"
        },
        {
          "name": "as_of",
          "label": "Date ISO-8601"
        }
      ]
    },
    {
      "id": "graph-impact",
      "label": "Analyser les impacts",
      "path": "/v1/graph/impact",
      "method": "GET",
      "fields": [
        {
          "name": "root_key",
          "label": "Clé racine",
          "required": true
        },
        {
          "name": "direction",
          "label": "Direction",
          "type": "select",
          "options": [
            "incoming",
            "outgoing",
            "both"
          ],
          "defaultValue": "incoming"
        },
        {
          "name": "max_depth",
          "label": "Profondeur maximale",
          "type": "number",
          "defaultValue": "6"
        },
        {
          "name": "max_nodes",
          "label": "Nombre maximal de nœuds",
          "type": "number",
          "defaultValue": "1000"
        },
        {
          "name": "relation_type",
          "label": "Type de relation"
        },
        {
          "name": "as_of",
          "label": "Date ISO-8601"
        }
      ]
    },
    {
      "id": "graph-path",
      "label": "Trouver le chemin le plus court",
      "path": "/v1/graph/path",
      "method": "GET",
      "fields": [
        {
          "name": "source_key",
          "label": "Ressource source",
          "required": true
        },
        {
          "name": "target_key",
          "label": "Ressource cible",
          "required": true
        },
        {
          "name": "direction",
          "label": "Direction",
          "type": "select",
          "options": [
            "outgoing",
            "incoming",
            "both"
          ],
          "defaultValue": "outgoing"
        },
        {
          "name": "max_depth",
          "label": "Profondeur maximale",
          "type": "number",
          "defaultValue": "8"
        },
        {
          "name": "max_nodes",
          "label": "Nombre maximal de nœuds",
          "type": "number",
          "defaultValue": "1000"
        },
        {
          "name": "relation_type",
          "label": "Type de relation"
        },
        {
          "name": "as_of",
          "label": "Date ISO-8601"
        }
      ]
    },
    {
      "id": "graph-spof",
      "label": "Détecter les points uniques de défaillance",
      "path": "/v1/graph/spof",
      "method": "GET",
      "fields": [
        {
          "name": "root_key",
          "label": "Clé racine",
          "required": true
        },
        {
          "name": "direction",
          "label": "Direction",
          "type": "select",
          "options": [
            "outgoing",
            "incoming",
            "both"
          ],
          "defaultValue": "both"
        },
        {
          "name": "max_depth",
          "label": "Profondeur maximale",
          "type": "number",
          "defaultValue": "8"
        },
        {
          "name": "max_nodes",
          "label": "Nombre maximal de nœuds",
          "type": "number",
          "defaultValue": "2000"
        },
        {
          "name": "relation_type",
          "label": "Type de relation"
        },
        {
          "name": "as_of",
          "label": "Date ISO-8601"
        },
        {
          "name": "candidate_kind",
          "label": "Type de candidat"
        },
        {
          "name": "candidate_resource_category",
          "label": "Catégorie ressource candidate"
        },
        {
          "name": "candidate_resource_type",
          "label": "Type de ressource candidat"
        },
        {
          "name": "candidate_status",
          "label": "Statut candidat"
        },
        {
          "name": "minimum_affected_nodes",
          "label": "Nombre minimal d’objets affectés",
          "type": "number",
          "defaultValue": "1"
        },
        {
          "name": "affected_sample_limit",
          "label": "Limite échantillon affecté",
          "type": "number",
          "defaultValue": "25"
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "defaultValue": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur"
        }
      ]
    },
    {
      "id": "graph-export",
      "label": "Exporter le graphe de dépendances",
      "path": "/v1/graph/export",
      "method": "GET",
      "download": true,
      "fields": [
        {
          "name": "root_key",
          "label": "Clé racine",
          "required": true
        },
        {
          "name": "format",
          "label": "Format d’export",
          "type": "select",
          "options": [
            "json",
            "csv",
            "graphml"
          ],
          "defaultValue": "json"
        },
        {
          "name": "direction",
          "label": "Direction",
          "type": "select",
          "options": [
            "outgoing",
            "incoming",
            "both"
          ],
          "defaultValue": "both"
        },
        {
          "name": "max_depth",
          "label": "Profondeur maximale",
          "type": "number",
          "defaultValue": "8"
        },
        {
          "name": "max_nodes",
          "label": "Nombre maximal de nœuds",
          "type": "number",
          "defaultValue": "2000"
        },
        {
          "name": "relation_type",
          "label": "Type de relation"
        },
        {
          "name": "as_of",
          "label": "Date ISO-8601"
        },
        {
          "name": "include_spof",
          "label": "Inclure les SPOF",
          "type": "boolean",
          "defaultValue": "true"
        },
        {
          "name": "candidate_kind",
          "label": "Type de candidat"
        },
        {
          "name": "candidate_resource_category",
          "label": "Catégorie ressource candidate"
        },
        {
          "name": "candidate_resource_type",
          "label": "Type de ressource candidat"
        },
        {
          "name": "candidate_status",
          "label": "Statut candidat"
        },
        {
          "name": "minimum_affected_nodes",
          "label": "Nombre minimal d’objets affectés",
          "type": "number",
          "defaultValue": "1"
        }
      ]
    },
    {
      "id": "simulation-create",
      "label": "Créer un scénario de changement",
      "path": "/v1/simulation-scenarios/create",
      "method": "POST",
      "fields": [
        "Opérateur",
        {
          "name": "name",
          "label": "Nom du scénario",
          "required": true
        },
        {
          "name": "description",
          "label": "Description",
          "type": "textarea",
          "required": true
        },
        {
          "name": "owner",
          "label": "Propriétaire",
          "required": true
        },
        {
          "name": "idempotency_key",
          "label": "Clé d’idempotence",
          "required": true
        },
        {
          "name": "site",
          "label": "Site"
        },
        {
          "name": "environment",
          "label": "Environnement"
        },
        {
          "name": "criticality",
          "label": "Criticité",
          "type": "select",
          "options": [
            "low",
            "medium",
            "high",
            "critical"
          ]
        },
        {
          "name": "changes",
          "label": "Changements JSON",
          "type": "json",
          "required": true,
          "defaultValue": "[]"
        }
      ]
    },
    {
      "id": "simulation-list",
      "label": "Lister les scénarios",
      "path": "/v1/simulation-scenarios",
      "method": "GET",
      "fields": [
        {
          "name": "status",
          "label": "Statut",
          "type": "select",
          "options": [
            "draft",
            "queued",
            "running",
            "completed",
            "failed",
            "cancelled"
          ]
        },
        {
          "name": "site",
          "label": "Site"
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "defaultValue": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur"
        }
      ]
    },
    {
      "id": "simulation-run",
      "label": "Calculer l’impact d’un scénario",
      "path": "/v1/simulation-scenarios/run",
      "method": "POST",
      "fields": [
        "Opérateur",
        {
          "name": "scenario_id",
          "label": "ID scénario",
          "required": true
        },
        {
          "name": "max_depth",
          "label": "Profondeur maximale",
          "type": "number",
          "defaultValue": "8"
        },
        {
          "name": "max_nodes",
          "label": "Nombre maximal de nœuds",
          "type": "number",
          "defaultValue": "2000"
        }
      ]
    },
    {
      "id": "simulation-reports",
      "label": "Lister les rapports d’impact",
      "path": "/v1/impact-reports",
      "method": "GET",
      "fields": [
        {
          "name": "scenario_id",
          "label": "ID scénario"
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "defaultValue": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur"
        }
      ]
    },
    {
      "id": "simulation-compare",
      "label": "Comparer deux rapports",
      "path": "/v1/scenario-comparisons/create",
      "method": "POST",
      "fields": [
        "Opérateur",
        {
          "name": "left_report_id",
          "label": "ID rapport gauche",
          "required": true
        },
        {
          "name": "right_report_id",
          "label": "ID rapport droit",
          "required": true
        }
      ]
    },
    {
      "id": "simulation-comparisons",
      "label": "Lister les comparaisons",
      "path": "/v1/scenario-comparisons",
      "method": "GET",
      "fields": [
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "defaultValue": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur"
        }
      ]
    },
    {
      "id": "rag-document-upsert",
      "label": "Indexer un document gouverné",
      "path": "/v1/rag/documents/upsert",
      "method": "POST",
      "fields": [
        {
          "name": "source_type",
          "label": "Type de source",
          "type": "select",
          "options": [
            "rsot",
            "documentation",
            "runbook",
            "policy",
            "other"
          ],
          "defaultValue": "documentation",
          "required": true
        },
        {
          "name": "source_ref",
          "label": "Référence source",
          "required": true
        },
        {
          "name": "title",
          "label": "Titre",
          "required": true
        },
        {
          "name": "content",
          "label": "Contenu",
          "type": "textarea",
          "required": true
        },
        {
          "name": "source_uri",
          "label": "URI source"
        },
        {
          "name": "required_permissions",
          "label": "Permissions requises",
          "type": "csv",
          "defaultValue": "rag.read"
        },
        {
          "name": "tags",
          "label": "Tags",
          "type": "csv"
        },
        {
          "name": "metadata",
          "label": "Métadonnées JSON",
          "type": "json",
          "defaultValue": "{}"
        },
        "Opérateur"
      ]
    },
    {
      "id": "rag-documents",
      "label": "Lister les documents gouvernés",
      "path": "/v1/rag/documents",
      "method": "GET",
      "fields": [
        {
          "name": "source_type",
          "label": "Type de source"
        },
        {
          "name": "active",
          "label": "Actif",
          "type": "boolean"
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "defaultValue": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur"
        }
      ]
    },
    {
      "id": "rag-document-get",
      "label": "Consulter un document gouverné",
      "path": "/v1/rag/documents/get",
      "method": "GET",
      "fields": [
        {
          "name": "document_id",
          "label": "ID document",
          "required": true
        }
      ]
    },
    {
      "id": "rag-document-deactivate",
      "label": "Désactiver un document gouverné",
      "path": "/v1/rag/documents/deactivate",
      "method": "POST",
      "fields": [
        {
          "name": "document_id",
          "label": "ID document",
          "required": true
        },
        "Opérateur"
      ]
    },
    {
      "id": "rag-rsot-sync",
      "label": "Synchroniser l’index depuis RSOT",
      "path": "/v1/rag/index/rsot",
      "method": "POST",
      "fields": [
        {
          "name": "max_objects",
          "label": "Nombre maximal d’objets",
          "type": "number",
          "defaultValue": "5000"
        },
        {
          "name": "deactivate_missing",
          "label": "Désactiver les objets absents",
          "type": "boolean",
          "defaultValue": "false"
        },
        "Opérateur"
      ]
    },
    {
      "id": "rag-query",
      "label": "Interroger l’assistant gouverné",
      "path": "/v1/rag/query",
      "method": "POST",
      "fields": [
        {
          "name": "question",
          "label": "Question",
          "type": "textarea",
          "required": true
        },
        {
          "name": "limit",
          "label": "Nombre maximal de citations",
          "type": "number",
          "defaultValue": "6"
        },
        "Opérateur"
      ]
    },
    {
      "id": "rag-answers",
      "label": "Lister les réponses citées",
      "path": "/v1/rag/answers",
      "method": "GET",
      "fields": [
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "defaultValue": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur"
        }
      ]
    },
    {
      "id": "rag-answer-get",
      "label": "Consulter une réponse citée",
      "path": "/v1/rag/answers/get",
      "method": "GET",
      "fields": [
        {
          "name": "answer_id",
          "label": "ID réponse",
          "required": true
        }
      ]
    },
    {
      "id": "rag-job-create",
      "label": "Créer un job RAG",
      "path": "/v1/rag/jobs/create",
      "method": "POST",
      "fields": [
        {
          "name": "kind",
          "label": "Type de job",
          "type": "select",
          "options": [
            "document-import",
            "answer-export"
          ],
          "required": true
        },
        {
          "name": "idempotency_key",
          "label": "Clé d’idempotence",
          "required": true
        },
        {
          "name": "payload",
          "label": "Charge utile JSON",
          "type": "json",
          "required": true,
          "defaultValue": "{}"
        },
        {
          "name": "batch_size",
          "label": "Taille de lot",
          "type": "number",
          "defaultValue": "100"
        },
        "Opérateur"
      ]
    },
    {
      "id": "rag-jobs",
      "label": "Lister les jobs RAG",
      "path": "/v1/rag/jobs",
      "method": "GET",
      "fields": [
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "defaultValue": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur"
        }
      ]
    },
    {
      "id": "rag-job-get",
      "label": "Consulter un job RAG",
      "path": "/v1/rag/jobs/get",
      "method": "GET",
      "fields": [
        {
          "name": "job_id",
          "label": "ID job",
          "required": true
        }
      ]
    },
    {
      "id": "rag-job-run",
      "label": "Exécuter une tranche de job RAG",
      "path": "/v1/rag/jobs/run",
      "method": "POST",
      "fields": [
        {
          "name": "job_id",
          "label": "ID job",
          "required": true
        },
        "Opérateur"
      ]
    },
    {
      "id": "rag-job-artifact",
      "label": "Télécharger un export RAG",
      "path": "/v1/rag/jobs/artifact",
      "method": "GET",
      "download": true,
      "fields": [
        {
          "name": "job_id",
          "label": "ID job",
          "required": true
        }
      ]
    }
  ]
};

export { moduleDefinition };
export default moduleDefinition;
