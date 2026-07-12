const moduleDefinition = {
  "id": "ipam",
  "label": "IPAM",
  "icon": "grid",
  "description": "IPv4/IPv6, VRF, préfixes, plages, VLAN/VXLAN, ASN/BGP, DNS/DHCP, DDI, conflits, capacité et allocations.",
  "operations": [
    {
      "id": "ipam-dashboard",
      "label": "Dashboard IPAM",
      "method": "GET",
      "path": "/v1/ipam/ui-dashboard",
      "query": [
        {
          "name": "vrf",
          "label": "VRF",
          "placeholder": "global"
        }
      ]
    },
    {
      "id": "ipam-search",
      "label": "Rechercher dans l’IPAM",
      "method": "GET",
      "path": "/v1/ipam/ui-search",
      "query": [
        {
          "name": "query",
          "label": "Recherche",
          "required": true,
          "placeholder": "10.20.0.0/24 ou srv-db"
        },
        {
          "name": "vrf",
          "label": "VRF",
          "placeholder": "global"
        }
      ]
    },
    {
      "id": "ipam-define-vrf",
      "label": "Définir une VRF",
      "method": "POST",
      "path": "/v1/ipam/vrfs",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "name",
          "label": "Nom VRF",
          "required": true,
          "placeholder": "global"
        },
        {
          "name": "route_distinguisher",
          "label": "Route distinguisher",
          "placeholder": "65000:100"
        }
      ]
    },
    {
      "id": "ipam-define-aggregate",
      "label": "Définir un agrégat IP",
      "method": "POST",
      "path": "/v1/ipam/aggregates",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "vrf",
          "label": "VRF",
          "required": true,
          "placeholder": "global"
        },
        {
          "name": "cidr",
          "label": "CIDR agrégat",
          "required": true,
          "placeholder": "10.20.0.0/16"
        },
        {
          "name": "description",
          "label": "Description",
          "placeholder": "Bloc site PAR1"
        }
      ]
    },
    {
      "id": "ipam-define-prefix",
      "label": "Définir un préfixe IP",
      "method": "POST",
      "path": "/v1/ipam/prefixes",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "vrf",
          "label": "VRF",
          "required": true,
          "placeholder": "global"
        },
        {
          "name": "cidr",
          "label": "CIDR préfixe",
          "required": true,
          "placeholder": "10.20.30.2/24"
        },
        {
          "name": "description",
          "label": "Description",
          "placeholder": "Réseau serveurs"
        }
      ]
    },
    {
      "id": "ipam-list-prefixes",
      "label": "Lister les préfixes",
      "method": "GET",
      "path": "/v1/ipam/prefixes",
      "query": [
        {
          "name": "vrf",
          "label": "VRF",
          "required": true,
          "placeholder": "global"
        }
      ]
    },
    {
      "id": "ipam-define-range",
      "label": "Définir une plage IP",
      "method": "POST",
      "path": "/v1/ipam/ranges",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "vrf",
          "label": "VRF",
          "required": true,
          "placeholder": "global"
        },
        {
          "name": "prefix",
          "label": "Préfixe",
          "required": true,
          "placeholder": "10.20.30.2/24"
        },
        {
          "name": "start",
          "label": "Début plage",
          "required": true,
          "placeholder": "10.20.30.20"
        },
        {
          "name": "end",
          "label": "Fin plage",
          "required": true,
          "placeholder": "10.20.30.200"
        },
        {
          "name": "purpose",
          "label": "Usage plage",
          "type": "select",
          "options": [
            {
              "value": "allocation",
              "label": "Allocation"
            },
            {
              "value": "reservation",
              "label": "Réservation"
            },
            {
              "value": "exclusion",
              "label": "Exclusion"
            }
          ],
          "defaultValue": "allocation"
        },
        {
          "name": "description",
          "label": "Description",
          "placeholder": "Pool applicatif"
        }
      ]
    },
    {
      "id": "ipam-register-address",
      "label": "Enregistrer une adresse IP",
      "method": "POST",
      "path": "/v1/ipam/addresses",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "vrf",
          "label": "VRF",
          "required": true,
          "placeholder": "global"
        },
        {
          "name": "prefix",
          "label": "Préfixe",
          "required": true,
          "placeholder": "10.20.30.2/24"
        },
        {
          "name": "address",
          "label": "Adresse IP",
          "required": true,
          "placeholder": "10.20.30.21"
        },
        {
          "name": "hostname",
          "label": "Nom DNS / équipement",
          "required": true,
          "placeholder": "srv-app-01"
        },
        {
          "name": "interface_name",
          "label": "Interface",
          "placeholder": "eth0"
        },
        {
          "name": "status",
          "label": "Statut adresse",
          "type": "select",
          "options": [
            {
              "value": "planned",
              "label": "Planifiée"
            },
            {
              "value": "reserved",
              "label": "Réservée"
            },
            {
              "value": "active",
              "label": "Active"
            },
            {
              "value": "deprecated",
              "label": "Dépréciée"
            }
          ],
          "defaultValue": "reserved"
        }
      ]
    },
    {
      "id": "ipam-allocate",
      "label": "Allouer une adresse IP",
      "method": "POST",
      "path": "/v1/ipam/allocate",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "vrf",
          "label": "VRF",
          "required": true,
          "placeholder": "global"
        },
        {
          "name": "prefix",
          "label": "Préfixe",
          "required": true,
          "placeholder": "10.20.30.2/24"
        },
        {
          "name": "hostname",
          "label": "Nom DNS / équipement",
          "required": true,
          "placeholder": "srv-app-01"
        },
        {
          "name": "idempotency_key",
          "label": "Clé d’idempotence",
          "required": true,
          "placeholder": "ipam-alloc-srv-app-01"
        }
      ]
    },
    {
      "id": "ipam-reservation-wizard",
      "label": "Assistant de réservation IP",
      "method": "POST",
      "path": "/v1/ipam/reservation-wizard",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "vrf",
          "label": "VRF",
          "required": true,
          "placeholder": "global"
        },
        {
          "name": "prefix",
          "label": "Préfixe",
          "required": true,
          "placeholder": "10.20.30.2/24"
        },
        {
          "name": "hostname",
          "label": "Nom DNS / équipement",
          "required": true,
          "placeholder": "srv-app-02"
        },
        {
          "name": "idempotency_key",
          "label": "Clé d’idempotence",
          "required": true,
          "placeholder": "ipam-wizard-srv-app-02"
        },
        {
          "name": "apply",
          "label": "Appliquer la réservation",
          "type": "boolean"
        }
      ]
    },
    {
      "id": "ipam-capacity",
      "label": "Calculer la capacité d’un préfixe",
      "method": "GET",
      "path": "/v1/ipam/capacity",
      "query": [
        {
          "name": "vrf",
          "label": "VRF",
          "required": true,
          "placeholder": "global"
        },
        {
          "name": "prefix",
          "label": "Préfixe",
          "required": true,
          "placeholder": "10.20.30.2/24"
        }
      ]
    },
    {
      "id": "ipam-network-bindings",
      "label": "Afficher les bindings réseau",
      "method": "GET",
      "path": "/v1/ipam/network-bindings",
      "query": [
        {
          "name": "vrf",
          "label": "VRF",
          "placeholder": "global"
        }
      ]
    },
    {
      "id": "ipam-topology",
      "label": "Topologie opérationnelle IPAM",
      "method": "GET",
      "path": "/v1/ipam/topology",
      "query": [
        {
          "name": "vrf",
          "label": "VRF",
          "placeholder": "global"
        }
      ]
    },
    {
      "id": "ipam-define-vlan-group",
      "label": "Définir un groupe VLAN",
      "method": "POST",
      "path": "/v1/ipam/vlan-groups",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "name",
          "label": "Groupe VLAN",
          "required": true,
          "placeholder": "dc-par1"
        },
        {
          "name": "scope",
          "label": "Scope VLAN",
          "placeholder": "site/PAR1"
        },
        {
          "name": "description",
          "label": "Description",
          "placeholder": "VLAN datacenter PAR1"
        }
      ]
    },
    {
      "id": "ipam-define-vxlan-vni",
      "label": "Définir un VXLAN VNI",
      "method": "POST",
      "path": "/v1/ipam/vxlan-vnis",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "vni",
          "label": "VNI",
          "type": "number",
          "required": true,
          "placeholder": "10010"
        },
        {
          "name": "name",
          "label": "Nom VNI",
          "required": true,
          "placeholder": "prod-app"
        },
        {
          "name": "vrf",
          "label": "VRF",
          "required": true,
          "placeholder": "global"
        },
        {
          "name": "route_targets_import",
          "label": "RT import",
          "type": "csv",
          "placeholder": "65000:10010"
        },
        {
          "name": "route_targets_export",
          "label": "RT export",
          "type": "csv",
          "placeholder": "65000:10010"
        },
        {
          "name": "description",
          "label": "Description",
          "placeholder": "Segment applicatif"
        }
      ]
    },
    {
      "id": "ipam-define-vlan",
      "label": "Définir un VLAN",
      "method": "POST",
      "path": "/v1/ipam/vlans",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "group",
          "label": "Groupe VLAN",
          "required": true,
          "placeholder": "dc-par1"
        },
        {
          "name": "vlan_id",
          "label": "VLAN ID",
          "type": "number",
          "required": true,
          "placeholder": "210"
        },
        {
          "name": "name",
          "label": "Nom VLAN",
          "required": true,
          "placeholder": "prod-app"
        },
        {
          "name": "vrf",
          "label": "VRF",
          "placeholder": "global"
        },
        {
          "name": "vni",
          "label": "VNI",
          "type": "number",
          "placeholder": "10010"
        },
        {
          "name": "description",
          "label": "Description",
          "placeholder": "Réseau applicatif"
        }
      ]
    },
    {
      "id": "ipam-define-asn",
      "label": "Définir un ASN",
      "method": "POST",
      "path": "/v1/ipam/asns",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "asn",
          "label": "ASN",
          "type": "number",
          "required": true,
          "placeholder": "65000"
        },
        {
          "name": "name",
          "label": "Nom AS",
          "required": true,
          "placeholder": "OpenInfra Core"
        },
        {
          "name": "description",
          "label": "Description",
          "placeholder": "Autonomous system interne"
        }
      ]
    },
    {
      "id": "ipam-define-bgp-peer",
      "label": "Définir un peer BGP",
      "method": "POST",
      "path": "/v1/ipam/bgp-peers",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "vrf",
          "label": "VRF",
          "required": true,
          "placeholder": "global"
        },
        {
          "name": "local_asn",
          "label": "ASN local",
          "type": "number",
          "required": true,
          "placeholder": "65000"
        },
        {
          "name": "remote_asn",
          "label": "ASN distant",
          "type": "number",
          "required": true,
          "placeholder": "65010"
        },
        {
          "name": "peer_address",
          "label": "Adresse peer",
          "required": true,
          "placeholder": "192.0.2.2"
        },
        {
          "name": "address_family",
          "label": "Famille d’adresses",
          "type": "select",
          "options": [
            {
              "value": "ipv4",
              "label": "IPv4"
            },
            {
              "value": "ipv6",
              "label": "IPv6"
            }
          ]
        },
        {
          "name": "route_targets_import",
          "label": "RT import",
          "type": "csv",
          "placeholder": "65000:10010"
        },
        {
          "name": "route_targets_export",
          "label": "RT export",
          "type": "csv",
          "placeholder": "65000:10010"
        },
        {
          "name": "description",
          "label": "Description",
          "placeholder": "Peer datacenter"
        }
      ]
    },
    {
      "id": "ipam-observe-dns",
      "label": "Observer un enregistrement DNS",
      "method": "POST",
      "path": "/v1/ipam/dns-observations",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "vrf",
          "label": "VRF",
          "required": true,
          "placeholder": "global"
        },
        {
          "name": "hostname",
          "label": "Nom DNS",
          "required": true,
          "placeholder": "srv-app-01.example.net"
        },
        {
          "name": "address",
          "label": "Adresse IP",
          "required": true,
          "placeholder": "10.20.30.21"
        },
        {
          "name": "ptr_hostname",
          "label": "Nom PTR",
          "placeholder": "srv-app-01.example.net"
        },
        {
          "name": "source",
          "label": "Source observation",
          "placeholder": "bind"
        }
      ]
    },
    {
      "id": "ipam-observe-dhcp",
      "label": "Observer un bail DHCP",
      "method": "POST",
      "path": "/v1/ipam/dhcp-leases",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "vrf",
          "label": "VRF",
          "required": true,
          "placeholder": "global"
        },
        {
          "name": "prefix",
          "label": "Préfixe",
          "required": true,
          "placeholder": "10.20.30.2/24"
        },
        {
          "name": "address",
          "label": "Adresse IP",
          "required": true,
          "placeholder": "10.20.31.14"
        },
        {
          "name": "mac_address",
          "label": "Adresse MAC",
          "required": true,
          "placeholder": "00:11:22:33:44:55"
        },
        {
          "name": "hostname",
          "label": "Nom DHCP",
          "required": true,
          "placeholder": "srv-dhcp-01"
        },
        {
          "name": "source",
          "label": "Source observation",
          "placeholder": "kea"
        },
        {
          "name": "active",
          "label": "Bail actif",
          "type": "boolean",
          "defaultValue": "true"
        }
      ]
    },
    {
      "id": "ipam-conflicts",
      "label": "Détecter les conflits",
      "method": "GET",
      "path": "/v1/ipam/conflicts",
      "query": [
        {
          "name": "vrf",
          "label": "VRF",
          "placeholder": "global"
        }
      ]
    },
    {
      "id": "ipam-ddi-preview",
      "label": "Prévisualiser DDI",
      "method": "POST",
      "path": "/v1/ipam/ddi-preview",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "vrf",
          "label": "VRF",
          "required": true,
          "placeholder": "global"
        },
        {
          "name": "idempotency_key",
          "label": "Clé d’idempotence",
          "required": true,
          "placeholder": "ipam-alloc-srv-app-01"
        },
        {
          "name": "providers",
          "label": "Fournisseurs DDI",
          "type": "csv",
          "placeholder": "bind,kea"
        },
        {
          "name": "dns_zone",
          "label": "Zone DNS",
          "placeholder": "example.net"
        },
        {
          "name": "mac_address",
          "label": "Adresse MAC",
          "placeholder": "00:11:22:33:44:55"
        },
        {
          "name": "ttl",
          "label": "TTL",
          "type": "number",
          "placeholder": "300"
        },
        {
          "name": "apply_preview",
          "label": "Appliquer la prévisualisation",
          "type": "boolean"
        }
      ]
    },
    {
      "id": "network-config-baseline-upsert",
      "label": "Créer ou réviser une golden configuration",
      "method": "POST",
      "path": "/v1/network-config/baselines/upsert",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "code",
          "label": "Code",
          "required": true
        },
        {
          "name": "device_object_key",
          "label": "Objet équipement RSOT",
          "required": true
        },
        {
          "name": "platform",
          "label": "Plateforme réseau",
          "required": true
        },
        {
          "name": "expected_config",
          "label": "Configuration attendue JSON",
          "type": "textarea",
          "required": true
        },
        {
          "name": "ignored_paths",
          "label": "Chemins ignorés",
          "type": "csv"
        },
        {
          "name": "critical_paths",
          "label": "Chemins critiques",
          "type": "csv"
        },
        {
          "name": "owner",
          "label": "Propriétaire",
          "required": true
        },
        {
          "name": "justification",
          "label": "Justification",
          "required": true
        }
      ]
    },
    {
      "id": "network-config-baseline-list",
      "label": "Lister les golden configurations",
      "method": "GET",
      "path": "/v1/network-config/baselines",
      "query": [
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "defaultValue": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur"
        },
        {
          "name": "include_retired",
          "label": "Inclure retirés",
          "type": "boolean"
        }
      ]
    },
    {
      "id": "network-config-baseline-retire",
      "label": "Retirer une golden configuration",
      "method": "POST",
      "path": "/v1/network-config/baselines/retire",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "baseline_id",
          "label": "ID baseline",
          "required": true
        }
      ]
    },
    {
      "id": "network-config-observation-submit",
      "label": "Ingérer une configuration découverte",
      "method": "POST",
      "path": "/v1/network-config/observations/submit",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "idempotency_key",
          "label": "Clé d’idempotence",
          "required": true
        },
        {
          "name": "source",
          "label": "Source observation",
          "type": "select",
          "options": [
            "ssh",
            "api",
            "netconf",
            "restconf",
            "gnmi",
            "discovery",
            "import",
            "manual"
          ],
          "required": true
        },
        {
          "name": "collector",
          "label": "Collecteur",
          "required": true
        },
        {
          "name": "device_object_key",
          "label": "Objet équipement RSOT",
          "required": true
        },
        {
          "name": "platform",
          "label": "Plateforme réseau",
          "required": true
        },
        {
          "name": "observed_config",
          "label": "Configuration observée JSON",
          "type": "textarea",
          "required": true
        },
        {
          "name": "observed_at",
          "label": "Observé le (ISO-8601)",
          "required": true
        }
      ]
    },
    {
      "id": "network-config-observation-list",
      "label": "Lister les configurations découvertes",
      "method": "GET",
      "path": "/v1/network-config/observations",
      "query": [
        {
          "name": "device_object_key",
          "label": "Objet équipement RSOT"
        },
        {
          "name": "platform",
          "label": "Plateforme réseau"
        },
        {
          "name": "observed_before",
          "label": "Observé avant"
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
      "id": "network-config-assessment",
      "label": "Évaluer la dérive réseau",
      "method": "GET",
      "path": "/v1/network-config/assessment",
      "query": [
        {
          "name": "actor",
          "label": "Opérateur",
          "defaultValue": "web"
        },
        {
          "name": "baseline_code",
          "label": "Code baseline"
        },
        {
          "name": "as_of",
          "label": "Date de référence",
          "format": "date-time"
        },
        {
          "name": "status",
          "label": "Statut conformité",
          "type": "select",
          "options": [
            "compliant",
            "drift",
            "missing-observation"
          ]
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
      "id": "flow-declaration-upsert",
      "label": "Créer ou réviser un flux déclaré",
      "method": "POST",
      "path": "/v1/flows/declarations/upsert",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "code",
          "label": "Code",
          "required": true,
          "placeholder": "APP-WEB-HTTPS"
        },
        {
          "name": "source_selector",
          "label": "Sélecteur source",
          "required": true,
          "placeholder": "object:application/portail"
        },
        {
          "name": "destination_selector",
          "label": "Sélecteur destination",
          "required": true,
          "placeholder": "cidr:10.20.30.2/24"
        },
        {
          "name": "protocol",
          "label": "Protocole",
          "type": "select",
          "options": [
            "any",
            "tcp",
            "udp",
            "sctp",
            "icmp",
            "icmpv6",
            "esp",
            "ah",
            "gre"
          ],
          "defaultValue": "tcp"
        },
        {
          "name": "destination_port_start",
          "label": "Port destination début",
          "type": "number",
          "placeholder": "443"
        },
        {
          "name": "destination_port_end",
          "label": "Port destination fin",
          "type": "number",
          "placeholder": "443"
        },
        {
          "name": "decision",
          "label": "Décision",
          "type": "select",
          "options": [
            "allow",
            "deny"
          ],
          "defaultValue": "allow"
        },
        {
          "name": "priority",
          "label": "Priorité",
          "type": "number",
          "defaultValue": "100"
        },
        {
          "name": "owner",
          "label": "Propriétaire",
          "required": true,
          "placeholder": "Équipe réseau"
        },
        {
          "name": "justification",
          "label": "Justification",
          "required": true,
          "placeholder": "Flux applicatif approuvé"
        },
        {
          "name": "valid_from",
          "label": "Début validité",
          "placeholder": "2026-07-10T00:00:00Z"
        },
        {
          "name": "valid_to",
          "label": "Fin validité",
          "placeholder": "2027-07-10T00:00:00Z"
        }
      ]
    },
    {
      "id": "flow-declaration-list",
      "label": "Lister les flux déclarés",
      "method": "GET",
      "path": "/v1/flows/declarations",
      "query": [
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "defaultValue": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur"
        },
        {
          "name": "include_retired",
          "label": "Inclure retirés",
          "type": "boolean"
        }
      ]
    },
    {
      "id": "flow-declaration-retire",
      "label": "Retirer un flux déclaré",
      "method": "POST",
      "path": "/v1/flows/declarations/retire",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "declaration_id",
          "label": "ID déclaration",
          "required": true
        }
      ]
    },
    {
      "id": "flow-observation-submit",
      "label": "Ingérer un flux observé",
      "method": "POST",
      "path": "/v1/flows/observations/submit",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "idempotency_key",
          "label": "Clé d’idempotence",
          "required": true,
          "placeholder": "collector-01:20260710:000001"
        },
        {
          "name": "source",
          "label": "Source observation",
          "type": "select",
          "options": [
            "netflow",
            "sflow",
            "ipfix",
            "firewall-log",
            "application-log",
            "import",
            "manual"
          ],
          "defaultValue": "netflow"
        },
        {
          "name": "collector",
          "label": "Collecteur",
          "required": true,
          "placeholder": "netflow-par-01"
        },
        {
          "name": "source_ip",
          "label": "IP source",
          "required": true,
          "placeholder": "10.10.1.10"
        },
        {
          "name": "destination_ip",
          "label": "IP destination",
          "required": true,
          "placeholder": "10.20.31.10"
        },
        {
          "name": "source_object_key",
          "label": "Objet source",
          "placeholder": "application/portail"
        },
        {
          "name": "destination_object_key",
          "label": "Objet destination",
          "placeholder": "server/web-01"
        },
        {
          "name": "protocol",
          "label": "Protocole",
          "type": "select",
          "options": [
            "tcp",
            "udp",
            "sctp",
            "icmp",
            "icmpv6",
            "esp",
            "ah",
            "gre"
          ],
          "defaultValue": "tcp"
        },
        {
          "name": "destination_port",
          "label": "Port destination",
          "type": "number",
          "placeholder": "443"
        },
        {
          "name": "packets",
          "label": "Paquets",
          "type": "number",
          "required": true,
          "placeholder": "10"
        },
        {
          "name": "bytes",
          "label": "Octets",
          "type": "number",
          "required": true,
          "placeholder": "2048"
        },
        {
          "name": "first_seen",
          "label": "Premier événement",
          "required": true,
          "placeholder": "2026-07-10T12:00:00Z"
        },
        {
          "name": "last_seen",
          "label": "Dernier événement",
          "required": true,
          "placeholder": "2026-07-10T12:05:00Z"
        }
      ]
    },
    {
      "id": "flow-observation-list",
      "label": "Lister les flux observés",
      "method": "GET",
      "path": "/v1/flows/observations",
      "query": [
        {
          "name": "window_start",
          "label": "Début fenêtre",
          "required": true,
          "placeholder": "2026-07-10T00:00:00Z"
        },
        {
          "name": "window_end",
          "label": "Fin fenêtre",
          "required": true,
          "placeholder": "2026-07-11T00:00:00Z"
        },
        {
          "name": "source",
          "label": "Source observation",
          "type": "select",
          "options": [
            "",
            "netflow",
            "sflow",
            "ipfix",
            "firewall-log",
            "application-log",
            "import",
            "manual"
          ]
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
      "id": "flow-matrix",
      "label": "Comparer flux déclarés et observés",
      "method": "GET",
      "path": "/v1/flows/matrix",
      "query": [
        {
          "name": "window_start",
          "label": "Début fenêtre",
          "placeholder": "2026-07-10T00:00:00Z"
        },
        {
          "name": "window_end",
          "label": "Fin fenêtre",
          "placeholder": "2026-07-11T00:00:00Z"
        },
        {
          "name": "status",
          "label": "Statut conformité",
          "type": "select",
          "options": [
            "",
            "compliant",
            "denied-observed",
            "undeclared-observed",
            "declared-unobserved"
          ]
        },
        {
          "name": "source",
          "label": "Source observation",
          "type": "select",
          "options": [
            "",
            "netflow",
            "sflow",
            "ipfix",
            "firewall-log",
            "application-log",
            "import",
            "manual"
          ]
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
    }
  ]
};

export { moduleDefinition };
export default moduleDefinition;
