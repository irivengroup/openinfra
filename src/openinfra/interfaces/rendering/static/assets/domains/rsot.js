const moduleDefinition = {
  "id": "rsot",
  "label": "RSOT (Ressource Source of Truth)",
  "shortLabel": "RSOT",
  "icon": "reference",
  "description": "Inventaire canonique, relations, versions, gouvernance et certification.",
  "operations": [
    {
      "id": "rsot-taxonomy",
      "label": "Catalogue catégories / types",
      "method": "GET",
      "path": "/v1/rsot/resource-taxonomy",
      "query": []
    },
    {
      "id": "rsot-list",
      "label": "Lister les objets RSOT",
      "method": "GET",
      "path": "/v1/rsot/objects",
      "query": [
        {
          "name": "resource_category",
          "label": "Catégorie",
          "type": "select",
          "options": [
            {
              "value": "server",
              "label": "Server"
            },
            {
              "value": "personal-computer",
              "label": "Personal computer"
            },
            {
              "value": "monitor-peripheral",
              "label": "Monitor and peripheral"
            },
            {
              "value": "network-device",
              "label": "Network device"
            },
            {
              "value": "storage",
              "label": "Storage"
            },
            {
              "value": "power-supply",
              "label": "Power supply"
            },
            {
              "value": "rack-facility",
              "label": "Rack and facility"
            },
            {
              "value": "cooling",
              "label": "Cooling"
            },
            {
              "value": "security-safety",
              "label": "Security and safety"
            },
            {
              "value": "telecom",
              "label": "Telecom"
            },
            {
              "value": "cloud-virtualization",
              "label": "Cloud and virtualization"
            },
            {
              "value": "software-service",
              "label": "Software and service"
            },
            {
              "value": "cable-connectivity",
              "label": "Cable and connectivity"
            },
            {
              "value": "mobile-iot",
              "label": "Mobile and IoT"
            },
            {
              "value": "other",
              "label": "Other"
            }
          ]
        },
        {
          "name": "resource_type",
          "label": "Type de ressource",
          "type": "select",
          "optionsByField": "resource_category",
          "optionsMap": {
            "server": [
              {
                "value": "rack-server",
                "label": "Rack server"
              },
              {
                "value": "blade-server",
                "label": "Blade server"
              },
              {
                "value": "tower-server",
                "label": "Tower server"
              },
              {
                "value": "hypervisor-host",
                "label": "Hypervisor host"
              },
              {
                "value": "virtual-machine",
                "label": "Virtual machine"
              },
              {
                "value": "container-host",
                "label": "Container host"
              },
              {
                "value": "compute-appliance",
                "label": "Compute appliance"
              }
            ],
            "personal-computer": [
              {
                "value": "laptop",
                "label": "Laptop"
              },
              {
                "value": "desktop",
                "label": "Desktop"
              },
              {
                "value": "workstation",
                "label": "Workstation"
              },
              {
                "value": "thin-client",
                "label": "Thin client"
              },
              {
                "value": "all-in-one",
                "label": "All-in-one"
              },
              {
                "value": "tablet",
                "label": "Tablet"
              },
              {
                "value": "kiosk",
                "label": "Kiosk"
              }
            ],
            "monitor-peripheral": [
              {
                "value": "monitor",
                "label": "Monitor"
              },
              {
                "value": "keyboard",
                "label": "Keyboard"
              },
              {
                "value": "mouse",
                "label": "Mouse"
              },
              {
                "value": "docking-station",
                "label": "Docking station"
              },
              {
                "value": "webcam",
                "label": "Webcam"
              },
              {
                "value": "headset",
                "label": "Headset"
              },
              {
                "value": "printer",
                "label": "Printer"
              },
              {
                "value": "scanner",
                "label": "Scanner"
              },
              {
                "value": "barcode-scanner",
                "label": "Barcode scanner"
              },
              {
                "value": "kvm-console",
                "label": "KVM console"
              }
            ],
            "network-device": [
              {
                "value": "switch",
                "label": "Switch"
              },
              {
                "value": "core-switch",
                "label": "Core switch"
              },
              {
                "value": "distribution-switch",
                "label": "Distribution switch"
              },
              {
                "value": "access-switch",
                "label": "Access switch"
              },
              {
                "value": "router",
                "label": "Router"
              },
              {
                "value": "firewall",
                "label": "Firewall"
              },
              {
                "value": "load-balancer",
                "label": "Load balancer"
              },
              {
                "value": "vpn-gateway",
                "label": "VPN gateway"
              },
              {
                "value": "sdwan-edge",
                "label": "SD-WAN edge"
              },
              {
                "value": "wireless-controller",
                "label": "Wireless controller"
              },
              {
                "value": "wireless-access-point",
                "label": "Wireless access point"
              },
              {
                "value": "proxy-appliance",
                "label": "Proxy appliance"
              },
              {
                "value": "wan-accelerator",
                "label": "WAN accelerator"
              },
              {
                "value": "network-tap",
                "label": "Network TAP"
              },
              {
                "value": "packet-broker",
                "label": "Packet broker"
              },
              {
                "value": "network-interface",
                "label": "Network interface"
              }
            ],
            "storage": [
              {
                "value": "storage-array",
                "label": "Storage array"
              },
              {
                "value": "nas-appliance",
                "label": "NAS appliance"
              },
              {
                "value": "san-switch",
                "label": "SAN switch"
              },
              {
                "value": "storage-controller",
                "label": "Storage controller"
              },
              {
                "value": "storage-shelf",
                "label": "Storage shelf"
              },
              {
                "value": "hdd",
                "label": "HDD"
              },
              {
                "value": "ssd",
                "label": "SSD"
              },
              {
                "value": "nvme-drive",
                "label": "NVMe drive"
              },
              {
                "value": "tape-library",
                "label": "Tape library"
              },
              {
                "value": "backup-appliance",
                "label": "Backup appliance"
              },
              {
                "value": "object-storage-node",
                "label": "Object storage node"
              }
            ],
            "power-supply": [
              {
                "value": "ups",
                "label": "UPS"
              },
              {
                "value": "pdu",
                "label": "PDU"
              },
              {
                "value": "ats",
                "label": "Automatic transfer switch"
              },
              {
                "value": "sts",
                "label": "Static transfer switch"
              },
              {
                "value": "rectifier",
                "label": "Rectifier"
              },
              {
                "value": "inverter",
                "label": "Inverter"
              },
              {
                "value": "battery-pack",
                "label": "Battery pack"
              },
              {
                "value": "power-shelf",
                "label": "Power shelf"
              },
              {
                "value": "generator",
                "label": "Generator"
              },
              {
                "value": "busway",
                "label": "Busway"
              },
              {
                "value": "power-meter",
                "label": "Power meter"
              }
            ],
            "rack-facility": [
              {
                "value": "rack",
                "label": "Rack"
              },
              {
                "value": "cabinet",
                "label": "Cabinet"
              },
              {
                "value": "patch-panel",
                "label": "Patch panel"
              },
              {
                "value": "fiber-panel",
                "label": "Fiber panel"
              },
              {
                "value": "cable-management",
                "label": "Cable management"
              },
              {
                "value": "containment",
                "label": "Containment"
              },
              {
                "value": "raised-floor-tile",
                "label": "Raised floor tile"
              },
              {
                "value": "sensor-probe",
                "label": "Sensor probe"
              },
              {
                "value": "rack-accessory",
                "label": "Rack accessory"
              }
            ],
            "cooling": [
              {
                "value": "crac",
                "label": "CRAC"
              },
              {
                "value": "crah",
                "label": "CRAH"
              },
              {
                "value": "in-row-cooler",
                "label": "In-row cooler"
              },
              {
                "value": "rear-door-heat-exchanger",
                "label": "Rear-door heat exchanger"
              },
              {
                "value": "chiller",
                "label": "Chiller"
              },
              {
                "value": "cooling-tower",
                "label": "Cooling tower"
              },
              {
                "value": "heat-exchanger",
                "label": "Heat exchanger"
              },
              {
                "value": "humidifier",
                "label": "Humidifier"
              },
              {
                "value": "environmental-sensor",
                "label": "Environmental sensor"
              }
            ],
            "security-safety": [
              {
                "value": "cctv-camera",
                "label": "CCTV camera"
              },
              {
                "value": "access-control-reader",
                "label": "Access control reader"
              },
              {
                "value": "door-controller",
                "label": "Door controller"
              },
              {
                "value": "biometric-reader",
                "label": "Biometric reader"
              },
              {
                "value": "fire-panel",
                "label": "Fire panel"
              },
              {
                "value": "smoke-detector",
                "label": "Smoke detector"
              },
              {
                "value": "leak-detector",
                "label": "Leak detector"
              },
              {
                "value": "alarm-siren",
                "label": "Alarm siren"
              }
            ],
            "telecom": [
              {
                "value": "pbx",
                "label": "PBX"
              },
              {
                "value": "voip-gateway",
                "label": "VoIP gateway"
              },
              {
                "value": "ip-phone",
                "label": "IP phone"
              },
              {
                "value": "conference-phone",
                "label": "Conference phone"
              },
              {
                "value": "modem",
                "label": "Modem"
              },
              {
                "value": "optical-transponder",
                "label": "Optical transponder"
              },
              {
                "value": "mux",
                "label": "Multiplexer"
              },
              {
                "value": "radio-link",
                "label": "Radio link"
              }
            ],
            "cloud-virtualization": [
              {
                "value": "cloud-account",
                "label": "Cloud account"
              },
              {
                "value": "cloud-region",
                "label": "Cloud region"
              },
              {
                "value": "vpc",
                "label": "VPC"
              },
              {
                "value": "cloud-subnet",
                "label": "Cloud subnet"
              },
              {
                "value": "security-group",
                "label": "Security group"
              },
              {
                "value": "cloud-load-balancer",
                "label": "Cloud load balancer"
              },
              {
                "value": "cloud-instance",
                "label": "Cloud instance"
              },
              {
                "value": "cloud-volume",
                "label": "Cloud volume"
              },
              {
                "value": "kubernetes-cluster",
                "label": "Kubernetes cluster"
              },
              {
                "value": "kubernetes-node",
                "label": "Kubernetes node"
              },
              {
                "value": "container",
                "label": "Container"
              },
              {
                "value": "namespace",
                "label": "Namespace"
              }
            ],
            "software-service": [
              {
                "value": "application",
                "label": "Application"
              },
              {
                "value": "service",
                "label": "Service"
              },
              {
                "value": "api-service",
                "label": "API service"
              },
              {
                "value": "web-service",
                "label": "Web service"
              },
              {
                "value": "database-instance",
                "label": "Database instance"
              },
              {
                "value": "middleware",
                "label": "Middleware"
              },
              {
                "value": "message-broker",
                "label": "Message broker"
              },
              {
                "value": "license",
                "label": "License"
              },
              {
                "value": "certificate",
                "label": "Certificate"
              },
              {
                "value": "dns-zone",
                "label": "DNS zone"
              }
            ],
            "cable-connectivity": [
              {
                "value": "copper-cable",
                "label": "Copper cable"
              },
              {
                "value": "fiber-cable",
                "label": "Fiber cable"
              },
              {
                "value": "patch-cord",
                "label": "Patch cord"
              },
              {
                "value": "trunk-cable",
                "label": "Trunk cable"
              },
              {
                "value": "transceiver",
                "label": "Transceiver"
              },
              {
                "value": "sfp-module",
                "label": "SFP module"
              },
              {
                "value": "qsfp-module",
                "label": "QSFP module"
              },
              {
                "value": "patch-cassette",
                "label": "Patch cassette"
              }
            ],
            "mobile-iot": [
              {
                "value": "smartphone",
                "label": "Smartphone"
              },
              {
                "value": "rugged-handheld",
                "label": "Rugged handheld"
              },
              {
                "value": "iot-gateway",
                "label": "IoT gateway"
              },
              {
                "value": "industrial-controller",
                "label": "Industrial controller"
              },
              {
                "value": "plc",
                "label": "PLC"
              },
              {
                "value": "sensor",
                "label": "Sensor"
              },
              {
                "value": "actuator",
                "label": "Actuator"
              }
            ],
            "other": [
              {
                "value": "generic-asset",
                "label": "Generic asset"
              },
              {
                "value": "unknown-device",
                "label": "Unknown device"
              },
              {
                "value": "external-resource",
                "label": "External resource"
              }
            ]
          }
        },
        {
          "name": "tag",
          "label": "Tag",
          "placeholder": "prod"
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        }
      ]
    },
    {
      "id": "rsot-upsert",
      "label": "Créer / mettre à jour une ressource",
      "method": "POST",
      "path": "/v1/rsot/objects",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "key",
          "label": "Clé RSOT",
          "required": true,
          "placeholder": "server/srv-db-01"
        },
        {
          "name": "resource_category",
          "label": "Catégorie",
          "type": "select",
          "options": [
            {
              "value": "server",
              "label": "Server"
            },
            {
              "value": "personal-computer",
              "label": "Personal computer"
            },
            {
              "value": "monitor-peripheral",
              "label": "Monitor and peripheral"
            },
            {
              "value": "network-device",
              "label": "Network device"
            },
            {
              "value": "storage",
              "label": "Storage"
            },
            {
              "value": "power-supply",
              "label": "Power supply"
            },
            {
              "value": "rack-facility",
              "label": "Rack and facility"
            },
            {
              "value": "cooling",
              "label": "Cooling"
            },
            {
              "value": "security-safety",
              "label": "Security and safety"
            },
            {
              "value": "telecom",
              "label": "Telecom"
            },
            {
              "value": "cloud-virtualization",
              "label": "Cloud and virtualization"
            },
            {
              "value": "software-service",
              "label": "Software and service"
            },
            {
              "value": "cable-connectivity",
              "label": "Cable and connectivity"
            },
            {
              "value": "mobile-iot",
              "label": "Mobile and IoT"
            },
            {
              "value": "other",
              "label": "Other"
            }
          ],
          "target": "kind",
          "defaultValue": "server",
          "required": true
        },
        {
          "name": "resource_type",
          "label": "Type de ressource",
          "type": "select",
          "optionsByField": "resource_category",
          "optionsMap": {
            "server": [
              {
                "value": "rack-server",
                "label": "Rack server"
              },
              {
                "value": "blade-server",
                "label": "Blade server"
              },
              {
                "value": "tower-server",
                "label": "Tower server"
              },
              {
                "value": "hypervisor-host",
                "label": "Hypervisor host"
              },
              {
                "value": "virtual-machine",
                "label": "Virtual machine"
              },
              {
                "value": "container-host",
                "label": "Container host"
              },
              {
                "value": "compute-appliance",
                "label": "Compute appliance"
              }
            ],
            "personal-computer": [
              {
                "value": "laptop",
                "label": "Laptop"
              },
              {
                "value": "desktop",
                "label": "Desktop"
              },
              {
                "value": "workstation",
                "label": "Workstation"
              },
              {
                "value": "thin-client",
                "label": "Thin client"
              },
              {
                "value": "all-in-one",
                "label": "All-in-one"
              },
              {
                "value": "tablet",
                "label": "Tablet"
              },
              {
                "value": "kiosk",
                "label": "Kiosk"
              }
            ],
            "monitor-peripheral": [
              {
                "value": "monitor",
                "label": "Monitor"
              },
              {
                "value": "keyboard",
                "label": "Keyboard"
              },
              {
                "value": "mouse",
                "label": "Mouse"
              },
              {
                "value": "docking-station",
                "label": "Docking station"
              },
              {
                "value": "webcam",
                "label": "Webcam"
              },
              {
                "value": "headset",
                "label": "Headset"
              },
              {
                "value": "printer",
                "label": "Printer"
              },
              {
                "value": "scanner",
                "label": "Scanner"
              },
              {
                "value": "barcode-scanner",
                "label": "Barcode scanner"
              },
              {
                "value": "kvm-console",
                "label": "KVM console"
              }
            ],
            "network-device": [
              {
                "value": "switch",
                "label": "Switch"
              },
              {
                "value": "core-switch",
                "label": "Core switch"
              },
              {
                "value": "distribution-switch",
                "label": "Distribution switch"
              },
              {
                "value": "access-switch",
                "label": "Access switch"
              },
              {
                "value": "router",
                "label": "Router"
              },
              {
                "value": "firewall",
                "label": "Firewall"
              },
              {
                "value": "load-balancer",
                "label": "Load balancer"
              },
              {
                "value": "vpn-gateway",
                "label": "VPN gateway"
              },
              {
                "value": "sdwan-edge",
                "label": "SD-WAN edge"
              },
              {
                "value": "wireless-controller",
                "label": "Wireless controller"
              },
              {
                "value": "wireless-access-point",
                "label": "Wireless access point"
              },
              {
                "value": "proxy-appliance",
                "label": "Proxy appliance"
              },
              {
                "value": "wan-accelerator",
                "label": "WAN accelerator"
              },
              {
                "value": "network-tap",
                "label": "Network TAP"
              },
              {
                "value": "packet-broker",
                "label": "Packet broker"
              },
              {
                "value": "network-interface",
                "label": "Network interface"
              }
            ],
            "storage": [
              {
                "value": "storage-array",
                "label": "Storage array"
              },
              {
                "value": "nas-appliance",
                "label": "NAS appliance"
              },
              {
                "value": "san-switch",
                "label": "SAN switch"
              },
              {
                "value": "storage-controller",
                "label": "Storage controller"
              },
              {
                "value": "storage-shelf",
                "label": "Storage shelf"
              },
              {
                "value": "hdd",
                "label": "HDD"
              },
              {
                "value": "ssd",
                "label": "SSD"
              },
              {
                "value": "nvme-drive",
                "label": "NVMe drive"
              },
              {
                "value": "tape-library",
                "label": "Tape library"
              },
              {
                "value": "backup-appliance",
                "label": "Backup appliance"
              },
              {
                "value": "object-storage-node",
                "label": "Object storage node"
              }
            ],
            "power-supply": [
              {
                "value": "ups",
                "label": "UPS"
              },
              {
                "value": "pdu",
                "label": "PDU"
              },
              {
                "value": "ats",
                "label": "Automatic transfer switch"
              },
              {
                "value": "sts",
                "label": "Static transfer switch"
              },
              {
                "value": "rectifier",
                "label": "Rectifier"
              },
              {
                "value": "inverter",
                "label": "Inverter"
              },
              {
                "value": "battery-pack",
                "label": "Battery pack"
              },
              {
                "value": "power-shelf",
                "label": "Power shelf"
              },
              {
                "value": "generator",
                "label": "Generator"
              },
              {
                "value": "busway",
                "label": "Busway"
              },
              {
                "value": "power-meter",
                "label": "Power meter"
              }
            ],
            "rack-facility": [
              {
                "value": "rack",
                "label": "Rack"
              },
              {
                "value": "cabinet",
                "label": "Cabinet"
              },
              {
                "value": "patch-panel",
                "label": "Patch panel"
              },
              {
                "value": "fiber-panel",
                "label": "Fiber panel"
              },
              {
                "value": "cable-management",
                "label": "Cable management"
              },
              {
                "value": "containment",
                "label": "Containment"
              },
              {
                "value": "raised-floor-tile",
                "label": "Raised floor tile"
              },
              {
                "value": "sensor-probe",
                "label": "Sensor probe"
              },
              {
                "value": "rack-accessory",
                "label": "Rack accessory"
              }
            ],
            "cooling": [
              {
                "value": "crac",
                "label": "CRAC"
              },
              {
                "value": "crah",
                "label": "CRAH"
              },
              {
                "value": "in-row-cooler",
                "label": "In-row cooler"
              },
              {
                "value": "rear-door-heat-exchanger",
                "label": "Rear-door heat exchanger"
              },
              {
                "value": "chiller",
                "label": "Chiller"
              },
              {
                "value": "cooling-tower",
                "label": "Cooling tower"
              },
              {
                "value": "heat-exchanger",
                "label": "Heat exchanger"
              },
              {
                "value": "humidifier",
                "label": "Humidifier"
              },
              {
                "value": "environmental-sensor",
                "label": "Environmental sensor"
              }
            ],
            "security-safety": [
              {
                "value": "cctv-camera",
                "label": "CCTV camera"
              },
              {
                "value": "access-control-reader",
                "label": "Access control reader"
              },
              {
                "value": "door-controller",
                "label": "Door controller"
              },
              {
                "value": "biometric-reader",
                "label": "Biometric reader"
              },
              {
                "value": "fire-panel",
                "label": "Fire panel"
              },
              {
                "value": "smoke-detector",
                "label": "Smoke detector"
              },
              {
                "value": "leak-detector",
                "label": "Leak detector"
              },
              {
                "value": "alarm-siren",
                "label": "Alarm siren"
              }
            ],
            "telecom": [
              {
                "value": "pbx",
                "label": "PBX"
              },
              {
                "value": "voip-gateway",
                "label": "VoIP gateway"
              },
              {
                "value": "ip-phone",
                "label": "IP phone"
              },
              {
                "value": "conference-phone",
                "label": "Conference phone"
              },
              {
                "value": "modem",
                "label": "Modem"
              },
              {
                "value": "optical-transponder",
                "label": "Optical transponder"
              },
              {
                "value": "mux",
                "label": "Multiplexer"
              },
              {
                "value": "radio-link",
                "label": "Radio link"
              }
            ],
            "cloud-virtualization": [
              {
                "value": "cloud-account",
                "label": "Cloud account"
              },
              {
                "value": "cloud-region",
                "label": "Cloud region"
              },
              {
                "value": "vpc",
                "label": "VPC"
              },
              {
                "value": "cloud-subnet",
                "label": "Cloud subnet"
              },
              {
                "value": "security-group",
                "label": "Security group"
              },
              {
                "value": "cloud-load-balancer",
                "label": "Cloud load balancer"
              },
              {
                "value": "cloud-instance",
                "label": "Cloud instance"
              },
              {
                "value": "cloud-volume",
                "label": "Cloud volume"
              },
              {
                "value": "kubernetes-cluster",
                "label": "Kubernetes cluster"
              },
              {
                "value": "kubernetes-node",
                "label": "Kubernetes node"
              },
              {
                "value": "container",
                "label": "Container"
              },
              {
                "value": "namespace",
                "label": "Namespace"
              }
            ],
            "software-service": [
              {
                "value": "application",
                "label": "Application"
              },
              {
                "value": "service",
                "label": "Service"
              },
              {
                "value": "api-service",
                "label": "API service"
              },
              {
                "value": "web-service",
                "label": "Web service"
              },
              {
                "value": "database-instance",
                "label": "Database instance"
              },
              {
                "value": "middleware",
                "label": "Middleware"
              },
              {
                "value": "message-broker",
                "label": "Message broker"
              },
              {
                "value": "license",
                "label": "License"
              },
              {
                "value": "certificate",
                "label": "Certificate"
              },
              {
                "value": "dns-zone",
                "label": "DNS zone"
              }
            ],
            "cable-connectivity": [
              {
                "value": "copper-cable",
                "label": "Copper cable"
              },
              {
                "value": "fiber-cable",
                "label": "Fiber cable"
              },
              {
                "value": "patch-cord",
                "label": "Patch cord"
              },
              {
                "value": "trunk-cable",
                "label": "Trunk cable"
              },
              {
                "value": "transceiver",
                "label": "Transceiver"
              },
              {
                "value": "sfp-module",
                "label": "SFP module"
              },
              {
                "value": "qsfp-module",
                "label": "QSFP module"
              },
              {
                "value": "patch-cassette",
                "label": "Patch cassette"
              }
            ],
            "mobile-iot": [
              {
                "value": "smartphone",
                "label": "Smartphone"
              },
              {
                "value": "rugged-handheld",
                "label": "Rugged handheld"
              },
              {
                "value": "iot-gateway",
                "label": "IoT gateway"
              },
              {
                "value": "industrial-controller",
                "label": "Industrial controller"
              },
              {
                "value": "plc",
                "label": "PLC"
              },
              {
                "value": "sensor",
                "label": "Sensor"
              },
              {
                "value": "actuator",
                "label": "Actuator"
              }
            ],
            "other": [
              {
                "value": "generic-asset",
                "label": "Generic asset"
              },
              {
                "value": "unknown-device",
                "label": "Unknown device"
              },
              {
                "value": "external-resource",
                "label": "External resource"
              }
            ]
          },
          "target": "attributes.resource_type",
          "defaultValue": "rack-server",
          "required": true
        },
        {
          "name": "display_name",
          "label": "Nom affiché",
          "required": true,
          "placeholder": "srv-db-01"
        },
        {
          "name": "source",
          "label": "Source autoritative",
          "required": true,
          "type": "select",
          "options": [
            "manual",
            "import",
            "backend-discovery",
            "enterprise-proxy",
            "api"
          ]
        },
        {
          "name": "serial",
          "label": "Numéro de série",
          "target": "attributes.serial",
          "placeholder": "SN123456"
        },
        {
          "name": "vendor",
          "label": "Constructeur",
          "target": "attributes.vendor",
          "placeholder": "Dell, HPE, Cisco"
        },
        {
          "name": "model",
          "label": "Modèle",
          "target": "attributes.model",
          "placeholder": "PowerEdge R760"
        },
        {
          "name": "site",
          "label": "Site",
          "target": "attributes.site",
          "placeholder": "PAR1"
        },
        {
          "name": "building",
          "label": "Bâtiment",
          "target": "attributes.building",
          "placeholder": "B1"
        },
        {
          "name": "room",
          "label": "Salle",
          "target": "attributes.room",
          "placeholder": "DC-A"
        },
        {
          "name": "row",
          "label": "Ligne salle",
          "target": "attributes.row",
          "placeholder": "Rangée A"
        },
        {
          "name": "column",
          "label": "Colonne salle",
          "target": "attributes.column",
          "placeholder": "Colonne 04"
        },
        {
          "name": "rack",
          "label": "Rack",
          "target": "attributes.rack",
          "placeholder": "R12"
        },
        {
          "name": "management_ip",
          "label": "IP de management",
          "target": "attributes.management_ip",
          "placeholder": "10.10.10.15"
        },
        {
          "name": "lifecycle_state",
          "label": "État cycle de vie",
          "target": "attributes.lifecycle_state",
          "type": "select",
          "options": [
            "planned",
            "active",
            "maintenance",
            "retired"
          ]
        },
        {
          "name": "tags",
          "label": "Tags",
          "type": "csv",
          "placeholder": "prod,critical,postgres"
        }
      ]
    },
    {
      "id": "rsot-relations",
      "label": "Lister les relations",
      "method": "GET",
      "path": "/v1/rsot/relations",
      "query": [
        {
          "name": "source_key",
          "label": "Ressource source"
        },
        {
          "name": "target_key",
          "label": "Ressource cible"
        },
        {
          "name": "relation_type",
          "label": "Type de relation"
        },
        {
          "name": "as_of",
          "label": "Date ISO-8601",
          "required": false,
          "placeholder": "2026-07-06T10:00:00+02:00"
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        }
      ]
    },
    {
      "id": "rsot-as-of",
      "label": "Restituer une ressource à date",
      "method": "GET",
      "path": "/v1/rsot/object-as-of",
      "query": [
        {
          "name": "key",
          "label": "Clé RSOT",
          "required": true,
          "placeholder": "server/srv-db-01"
        },
        {
          "name": "as_of",
          "label": "Date ISO-8601",
          "required": true,
          "placeholder": "2026-07-06T10:00:00+02:00"
        },
        {
          "name": "relation_limit",
          "label": "Limite de relations",
          "type": "number",
          "placeholder": "100",
          "minimum": 1,
          "maximum": 500
        }
      ]
    },
    {
      "id": "rsot-object-audit",
      "label": "Audit d’une ressource",
      "method": "GET",
      "path": "/v1/rsot/object-audit",
      "query": [
        {
          "name": "key",
          "label": "Clé RSOT",
          "required": true,
          "placeholder": "server/srv-db-01"
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        }
      ]
    },
    {
      "id": "rsot-quality-object",
      "label": "Évaluer la qualité d’une ressource",
      "method": "GET",
      "path": "/v1/rsot/quality/object",
      "query": [
        {
          "name": "key",
          "label": "Clé RSOT",
          "required": true,
          "placeholder": "server/srv-db-01"
        }
      ]
    },
    {
      "id": "rsot-quality-summary",
      "label": "Synthèse qualité / certification",
      "method": "GET",
      "path": "/v1/rsot/quality/summary",
      "query": [
        {
          "name": "resource_category",
          "label": "Catégorie",
          "type": "select",
          "options": [
            {
              "value": "server",
              "label": "Server"
            },
            {
              "value": "personal-computer",
              "label": "Personal computer"
            },
            {
              "value": "monitor-peripheral",
              "label": "Monitor and peripheral"
            },
            {
              "value": "network-device",
              "label": "Network device"
            },
            {
              "value": "storage",
              "label": "Storage"
            },
            {
              "value": "power-supply",
              "label": "Power supply"
            },
            {
              "value": "rack-facility",
              "label": "Rack and facility"
            },
            {
              "value": "cooling",
              "label": "Cooling"
            },
            {
              "value": "security-safety",
              "label": "Security and safety"
            },
            {
              "value": "telecom",
              "label": "Telecom"
            },
            {
              "value": "cloud-virtualization",
              "label": "Cloud and virtualization"
            },
            {
              "value": "software-service",
              "label": "Software and service"
            },
            {
              "value": "cable-connectivity",
              "label": "Cable and connectivity"
            },
            {
              "value": "mobile-iot",
              "label": "Mobile and IoT"
            },
            {
              "value": "other",
              "label": "Other"
            }
          ]
        },
        {
          "name": "resource_type",
          "label": "Type de ressource",
          "type": "select",
          "optionsByField": "resource_category",
          "optionsMap": {
            "server": [
              {
                "value": "rack-server",
                "label": "Rack server"
              },
              {
                "value": "blade-server",
                "label": "Blade server"
              },
              {
                "value": "tower-server",
                "label": "Tower server"
              },
              {
                "value": "hypervisor-host",
                "label": "Hypervisor host"
              },
              {
                "value": "virtual-machine",
                "label": "Virtual machine"
              },
              {
                "value": "container-host",
                "label": "Container host"
              },
              {
                "value": "compute-appliance",
                "label": "Compute appliance"
              }
            ],
            "personal-computer": [
              {
                "value": "laptop",
                "label": "Laptop"
              },
              {
                "value": "desktop",
                "label": "Desktop"
              },
              {
                "value": "workstation",
                "label": "Workstation"
              },
              {
                "value": "thin-client",
                "label": "Thin client"
              },
              {
                "value": "all-in-one",
                "label": "All-in-one"
              },
              {
                "value": "tablet",
                "label": "Tablet"
              },
              {
                "value": "kiosk",
                "label": "Kiosk"
              }
            ],
            "monitor-peripheral": [
              {
                "value": "monitor",
                "label": "Monitor"
              },
              {
                "value": "keyboard",
                "label": "Keyboard"
              },
              {
                "value": "mouse",
                "label": "Mouse"
              },
              {
                "value": "docking-station",
                "label": "Docking station"
              },
              {
                "value": "webcam",
                "label": "Webcam"
              },
              {
                "value": "headset",
                "label": "Headset"
              },
              {
                "value": "printer",
                "label": "Printer"
              },
              {
                "value": "scanner",
                "label": "Scanner"
              },
              {
                "value": "barcode-scanner",
                "label": "Barcode scanner"
              },
              {
                "value": "kvm-console",
                "label": "KVM console"
              }
            ],
            "network-device": [
              {
                "value": "switch",
                "label": "Switch"
              },
              {
                "value": "core-switch",
                "label": "Core switch"
              },
              {
                "value": "distribution-switch",
                "label": "Distribution switch"
              },
              {
                "value": "access-switch",
                "label": "Access switch"
              },
              {
                "value": "router",
                "label": "Router"
              },
              {
                "value": "firewall",
                "label": "Firewall"
              },
              {
                "value": "load-balancer",
                "label": "Load balancer"
              },
              {
                "value": "vpn-gateway",
                "label": "VPN gateway"
              },
              {
                "value": "sdwan-edge",
                "label": "SD-WAN edge"
              },
              {
                "value": "wireless-controller",
                "label": "Wireless controller"
              },
              {
                "value": "wireless-access-point",
                "label": "Wireless access point"
              },
              {
                "value": "proxy-appliance",
                "label": "Proxy appliance"
              },
              {
                "value": "wan-accelerator",
                "label": "WAN accelerator"
              },
              {
                "value": "network-tap",
                "label": "Network TAP"
              },
              {
                "value": "packet-broker",
                "label": "Packet broker"
              },
              {
                "value": "network-interface",
                "label": "Network interface"
              }
            ],
            "storage": [
              {
                "value": "storage-array",
                "label": "Storage array"
              },
              {
                "value": "nas-appliance",
                "label": "NAS appliance"
              },
              {
                "value": "san-switch",
                "label": "SAN switch"
              },
              {
                "value": "storage-controller",
                "label": "Storage controller"
              },
              {
                "value": "storage-shelf",
                "label": "Storage shelf"
              },
              {
                "value": "hdd",
                "label": "HDD"
              },
              {
                "value": "ssd",
                "label": "SSD"
              },
              {
                "value": "nvme-drive",
                "label": "NVMe drive"
              },
              {
                "value": "tape-library",
                "label": "Tape library"
              },
              {
                "value": "backup-appliance",
                "label": "Backup appliance"
              },
              {
                "value": "object-storage-node",
                "label": "Object storage node"
              }
            ],
            "power-supply": [
              {
                "value": "ups",
                "label": "UPS"
              },
              {
                "value": "pdu",
                "label": "PDU"
              },
              {
                "value": "ats",
                "label": "Automatic transfer switch"
              },
              {
                "value": "sts",
                "label": "Static transfer switch"
              },
              {
                "value": "rectifier",
                "label": "Rectifier"
              },
              {
                "value": "inverter",
                "label": "Inverter"
              },
              {
                "value": "battery-pack",
                "label": "Battery pack"
              },
              {
                "value": "power-shelf",
                "label": "Power shelf"
              },
              {
                "value": "generator",
                "label": "Generator"
              },
              {
                "value": "busway",
                "label": "Busway"
              },
              {
                "value": "power-meter",
                "label": "Power meter"
              }
            ],
            "rack-facility": [
              {
                "value": "rack",
                "label": "Rack"
              },
              {
                "value": "cabinet",
                "label": "Cabinet"
              },
              {
                "value": "patch-panel",
                "label": "Patch panel"
              },
              {
                "value": "fiber-panel",
                "label": "Fiber panel"
              },
              {
                "value": "cable-management",
                "label": "Cable management"
              },
              {
                "value": "containment",
                "label": "Containment"
              },
              {
                "value": "raised-floor-tile",
                "label": "Raised floor tile"
              },
              {
                "value": "sensor-probe",
                "label": "Sensor probe"
              },
              {
                "value": "rack-accessory",
                "label": "Rack accessory"
              }
            ],
            "cooling": [
              {
                "value": "crac",
                "label": "CRAC"
              },
              {
                "value": "crah",
                "label": "CRAH"
              },
              {
                "value": "in-row-cooler",
                "label": "In-row cooler"
              },
              {
                "value": "rear-door-heat-exchanger",
                "label": "Rear-door heat exchanger"
              },
              {
                "value": "chiller",
                "label": "Chiller"
              },
              {
                "value": "cooling-tower",
                "label": "Cooling tower"
              },
              {
                "value": "heat-exchanger",
                "label": "Heat exchanger"
              },
              {
                "value": "humidifier",
                "label": "Humidifier"
              },
              {
                "value": "environmental-sensor",
                "label": "Environmental sensor"
              }
            ],
            "security-safety": [
              {
                "value": "cctv-camera",
                "label": "CCTV camera"
              },
              {
                "value": "access-control-reader",
                "label": "Access control reader"
              },
              {
                "value": "door-controller",
                "label": "Door controller"
              },
              {
                "value": "biometric-reader",
                "label": "Biometric reader"
              },
              {
                "value": "fire-panel",
                "label": "Fire panel"
              },
              {
                "value": "smoke-detector",
                "label": "Smoke detector"
              },
              {
                "value": "leak-detector",
                "label": "Leak detector"
              },
              {
                "value": "alarm-siren",
                "label": "Alarm siren"
              }
            ],
            "telecom": [
              {
                "value": "pbx",
                "label": "PBX"
              },
              {
                "value": "voip-gateway",
                "label": "VoIP gateway"
              },
              {
                "value": "ip-phone",
                "label": "IP phone"
              },
              {
                "value": "conference-phone",
                "label": "Conference phone"
              },
              {
                "value": "modem",
                "label": "Modem"
              },
              {
                "value": "optical-transponder",
                "label": "Optical transponder"
              },
              {
                "value": "mux",
                "label": "Multiplexer"
              },
              {
                "value": "radio-link",
                "label": "Radio link"
              }
            ],
            "cloud-virtualization": [
              {
                "value": "cloud-account",
                "label": "Cloud account"
              },
              {
                "value": "cloud-region",
                "label": "Cloud region"
              },
              {
                "value": "vpc",
                "label": "VPC"
              },
              {
                "value": "cloud-subnet",
                "label": "Cloud subnet"
              },
              {
                "value": "security-group",
                "label": "Security group"
              },
              {
                "value": "cloud-load-balancer",
                "label": "Cloud load balancer"
              },
              {
                "value": "cloud-instance",
                "label": "Cloud instance"
              },
              {
                "value": "cloud-volume",
                "label": "Cloud volume"
              },
              {
                "value": "kubernetes-cluster",
                "label": "Kubernetes cluster"
              },
              {
                "value": "kubernetes-node",
                "label": "Kubernetes node"
              },
              {
                "value": "container",
                "label": "Container"
              },
              {
                "value": "namespace",
                "label": "Namespace"
              }
            ],
            "software-service": [
              {
                "value": "application",
                "label": "Application"
              },
              {
                "value": "service",
                "label": "Service"
              },
              {
                "value": "api-service",
                "label": "API service"
              },
              {
                "value": "web-service",
                "label": "Web service"
              },
              {
                "value": "database-instance",
                "label": "Database instance"
              },
              {
                "value": "middleware",
                "label": "Middleware"
              },
              {
                "value": "message-broker",
                "label": "Message broker"
              },
              {
                "value": "license",
                "label": "License"
              },
              {
                "value": "certificate",
                "label": "Certificate"
              },
              {
                "value": "dns-zone",
                "label": "DNS zone"
              }
            ],
            "cable-connectivity": [
              {
                "value": "copper-cable",
                "label": "Copper cable"
              },
              {
                "value": "fiber-cable",
                "label": "Fiber cable"
              },
              {
                "value": "patch-cord",
                "label": "Patch cord"
              },
              {
                "value": "trunk-cable",
                "label": "Trunk cable"
              },
              {
                "value": "transceiver",
                "label": "Transceiver"
              },
              {
                "value": "sfp-module",
                "label": "SFP module"
              },
              {
                "value": "qsfp-module",
                "label": "QSFP module"
              },
              {
                "value": "patch-cassette",
                "label": "Patch cassette"
              }
            ],
            "mobile-iot": [
              {
                "value": "smartphone",
                "label": "Smartphone"
              },
              {
                "value": "rugged-handheld",
                "label": "Rugged handheld"
              },
              {
                "value": "iot-gateway",
                "label": "IoT gateway"
              },
              {
                "value": "industrial-controller",
                "label": "Industrial controller"
              },
              {
                "value": "plc",
                "label": "PLC"
              },
              {
                "value": "sensor",
                "label": "Sensor"
              },
              {
                "value": "actuator",
                "label": "Actuator"
              }
            ],
            "other": [
              {
                "value": "generic-asset",
                "label": "Generic asset"
              },
              {
                "value": "unknown-device",
                "label": "Unknown device"
              },
              {
                "value": "external-resource",
                "label": "External resource"
              }
            ]
          }
        },
        {
          "name": "tag",
          "label": "Tag",
          "placeholder": "prod"
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        }
      ]
    },
    {
      "id": "rsot-governance",
      "label": "Évaluer une règle de gouvernance",
      "method": "POST",
      "path": "/v1/rsot/governance/evaluate",
      "body": [
        {
          "name": "object_kind",
          "label": "Catégorie d’objet",
          "required": true,
          "type": "select",
          "options": [
            {
              "value": "server",
              "label": "Server"
            },
            {
              "value": "personal-computer",
              "label": "Personal computer"
            },
            {
              "value": "monitor-peripheral",
              "label": "Monitor and peripheral"
            },
            {
              "value": "network-device",
              "label": "Network device"
            },
            {
              "value": "storage",
              "label": "Storage"
            },
            {
              "value": "power-supply",
              "label": "Power supply"
            },
            {
              "value": "rack-facility",
              "label": "Rack and facility"
            },
            {
              "value": "cooling",
              "label": "Cooling"
            },
            {
              "value": "security-safety",
              "label": "Security and safety"
            },
            {
              "value": "telecom",
              "label": "Telecom"
            },
            {
              "value": "cloud-virtualization",
              "label": "Cloud and virtualization"
            },
            {
              "value": "software-service",
              "label": "Software and service"
            },
            {
              "value": "cable-connectivity",
              "label": "Cable and connectivity"
            },
            {
              "value": "mobile-iot",
              "label": "Mobile and IoT"
            },
            {
              "value": "other",
              "label": "Other"
            }
          ]
        },
        {
          "name": "incoming_source",
          "label": "Source entrante",
          "required": true,
          "type": "select",
          "options": [
            "manual",
            "import",
            "backend-discovery",
            "enterprise-proxy",
            "api"
          ]
        },
        {
          "name": "existing_serial",
          "label": "Serial existant",
          "target": "existing_attributes.serial"
        },
        {
          "name": "incoming_serial",
          "label": "Serial entrant",
          "target": "incoming_attributes.serial"
        },
        {
          "name": "existing_site",
          "label": "Site existant",
          "target": "existing_attributes.site"
        },
        {
          "name": "incoming_site",
          "label": "Site entrant",
          "target": "incoming_attributes.site"
        }
      ]
    },
    {
      "id": "rsot-reconcile",
      "label": "Réconcilier une ressource",
      "method": "POST",
      "path": "/v1/rsot/reconcile-object",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "key",
          "label": "Clé RSOT",
          "required": true,
          "placeholder": "server/srv-db-01"
        },
        {
          "name": "source",
          "label": "Source autoritative",
          "required": true,
          "type": "select",
          "options": [
            "manual",
            "import",
            "backend-discovery",
            "enterprise-proxy",
            "api"
          ]
        },
        {
          "name": "resource_category",
          "label": "Catégorie",
          "type": "select",
          "options": [
            {
              "value": "server",
              "label": "Server"
            },
            {
              "value": "personal-computer",
              "label": "Personal computer"
            },
            {
              "value": "monitor-peripheral",
              "label": "Monitor and peripheral"
            },
            {
              "value": "network-device",
              "label": "Network device"
            },
            {
              "value": "storage",
              "label": "Storage"
            },
            {
              "value": "power-supply",
              "label": "Power supply"
            },
            {
              "value": "rack-facility",
              "label": "Rack and facility"
            },
            {
              "value": "cooling",
              "label": "Cooling"
            },
            {
              "value": "security-safety",
              "label": "Security and safety"
            },
            {
              "value": "telecom",
              "label": "Telecom"
            },
            {
              "value": "cloud-virtualization",
              "label": "Cloud and virtualization"
            },
            {
              "value": "software-service",
              "label": "Software and service"
            },
            {
              "value": "cable-connectivity",
              "label": "Cable and connectivity"
            },
            {
              "value": "mobile-iot",
              "label": "Mobile and IoT"
            },
            {
              "value": "other",
              "label": "Other"
            }
          ],
          "target": "kind",
          "defaultValue": "server",
          "required": false
        },
        {
          "name": "resource_type",
          "label": "Type de ressource",
          "type": "select",
          "optionsByField": "resource_category",
          "optionsMap": {
            "server": [
              {
                "value": "rack-server",
                "label": "Rack server"
              },
              {
                "value": "blade-server",
                "label": "Blade server"
              },
              {
                "value": "tower-server",
                "label": "Tower server"
              },
              {
                "value": "hypervisor-host",
                "label": "Hypervisor host"
              },
              {
                "value": "virtual-machine",
                "label": "Virtual machine"
              },
              {
                "value": "container-host",
                "label": "Container host"
              },
              {
                "value": "compute-appliance",
                "label": "Compute appliance"
              }
            ],
            "personal-computer": [
              {
                "value": "laptop",
                "label": "Laptop"
              },
              {
                "value": "desktop",
                "label": "Desktop"
              },
              {
                "value": "workstation",
                "label": "Workstation"
              },
              {
                "value": "thin-client",
                "label": "Thin client"
              },
              {
                "value": "all-in-one",
                "label": "All-in-one"
              },
              {
                "value": "tablet",
                "label": "Tablet"
              },
              {
                "value": "kiosk",
                "label": "Kiosk"
              }
            ],
            "monitor-peripheral": [
              {
                "value": "monitor",
                "label": "Monitor"
              },
              {
                "value": "keyboard",
                "label": "Keyboard"
              },
              {
                "value": "mouse",
                "label": "Mouse"
              },
              {
                "value": "docking-station",
                "label": "Docking station"
              },
              {
                "value": "webcam",
                "label": "Webcam"
              },
              {
                "value": "headset",
                "label": "Headset"
              },
              {
                "value": "printer",
                "label": "Printer"
              },
              {
                "value": "scanner",
                "label": "Scanner"
              },
              {
                "value": "barcode-scanner",
                "label": "Barcode scanner"
              },
              {
                "value": "kvm-console",
                "label": "KVM console"
              }
            ],
            "network-device": [
              {
                "value": "switch",
                "label": "Switch"
              },
              {
                "value": "core-switch",
                "label": "Core switch"
              },
              {
                "value": "distribution-switch",
                "label": "Distribution switch"
              },
              {
                "value": "access-switch",
                "label": "Access switch"
              },
              {
                "value": "router",
                "label": "Router"
              },
              {
                "value": "firewall",
                "label": "Firewall"
              },
              {
                "value": "load-balancer",
                "label": "Load balancer"
              },
              {
                "value": "vpn-gateway",
                "label": "VPN gateway"
              },
              {
                "value": "sdwan-edge",
                "label": "SD-WAN edge"
              },
              {
                "value": "wireless-controller",
                "label": "Wireless controller"
              },
              {
                "value": "wireless-access-point",
                "label": "Wireless access point"
              },
              {
                "value": "proxy-appliance",
                "label": "Proxy appliance"
              },
              {
                "value": "wan-accelerator",
                "label": "WAN accelerator"
              },
              {
                "value": "network-tap",
                "label": "Network TAP"
              },
              {
                "value": "packet-broker",
                "label": "Packet broker"
              },
              {
                "value": "network-interface",
                "label": "Network interface"
              }
            ],
            "storage": [
              {
                "value": "storage-array",
                "label": "Storage array"
              },
              {
                "value": "nas-appliance",
                "label": "NAS appliance"
              },
              {
                "value": "san-switch",
                "label": "SAN switch"
              },
              {
                "value": "storage-controller",
                "label": "Storage controller"
              },
              {
                "value": "storage-shelf",
                "label": "Storage shelf"
              },
              {
                "value": "hdd",
                "label": "HDD"
              },
              {
                "value": "ssd",
                "label": "SSD"
              },
              {
                "value": "nvme-drive",
                "label": "NVMe drive"
              },
              {
                "value": "tape-library",
                "label": "Tape library"
              },
              {
                "value": "backup-appliance",
                "label": "Backup appliance"
              },
              {
                "value": "object-storage-node",
                "label": "Object storage node"
              }
            ],
            "power-supply": [
              {
                "value": "ups",
                "label": "UPS"
              },
              {
                "value": "pdu",
                "label": "PDU"
              },
              {
                "value": "ats",
                "label": "Automatic transfer switch"
              },
              {
                "value": "sts",
                "label": "Static transfer switch"
              },
              {
                "value": "rectifier",
                "label": "Rectifier"
              },
              {
                "value": "inverter",
                "label": "Inverter"
              },
              {
                "value": "battery-pack",
                "label": "Battery pack"
              },
              {
                "value": "power-shelf",
                "label": "Power shelf"
              },
              {
                "value": "generator",
                "label": "Generator"
              },
              {
                "value": "busway",
                "label": "Busway"
              },
              {
                "value": "power-meter",
                "label": "Power meter"
              }
            ],
            "rack-facility": [
              {
                "value": "rack",
                "label": "Rack"
              },
              {
                "value": "cabinet",
                "label": "Cabinet"
              },
              {
                "value": "patch-panel",
                "label": "Patch panel"
              },
              {
                "value": "fiber-panel",
                "label": "Fiber panel"
              },
              {
                "value": "cable-management",
                "label": "Cable management"
              },
              {
                "value": "containment",
                "label": "Containment"
              },
              {
                "value": "raised-floor-tile",
                "label": "Raised floor tile"
              },
              {
                "value": "sensor-probe",
                "label": "Sensor probe"
              },
              {
                "value": "rack-accessory",
                "label": "Rack accessory"
              }
            ],
            "cooling": [
              {
                "value": "crac",
                "label": "CRAC"
              },
              {
                "value": "crah",
                "label": "CRAH"
              },
              {
                "value": "in-row-cooler",
                "label": "In-row cooler"
              },
              {
                "value": "rear-door-heat-exchanger",
                "label": "Rear-door heat exchanger"
              },
              {
                "value": "chiller",
                "label": "Chiller"
              },
              {
                "value": "cooling-tower",
                "label": "Cooling tower"
              },
              {
                "value": "heat-exchanger",
                "label": "Heat exchanger"
              },
              {
                "value": "humidifier",
                "label": "Humidifier"
              },
              {
                "value": "environmental-sensor",
                "label": "Environmental sensor"
              }
            ],
            "security-safety": [
              {
                "value": "cctv-camera",
                "label": "CCTV camera"
              },
              {
                "value": "access-control-reader",
                "label": "Access control reader"
              },
              {
                "value": "door-controller",
                "label": "Door controller"
              },
              {
                "value": "biometric-reader",
                "label": "Biometric reader"
              },
              {
                "value": "fire-panel",
                "label": "Fire panel"
              },
              {
                "value": "smoke-detector",
                "label": "Smoke detector"
              },
              {
                "value": "leak-detector",
                "label": "Leak detector"
              },
              {
                "value": "alarm-siren",
                "label": "Alarm siren"
              }
            ],
            "telecom": [
              {
                "value": "pbx",
                "label": "PBX"
              },
              {
                "value": "voip-gateway",
                "label": "VoIP gateway"
              },
              {
                "value": "ip-phone",
                "label": "IP phone"
              },
              {
                "value": "conference-phone",
                "label": "Conference phone"
              },
              {
                "value": "modem",
                "label": "Modem"
              },
              {
                "value": "optical-transponder",
                "label": "Optical transponder"
              },
              {
                "value": "mux",
                "label": "Multiplexer"
              },
              {
                "value": "radio-link",
                "label": "Radio link"
              }
            ],
            "cloud-virtualization": [
              {
                "value": "cloud-account",
                "label": "Cloud account"
              },
              {
                "value": "cloud-region",
                "label": "Cloud region"
              },
              {
                "value": "vpc",
                "label": "VPC"
              },
              {
                "value": "cloud-subnet",
                "label": "Cloud subnet"
              },
              {
                "value": "security-group",
                "label": "Security group"
              },
              {
                "value": "cloud-load-balancer",
                "label": "Cloud load balancer"
              },
              {
                "value": "cloud-instance",
                "label": "Cloud instance"
              },
              {
                "value": "cloud-volume",
                "label": "Cloud volume"
              },
              {
                "value": "kubernetes-cluster",
                "label": "Kubernetes cluster"
              },
              {
                "value": "kubernetes-node",
                "label": "Kubernetes node"
              },
              {
                "value": "container",
                "label": "Container"
              },
              {
                "value": "namespace",
                "label": "Namespace"
              }
            ],
            "software-service": [
              {
                "value": "application",
                "label": "Application"
              },
              {
                "value": "service",
                "label": "Service"
              },
              {
                "value": "api-service",
                "label": "API service"
              },
              {
                "value": "web-service",
                "label": "Web service"
              },
              {
                "value": "database-instance",
                "label": "Database instance"
              },
              {
                "value": "middleware",
                "label": "Middleware"
              },
              {
                "value": "message-broker",
                "label": "Message broker"
              },
              {
                "value": "license",
                "label": "License"
              },
              {
                "value": "certificate",
                "label": "Certificate"
              },
              {
                "value": "dns-zone",
                "label": "DNS zone"
              }
            ],
            "cable-connectivity": [
              {
                "value": "copper-cable",
                "label": "Copper cable"
              },
              {
                "value": "fiber-cable",
                "label": "Fiber cable"
              },
              {
                "value": "patch-cord",
                "label": "Patch cord"
              },
              {
                "value": "trunk-cable",
                "label": "Trunk cable"
              },
              {
                "value": "transceiver",
                "label": "Transceiver"
              },
              {
                "value": "sfp-module",
                "label": "SFP module"
              },
              {
                "value": "qsfp-module",
                "label": "QSFP module"
              },
              {
                "value": "patch-cassette",
                "label": "Patch cassette"
              }
            ],
            "mobile-iot": [
              {
                "value": "smartphone",
                "label": "Smartphone"
              },
              {
                "value": "rugged-handheld",
                "label": "Rugged handheld"
              },
              {
                "value": "iot-gateway",
                "label": "IoT gateway"
              },
              {
                "value": "industrial-controller",
                "label": "Industrial controller"
              },
              {
                "value": "plc",
                "label": "PLC"
              },
              {
                "value": "sensor",
                "label": "Sensor"
              },
              {
                "value": "actuator",
                "label": "Actuator"
              }
            ],
            "other": [
              {
                "value": "generic-asset",
                "label": "Generic asset"
              },
              {
                "value": "unknown-device",
                "label": "Unknown device"
              },
              {
                "value": "external-resource",
                "label": "External resource"
              }
            ]
          },
          "target": "attributes.resource_type",
          "defaultValue": "rack-server",
          "required": false
        },
        {
          "name": "display_name",
          "label": "Nom affiché cible",
          "placeholder": "srv-db-01 réconcilié"
        },
        {
          "name": "serial",
          "label": "Numéro de série",
          "target": "attributes.serial",
          "placeholder": "SN123456"
        },
        {
          "name": "vendor",
          "label": "Constructeur",
          "target": "attributes.vendor",
          "placeholder": "Dell, HPE, Cisco"
        },
        {
          "name": "model",
          "label": "Modèle",
          "target": "attributes.model",
          "placeholder": "PowerEdge R760"
        },
        {
          "name": "site",
          "label": "Site",
          "target": "attributes.site",
          "placeholder": "PAR1"
        },
        {
          "name": "rack",
          "label": "Rack",
          "target": "attributes.rack",
          "placeholder": "R12"
        },
        {
          "name": "tags",
          "label": "Tags",
          "type": "csv",
          "placeholder": "prod,critical,postgres"
        },
        {
          "name": "apply",
          "label": "Appliquer le plan",
          "type": "boolean"
        }
      ]
    },
    {
      "id": "graph-traverse",
      "label": "Explorer le graphe de dépendances",
      "method": "GET",
      "path": "/v1/graph/traverse",
      "query": [
        {
          "name": "root_key",
          "label": "Clé racine",
          "required": true,
          "placeholder": "application/portail"
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
          "defaultValue": "3",
          "placeholder": "3"
        },
        {
          "name": "max_nodes",
          "label": "Nombre maximal de nœuds",
          "type": "number",
          "defaultValue": "500",
          "placeholder": "500"
        },
        {
          "name": "relation_type",
          "label": "Type de relation",
          "placeholder": "depends_on"
        },
        {
          "name": "as_of",
          "label": "Date ISO-8601",
          "required": false,
          "placeholder": "2026-07-06T10:00:00+02:00"
        }
      ]
    },
    {
      "id": "graph-impact",
      "label": "Analyser les impacts",
      "method": "GET",
      "path": "/v1/graph/impact",
      "query": [
        {
          "name": "root_key",
          "label": "Clé racine",
          "required": true,
          "placeholder": "server/db-01"
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
          "defaultValue": "6",
          "placeholder": "6"
        },
        {
          "name": "max_nodes",
          "label": "Nombre maximal de nœuds",
          "type": "number",
          "defaultValue": "1000",
          "placeholder": "1000"
        },
        {
          "name": "relation_type",
          "label": "Type de relation",
          "placeholder": "depends_on"
        },
        {
          "name": "as_of",
          "label": "Date ISO-8601",
          "required": false,
          "placeholder": "2026-07-06T10:00:00+02:00"
        }
      ]
    },
    {
      "id": "graph-change-impact",
      "label": "Analyser l’impact d’un changement applicatif",
      "method": "GET",
      "path": "/v1/graph/change-impact",
      "query": [
        {"name": "root_key", "label": "Clé de la ressource modifiée", "required": true, "placeholder": "server/db-01"},
        {"name": "direction", "label": "Direction", "type": "select", "options": ["incoming", "outgoing", "both"], "defaultValue": "incoming"},
        {"name": "max_depth", "label": "Profondeur maximale", "type": "number", "defaultValue": "8", "placeholder": "8"},
        {"name": "max_nodes", "label": "Nombre maximal de nœuds", "type": "number", "defaultValue": "2000", "placeholder": "2000"},
        {"name": "relation_type", "label": "Type de relation", "placeholder": "depends_on"},
        {"name": "as_of", "label": "Date ISO-8601", "required": false, "placeholder": "2026-07-06T10:00:00+02:00"},
        {"name": "business_service_kind", "label": "Type de service métier", "placeholder": "application"},
        {"name": "business_service_resource_type", "label": "Type de ressource métier", "placeholder": "api-service"},
        {"name": "affected_sample_limit", "label": "Taille maximale des échantillons", "type": "number", "min": "1", "max": "200", "defaultValue": "25", "placeholder": "25"}
      ]
    },
    {
      "id": "graph-path",
      "label": "Trouver le chemin le plus court",
      "method": "GET",
      "path": "/v1/graph/path",
      "query": [
        {
          "name": "source_key",
          "label": "Ressource source",
          "required": true,
          "placeholder": "application/portail"
        },
        {
          "name": "target_key",
          "label": "Ressource cible",
          "required": true,
          "placeholder": "server/db-01"
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
          "defaultValue": "8",
          "placeholder": "8"
        },
        {
          "name": "max_nodes",
          "label": "Nombre maximal de nœuds",
          "type": "number",
          "defaultValue": "1000",
          "placeholder": "1000"
        },
        {
          "name": "relation_type",
          "label": "Type de relation",
          "placeholder": "depends_on"
        },
        {
          "name": "as_of",
          "label": "Date ISO-8601",
          "required": false,
          "placeholder": "2026-07-06T10:00:00+02:00"
        }
      ]
    },
    {
      "id": "graph-spof",
      "label": "Détecter les points uniques de défaillance",
      "method": "GET",
      "path": "/v1/graph/spof",
      "query": [
        {
          "name": "root_key",
          "label": "Clé racine",
          "required": true,
          "placeholder": "application/portail"
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
          "min": "1",
          "max": "12",
          "defaultValue": "8"
        },
        {
          "name": "max_nodes",
          "label": "Nombre maximal de nœuds",
          "type": "number",
          "min": "2",
          "max": "5000",
          "defaultValue": "2000"
        },
        {
          "name": "relation_type",
          "label": "Type de relation",
          "placeholder": "depends_on"
        },
        {
          "name": "as_of",
          "label": "Date ISO-8601",
          "required": false,
          "placeholder": "2026-07-06T10:00:00+02:00"
        },
        {
          "name": "candidate_kind",
          "label": "Type de candidat",
          "placeholder": "server"
        },
        {
          "name": "candidate_resource_category",
          "label": "Catégorie ressource candidate",
          "placeholder": "network-device"
        },
        {
          "name": "candidate_resource_type",
          "label": "Type de ressource candidat",
          "placeholder": "switch"
        },
        {
          "name": "candidate_status",
          "label": "Statut candidat",
          "placeholder": "active"
        },
        {
          "name": "minimum_affected_nodes",
          "label": "Nombre minimal d’objets affectés",
          "type": "number",
          "min": "1",
          "max": "4999",
          "defaultValue": "1"
        },
        {
          "name": "affected_sample_limit",
          "label": "Limite échantillon affecté",
          "type": "number",
          "min": "1",
          "max": "200",
          "defaultValue": "25"
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "min": "1",
          "max": "500",
          "defaultValue": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur",
          "placeholder": "Curseur opaque retourné par l’API"
        }
      ]
    },
    {
      "id": "graph-export",
      "label": "Exporter le graphe de dépendances",
      "method": "GET",
      "path": "/v1/graph/export",
      "download": true,
      "downloadFilename": "openinfra-graph-export.json",
      "query": [
        {
          "name": "root_key",
          "label": "Clé racine",
          "required": true,
          "placeholder": "application/portail"
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
          "min": "1",
          "max": "12",
          "defaultValue": "8"
        },
        {
          "name": "max_nodes",
          "label": "Nombre maximal de nœuds",
          "type": "number",
          "min": "2",
          "max": "5000",
          "defaultValue": "2000"
        },
        {
          "name": "relation_type",
          "label": "Type de relation",
          "placeholder": "depends_on"
        },
        {
          "name": "as_of",
          "label": "Date ISO-8601",
          "required": false,
          "placeholder": "2026-07-06T10:00:00+02:00"
        },
        {
          "name": "include_spof",
          "label": "Inclure les SPOF",
          "type": "boolean",
          "defaultValue": "true"
        },
        {
          "name": "candidate_kind",
          "label": "Type de candidat",
          "placeholder": "server"
        },
        {
          "name": "candidate_resource_category",
          "label": "Catégorie ressource candidate",
          "placeholder": "network-device"
        },
        {
          "name": "candidate_resource_type",
          "label": "Type de ressource candidat",
          "placeholder": "switch"
        },
        {
          "name": "candidate_status",
          "label": "Statut candidat",
          "placeholder": "active"
        },
        {
          "name": "minimum_affected_nodes",
          "label": "Nombre minimal d’objets affectés",
          "type": "number",
          "min": "1",
          "max": "4999",
          "defaultValue": "1"
        }
      ]
    },
    {
      "id": "simulation-create",
      "label": "Créer un scénario de changement",
      "method": "POST",
      "path": "/v1/simulation-scenarios/create",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "name",
          "label": "Nom du scénario",
          "required": true
        },
        {
          "name": "description",
          "label": "Description",
          "type": "textarea",
          "rows": 4,
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
      "method": "GET",
      "path": "/v1/simulation-scenarios",
      "query": [
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
          "placeholder": "100"
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
      "method": "POST",
      "path": "/v1/simulation-scenarios/run",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "scenario_id",
          "label": "ID scénario",
          "required": true
        },
        {
          "name": "max_depth",
          "label": "Profondeur maximale",
          "type": "number",
          "min": "1",
          "max": "12",
          "defaultValue": "8"
        },
        {
          "name": "max_nodes",
          "label": "Nombre maximal de nœuds",
          "type": "number",
          "min": "2",
          "max": "5000",
          "defaultValue": "2000"
        }
      ]
    },
    {
      "id": "simulation-reports",
      "label": "Lister les rapports d’impact",
      "method": "GET",
      "path": "/v1/impact-reports",
      "query": [
        {
          "name": "scenario_id",
          "label": "ID scénario"
        },
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
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
      "method": "POST",
      "path": "/v1/scenario-comparisons/create",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
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
      "method": "GET",
      "path": "/v1/scenario-comparisons",
      "query": [
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
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
      "method": "POST",
      "path": "/v1/rag/documents/upsert",
      "body": [
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
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        }
      ]
    },
    {
      "id": "rag-documents",
      "label": "Lister les documents gouvernés",
      "method": "GET",
      "path": "/v1/rag/documents",
      "query": [
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
          "placeholder": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur",
          "placeholder": "Curseur de pagination"
        }
      ]
    },
    {
      "id": "rag-document-get",
      "label": "Consulter un document gouverné",
      "method": "GET",
      "path": "/v1/rag/documents/get",
      "query": [
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
      "method": "POST",
      "path": "/v1/rag/documents/deactivate",
      "body": [
        {
          "name": "document_id",
          "label": "ID document",
          "required": true
        },
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        }
      ]
    },
    {
      "id": "rag-rsot-sync",
      "label": "Synchroniser l’index depuis RSOT",
      "method": "POST",
      "path": "/v1/rag/index/rsot",
      "body": [
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
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        }
      ]
    },
    {
      "id": "rag-query",
      "label": "Interroger l’assistant gouverné",
      "method": "POST",
      "path": "/v1/rag/query",
      "body": [
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
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        }
      ]
    },
    {
      "id": "rag-answers",
      "label": "Lister les réponses citées",
      "method": "GET",
      "path": "/v1/rag/answers",
      "query": [
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur",
          "placeholder": "Curseur de pagination"
        }
      ]
    },
    {
      "id": "rag-answer-get",
      "label": "Consulter une réponse citée",
      "method": "GET",
      "path": "/v1/rag/answers/get",
      "query": [
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
      "method": "POST",
      "path": "/v1/rag/jobs/create",
      "body": [
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
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        }
      ]
    },
    {
      "id": "rag-jobs",
      "label": "Lister les jobs RAG",
      "method": "GET",
      "path": "/v1/rag/jobs",
      "query": [
        {
          "name": "limit",
          "label": "Limite",
          "type": "number",
          "placeholder": "100"
        },
        {
          "name": "cursor",
          "label": "Curseur",
          "placeholder": "Curseur de pagination"
        }
      ]
    },
    {
      "id": "rag-job-get",
      "label": "Consulter un job RAG",
      "method": "GET",
      "path": "/v1/rag/jobs/get",
      "query": [
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
      "method": "POST",
      "path": "/v1/rag/jobs/run",
      "body": [
        {
          "name": "job_id",
          "label": "ID job",
          "required": true
        },
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        }
      ]
    },
    {
      "id": "rag-job-artifact",
      "label": "Télécharger un export RAG",
      "method": "GET",
      "path": "/v1/rag/jobs/artifact",
      "download": true,
      "query": [
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

function renderRsotQualityReport(r, app) {
  const reports = Array.isArray(r.reports) ? r.reports : [r];
  const certified = Number(r.certified ?? reports.filter((report) => report.certification_status === "certified").length);
  const warning = Number(r.warning ?? reports.filter((report) => report.certification_status === "warning").length);
  const rejected = Number(r.rejected ?? reports.filter((report) => report.certification_status === "rejected").length);
  const average = Number(r.average_score ?? reports.reduce((total, report) => total + Number(report.score || 0), 0) / Math.max(reports.length, 1));
  const issues = reports.flatMap((report) => Array.isArray(report.issues) ? report.issues.map((issue) => ({ ...issue, key: report.key })) : []);
  const e = (value) => app.escape(String(value ?? "—"));
  const statusClass = rejected > 0 ? "text-bg-danger" : warning > 0 ? "text-bg-warning" : "text-bg-success";
  const status = rejected > 0 ? "Rejeté" : warning > 0 ? "Avertissement" : "Certifié";
  const reportRows = reports.map((report) => `<tr><th scope="row">${e(report.display_name || report.key)}<small class="d-block text-muted">${e(report.key)} · ${e(report.source)}</small></th><td>${e(report.certification_status)}</td><td>${e(report.score || 0)}</td><td>${e(report.completeness_score || 0)}</td><td>${e(report.freshness_score || 0)}</td><td>${e(report.authority_score || 0)}</td><td>${e(report.confidence_score || 0)}</td></tr>`).join("");
  const issueRows = issues.map((issue) => {
    const authorityDetails = issue.actual_source || issue.expected_source || issue.governance_rule
      ? `<small class="d-block text-muted">${e(app.i18n.label("Source observée"))}: ${e(issue.actual_source)} · ${e(app.i18n.label("Source attendue"))}: ${e(issue.expected_source)} · ${e(app.i18n.label("Règle"))}: ${e(issue.governance_rule)}</small>`
      : "";
    return `<tr><td>${e(issue.key)}</td><td>${e(issue.severity)}</td><td>${e(issue.field)}</td><td>${e(issue.code)}</td><td>${e(issue.message)}${authorityDetails}</td></tr>`;
  }).join("");
  return `<section class="openinfra-rsot-quality-report" aria-labelledby="openinfra-rsot-quality-title"><div class="d-flex flex-wrap justify-content-between gap-2"><h4 id="openinfra-rsot-quality-title" class="h6">${e(app.i18n.label("Certification qualité RSOT"))}</h4><span class="badge ${statusClass}">${e(app.i18n.label(status))}</span></div><dl class="row g-2 openinfra-rsot-quality-summary"><div class="col-sm-6"><dt>${e(app.i18n.label("Objets évalués"))}</dt><dd>${e(r.total ?? reports.length)}</dd></div><div class="col-sm-6"><dt>${e(app.i18n.label("Score moyen"))}</dt><dd>${e(average.toFixed(2))}</dd></div><div class="col-sm-6"><dt>${e(app.i18n.label("Certifiés"))}</dt><dd>${e(certified)}</dd></div><div class="col-sm-6"><dt>${e(app.i18n.label("Avertissements / rejets"))}</dt><dd>${e(warning)} / ${e(rejected)}</dd></div></dl><div class="table-responsive"><table class="table table-sm openinfra-rsot-quality-dimensions"><caption>${e(app.i18n.label("Dimensions de qualité"))}</caption><thead><tr><th>${e(app.i18n.t("sourceObject"))}</th><th>${e(app.i18n.label("Statut"))}</th><th>${e(app.i18n.label("Score"))}</th><th>${e(app.i18n.label("Complétude"))}</th><th>${e(app.i18n.label("Fraîcheur"))}</th><th>${e(app.i18n.label("Autorité"))}</th><th>${e(app.i18n.label("Confiance"))}</th></tr></thead><tbody>${reportRows}</tbody></table></div><div class="table-responsive"><table class="table table-sm openinfra-rsot-quality-issues"><caption>${e(app.i18n.label("Anomalies qualité"))}</caption><thead><tr><th>${e(app.i18n.t("sourceObject"))}</th><th>${e(app.i18n.label("Sévérité"))}</th><th>${e(app.i18n.label("Champ"))}</th><th>${e(app.i18n.label("Code"))}</th><th>${e(app.i18n.label("Message"))}</th></tr></thead><tbody>${issueRows || `<tr><td colspan="5">${e(app.i18n.label("Aucune anomalie qualité"))}</td></tr>`}</tbody></table></div></section>`;
}

function renderGovernedRagReport(r, app) {
  const e = (v) => app.escape(v ?? "—"), t = (k) => e(app.i18n.t(k));
  const citations = Array.isArray(r.citations) ? r.citations : [];
  const sources = Array.isArray(r.source_objects) ? r.source_objects : [];
  const governance = r.governance && typeof r.governance === "object" ? r.governance : {};
  const mutationPerformed = governance.source_data_mutation_performed === true;
  const validationRequired = governance.change_validation_required !== false;
  const sourceRows = sources.map((source) => `<tr><th>${e(source.title || source.object_key)}<small class="d-block text-muted">${e(source.object_key)}</small></th><td>${e(source.source_uri)}</td><td>${e(source.score || "0")}</td></tr>`).join("");
  const citationRows = citations.map((citation) => `<tr><th>${e(citation.title || citation.source_ref)}<small class="d-block text-muted">${e(citation.source_ref)}</small></th><td>${e(citation.source_type)}</td><td>${e(citation.score || "0")}</td><td>${e(citation.excerpt)}</td></tr>`).join("");
  return `<section class="openinfra-rag-governance-report" aria-labelledby="openinfra-rag-governance-title"><div class="d-flex flex-wrap justify-content-between gap-2"><h4 id="openinfra-rag-governance-title" class="h6">${t("resultTitle")}</h4><span class="badge ${mutationPerformed ? "text-bg-danger" : "text-bg-success"}">${e(governance.mode || app.i18n.t("reads"))}</span></div><dl class="row g-2 openinfra-rag-governance-summary"><div class="col-sm-6 col-xl-3"><dt>${e(app.i18n.label("Statut"))}</dt><dd>${e(r.status)}</dd></div><div class="col-sm-6 col-xl-3"><dt>${e(app.i18n.label("Confiance (0 à 1)"))}</dt><dd>${e(r.confidence || "0")}</dd></div><div class="col-sm-6 col-xl-3"><dt>${t("mutations")}</dt><dd>${t(mutationPerformed ? "yes" : "no")}</dd></div><div class="col-sm-6 col-xl-3"><dt>${t("required")}</dt><dd>${t(validationRequired ? "yes" : "no")}</dd></div></dl><p class="openinfra-rag-answer" role="status" aria-live="polite">${e(r.answer)}</p><div class="table-responsive"><table class="table table-sm openinfra-rag-source-objects"><caption>${t("sourceObject")}</caption><thead><tr><th>${t("sourceObject")}</th><th>${t("provenance")}</th><th>${e(app.i18n.label("Confiance (0 à 1)"))}</th></tr></thead><tbody>${sourceRows || `<tr><td colspan="3">${t("noGraphData")}</td></tr>`}</tbody></table></div><div class="table-responsive"><table class="table table-sm openinfra-rag-citations"><caption>${t("provenance")}</caption><thead><tr><th>${t("sourceObject")}</th><th>${e(app.i18n.label("Source"))}</th><th>${e(app.i18n.label("Confiance (0 à 1)"))}</th><th>${t("resultTitle")}</th></tr></thead><tbody>${citationRows || `<tr><td colspan="4">${t("noGraphData")}</td></tr>`}</tbody></table></div></section>`;
}

function renderChangeImpactReport(r, app) {
  const e = (v) => app.escape(v ?? "—"), t = (k) => e(app.i18n.t(k));
  const services = Array.isArray(r.business_services) ? r.business_services : [];
  const dependencies = Array.isArray(r.critical_dependencies) ? r.critical_dependencies : [];
  const serviceRows = services.map((v) => `<tr><th>${e(v.display_name || v.key)}</th><td>${e(v.resource_type || v.kind)}</td><td>${e(v.depth)}</td></tr>`).join("");
  const dependencyRows = dependencies.map((v) => { const n = v.node || {}; return `<tr><th>${e(n.display_name || n.key)}</th><td>${e(String(v.risk_level || "").toUpperCase())}</td><td>${e(v.affected_business_service_count || 0)}</td><td>${e(v.affected_node_count || 0)}</td><td>${e((v.affected_business_service_keys || []).join(", "))}</td></tr>`; }).join("");
  return `<section class="openinfra-change-impact-report" aria-labelledby="openinfra-change-impact-title"><h4 id="openinfra-change-impact-title" class="h6">${t("changeImpactReport")}</h4><p><span class="badge ${r.complete === false ? "text-bg-warning" : "text-bg-success"}">${t(r.complete === false ? "boundedAnalysis" : "completeAnalysis")}</span> · ${t("affectedNodes")}: ${e(r.impacted_count || 0)} · ${t("impactedBusinessServices")}: ${e(r.business_service_count || services.length)} · ${t("criticalDependencies")}: ${e(r.critical_dependency_count || dependencies.length)} · ${t("rootSpofRisk")}: ${t(r.root_spof_risk ? "yes" : "no")}</p><div class="table-responsive"><table class="table table-sm openinfra-change-impact-services"><caption>${t("impactedBusinessServices")}</caption><thead><tr><th>${t("impactedBusinessServices")}</th><th>${e(app.i18n.label("Type de ressource"))}</th><th>${t("graphDepth")}</th></tr></thead><tbody>${serviceRows || `<tr><td colspan="3">${t("noGraphData")}</td></tr>`}</tbody></table></div><div class="table-responsive"><table class="table table-sm openinfra-change-impact-dependencies"><caption>${t("criticalDependencies")}</caption><thead><tr><th>${t("criticalDependencies")}</th><th>${t("riskLevel")}</th><th>${t("impactedBusinessServices")}</th><th>${t("affectedNodes")}</th><th>${t("affectedSample")}</th></tr></thead><tbody>${dependencyRows || `<tr><td colspan="5">${t("noGraphData")}</td></tr>`}</tbody></table></div></section>`;
}

function renderTimeTravelReport(r, app) {
  const e = (v) => app.escape(v ?? "—"), t = (k) => e(app.i18n.t(k));
  const relations = Array.isArray(r.relations) ? r.relations : [];
  const provenance = r.provenance && typeof r.provenance === "object" ? r.provenance : {};
  const relationRows = relations.map((relation) => `<tr><td>${e(relation.relation_type)}</td><td>${e(relation.source_key)}</td><td>${e(relation.target_key)}</td><td>${e(relation.provenance)}</td><td>${e(relation.valid_from)} → ${e(relation.valid_to || "∞")}</td></tr>`).join("");
  return `<section class="openinfra-time-travel-report" aria-labelledby="openinfra-time-travel-title"><div class="d-flex flex-wrap justify-content-between gap-2"><h4 id="openinfra-time-travel-title" class="h6">${t("timeTravelReport")}</h4><span class="badge ${r.complete === false ? "text-bg-warning" : "text-bg-success"}">${t(r.complete === false ? "boundedHistoricalState" : "completeHistoricalState")}</span></div><dl class="row g-2 openinfra-time-travel-summary"><div class="col-sm-6"><dt>${t("historicalObject")}</dt><dd>${e(r.display_name || r.key)}<small class="d-block text-muted">${e(r.key)}</small></dd></div><div class="col-sm-6"><dt>${t("requestedAt")}</dt><dd>${e(r.as_of)}</dd></div><div class="col-sm-6"><dt>${t("resolvedVersion")}</dt><dd>${e(r.resolved_version || r.version)}</dd></div><div class="col-sm-6"><dt>${t("historicalRelations")}</dt><dd>${e(r.relation_count || relations.length)}</dd></div></dl><div class="table-responsive"><table class="table table-sm openinfra-time-travel-provenance"><caption>${t("provenance")}</caption><thead><tr><th>${t("sourceSystem")}</th><th>${t("snapshotChangedBy")}</th><th>${t("snapshotChangedAt")}</th><th>${t("snapshotIdentifier")}</th></tr></thead><tbody><tr><td>${e(provenance.source_system || r.source)}</td><td>${e(provenance.changed_by || r.snapshot_changed_by)}</td><td>${e(provenance.snapshot_changed_at || r.snapshot_changed_at)}</td><td>${e(provenance.snapshot_id || r.snapshot_id)}</td></tr></tbody></table></div><div class="table-responsive"><table class="table table-sm openinfra-time-travel-relations"><caption>${t("historicalRelations")}</caption><thead><tr><th>${t("relationType")}</th><th>${t("sourceObject")}</th><th>${t("targetObject")}</th><th>${t("provenance")}</th><th>${t("validityWindow")}</th></tr></thead><tbody>${relationRows || `<tr><td colspan="5">${t("noHistoricalRelations")}</td></tr>`}</tbody></table></div></section>`;
}

moduleDefinition.renderResult = (operation, result, app) => {
  if (operation.id === "rsot-as-of") return renderTimeTravelReport(result, app);
  if (operation.id === "rag-query") return renderGovernedRagReport(result, app);
  if (operation.id === "rsot-quality-object" || operation.id === "rsot-quality-summary") return renderRsotQualityReport(result, app);
  if (operation.id === "graph-change-impact") return renderChangeImpactReport(result, app) + app.renderDependencyGraph(result);
  return "";
};

export default moduleDefinition;

export const resourceTaxonomy = {
  "server": [
    {
      "value": "rack-server",
      "label": "Rack server"
    },
    {
      "value": "blade-server",
      "label": "Blade server"
    },
    {
      "value": "tower-server",
      "label": "Tower server"
    },
    {
      "value": "hypervisor-host",
      "label": "Hypervisor host"
    },
    {
      "value": "virtual-machine",
      "label": "Virtual machine"
    },
    {
      "value": "container-host",
      "label": "Container host"
    },
    {
      "value": "compute-appliance",
      "label": "Compute appliance"
    }
  ],
  "personal-computer": [
    {
      "value": "laptop",
      "label": "Laptop"
    },
    {
      "value": "desktop",
      "label": "Desktop"
    },
    {
      "value": "workstation",
      "label": "Workstation"
    },
    {
      "value": "thin-client",
      "label": "Thin client"
    },
    {
      "value": "all-in-one",
      "label": "All-in-one"
    },
    {
      "value": "tablet",
      "label": "Tablet"
    },
    {
      "value": "kiosk",
      "label": "Kiosk"
    }
  ],
  "monitor-peripheral": [
    {
      "value": "monitor",
      "label": "Monitor"
    },
    {
      "value": "keyboard",
      "label": "Keyboard"
    },
    {
      "value": "mouse",
      "label": "Mouse"
    },
    {
      "value": "docking-station",
      "label": "Docking station"
    },
    {
      "value": "webcam",
      "label": "Webcam"
    },
    {
      "value": "headset",
      "label": "Headset"
    },
    {
      "value": "printer",
      "label": "Printer"
    },
    {
      "value": "scanner",
      "label": "Scanner"
    },
    {
      "value": "barcode-scanner",
      "label": "Barcode scanner"
    },
    {
      "value": "kvm-console",
      "label": "KVM console"
    }
  ],
  "network-device": [
    {
      "value": "switch",
      "label": "Switch"
    },
    {
      "value": "core-switch",
      "label": "Core switch"
    },
    {
      "value": "distribution-switch",
      "label": "Distribution switch"
    },
    {
      "value": "access-switch",
      "label": "Access switch"
    },
    {
      "value": "router",
      "label": "Router"
    },
    {
      "value": "firewall",
      "label": "Firewall"
    },
    {
      "value": "load-balancer",
      "label": "Load balancer"
    },
    {
      "value": "vpn-gateway",
      "label": "VPN gateway"
    },
    {
      "value": "sdwan-edge",
      "label": "SD-WAN edge"
    },
    {
      "value": "wireless-controller",
      "label": "Wireless controller"
    },
    {
      "value": "wireless-access-point",
      "label": "Wireless access point"
    },
    {
      "value": "proxy-appliance",
      "label": "Proxy appliance"
    },
    {
      "value": "wan-accelerator",
      "label": "WAN accelerator"
    },
    {
      "value": "network-tap",
      "label": "Network TAP"
    },
    {
      "value": "packet-broker",
      "label": "Packet broker"
    },
    {
      "value": "network-interface",
      "label": "Network interface"
    }
  ],
  "storage": [
    {
      "value": "storage-array",
      "label": "Storage array"
    },
    {
      "value": "nas-appliance",
      "label": "NAS appliance"
    },
    {
      "value": "san-switch",
      "label": "SAN switch"
    },
    {
      "value": "storage-controller",
      "label": "Storage controller"
    },
    {
      "value": "storage-shelf",
      "label": "Storage shelf"
    },
    {
      "value": "hdd",
      "label": "HDD"
    },
    {
      "value": "ssd",
      "label": "SSD"
    },
    {
      "value": "nvme-drive",
      "label": "NVMe drive"
    },
    {
      "value": "tape-library",
      "label": "Tape library"
    },
    {
      "value": "backup-appliance",
      "label": "Backup appliance"
    },
    {
      "value": "object-storage-node",
      "label": "Object storage node"
    }
  ],
  "power-supply": [
    {
      "value": "ups",
      "label": "UPS"
    },
    {
      "value": "pdu",
      "label": "PDU"
    },
    {
      "value": "ats",
      "label": "Automatic transfer switch"
    },
    {
      "value": "sts",
      "label": "Static transfer switch"
    },
    {
      "value": "rectifier",
      "label": "Rectifier"
    },
    {
      "value": "inverter",
      "label": "Inverter"
    },
    {
      "value": "battery-pack",
      "label": "Battery pack"
    },
    {
      "value": "power-shelf",
      "label": "Power shelf"
    },
    {
      "value": "generator",
      "label": "Generator"
    },
    {
      "value": "busway",
      "label": "Busway"
    },
    {
      "value": "power-meter",
      "label": "Power meter"
    }
  ],
  "rack-facility": [
    {
      "value": "rack",
      "label": "Rack"
    },
    {
      "value": "cabinet",
      "label": "Cabinet"
    },
    {
      "value": "patch-panel",
      "label": "Patch panel"
    },
    {
      "value": "fiber-panel",
      "label": "Fiber panel"
    },
    {
      "value": "cable-management",
      "label": "Cable management"
    },
    {
      "value": "containment",
      "label": "Containment"
    },
    {
      "value": "raised-floor-tile",
      "label": "Raised floor tile"
    },
    {
      "value": "sensor-probe",
      "label": "Sensor probe"
    },
    {
      "value": "rack-accessory",
      "label": "Rack accessory"
    }
  ],
  "cooling": [
    {
      "value": "crac",
      "label": "CRAC"
    },
    {
      "value": "crah",
      "label": "CRAH"
    },
    {
      "value": "in-row-cooler",
      "label": "In-row cooler"
    },
    {
      "value": "rear-door-heat-exchanger",
      "label": "Rear-door heat exchanger"
    },
    {
      "value": "chiller",
      "label": "Chiller"
    },
    {
      "value": "cooling-tower",
      "label": "Cooling tower"
    },
    {
      "value": "heat-exchanger",
      "label": "Heat exchanger"
    },
    {
      "value": "humidifier",
      "label": "Humidifier"
    },
    {
      "value": "environmental-sensor",
      "label": "Environmental sensor"
    }
  ],
  "security-safety": [
    {
      "value": "cctv-camera",
      "label": "CCTV camera"
    },
    {
      "value": "access-control-reader",
      "label": "Access control reader"
    },
    {
      "value": "door-controller",
      "label": "Door controller"
    },
    {
      "value": "biometric-reader",
      "label": "Biometric reader"
    },
    {
      "value": "fire-panel",
      "label": "Fire panel"
    },
    {
      "value": "smoke-detector",
      "label": "Smoke detector"
    },
    {
      "value": "leak-detector",
      "label": "Leak detector"
    },
    {
      "value": "alarm-siren",
      "label": "Alarm siren"
    }
  ],
  "telecom": [
    {
      "value": "pbx",
      "label": "PBX"
    },
    {
      "value": "voip-gateway",
      "label": "VoIP gateway"
    },
    {
      "value": "ip-phone",
      "label": "IP phone"
    },
    {
      "value": "conference-phone",
      "label": "Conference phone"
    },
    {
      "value": "modem",
      "label": "Modem"
    },
    {
      "value": "optical-transponder",
      "label": "Optical transponder"
    },
    {
      "value": "mux",
      "label": "Multiplexer"
    },
    {
      "value": "radio-link",
      "label": "Radio link"
    }
  ],
  "cloud-virtualization": [
    {
      "value": "cloud-account",
      "label": "Cloud account"
    },
    {
      "value": "cloud-region",
      "label": "Cloud region"
    },
    {
      "value": "vpc",
      "label": "VPC"
    },
    {
      "value": "cloud-subnet",
      "label": "Cloud subnet"
    },
    {
      "value": "security-group",
      "label": "Security group"
    },
    {
      "value": "cloud-load-balancer",
      "label": "Cloud load balancer"
    },
    {
      "value": "cloud-instance",
      "label": "Cloud instance"
    },
    {
      "value": "cloud-volume",
      "label": "Cloud volume"
    },
    {
      "value": "kubernetes-cluster",
      "label": "Kubernetes cluster"
    },
    {
      "value": "kubernetes-node",
      "label": "Kubernetes node"
    },
    {
      "value": "container",
      "label": "Container"
    },
    {
      "value": "namespace",
      "label": "Namespace"
    }
  ],
  "software-service": [
    {
      "value": "application",
      "label": "Application"
    },
    {
      "value": "service",
      "label": "Service"
    },
    {
      "value": "api-service",
      "label": "API service"
    },
    {
      "value": "web-service",
      "label": "Web service"
    },
    {
      "value": "database-instance",
      "label": "Database instance"
    },
    {
      "value": "middleware",
      "label": "Middleware"
    },
    {
      "value": "message-broker",
      "label": "Message broker"
    },
    {
      "value": "license",
      "label": "License"
    },
    {
      "value": "certificate",
      "label": "Certificate"
    },
    {
      "value": "dns-zone",
      "label": "DNS zone"
    }
  ],
  "cable-connectivity": [
    {
      "value": "copper-cable",
      "label": "Copper cable"
    },
    {
      "value": "fiber-cable",
      "label": "Fiber cable"
    },
    {
      "value": "patch-cord",
      "label": "Patch cord"
    },
    {
      "value": "trunk-cable",
      "label": "Trunk cable"
    },
    {
      "value": "transceiver",
      "label": "Transceiver"
    },
    {
      "value": "sfp-module",
      "label": "SFP module"
    },
    {
      "value": "qsfp-module",
      "label": "QSFP module"
    },
    {
      "value": "patch-cassette",
      "label": "Patch cassette"
    }
  ],
  "mobile-iot": [
    {
      "value": "smartphone",
      "label": "Smartphone"
    },
    {
      "value": "rugged-handheld",
      "label": "Rugged handheld"
    },
    {
      "value": "iot-gateway",
      "label": "IoT gateway"
    },
    {
      "value": "industrial-controller",
      "label": "Industrial controller"
    },
    {
      "value": "plc",
      "label": "PLC"
    },
    {
      "value": "sensor",
      "label": "Sensor"
    },
    {
      "value": "actuator",
      "label": "Actuator"
    }
  ],
  "other": [
    {
      "value": "generic-asset",
      "label": "Generic asset"
    },
    {
      "value": "unknown-device",
      "label": "Unknown device"
    },
    {
      "value": "external-resource",
      "label": "External resource"
    }
  ]
};
export const resourceCategories = [
  {
    "value": "server",
    "label": "Server"
  },
  {
    "value": "personal-computer",
    "label": "Personal computer"
  },
  {
    "value": "monitor-peripheral",
    "label": "Monitor and peripheral"
  },
  {
    "value": "network-device",
    "label": "Network device"
  },
  {
    "value": "storage",
    "label": "Storage"
  },
  {
    "value": "power-supply",
    "label": "Power supply"
  },
  {
    "value": "rack-facility",
    "label": "Rack and facility"
  },
  {
    "value": "cooling",
    "label": "Cooling"
  },
  {
    "value": "security-safety",
    "label": "Security and safety"
  },
  {
    "value": "telecom",
    "label": "Telecom"
  },
  {
    "value": "cloud-virtualization",
    "label": "Cloud and virtualization"
  },
  {
    "value": "software-service",
    "label": "Software and service"
  },
  {
    "value": "cable-connectivity",
    "label": "Cable and connectivity"
  },
  {
    "value": "mobile-iot",
    "label": "Mobile and IoT"
  },
  {
    "value": "other",
    "label": "Other"
  }
];
