const moduleDefinition = {
  "id": "discovery",
  "label": "Discovery",
  "icon": "activity",
  "operations": [
    {
      "id": "discovery-evidence-list",
      "label": "Lister les preuves immuables",
      "path": "/v1/discovery/evidence-list",
      "method": "GET",
      "fields": [
        "Clé objet",
        "Limite"
      ]
    },
    {
      "id": "discovery-evidence",
      "label": "Voir une preuve immuable",
      "path": "/v1/discovery/evidence",
      "method": "GET",
      "fields": [
        "ID preuve"
      ]
    },
    {
      "id": "discovery-evidence-submit",
      "label": "Enregistrer une preuve Discovery",
      "path": "/v1/discovery/evidence",
      "method": "POST",
      "fields": [
        "Opérateur",
        "ID preuve imposé",
        "Clé objet",
        "Type objet",
        "Source",
        "Référence source",
        "Scope",
        "ID externe",
        "Confiance",
        "Observé le",
        "Preuve JSON sans secret"
      ]
    },
    {
      "id": "discovery-reconciliation-list",
      "label": "Lister les rapprochements",
      "path": "/v1/discovery/reconciliation-list",
      "method": "GET",
      "fields": [
        "Statut",
        "Limite"
      ]
    },
    {
      "id": "discovery-reconciliation",
      "label": "Voir un rapprochement",
      "path": "/v1/discovery/reconciliation",
      "method": "GET",
      "fields": [
        "ID rapprochement"
      ]
    },
    {
      "id": "discovery-reconcile",
      "label": "Rapprocher plusieurs preuves",
      "path": "/v1/discovery/reconciliation",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Clé objet",
        "IDs preuves",
        "Âge maximal"
      ]
    },
    {
      "id": "discovery-reconciliation-resolve",
      "label": "Résoudre les conflits",
      "path": "/v1/discovery/reconciliation/resolve",
      "method": "POST",
      "fields": [
        "Opérateur",
        "ID rapprochement",
        "Sélections par chemin JSON",
        "Justification"
      ]
    },
    {
      "id": "local-discovery-plan",
      "label": "Plan discovery locale Lite/Pro",
      "path": "/v1/discovery/local-plan",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Nom plan",
        "Scope",
        "Protocole",
        "Cibles",
        "Référence secret",
        "Concurrence max",
        "Rate limit/min"
      ]
    },
    {
      "id": "agent-bootstrap-plan",
      "label": "Plan bootstrap agent Enterprise",
      "path": "/v1/discovery/agent-bootstrap-plan",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Nom agent",
        "Rôle agent",
        "Scopes autorisés",
        "URL backend HTTPS",
        "Empreinte certificat",
        "Référence secret enrollment",
        "Version agent",
        "Compte service",
        "Chemin configuration",
        "Répertoire état",
        "Répertoire logs"
      ]
    },
    {
      "id": "kubernetes-topologies-list",
      "label": "Lister les instantanés Kubernetes",
      "path": "/v1/kubernetes/topologies",
      "method": "GET",
      "fields": [
        {"name": "limit", "label": "Limite", "type": "number", "defaultValue": "100", "min": 1, "max": 500},
        {"name": "cursor", "label": "Curseur"},
        {"name": "cluster_key", "label": "Clé cluster"},
        {"name": "provider", "label": "Fournisseur Kubernetes"},
        {"name": "site_code", "label": "Code site"}
      ]
    },
    {
      "id": "kubernetes-topology-latest",
      "label": "Consulter le dernier inventaire Kubernetes",
      "path": "/v1/kubernetes/topologies/latest",
      "method": "GET",
      "fields": [
        {"name": "cluster_key", "label": "Clé cluster", "required": true}
      ]
    },
    {
      "id": "kubernetes-topology-graph",
      "label": "Afficher la topologie Kubernetes et physique",
      "path": "/v1/kubernetes/topologies/latest-topology",
      "method": "GET",
      "fields": [
        {"name": "cluster_key", "label": "Clé cluster", "required": true}
      ]
    },
    {
      "id": "kubernetes-exposure-latest",
      "label": "Analyser les expositions réseau cloud-native",
      "path": "/v1/kubernetes/topologies/latest-exposure",
      "method": "GET",
      "fields": [
        {"name": "cluster_key", "label": "Clé cluster", "required": true}
      ]
    },
    {
      "id": "kubernetes-exposure-snapshot",
      "label": "Analyser les expositions d’un instantané Kubernetes",
      "path": "/v1/kubernetes/topologies/exposure",
      "method": "GET",
      "fields": [
        {"name": "snapshot_id", "label": "ID instantané", "required": true}
      ]
    },
    {
      "id": "kubernetes-topology-import",
      "label": "Importer un inventaire Kubernetes",
      "path": "/v1/kubernetes/topologies/import",
      "method": "POST",
      "fields": [
        {"name": "actor", "label": "Opérateur", "required": true, "defaultValue": "web"},
        {"name": "cluster_key", "label": "Clé cluster", "required": true},
        {"name": "cluster_name", "label": "Nom cluster", "required": true},
        {"name": "provider", "label": "Fournisseur Kubernetes", "required": true},
        {"name": "kubernetes_version", "label": "Version Kubernetes", "required": true},
        {"name": "region", "label": "Région"},
        {"name": "site_code", "label": "Code site"},
        {"name": "source_ref", "label": "Référence source", "required": true},
        {"name": "observed_at", "label": "Observé le", "format": "date-time", "required": true},
        {"name": "resources", "label": "Ressources Kubernetes (JSON)", "type": "json", "required": true, "defaultValue": "[]"}
      ]
    },
    {
      "id": "collectors-register",
      "label": "Enregistrer un agent proxy Enterprise",
      "path": "/v1/discovery/collectors",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Nom agent proxy",
        "Type",
        "Empreinte certificat",
        "Scopes autorisés",
        "Version agent",
        "Endpoint mTLS"
      ]
    }
  ]
};

export { moduleDefinition };
export default moduleDefinition;
