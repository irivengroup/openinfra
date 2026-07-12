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
