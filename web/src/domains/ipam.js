const moduleDefinition = {
  "id": "ipam",
  "label": "IPAM",
  "icon": "grid",
  "operations": [
    {
      "id": "ipam-dashboard",
      "label": "Dashboard IPAM",
      "path": "/v1/ipam/ui-dashboard",
      "method": "GET",
      "fields": [
        "VRF"
      ]
    },
    {
      "id": "ipam-search",
      "label": "Rechercher dans l’IPAM",
      "path": "/v1/ipam/ui-search",
      "method": "GET",
      "fields": [
        "Recherche",
        "VRF"
      ]
    },
    {
      "id": "ipam-define-vrf",
      "label": "Définir une VRF",
      "path": "/v1/ipam/vrfs",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Nom VRF",
        "Route distinguisher"
      ]
    },
    {
      "id": "ipam-define-aggregate",
      "label": "Définir un agrégat IP",
      "path": "/v1/ipam/aggregates",
      "method": "POST",
      "fields": [
        "Opérateur",
        "VRF",
        "CIDR agrégat",
        "Description"
      ]
    },
    {
      "id": "ipam-define-prefix",
      "label": "Définir un préfixe IP",
      "path": "/v1/ipam/prefixes",
      "method": "POST",
      "fields": [
        "Opérateur",
        "VRF",
        "CIDR préfixe",
        "Description"
      ]
    },
    {
      "id": "ipam-list-prefixes",
      "label": "Lister les préfixes",
      "path": "/v1/ipam/prefixes",
      "method": "GET",
      "fields": [
        "VRF"
      ]
    },
    {
      "id": "ipam-define-range",
      "label": "Définir une plage IP",
      "path": "/v1/ipam/ranges",
      "method": "POST",
      "fields": [
        "Opérateur",
        "VRF",
        "Préfixe",
        "Début plage",
        "Fin plage",
        "Usage plage",
        "Description"
      ]
    },
    {
      "id": "ipam-register-address",
      "label": "Enregistrer une adresse IP",
      "path": "/v1/ipam/addresses",
      "method": "POST",
      "fields": [
        "Opérateur",
        "VRF",
        "Préfixe",
        "Adresse IP",
        "Nom DNS / équipement",
        "Interface",
        "Statut adresse"
      ]
    },
    {
      "id": "ipam-allocate",
      "label": "Allouer une adresse IP",
      "path": "/v1/ipam/allocate",
      "method": "POST",
      "fields": [
        "Opérateur",
        "VRF",
        "Préfixe",
        "Nom DNS / équipement",
        "Clé d’idempotence"
      ]
    },
    {
      "id": "ipam-reservation-wizard",
      "label": "Assistant de réservation IP",
      "path": "/v1/ipam/reservation-wizard",
      "method": "POST",
      "fields": [
        "Opérateur",
        "VRF",
        "Préfixe",
        "Nom DNS / équipement",
        "Clé d’idempotence",
        "Appliquer la réservation"
      ]
    },
    {
      "id": "ipam-capacity",
      "label": "Calculer la capacité d’un préfixe",
      "path": "/v1/ipam/capacity",
      "method": "GET",
      "fields": [
        "VRF",
        "Préfixe"
      ]
    },
    {
      "id": "ipam-network-bindings",
      "label": "Afficher les bindings réseau",
      "path": "/v1/ipam/network-bindings",
      "method": "GET",
      "fields": [
        "VRF"
      ]
    },
    {
      "id": "ipam-topology",
      "label": "Topologie opérationnelle IPAM",
      "path": "/v1/ipam/topology",
      "method": "GET",
      "fields": [
        "VRF"
      ]
    },
    {
      "id": "ipam-define-vlan-group",
      "label": "Définir un groupe VLAN",
      "path": "/v1/ipam/vlan-groups",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Groupe VLAN",
        "Scope VLAN",
        "Description"
      ]
    },
    {
      "id": "ipam-define-vxlan-vni",
      "label": "Définir un VXLAN VNI",
      "path": "/v1/ipam/vxlan-vnis",
      "method": "POST",
      "fields": [
        "Opérateur",
        "VNI",
        "Nom VNI",
        "VRF",
        "RT import",
        "RT export",
        "Description"
      ]
    },
    {
      "id": "ipam-define-vlan",
      "label": "Définir un VLAN",
      "path": "/v1/ipam/vlans",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Groupe VLAN",
        "VLAN ID",
        "Nom VLAN",
        "VRF",
        "VNI",
        "Description"
      ]
    },
    {
      "id": "ipam-define-asn",
      "label": "Définir un ASN",
      "path": "/v1/ipam/asns",
      "method": "POST",
      "fields": [
        "Opérateur",
        "ASN",
        "Nom AS",
        "Description"
      ]
    },
    {
      "id": "ipam-define-bgp-peer",
      "label": "Définir un peer BGP",
      "path": "/v1/ipam/bgp-peers",
      "method": "POST",
      "fields": [
        "Opérateur",
        "VRF",
        "ASN local",
        "ASN distant",
        "Adresse peer",
        "Famille d’adresses",
        "RT import",
        "RT export",
        "Description"
      ]
    },
    {
      "id": "ipam-observe-dns",
      "label": "Observer un enregistrement DNS",
      "path": "/v1/ipam/dns-observations",
      "method": "POST",
      "fields": [
        "Opérateur",
        "VRF",
        "Nom DNS",
        "Adresse IP",
        "Nom PTR",
        "Source observation"
      ]
    },
    {
      "id": "ipam-observe-dhcp",
      "label": "Observer un bail DHCP",
      "path": "/v1/ipam/dhcp-leases",
      "method": "POST",
      "fields": [
        "Opérateur",
        "VRF",
        "Préfixe",
        "Adresse IP",
        "Adresse MAC",
        "Nom DHCP",
        "Source observation",
        "Bail actif"
      ]
    },
    {
      "id": "ipam-conflicts",
      "label": "Détecter les conflits",
      "path": "/v1/ipam/conflicts",
      "method": "GET",
      "fields": [
        "VRF"
      ]
    },
    {
      "id": "ipam-ddi-preview",
      "label": "Prévisualiser DDI",
      "path": "/v1/ipam/ddi-preview",
      "method": "POST",
      "fields": [
        "Opérateur",
        "VRF",
        "Clé d’idempotence",
        "Fournisseurs DDI",
        "Zone DNS",
        "Adresse MAC",
        "TTL",
        "Appliquer la prévisualisation"
      ]
    },
    {
      "id": "ipam-ddi-sync",
      "label": "Synchroniser DNS/DHCP",
      "path": "/v1/ipam/ddi-sync",
      "method": "POST",
      "fields": [
        "Opérateur",
        "VRF",
        "Clé réservation",
        "Clé exécution",
        "Fournisseurs DDI",
        "Zone DNS",
        "Zone DNS inverse",
        "Adresse MAC",
        "TTL",
        "Reprendre une exécution"
      ]
    },
    {
      "id": "network-config-baseline-upsert",
      "label": "Créer ou réviser une golden configuration",
      "path": "/v1/network-config/baselines/upsert",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Code",
        "Objet équipement RSOT",
        "Plateforme réseau",
        "Configuration attendue JSON",
        "Chemins ignorés",
        "Chemins critiques",
        "Propriétaire",
        "Justification"
      ]
    },
    {
      "id": "network-config-baseline-list",
      "label": "Lister les golden configurations",
      "path": "/v1/network-config/baselines",
      "method": "GET",
      "fields": [
        "Limite",
        "Curseur",
        "Inclure retirés"
      ]
    },
    {
      "id": "network-config-baseline-retire",
      "label": "Retirer une golden configuration",
      "path": "/v1/network-config/baselines/retire",
      "method": "POST",
      "fields": [
        "Opérateur",
        "ID baseline"
      ]
    },
    {
      "id": "network-config-observation-submit",
      "label": "Ingérer une configuration découverte",
      "path": "/v1/network-config/observations/submit",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Clé d’idempotence",
        "Source observation",
        "Collecteur",
        "Objet équipement RSOT",
        "Plateforme réseau",
        "Configuration observée JSON",
        "Observé le (ISO-8601)"
      ]
    },
    {
      "id": "network-config-observation-list",
      "label": "Lister les configurations découvertes",
      "path": "/v1/network-config/observations",
      "method": "GET",
      "fields": [
        "Objet équipement RSOT",
        "Plateforme réseau",
        "Observé avant",
        "Limite",
        "Curseur"
      ]
    },
    {
      "id": "network-config-assessment",
      "label": "Évaluer la dérive réseau",
      "path": "/v1/network-config/assessment",
      "method": "GET",
      "fields": [
        "Opérateur",
        "Code baseline",
        "Date de référence",
        "Statut conformité",
        "Limite",
        "Curseur"
      ]
    },
    {
      "id": "flow-declaration-upsert",
      "label": "Créer ou réviser un flux déclaré",
      "path": "/v1/flows/declarations/upsert",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Code",
        "Sélecteur source",
        "Sélecteur destination",
        "Protocole",
        "Port destination début",
        "Port destination fin",
        "Décision",
        "Priorité",
        "Propriétaire",
        "Justification",
        "Début validité",
        "Fin validité"
      ]
    },
    {
      "id": "flow-declaration-list",
      "label": "Lister les flux déclarés",
      "path": "/v1/flows/declarations",
      "method": "GET",
      "fields": [
        "Limite",
        "Curseur",
        "Inclure retirés"
      ]
    },
    {
      "id": "flow-declaration-retire",
      "label": "Retirer un flux déclaré",
      "path": "/v1/flows/declarations/retire",
      "method": "POST",
      "fields": [
        "Opérateur",
        "ID déclaration"
      ]
    },
    {
      "id": "flow-observation-submit",
      "label": "Ingérer un flux observé",
      "path": "/v1/flows/observations/submit",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Clé d’idempotence",
        "Source observation",
        "Collecteur",
        "IP source",
        "IP destination",
        "Objet source",
        "Objet destination",
        "Protocole",
        "Port destination",
        "Paquets",
        "Octets",
        "Premier événement",
        "Dernier événement"
      ]
    },
    {
      "id": "flow-observation-list",
      "label": "Lister les flux observés",
      "path": "/v1/flows/observations",
      "method": "GET",
      "fields": [
        "Début fenêtre",
        "Fin fenêtre",
        "Source observation",
        "Limite",
        "Curseur"
      ]
    },
    {
      "id": "flow-matrix",
      "label": "Comparer flux déclarés et observés",
      "path": "/v1/flows/matrix",
      "method": "GET",
      "fields": [
        "Début fenêtre",
        "Fin fenêtre",
        "Statut conformité",
        "Source observation",
        "Limite",
        "Curseur"
      ]
    }
  ]
};

export { moduleDefinition };
export default moduleDefinition;
