class OpenInfraApiClient {
  constructor(apiBaseUrl, tenantProvider) {
    this.apiBaseUrl = apiBaseUrl.replace(/\/$/, "");
    this.tenantProvider = tenantProvider;
  }

  async request(operation, payload) {
    const path = this.interpolatePath(operation.path, payload);
    const query = this.buildQuery(operation.query || [], payload);
    const headers = { Accept: "application/json" };
    if (operation.method !== "GET") {
      headers["Content-Type"] = "application/json";
    }
    const body = operation.method === "GET" ? undefined : JSON.stringify(this.buildBody(operation, payload));
    const response = await fetch(`${this.apiBaseUrl}${path}${query}`, {
      method: operation.method,
      credentials: "same-origin",
      headers,
      body
    });
    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json") ? await response.json() : await response.text();
    if (!response.ok) {
      throw new Error(typeof data === "string" ? data : JSON.stringify(data));
    }
    return data;
  }

  async getJson(path) {
    const response = await fetch(path, {
      credentials: "same-origin",
      headers: { Accept: "application/json" }
    });
    if (!response.ok) {
      throw new Error(`${path} returned ${response.status}`);
    }
    return response.json();
  }

  interpolatePath(path, payload) {
    return path.replace(/\{([^}]+)\}/g, (_, key) => encodeURIComponent(payload[key] || ""));
  }

  buildQuery(fields, payload) {
    const query = new URLSearchParams();
    for (const field of fields) {
      const value = this.normalizedFieldValue(field, payload[field.name]);
      if (value !== undefined && value !== null && String(value).trim() !== "") {
        query.set(field.name, String(value));
      }
    }
    const tenant = this.tenantProvider();
    if (tenant && !query.has("tenant_id")) {
      query.set("tenant_id", tenant);
    }
    return query.toString() ? `?${query.toString()}` : "";
  }

  buildBody(operation, payload) {
    const body = {};
    for (const field of operation.body || []) {
      const raw = payload[field.name];
      const value = this.normalizedFieldValue(field, raw);
      if (value === undefined || value === null || String(value).trim?.() === "") {
        if (field.required) {
          throw new Error(`Champ obligatoire manquant: ${field.label || field.name}`);
        }
        continue;
      }
      this.assignBodyValue(body, field.target || field.name, value);
    }
    const tenant = this.tenantProvider();
    if (tenant && operation.body && !Object.prototype.hasOwnProperty.call(body, "tenant_id")) {
      body.tenant_id = tenant;
    }
    return body;
  }

  normalizedFieldValue(field, raw) {
    if (raw === undefined || raw === null) {
      return undefined;
    }
    const value = String(raw).trim();
    if (!value) {
      return undefined;
    }
    if (field.type === "number") {
      const parsed = Number(value);
      if (Number.isNaN(parsed)) {
        throw new Error(`Valeur numérique invalide: ${field.label || field.name}`);
      }
      return parsed;
    }
    if (field.type === "boolean") {
      return ["1", "true", "yes", "oui"].includes(value.toLowerCase());
    }
    if (field.type === "csv") {
      return value.split(",").map((item) => item.trim()).filter(Boolean);
    }
    if (field.type === "json") {
      return JSON.parse(value);
    }
    return value;
  }

  assignBodyValue(body, target, value) {
    const parts = target.split(".");
    let current = body;
    for (const part of parts.slice(0, -1)) {
      if (!Object.prototype.hasOwnProperty.call(current, part)) {
        current[part] = {};
      }
      current = current[part];
    }
    current[parts[parts.length - 1]] = value;
  }
}

const OPENINFRA_ICONS = {
  home: "M8 3.293l6 6V15a1 1 0 0 1-1 1h-3v-4H6v4H3a1 1 0 0 1-1-1V9.293l6-6zm5-.793V6l-2-2V2.5a.5.5 0 0 1 .5-.5h1a.5.5 0 0 1 .5.5z",
  search: "M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.099zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z",
  speedometer2: "M8 4a.5.5 0 0 1 .5.5V6a.5.5 0 0 1-1 0V4.5A.5.5 0 0 1 8 4zM3.732 5.732a.5.5 0 0 1 .707 0l.915.914a.5.5 0 1 1-.708.708l-.914-.915a.5.5 0 0 1 0-.707zM2 10a.5.5 0 0 1 .5-.5h1.586a.5.5 0 0 1 0 1H2.5A.5.5 0 0 1 2 10zm9.5 0a.5.5 0 0 1 .5-.5h1.5a.5.5 0 0 1 0 1H12a.5.5 0 0 1-.5-.5zm.754-4.246a.5.5 0 0 1 0 .707l-.94.94a.5.5 0 1 1-.707-.708l.94-.94a.5.5 0 0 1 .707 0zM9.67 11.71a2 2 0 1 1-3.34-2.19l3.95-3.95a.5.5 0 0 1 .8.6l-1.41 5.54zM8 1a7 7 0 0 0-7 7c0 1.71.61 3.28 1.63 4.5a.5.5 0 0 0 .38.17h9.98a.5.5 0 0 0 .38-.17A6.97 6.97 0 0 0 15 8a7 7 0 0 0-7-7z",
  table: "M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V2zm15 2h-4v3h4V4zm0 4h-4v3h4V8zm0 4h-4v3h3a1 1 0 0 0 1-1v-2zm-5 3v-3H6v3h4zm-5 0v-3H1v2a1 1 0 0 0 1 1h3zm-4-4h4V8H1v3zm0-4h4V4H1v3zm5-3v3h4V4H6zm4 4H6v3h4V8z",
  reference: "M1 2a2 2 0 0 1 2-2h1.6a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V2zm6.7 0a2 2 0 0 1 2-2h1.6a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H9.7a2 2 0 0 1-2-2V2zm6.25.55A1.8 1.8 0 0 1 15 4.18v7.64a1.8 1.8 0 0 1-1.05 1.63V2.55z",
  asset: "M2 1a2 2 0 0 1 2-2h5.6a2 2 0 0 1 1.414.586l2.4 2.4A2 2 0 0 1 14 3.4V14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V1zm2 .8a.8.8 0 0 0-.8.8v10.8a.8.8 0 0 0 .8.8h8a.8.8 0 0 0 .8-.8V4.4h-2.2a1.8 1.8 0 0 1-1.8-1.8V.8H4zm1.25 5.05a.85.85 0 1 0 0-1.7.85.85 0 0 0 0 1.7zm2.05-.6a.6.6 0 0 0 0 1.2h3.9a.6.6 0 1 0 0-1.2H7.3zm-2.05 4.6a.85.85 0 1 0 0-1.7.85.85 0 0 0 0 1.7zm2.05-.6a.6.6 0 1 0 0 1.2h3.9a.6.6 0 1 0 0-1.2H7.3z",
  grid: "M1 2.5A1.5 1.5 0 0 1 2.5 1h3A1.5 1.5 0 0 1 7 2.5v3A1.5 1.5 0 0 1 5.5 7h-3A1.5 1.5 0 0 1 1 5.5v-3zm8 0A1.5 1.5 0 0 1 10.5 1h3A1.5 1.5 0 0 1 15 2.5v3A1.5 1.5 0 0 1 13.5 7h-3A1.5 1.5 0 0 1 9 5.5v-3zm-8 8A1.5 1.5 0 0 1 2.5 9h3A1.5 1.5 0 0 1 7 10.5v3A1.5 1.5 0 0 1 5.5 15h-3A1.5 1.5 0 0 1 1 13.5v-3zm8 0A1.5 1.5 0 0 1 10.5 9h3a1.5 1.5 0 0 1 1.5 1.5v3a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 9 13.5v-3z",
  people: "M11 6a3 3 0 1 1-6 0 3 3 0 0 1 6 0zm-1.559 4.27A4.985 4.985 0 0 0 8 10c-2.67 0-4.9 2.1-4.99 4.71A1 1 0 0 0 4 15h8a1 1 0 0 0 .99-1.29 5.002 5.002 0 0 0-3.549-3.44zM13.5 7a2.5 2.5 0 0 1-1.18 2.12 6.01 6.01 0 0 1 2.2 2.56A1 1 0 0 0 15.5 10.5 3.5 3.5 0 0 0 12 7h1.5z",
  shield: "M5.338 1.59a61.44 61.44 0 0 0-2.837.856.48.48 0 0 0-.328.39c-.554 4.157.726 7.19 2.253 9.188A10.7 10.7 0 0 0 8 15a10.7 10.7 0 0 0 3.574-2.976c1.527-1.998 2.807-5.031 2.253-9.188a.48.48 0 0 0-.328-.39 61.44 61.44 0 0 0-2.837-.856C9.552 1.29 8.531 1.067 8 1.067c-.531 0-1.552.223-2.662.523z",
  activity: "M6.5 12a.5.5 0 0 1-.447-.276L3.382 6.382 1.894 9.36A.5.5 0 0 1 1.447 9.636H.5a.5.5 0 0 1 0-1h.638l1.915-3.83a.5.5 0 0 1 .894 0L6.5 9.91l2.553-5.105a.5.5 0 0 1 .894 0l1.915 3.83h3.638a.5.5 0 0 1 0 1h-3.947a.5.5 0 0 1-.447-.276L9.5 6.382l-2.553 5.342A.5.5 0 0 1 6.5 12z"
};

const RESOURCE_TAXONOMY = {
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
const RESOURCE_CATEGORY_OPTIONS = [
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
const SOURCE_OPTIONS = ["manual", "import", "backend-discovery", "enterprise-proxy", "api"];

const FIELD_SETS = {
  tenant: { name: "tenant_id", label: "Tenant", defaultValue: "default", placeholder: "default" },
  limit: { name: "limit", label: "Limite", type: "number", placeholder: "100" },
  jobId: { name: "job_id", label: "Job ID", required: true, placeholder: "job import massif" },
  exportJobId: { name: "job_id", label: "Job export", required: true, placeholder: "job export signé" },
  chunkOffset: { name: "offset", label: "Offset octets", type: "number", defaultValue: "0", placeholder: "0" },
  chunkSize: { name: "size", label: "Taille chunk", type: "number", defaultValue: "65536", placeholder: "65536" },
  resourceCategory: { name: "resource_category", label: "Catégorie", type: "select", options: RESOURCE_CATEGORY_OPTIONS, target: "kind", defaultValue: "server" },
  resourceType: { name: "resource_type", label: "Type de ressource", type: "select", optionsByField: "resource_category", optionsMap: RESOURCE_TAXONOMY, target: "attributes.resource_type", defaultValue: "rack-server" },
  resourceCategoryFilter: { name: "resource_category", label: "Catégorie", type: "select", options: RESOURCE_CATEGORY_OPTIONS },
  resourceTypeFilter: { name: "resource_type", label: "Type de ressource", type: "select", optionsByField: "resource_category", optionsMap: RESOURCE_TAXONOMY },
  riKind: { name: "kind", label: "Catégorie", type: "select", options: RESOURCE_CATEGORY_OPTIONS },
  tag: { name: "tag", label: "Tag", placeholder: "prod" },
  actor: { name: "actor", label: "Opérateur", required: true, placeholder: "admin@openinfra" },
  riKey: { name: "key", label: "Clé ITRM", required: true, placeholder: "server/srv-db-01" },
  displayName: { name: "display_name", label: "Nom affiché", required: true, placeholder: "srv-db-01" },
  source: { name: "source", label: "Source autoritative", required: true, type: "select", options: SOURCE_OPTIONS },
  serial: { name: "serial", label: "Numéro de série", target: "attributes.serial", placeholder: "SN123456" },
  vendor: { name: "vendor", label: "Constructeur", target: "attributes.vendor", placeholder: "Dell, HPE, Cisco" },
  model: { name: "model", label: "Modèle", target: "attributes.model", placeholder: "PowerEdge R760" },
  site: { name: "site", label: "Site", target: "attributes.site", placeholder: "PAR1" },
  building: { name: "building", label: "Bâtiment", target: "attributes.building", placeholder: "B1" },
  room: { name: "room", label: "Salle", target: "attributes.room", placeholder: "DC-A" },
  row: { name: "row", label: "Ligne salle", target: "attributes.row", placeholder: "Rangée A" },
  column: { name: "column", label: "Colonne salle", target: "attributes.column", placeholder: "Colonne 04" },
  rack: { name: "rack", label: "Rack", target: "attributes.rack", placeholder: "R12" },
  managementIp: { name: "management_ip", label: "IP de management", target: "attributes.management_ip", placeholder: "10.10.10.15" },
  lifecycle: { name: "lifecycle_state", label: "État cycle de vie", target: "attributes.lifecycle_state", type: "select", options: ["planned", "active", "maintenance", "retired"] },
  tags: { name: "tags", label: "Tags", type: "csv", placeholder: "prod,critical,postgres" },
  asOf: { name: "as_of", label: "Date ISO-8601", required: true, placeholder: "2026-07-06T10:00:00+02:00" },
  edition: { name: "edition", label: "Édition", type: "select", options: ["lite", "pro", "enterprise"], defaultValue: "enterprise" },
  featureCapability: { name: "capability", label: "Capacité", type: "select", options: ["core_it_resources_management", "dcim", "ipam", "rbac", "audit", "import_export", "distributed_discovery_agents", "installer_agent_scope"], defaultValue: "ipam" },
  quotaResource: { name: "resource", label: "Ressource quota", type: "select", options: ["equipment", "subnet_vlan", "ip_dns_record", "user", "discovery_collector"], defaultValue: "equipment" },
  requestedIncrement: { name: "requested_increment", label: "Incrément demandé", type: "number", defaultValue: "1", placeholder: "1" }
};

const OPENINFRA_MODULES = [
  { id: "overview", label: "Dashboard", icon: "speedometer2", description: "Vue de synthèse, readiness backend, version package, trust web-backend et opérations rapides.", operations: [
    { id: "version", label: "Version runtime", method: "GET", path: "/v1/version", query: [] },
    { id: "schema", label: "Statut schéma DB", method: "GET", path: "/v1/database/schema", query: [] }
  ] },
  { id: "itrm", label: "IT Ressources Management", shortLabel: "ITRM", icon: "reference", description: "Inventaire canonique, relations, versions, gouvernance et certification.", operations: [
    { id: "itrm-taxonomy", label: "Catalogue catégories / types", method: "GET", path: "/v1/itrm/resource-taxonomy", query: [] },
    { id: "itrm-list", label: "Lister les objets ITRM", method: "GET", path: "/v1/itrm/objects", query: [FIELD_SETS.resourceCategoryFilter, FIELD_SETS.resourceTypeFilter, FIELD_SETS.tag, FIELD_SETS.limit] },
    { id: "itrm-upsert", label: "Créer / mettre à jour une ressource", method: "POST", path: "/v1/itrm/objects", body: [FIELD_SETS.actor, FIELD_SETS.riKey, { ...FIELD_SETS.resourceCategory, required: true }, { ...FIELD_SETS.resourceType, required: true }, FIELD_SETS.displayName, FIELD_SETS.source, FIELD_SETS.serial, FIELD_SETS.vendor, FIELD_SETS.model, FIELD_SETS.site, FIELD_SETS.building, FIELD_SETS.room, FIELD_SETS.row, FIELD_SETS.column, FIELD_SETS.rack, FIELD_SETS.managementIp, FIELD_SETS.lifecycle, FIELD_SETS.tags] },
    { id: "itrm-relations", label: "Lister les relations", method: "GET", path: "/v1/itrm/relations", query: [{ name: "source_key", label: "Ressource source" }, { name: "target_key", label: "Ressource cible" }, { name: "relation_type", label: "Type de relation" }, { ...FIELD_SETS.asOf, required: false }, FIELD_SETS.limit] },
    { id: "itrm-as-of", label: "Restituer une ressource à date", method: "GET", path: "/v1/itrm/object-as-of", query: [FIELD_SETS.riKey, FIELD_SETS.asOf] },
    { id: "itrm-object-audit", label: "Audit d’une ressource", method: "GET", path: "/v1/itrm/object-audit", query: [FIELD_SETS.riKey, FIELD_SETS.limit] },
    { id: "itrm-quality-object", label: "Évaluer la qualité d’une ressource", method: "GET", path: "/v1/itrm/quality/object", query: [FIELD_SETS.riKey] },
    { id: "itrm-quality-summary", label: "Synthèse qualité / certification", method: "GET", path: "/v1/itrm/quality/summary", query: [FIELD_SETS.resourceCategoryFilter, FIELD_SETS.resourceTypeFilter, FIELD_SETS.tag, FIELD_SETS.limit] },
    { id: "itrm-governance", label: "Évaluer une règle de gouvernance", method: "POST", path: "/v1/itrm/governance/evaluate", body: [
      { name: "object_kind", label: "Catégorie d’objet", required: true, type: "select", options: RESOURCE_CATEGORY_OPTIONS },
      { name: "incoming_source", label: "Source entrante", required: true, type: "select", options: SOURCE_OPTIONS },
      { name: "existing_serial", label: "Serial existant", target: "existing_attributes.serial" },
      { name: "incoming_serial", label: "Serial entrant", target: "incoming_attributes.serial" },
      { name: "existing_site", label: "Site existant", target: "existing_attributes.site" },
      { name: "incoming_site", label: "Site entrant", target: "incoming_attributes.site" }
    ] },
    { id: "itrm-reconcile", label: "Réconcilier une ressource", method: "POST", path: "/v1/itrm/reconcile-object", body: [
      FIELD_SETS.actor,
      FIELD_SETS.riKey,
      FIELD_SETS.source,
      { ...FIELD_SETS.resourceCategory, required: false },
      { ...FIELD_SETS.resourceType, required: false },
      { name: "display_name", label: "Nom affiché cible", placeholder: "srv-db-01 réconcilié" },
      FIELD_SETS.serial,
      FIELD_SETS.vendor,
      FIELD_SETS.model,
      FIELD_SETS.site,
      FIELD_SETS.rack,
      FIELD_SETS.tags,
      { name: "apply", label: "Appliquer le plan", type: "boolean" }
    ] }
  ] },
  { id: "ipam", label: "IPAM", icon: "grid", description: "IPv4/IPv6, VRF, préfixes, plages, VLAN/VXLAN, ASN/BGP, DNS/DHCP, DDI, conflits, capacité et allocations.", operations: [
    { id: "ipam-dashboard", label: "Dashboard IPAM", method: "GET", path: "/v1/ipam/ui-dashboard", query: [{ name: "vrf", label: "VRF", placeholder: "global" }] },
    { id: "ipam-search", label: "Rechercher dans l’IPAM", method: "GET", path: "/v1/ipam/ui-search", query: [{ name: "query", label: "Recherche", required: true, placeholder: "10.20.0.0/24 ou srv-db" }, { name: "vrf", label: "VRF", placeholder: "global" }] },
    { id: "ipam-define-vrf", label: "Définir une VRF", method: "POST", path: "/v1/ipam/vrfs", body: [FIELD_SETS.actor, { name: "name", label: "Nom VRF", required: true, placeholder: "global" }, { name: "route_distinguisher", label: "Route distinguisher", placeholder: "65000:100" }] },
    { id: "ipam-define-aggregate", label: "Définir un agrégat IP", method: "POST", path: "/v1/ipam/aggregates", body: [FIELD_SETS.actor, { name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "cidr", label: "CIDR agrégat", required: true, placeholder: "10.20.0.0/16" }, { name: "description", label: "Description", placeholder: "Bloc site PAR1" }] },
    { id: "ipam-define-prefix", label: "Définir un préfixe IP", method: "POST", path: "/v1/ipam/prefixes", body: [FIELD_SETS.actor, { name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "cidr", label: "CIDR préfixe", required: true, placeholder: "10.20.30.0/24" }, { name: "description", label: "Description", placeholder: "Réseau serveurs" }] },
    { id: "ipam-list-prefixes", label: "Lister les préfixes", method: "GET", path: "/v1/ipam/prefixes", query: [{ name: "vrf", label: "VRF", required: true, placeholder: "global" }] },
    { id: "ipam-define-range", label: "Définir une plage IP", method: "POST", path: "/v1/ipam/ranges", body: [FIELD_SETS.actor, { name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "prefix", label: "Préfixe", required: true, placeholder: "10.20.30.0/24" }, { name: "start", label: "Début plage", required: true, placeholder: "10.20.30.10" }, { name: "end", label: "Fin plage", required: true, placeholder: "10.20.30.200" }, { name: "purpose", label: "Usage plage", type: "select", options: [{ value: "allocation", label: "Allocation" }, { value: "reservation", label: "Réservation" }, { value: "exclusion", label: "Exclusion" }], defaultValue: "allocation" }, { name: "description", label: "Description", placeholder: "Pool applicatif" }] },
    { id: "ipam-register-address", label: "Enregistrer une adresse IP", method: "POST", path: "/v1/ipam/addresses", body: [FIELD_SETS.actor, { name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "prefix", label: "Préfixe", required: true, placeholder: "10.20.30.0/24" }, { name: "address", label: "Adresse IP", required: true, placeholder: "10.20.30.21" }, { name: "hostname", label: "Nom DNS / équipement", required: true, placeholder: "srv-app-01" }, { name: "interface_name", label: "Interface", placeholder: "eth0" }, { name: "status", label: "Statut adresse", type: "select", options: [{ value: "planned", label: "Planifiée" }, { value: "reserved", label: "Réservée" }, { value: "active", label: "Active" }, { value: "deprecated", label: "Dépréciée" }], defaultValue: "reserved" }] },
    { id: "ipam-allocate", label: "Allouer une adresse IP", method: "POST", path: "/v1/ipam/allocate", body: [FIELD_SETS.actor, { name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "prefix", label: "Préfixe", required: true, placeholder: "10.20.30.0/24" }, { name: "hostname", label: "Nom DNS / équipement", required: true, placeholder: "srv-app-01" }, { name: "idempotency_key", label: "Clé d’idempotence", required: true, placeholder: "ipam-alloc-srv-app-01" }] },
    { id: "ipam-reservation-wizard", label: "Assistant de réservation IP", method: "POST", path: "/v1/ipam/reservation-wizard", body: [FIELD_SETS.actor, { name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "prefix", label: "Préfixe", required: true, placeholder: "10.20.30.0/24" }, { name: "hostname", label: "Nom DNS / équipement", required: true, placeholder: "srv-app-02" }, { name: "idempotency_key", label: "Clé d’idempotence", required: true, placeholder: "ipam-wizard-srv-app-02" }, { name: "apply", label: "Appliquer la réservation", type: "boolean" }] },
    { id: "ipam-capacity", label: "Calculer la capacité d’un préfixe", method: "GET", path: "/v1/ipam/capacity", query: [{ name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "prefix", label: "Préfixe", required: true, placeholder: "10.20.30.0/24" }] },
    { id: "ipam-network-bindings", label: "Afficher les bindings réseau", method: "GET", path: "/v1/ipam/network-bindings", query: [{ name: "vrf", label: "VRF", placeholder: "global" }] },
    { id: "ipam-topology", label: "Topologie opérationnelle IPAM", method: "GET", path: "/v1/ipam/topology", query: [{ name: "vrf", label: "VRF", placeholder: "global" }] },
    { id: "ipam-define-vlan-group", label: "Définir un groupe VLAN", method: "POST", path: "/v1/ipam/vlan-groups", body: [FIELD_SETS.actor, { name: "name", label: "Groupe VLAN", required: true, placeholder: "dc-par1" }, { name: "scope", label: "Scope VLAN", placeholder: "site/PAR1" }, { name: "description", label: "Description", placeholder: "VLAN datacenter PAR1" }] },
    { id: "ipam-define-vxlan-vni", label: "Définir un VXLAN VNI", method: "POST", path: "/v1/ipam/vxlan-vnis", body: [FIELD_SETS.actor, { name: "vni", label: "VNI", type: "number", required: true, placeholder: "10010" }, { name: "name", label: "Nom VNI", required: true, placeholder: "prod-app" }, { name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "route_targets_import", label: "RT import", type: "csv", placeholder: "65000:10010" }, { name: "route_targets_export", label: "RT export", type: "csv", placeholder: "65000:10010" }, { name: "description", label: "Description", placeholder: "Segment applicatif" }] },
    { id: "ipam-define-vlan", label: "Définir un VLAN", method: "POST", path: "/v1/ipam/vlans", body: [FIELD_SETS.actor, { name: "group", label: "Groupe VLAN", required: true, placeholder: "dc-par1" }, { name: "vlan_id", label: "VLAN ID", type: "number", required: true, placeholder: "210" }, { name: "name", label: "Nom VLAN", required: true, placeholder: "prod-app" }, { name: "vrf", label: "VRF", placeholder: "global" }, { name: "vni", label: "VNI", type: "number", placeholder: "10010" }, { name: "description", label: "Description", placeholder: "Réseau applicatif" }] },
    { id: "ipam-define-asn", label: "Définir un ASN", method: "POST", path: "/v1/ipam/asns", body: [FIELD_SETS.actor, { name: "asn", label: "ASN", type: "number", required: true, placeholder: "65000" }, { name: "name", label: "Nom AS", required: true, placeholder: "OpenInfra Core" }, { name: "description", label: "Description", placeholder: "Autonomous system interne" }] },
    { id: "ipam-define-bgp-peer", label: "Définir un peer BGP", method: "POST", path: "/v1/ipam/bgp-peers", body: [FIELD_SETS.actor, { name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "local_asn", label: "ASN local", type: "number", required: true, placeholder: "65000" }, { name: "remote_asn", label: "ASN distant", type: "number", required: true, placeholder: "65010" }, { name: "peer_address", label: "Adresse peer", required: true, placeholder: "192.0.2.2" }, { name: "address_family", label: "Famille d’adresses", type: "select", options: [{ value: "ipv4", label: "IPv4" }, { value: "ipv6", label: "IPv6" }] }, { name: "route_targets_import", label: "RT import", type: "csv", placeholder: "65000:10010" }, { name: "route_targets_export", label: "RT export", type: "csv", placeholder: "65000:10010" }, { name: "description", label: "Description", placeholder: "Peer datacenter" }] },
    { id: "ipam-observe-dns", label: "Observer un enregistrement DNS", method: "POST", path: "/v1/ipam/dns-observations", body: [FIELD_SETS.actor, { name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "hostname", label: "Nom DNS", required: true, placeholder: "srv-app-01.example.net" }, { name: "address", label: "Adresse IP", required: true, placeholder: "10.20.30.21" }, { name: "ptr_hostname", label: "Nom PTR", placeholder: "srv-app-01.example.net" }, { name: "source", label: "Source observation", placeholder: "bind" }] },
    { id: "ipam-observe-dhcp", label: "Observer un bail DHCP", method: "POST", path: "/v1/ipam/dhcp-leases", body: [FIELD_SETS.actor, { name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "prefix", label: "Préfixe", required: true, placeholder: "10.20.30.0/24" }, { name: "address", label: "Adresse IP", required: true, placeholder: "10.20.30.44" }, { name: "mac_address", label: "Adresse MAC", required: true, placeholder: "00:11:22:33:44:55" }, { name: "hostname", label: "Nom DHCP", required: true, placeholder: "srv-dhcp-01" }, { name: "source", label: "Source observation", placeholder: "kea" }, { name: "active", label: "Bail actif", type: "boolean", defaultValue: "true" }] },
    { id: "ipam-conflicts", label: "Détecter les conflits", method: "GET", path: "/v1/ipam/conflicts", query: [{ name: "vrf", label: "VRF", placeholder: "global" }] },
    { id: "ipam-ddi-preview", label: "Prévisualiser DDI", method: "POST", path: "/v1/ipam/ddi-preview", body: [FIELD_SETS.actor, { name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "idempotency_key", label: "Clé d’idempotence", required: true, placeholder: "ipam-alloc-srv-app-01" }, { name: "providers", label: "Fournisseurs DDI", type: "csv", placeholder: "bind,kea" }, { name: "dns_zone", label: "Zone DNS", placeholder: "example.net" }, { name: "mac_address", label: "Adresse MAC", placeholder: "00:11:22:33:44:55" }, { name: "ttl", label: "TTL", type: "number", placeholder: "300" }, { name: "apply_preview", label: "Appliquer la prévisualisation", type: "boolean" }] }
  ] },
  { id: "dcim", label: "DCIM", icon: "home", description: "Sites, salles, zones, racks, ports, câbles, énergie et localisation terrain.", operations: [
    { id: "dcim-locate-equipment", label: "Localiser un équipement", method: "POST", path: "/v1/dcim/locations", body: [
      FIELD_SETS.actor,
      { name: "asset_tag", label: "Numéro d’actif", required: true, placeholder: "PAR-SRV-001" },
      { name: "equipment_name", label: "Nom équipement", required: true, placeholder: "srv-app-01" },
      { name: "site", label: "Site", required: true, placeholder: "PAR1" },
      { name: "building", label: "Bâtiment", required: true, placeholder: "BAT-A" },
      { name: "floor", label: "Étage", placeholder: "F01" },
      { name: "room", label: "Salle", required: true, placeholder: "MMR1" },
      { name: "zone", label: "Zone", placeholder: "Z1" },
      { name: "row", label: "Ligne salle", required: true, placeholder: "A" },
      { name: "column", label: "Colonne salle", required: true, placeholder: "01" },
      { name: "rack", label: "Rack", placeholder: "R01" },
      { name: "u_position", label: "Position U", type: "number", placeholder: "12" },
      { name: "rack_face", label: "Face rack", type: "select", options: ["front", "rear"] },
      { name: "u_height", label: "Hauteur U", type: "number", placeholder: "2" },
      { name: "x", label: "Coordonnée X", type: "number", placeholder: "1.25" },
      { name: "y", label: "Coordonnée Y", type: "number", placeholder: "2.50" },
      { name: "z", label: "Coordonnée Z", type: "number", placeholder: "0.00" }
    ] },
    { id: "dcim-rack-capacity", label: "Capacité rack", method: "GET", path: "/v1/dcim/rack-capacity", query: [{ name: "site", label: "Site", required: true }, { name: "building", label: "Bâtiment", required: true }, { name: "room", label: "Salle", required: true }, { name: "rack", label: "Rack", required: true }] },
    { id: "dcim-room-plan", label: "Plan de salle", method: "GET", path: "/v1/dcim/room-plan", query: [{ name: "site", label: "Site", required: true }, { name: "building", label: "Bâtiment", required: true }, { name: "room", label: "Salle", required: true }, { name: "format", label: "Format rendu", type: "select", options: ["json", "svg", "html"], defaultValue: "json" }] },
    { id: "dcim-rack-elevation", label: "Élévation rack", method: "GET", path: "/v1/dcim/rack-elevation", query: [{ name: "site", label: "Site", required: true }, { name: "building", label: "Bâtiment", required: true }, { name: "room", label: "Salle", required: true }, { name: "rack", label: "Rack", required: true }, { name: "face", label: "Face rack", type: "select", options: ["front", "rear"], defaultValue: "front" }, { name: "format", label: "Format rendu", type: "select", options: ["json", "svg", "html"], defaultValue: "json" }] },
    { id: "dcim-patch-panel", label: "Définir un panneau de brassage", method: "POST", path: "/v1/dcim/patch-panels", body: [FIELD_SETS.actor, { name: "site", label: "Site", required: true, placeholder: "PAR1" }, { name: "building", label: "Bâtiment", required: true, placeholder: "BAT-A" }, { name: "room", label: "Salle", required: true, placeholder: "MMR1" }, { name: "rack", label: "Rack", required: true, placeholder: "R01" }, { name: "patch_panel", label: "Panneau de brassage", required: true, placeholder: "PP01" }, { name: "rack_face", label: "Face rack", type: "select", options: ["front", "rear"], defaultValue: "front" }, { name: "u_position", label: "Position U", type: "number", required: true, placeholder: "1" }, { name: "u_height", label: "Hauteur U", type: "number", placeholder: "1" }, { name: "port_count", label: "Nombre de ports", type: "number", required: true, placeholder: "24" }, { name: "connector", label: "Connecteur", type: "select", options: ["rj45", "lc", "sc", "mpo", "sfp", "qsfp"], defaultValue: "rj45" }, { name: "medium", label: "Média câble", type: "select", options: ["copper", "fiber", "dac"], defaultValue: "copper" }, { name: "label", label: "Libellé", placeholder: "Panneau cuivre ToR" }, { name: "port_prefix", label: "Préfixe ports", placeholder: "P" }] },
    { id: "dcim-port", label: "Définir un port DCIM", method: "POST", path: "/v1/dcim/ports", body: [FIELD_SETS.actor, { name: "owner_type", label: "Type propriétaire", type: "select", options: ["equipment", "patch_panel"], defaultValue: "equipment" }, { name: "owner_code", label: "Code propriétaire", required: true, placeholder: "SRV-001" }, { name: "port_name", label: "Nom port", required: true, placeholder: "ETH0" }, { name: "connector", label: "Connecteur", type: "select", options: ["rj45", "lc", "sc", "mpo", "sfp", "qsfp"], defaultValue: "rj45" }, { name: "medium", label: "Média câble", type: "select", options: ["copper", "fiber", "dac"], defaultValue: "copper" }, { name: "site", label: "Site", placeholder: "PAR1" }, { name: "building", label: "Bâtiment", placeholder: "BAT-A" }, { name: "room", label: "Salle", placeholder: "MMR1" }, { name: "enabled", label: "Port actif", type: "boolean", placeholder: "true" }] },
    { id: "dcim-cable", label: "Connecter un câble", method: "POST", path: "/v1/dcim/cables", body: [FIELD_SETS.actor, { name: "cable_id", label: "Identifiant câble", required: true, placeholder: "CAB-000123" }, { name: "a_owner_type", label: "Type propriétaire A", type: "select", options: ["equipment", "patch_panel"], defaultValue: "equipment" }, { name: "a_owner_code", label: "Code propriétaire A", required: true, placeholder: "SRV-001" }, { name: "a_port_name", label: "Port A", required: true, placeholder: "ETH0" }, { name: "b_owner_type", label: "Type propriétaire B", type: "select", options: ["equipment", "patch_panel"], defaultValue: "patch_panel" }, { name: "b_owner_code", label: "Code propriétaire B", required: true, placeholder: "PP01" }, { name: "b_port_name", label: "Port B", required: true, placeholder: "P01" }, { name: "medium", label: "Média câble", type: "select", options: ["copper", "fiber", "dac"], defaultValue: "copper" }, { name: "status", label: "Statut câble", type: "select", options: ["planned", "installed", "retired"], defaultValue: "installed" }, { name: "path_segments", label: "Chemin câble", type: "csv", required: true, placeholder: "Rack R01 manager, Panneau PP01" }, { name: "length_m", label: "Longueur m", type: "number", placeholder: "2.5" }, { name: "label", label: "Libellé", placeholder: "Uplink serveur" }] },
    { id: "dcim-cable-trace", label: "Tracer un câble", method: "GET", path: "/v1/dcim/cable-trace", query: [{ name: "cable_id", label: "Identifiant câble", required: true, placeholder: "CAB-000123" }] },
    { id: "dcim-power-device", label: "Définir un équipement électrique", method: "POST", path: "/v1/dcim/power-devices", body: [FIELD_SETS.actor, { name: "code", label: "Code équipement électrique", required: true, placeholder: "PDU-A-R01" }, { name: "kind", label: "Type équipement électrique", type: "select", options: ["pdu", "ups"], defaultValue: "pdu" }, { name: "site", label: "Site", required: true, placeholder: "PAR1" }, { name: "building", label: "Bâtiment", required: true, placeholder: "BAT-A" }, { name: "room", label: "Salle", required: true, placeholder: "MMR1" }, { name: "rack", label: "Rack", placeholder: "R01" }, { name: "side", label: "Chaîne électrique", type: "select", options: ["A", "B"] }, { name: "capacity_watts", label: "Capacité watts", type: "number", required: true, placeholder: "5000" }, { name: "derating_percent", label: "Derating %", type: "number", placeholder: "80" }, { name: "input_source", label: "Source amont", placeholder: "utility" }, { name: "output_voltage", label: "Tension sortie V", type: "number", placeholder: "230" }, { name: "label", label: "Libellé", placeholder: "PDU A baie R01" }] },
    { id: "dcim-power-circuit", label: "Définir un circuit électrique", method: "POST", path: "/v1/dcim/power-circuits", body: [FIELD_SETS.actor, { name: "circuit_id", label: "Identifiant circuit", required: true, placeholder: "CIR-A-R01" }, { name: "source_device", label: "Source électrique", required: true, placeholder: "PDU-A-R01" }, { name: "site", label: "Site", required: true, placeholder: "PAR1" }, { name: "building", label: "Bâtiment", required: true, placeholder: "BAT-A" }, { name: "room", label: "Salle", required: true, placeholder: "MMR1" }, { name: "rack", label: "Rack", required: true, placeholder: "R01" }, { name: "side", label: "Chaîne électrique", type: "select", options: ["A", "B"], defaultValue: "A" }, { name: "capacity_watts", label: "Capacité watts", type: "number", required: true, placeholder: "2000" }, { name: "breaker_rating_amps", label: "Calibre disjoncteur A", type: "number", required: true, placeholder: "16" }, { name: "redundancy_group", label: "Groupe redondance", placeholder: "default" }, { name: "label", label: "Libellé", placeholder: "Circuit A baie R01" }] },
    { id: "dcim-cooling-zone", label: "Définir une zone de refroidissement", method: "POST", path: "/v1/dcim/cooling-zones", body: [FIELD_SETS.actor, { name: "site", label: "Site", required: true, placeholder: "PAR1" }, { name: "building", label: "Bâtiment", required: true, placeholder: "BAT-A" }, { name: "room", label: "Salle", required: true, placeholder: "MMR1" }, { name: "zone", label: "Zone froid/chaud", required: true, placeholder: "Z1" }, { name: "role", label: "Rôle refroidissement", type: "select", options: ["cold_aisle", "hot_aisle", "neutral"], defaultValue: "cold_aisle" }, { name: "cooling_capacity_watts", label: "Capacité froid watts", type: "number", required: true, placeholder: "3000" }, { name: "supply_temperature_c", label: "Température soufflage °C", type: "number", required: true, placeholder: "18" }, { name: "return_temperature_c", label: "Température retour °C", type: "number", required: true, placeholder: "30" }, { name: "label", label: "Libellé", placeholder: "Allée froide A" }] },
    { id: "dcim-power-reservation", label: "Réserver la puissance équipement", method: "POST", path: "/v1/dcim/power-reservations", body: [FIELD_SETS.actor, { name: "asset_tag", label: "Numéro d’actif", required: true, placeholder: "PAR-SRV-001" }, { name: "circuit_id", label: "Identifiant circuit", required: true, placeholder: "CIR-A-R01" }, { name: "expected_watts", label: "Puissance attendue watts", type: "number", required: true, placeholder: "600" }, { name: "label", label: "Libellé", placeholder: "Réservation alimentation principale" }] },
    { id: "dcim-digital-twin", label: "Jumeau numérique salle", method: "GET", path: "/v1/dcim/digital-twin", query: [{ name: "site", label: "Site", required: true, placeholder: "PAR1" }, { name: "building", label: "Bâtiment", required: true, placeholder: "BAT-A" }, { name: "room", label: "Salle", required: true, placeholder: "MMR1" }] },
    { id: "dcim-energy-cooling-capacity", label: "Capacité énergie/refroidissement", method: "GET", path: "/v1/dcim/energy-cooling-capacity", query: [{ name: "site", label: "Site", required: true, placeholder: "PAR1" }, { name: "building", label: "Bâtiment", required: true, placeholder: "BAT-A" }, { name: "room", label: "Salle", required: true, placeholder: "MMR1" }, { name: "rack", label: "Rack", required: true, placeholder: "R01" }] }
  ] },
  { id: "itam", label: "IT Asset Management", shortLabel: "ITAM", icon: "asset", description: "Inventaire financier et opérationnel des actifs, garanties constructeur, supports tiers et couverture renouvellement.", operations: [
    { id: "itam-support-profile", label: "Profil support actif", method: "GET", path: "/v1/itam/support-profile", query: [{ name: "asset_tag", label: "Numéro d’actif", required: true, placeholder: "PAR-SRV-001" }] },
    { id: "itam-support-coverage", label: "Couverture support actif", method: "GET", path: "/v1/itam/support-coverage", query: [{ name: "asset_tag", label: "Numéro d’actif", required: true, placeholder: "PAR-SRV-001" }, { name: "as_of", label: "Date de référence", placeholder: "2026-07-07" }] },
    { id: "itam-register-manufacturer", label: "Déclarer garantie constructeur", method: "POST", path: "/v1/itam/support-profile/manufacturer", body: [FIELD_SETS.actor, { name: "asset_tag", label: "Numéro d’actif", required: true, placeholder: "PAR-SRV-001" }, { name: "manufacturer", label: "Constructeur", required: true, placeholder: "Dell" }, { name: "warranty_reference", label: "Référence garantie", required: true, placeholder: "WR-123" }, { name: "warranty_level", label: "Niveau garantie", required: true, placeholder: "ProSupport" }, { name: "warranty_start", label: "Début garantie", required: true, placeholder: "2026-01-01" }, { name: "warranty_end", label: "Fin garantie", required: true, placeholder: "2029-01-01" }, { name: "support_reference", label: "Référence support", required: true, placeholder: "SUP-123" }, { name: "support_level", label: "Niveau support", required: true, placeholder: "24x7" }, { name: "support_contact", label: "Contact support", required: true, placeholder: "support@example.com" }] },
    { id: "itam-add-third-party", label: "Ajouter support tiers", method: "POST", path: "/v1/itam/support-profile/third-party", body: [FIELD_SETS.actor, { name: "asset_tag", label: "Numéro d’actif", required: true, placeholder: "PAR-SRV-001" }, { name: "provider", label: "Prestataire", required: true, placeholder: "Mainteneur tiers" }, { name: "contract_reference", label: "Référence contrat", required: true, placeholder: "TP-123" }, { name: "support_level", label: "Niveau support", required: true, placeholder: "8x5" }, { name: "support_start", label: "Début support", required: true, placeholder: "2029-01-02" }, { name: "support_end", label: "Fin support", required: true, placeholder: "2030-01-01" }, { name: "support_contact", label: "Contact support", required: true, placeholder: "n2@example.com" }, { name: "status", label: "Statut", type: "select", options: ["planned", "active", "expired", "terminated"], defaultValue: "active" }, { name: "notes", label: "Notes", placeholder: "Périmètre support" }] },
    { id: "itam-software-license", label: "Licence logicielle", method: "GET", path: "/v1/itam/software-license", query: [{ name: "license_reference", label: "Référence licence", required: true, placeholder: "LIC-OPENINFRA-001" }] },
    { id: "itam-software-compliance", label: "Conformité licence", method: "GET", path: "/v1/itam/software-license/compliance", query: [{ name: "license_reference", label: "Référence licence", required: true, placeholder: "LIC-OPENINFRA-001" }, { name: "as_of", label: "Date de référence", placeholder: "2026-07-08" }] },
    { id: "itam-register-software", label: "Déclarer licence logicielle", method: "POST", path: "/v1/itam/software-license", body: [FIELD_SETS.actor, { name: "product_name", label: "Produit", required: true, placeholder: "PostgreSQL Enterprise Support" }, { name: "vendor", label: "Éditeur", required: true, placeholder: "Vendor SA" }, { name: "license_reference", label: "Référence licence", required: true, placeholder: "LIC-OPENINFRA-001" }, { name: "contract_reference", label: "Référence contrat", placeholder: "CTR-SW-001" }, { name: "metric", label: "Métrique", type: "select", required: true, options: ["device", "user", "core", "socket", "instance", "subscription"], defaultValue: "device" }, { name: "purchased_quantity", label: "Quantité achetée", required: true, placeholder: "100" }, { name: "assigned_quantity", label: "Quantité assignée", placeholder: "0" }, { name: "entitlement_start", label: "Début droit", required: true, placeholder: "2026-01-01" }, { name: "entitlement_end", label: "Fin droit", required: true, placeholder: "2027-01-01" }, { name: "version", label: "Version", placeholder: "2026" }, { name: "status", label: "Statut", type: "select", options: ["planned", "active", "expired", "terminated"], defaultValue: "active" }, { name: "owner", label: "Propriétaire", placeholder: "DSI" }, { name: "notes", label: "Notes", placeholder: "Périmètre licence" }] },
    { id: "itam-update-license-assignment", label: "Mettre à jour affectation licence", method: "POST", path: "/v1/itam/software-license/assignment", body: [FIELD_SETS.actor, { name: "license_reference", label: "Référence licence", required: true, placeholder: "LIC-OPENINFRA-001" }, { name: "assigned_quantity", label: "Quantité assignée", required: true, placeholder: "75" }, { name: "notes", label: "Notes", placeholder: "Ajustement inventaire" }] }
  ] },
  { id: "discovery", label: "Discovery", icon: "activity", description: "Collecte backend locale en Lite/Pro ; agents proxy collectors Enterprise uniquement en topologie étoile.", operations: [
    { id: "collectors-list", label: "Lister les agents proxy Enterprise", method: "GET", path: "/v1/discovery/collectors", query: [{ name: "scope", label: "Scope autorisé" }, FIELD_SETS.limit] },
    { id: "collectors-register", label: "Enregistrer un agent proxy Enterprise", method: "POST", path: "/v1/discovery/collectors", body: [FIELD_SETS.actor, { name: "name", label: "Nom agent proxy", required: true }, { name: "kind", label: "Type", required: true, type: "select", options: ["site-proxy", "network-proxy", "datacenter-proxy"] }, { name: "certificate_fingerprint", label: "Empreinte certificat", required: true }, { name: "scopes", label: "Scopes autorisés", type: "csv", required: true, placeholder: "site/paris,network/core" }, { name: "version", label: "Version agent", required: true, defaultValue: "1.0.0" }, { name: "endpoint_url", label: "Endpoint mTLS", required: true, placeholder: "https://collector-paris.openinfra.local" }] },
    { id: "job-authorize", label: "Autoriser un job collector", method: "POST", path: "/v1/discovery/jobs/authorize", body: [{ name: "collector_id", label: "ID agent proxy", required: true }, { name: "certificate_fingerprint", label: "Empreinte certificat", required: true }, { name: "requested_scope", label: "Scope demandé", required: true }, { name: "job_type", label: "Type de job", required: true, type: "select", options: ["snmp", "ssh", "winrm", "vmware", "kubernetes"] }, { name: "target", label: "Cible", required: true, placeholder: "10.20.30.10" }] }
  ] },
  { id: "data", label: "Imports / Exports", shortLabel: "Data", icon: "table", description: "Imports massifs reprenables, exports asynchrones signés et lecture streaming par chunks.", operations: [
    { id: "import-bulk-progress", label: "Progression import massif", method: "GET", path: "/v1/imports/bulk-progress", query: [FIELD_SETS.jobId] },
    { id: "export-artifact-chunk", label: "Chunk export signé", method: "GET", path: "/v1/exports/artifact-chunk", query: [FIELD_SETS.exportJobId, FIELD_SETS.chunkOffset, FIELD_SETS.chunkSize] }
  ] },
  { id: "security", label: "Sécurité / RBAC / Audit", shortLabel: "Sécurité", icon: "shield", description: "Identité, RBAC, tokens, politiques d’accès, audit, éditions et quotas runtime.", operations: [
    { id: "edition-policies", label: "Politiques éditions et quotas", method: "GET", path: "/v1/editions/policies", query: [] },
    { id: "edition-feature-check", label: "Vérifier une capacité édition", method: "GET", path: "/v1/editions/feature-check", query: [FIELD_SETS.edition, FIELD_SETS.featureCapability] },
    { id: "edition-quota-check", label: "Vérifier un quota édition", method: "GET", path: "/v1/editions/quota-check", query: [FIELD_SETS.edition, FIELD_SETS.quotaResource, FIELD_SETS.requestedIncrement] },
    { id: "tokens-list", label: "Lister les tokens techniques", method: "GET", path: "/v1/security/tokens", query: [FIELD_SETS.limit, { name: "include_inactive", label: "Inclure inactifs", type: "boolean" }] },
    { id: "effective-identity", label: "Identité effective", method: "GET", path: "/v1/identity/effective", query: [{ name: "subject", label: "Sujet", placeholder: "user@example.com" }] },
    { id: "access-rules", label: "Politiques d’accès", method: "GET", path: "/v1/access/rules", query: [FIELD_SETS.limit, { name: "include_inactive", label: "Inclure inactives", type: "boolean" }] },
    { id: "audit-events", label: "Événements d’audit", method: "GET", path: "/v1/audit/events", query: [{ name: "action", label: "Action" }, { name: "target_type", label: "Type cible" }, FIELD_SETS.limit] },
    { id: "audit-integrity", label: "Intégrité audit", method: "GET", path: "/v1/audit/integrity", query: [FIELD_SETS.limit] }
  ] }
];

class OpenInfraDashboard {
  constructor(root) {
    this.root = root;
    this.state = {
      activeModuleId: "overview",
      selected: OPENINFRA_MODULES[0].operations[0],
      openedModules: new Set(["itrm"]),
      tenant: "default",
      config: null,
      ready: null,
      status: null,
      version: null,
      result: null,
      error: null,
      globalSearchQuery: "",
      globalSearchBackend: null,
      globalSearchLoading: false,
      globalSearchError: null
    };
    this.handleResize = () => this.syncFixedHeaderOffset();
  }

  async start() {
    window.addEventListener("resize", this.handleResize);
    await this.refreshRuntime();
    this.render();
  }

  async refreshRuntime() {
    try {
      const configResponse = await fetch("/config.json", { credentials: "same-origin", headers: { Accept: "application/json" } });
      if (!configResponse.ok) {
        throw new Error(`Configuration unavailable: ${configResponse.status}`);
      }
      const config = await configResponse.json();
      const [version, ready, status] = await Promise.all([
        fetch("/version", { credentials: "same-origin", headers: { Accept: "application/json" } }).then((response) => response.ok ? response.json() : { version: config.version }),
        fetch("/ready", { credentials: "same-origin", headers: { Accept: "application/json" } }).then((response) => response.ok ? response.json() : { ready: false }),
        fetch("/status", { credentials: "same-origin", headers: { Accept: "application/json" } }).then((response) => response.ok ? response.json() : { protectedForms: "unknown", trust: {} })
      ]);
      this.state = { ...this.state, config, version, ready, status, error: null };
    } catch (error) {
      this.state = { ...this.state, error };
    }
  }

  client() {
    return new OpenInfraApiClient(this.state.config?.apiBaseUrl || "/api", () => this.state.tenant);
  }

  globalSearchUrl(query, limit = 6) {
    const base = String(this.state.config?.apiBaseUrl || "/api").replace(/\/$/, "");
    const params = new URLSearchParams({
      tenant_id: this.state.tenant || "default",
      query,
      limit: String(limit)
    });
    return `${base}/v1/search/global?${params.toString()}`;
  }

  buildApiDocumentationUrl(route) {
    const normalizedRoute = String(route || "/docs").startsWith("/") ? String(route || "/docs") : `/${route}`;
    const value = String(this.state.config?.apiBaseUrl || "/api").trim();
    if (/^https?:\/\//i.test(value)) {
      const url = new URL(value);
      return `${url.origin}${normalizedRoute}`;
    }
    return normalizedRoute;
  }

  apiDocumentationLinks() {
    const published = this.state.config?.apiDocumentation || {};
    return {
      swaggerUrl: published.swaggerUrl || this.buildApiDocumentationUrl("/docs"),
      redocUrl: published.redocUrl || this.buildApiDocumentationUrl("/redoc"),
      openapiUrl: published.openapiUrl || this.buildApiDocumentationUrl("/openapi.yaml")
    };
  }


  syncFixedHeaderOffset() {
    const header = document.querySelector(".openinfra-header-stack");
    if (!header || typeof header.getBoundingClientRect !== "function") {
      return;
    }
    const height = Math.ceil(header.getBoundingClientRect().height);
    if (height > 0) {
      document.documentElement.style.setProperty("--openinfra-fixed-header-height", `${height}px`);
    }
  }

  visibleOperations(module) {
    return module.operations;
  }

  componentModules() {
    return OPENINFRA_MODULES.filter((module) => module.id !== "overview");
  }

  moduleStatistics(module) {
    const operations = module.operations.length;
    const readOperations = module.operations.filter((operation) => operation.method === "GET").length;
    const writeOperations = operations - readOperations;
    const fields = module.operations.reduce((total, operation) => total + (operation.query || []).length + (operation.body || []).length, 0);
    const requiredFields = module.operations.reduce((total, operation) => {
      return total + [...(operation.query || []), ...(operation.body || [])].filter((field) => field.required).length;
    }, 0);
    const readPercent = operations === 0 ? 0 : Math.round((readOperations / operations) * 100);
    return {
      operations,
      readOperations,
      writeOperations,
      fields,
      requiredFields,
      readPercent,
      writePercent: 100 - readPercent
    };
  }

  normalizeSearchText(value) {
    return String(value || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }

  operationSearchHaystack(module, operation) {
    const fields = [...(operation.query || []), ...(operation.body || [])];
    return [
      module.label,
      module.shortLabel,
      module.description,
      operation.id,
      operation.label,
      operation.method,
      operation.path,
      ...fields.flatMap((field) => [field.name, field.label, field.placeholder, field.target])
    ].filter(Boolean).join(" ");
  }

  globalSearchGroups() {
    const query = this.normalizeSearchText(this.state.globalSearchQuery.trim());
    if (!query) {
      return [];
    }
    return this.componentModules().map((module) => {
      const matches = module.operations.filter((operation) => {
        return this.normalizeSearchText(this.operationSearchHaystack(module, operation)).includes(query);
      });
      return { module, operations: matches.slice(0, 8), total: matches.length };
    }).filter((group) => group.total > 0);
  }

  renderGlobalSearchToolbar() {
    const query = this.state.globalSearchQuery;
    const hasQuery = query.trim() !== "";
    const docs = this.apiDocumentationLinks();
    return `<div class="px-3 py-2 border-bottom openinfra-global-toolbar">
      <div class="container-fluid openinfra-global-toolbar-inner">
        <div class="openinfra-global-toolbar-spacer" aria-hidden="true"></div>
        <form class="openinfra-global-search-form" role="search" aria-label="Recherche globale OpenInfra" autocomplete="off">
          <label class="visually-hidden" for="openinfra-global-search">Recherche globale OpenInfra</label>
          <div class="openinfra-global-search-control">
            ${this.icon("search", "openinfra-global-search-icon", 18, 18)}
            <input type="search" id="openinfra-global-search" class="form-control" placeholder="Recherche globale..." aria-label="Recherche globale OpenInfra" role="combobox" aria-autocomplete="list" aria-haspopup="listbox" aria-controls="openinfra-global-search-results" aria-expanded="${hasQuery ? "true" : "false"}" value="${this.escape(query)}">
          </div>
          <div id="openinfra-global-search-results" class="openinfra-global-search-results" role="listbox" aria-label="Résultats de recherche globale" aria-live="polite" ${hasQuery ? "" : "hidden"}>${this.renderGlobalSearchResults()}</div>
        </form>
        <div class="text-end openinfra-api-doc-actions">
          <a class="btn btn-light text-dark me-2" href="${this.escape(docs.swaggerUrl)}" target="_blank" rel="noopener noreferrer" aria-label="Ouvrir Swagger UI backend API">Swagger</a>
          <a class="btn btn-primary" href="${this.escape(docs.redocUrl)}" target="_blank" rel="noopener noreferrer" aria-label="Ouvrir ReDoc backend API">ReDoc</a>
        </div>
      </div>
    </div>`;
  }

  renderGlobalSearchResults() {
    const query = this.state.globalSearchQuery.trim();
    if (!query) {
      return "";
    }
    const groups = this.globalSearchGroups();
    const backend = this.state.globalSearchBackend;
    if (this.state.globalSearchLoading) {
      return `<div class="openinfra-global-search-empty">Recherche backend en cours pour <strong>${this.escape(query)}</strong>…</div>`;
    }
    if (backend && backend.query === query) {
      return this.renderBackendGlobalSearchResults(backend, query, groups);
    }
    if (this.state.globalSearchError) {
      return `<div class="openinfra-global-search-empty">Recherche backend temporairement indisponible. Résultats locaux ci-dessous.</div>${this.renderOperationSearchResults(groups, query)}`;
    }
    return this.renderOperationSearchResults(groups, query);
  }

  renderBackendGlobalSearchResults(backend, query, operationGroups) {
    const groups = Array.isArray(backend.groups) ? backend.groups : [];
    const visibleGroups = groups.filter((group) => group.status === "ok" && Array.isArray(group.items) && group.items.length > 0);
    const skipped = groups.filter((group) => group.status === "skipped");
    const sections = visibleGroups.map((group) => `<section class="openinfra-global-search-group" role="group" aria-label="Résultats ${this.escape(group.label || group.component)}">
      <div class="openinfra-global-search-group-title"><span>${this.escape(group.label || group.component)}</span><span>${group.total} résultat${group.total > 1 ? "s" : ""}</span></div>
      ${group.items.map((item) => `<button type="button" class="openinfra-global-search-item" role="option" data-search-route="${this.escape(item.route || "")}">
        <span>${this.escape(item.label || item.kind || "résultat")}</span><small>${this.escape(item.kind || group.component)} · ${this.escape(item.description || "")}</small>
      </button>`).join("")}
      ${group.total > group.items.length ? `<div class="openinfra-global-search-more">${group.total - group.items.length} résultat${group.total - group.items.length > 1 ? "s" : ""} supplémentaire${group.total - group.items.length > 1 ? "s" : ""}</div>` : ""}
    </section>`);
    const skippedNotice = skipped.length > 0
      ? `<div class="openinfra-global-search-empty">Composants ignorés selon les droits : ${this.escape(skipped.map((group) => group.label || group.component).join(", "))}.</div>`
      : "";
    if (sections.length === 0) {
      return `<div class="openinfra-global-search-empty">Aucun résultat métier pour <strong>${this.escape(query)}</strong>.</div>${skippedNotice}${this.renderOperationSearchResults(operationGroups, query)}`;
    }
    return sections.join("") + skippedNotice;
  }

  renderOperationSearchResults(groups, query) {
    if (groups.length === 0) {
      return `<div class="openinfra-global-search-empty">Aucun résultat global pour <strong>${this.escape(query)}</strong>.</div>`;
    }
    return groups.map(({ module, operations, total }) => `<section class="openinfra-global-search-group" role="group" aria-label="Résultats ${this.escape(module.shortLabel || module.label)}">
      <div class="openinfra-global-search-group-title"><span>${this.escape(module.shortLabel || module.label)}</span><span>${total} résultat${total > 1 ? "s" : ""}</span></div>
      ${operations.map((operation) => `<button type="button" class="openinfra-global-search-item" role="option" data-search-operation-id="${this.escape(operation.id)}">
        <span>${this.escape(operation.label)}</span><small>${this.escape(operation.method)} ${this.escape(operation.path)}</small>
      </button>`).join("")}
      ${total > operations.length ? `<div class="openinfra-global-search-more">${total - operations.length} résultat${total - operations.length > 1 ? "s" : ""} supplémentaire${total - operations.length > 1 ? "s" : ""}</div>` : ""}
    </section>`).join("");
  }

  render() {
    const { activeModuleId, selected, config, ready, status, version, error, result } = this.state;
    const displayedVersion = version?.version || config?.version || "indisponible";
    const protectedForms = status?.protectedForms === "enabled" ? "actifs" : "à configurer";
    const activeModule = OPENINFRA_MODULES.find((module) => module.id === activeModuleId) || OPENINFRA_MODULES[0];
    const pageTitle = activeModuleId === "overview" ? "Dashboard" : activeModule.shortLabel || activeModule.label;
    const pageSubtitle = activeModuleId === "overview"
      ? "Vue de synthèse OpenInfra, readiness backend et état du portail server-side."
      : `${selected.label} — formulaire métier typé, sans champs génériques ni secrets côté navigateur.`;
    this.root.innerHTML = `
      <a class="openinfra-skip-link" href="#openinfra-main-content">Aller au contenu principal</a>
      <header class="openinfra-header-stack">
        <div class="px-3 py-2 bg-dark text-white openinfra-top-header">
          <div class="container-fluid">
            <div class="d-flex flex-wrap align-items-center justify-content-center justify-content-lg-start">
              <a href="/" class="d-flex align-items-center my-2 my-lg-0 me-lg-auto text-white text-decoration-none" aria-label="OpenInfra accueil">
                <span class="openinfra-brand-mark me-2">OI</span><span class="fs-5 fw-semibold">OpenInfra</span><span class="badge openinfra-edition-badge ms-3">${this.escape(config?.edition || "runtime")}</span>
              </a>
              <ul class="nav col-12 col-lg-auto my-2 justify-content-center my-md-0 text-small">
                ${OPENINFRA_MODULES.map((module) => `
                  <li><button type="button" class="nav-link border-0 bg-transparent ${activeModuleId === module.id ? "text-secondary" : "text-white"}" data-module-id="${this.escape(module.id)}" aria-current="${activeModuleId === module.id ? "page" : "false"}">
                    ${this.icon(module.icon, "bi d-block mx-auto mb-1 openinfra-top-icon", 24, 24)}${this.escape(module.shortLabel || module.label)}
                  </button></li>
                `).join("")}
              </ul>
            </div>
          </div>
        </div>
        ${this.renderGlobalSearchToolbar()}
      </header>
      <div class="container-fluid">
        <div class="row">
          <nav class="col-lg-3 col-xl-2 openinfra-sidebar" aria-label="Sidebar navigation">
            <div class="openinfra-sidebar-heading">Pilotage</div>
            ${this.renderSidebar()}
            <div class="openinfra-sidebar-heading">État runtime</div>
            <div class="px-2 small text-muted">
              <p><span class="openinfra-status-dot ${ready?.ready === true ? "ready" : "warning"}"></span>Backend ${ready?.ready === true ? "prêt" : "à vérifier"}</p>
              <p>Version : <strong>${this.escape(displayedVersion)}</strong></p>
              <p>Trust web/backend : <strong>${this.escape(config?.webBackendTrust || "server-side")}</strong></p>
              <p>Formulaires protégés : <strong>${this.escape(protectedForms)}</strong></p>
            </div>
          </nav>
          <main id="openinfra-main-content" class="col-lg-9 col-xl-10 ms-sm-auto openinfra-main" tabindex="-1">
            <div class="pb-2 mb-3 openinfra-titlebar">
              <h1 class="h2">${this.escape(pageTitle)}</h1><p class="text-muted mb-0">${this.escape(pageSubtitle)}</p>
            </div>
            ${error ? `<div class="alert alert-warning" role="alert">${this.escape(error.message)}</div>` : ""}
            ${result && activeModuleId !== "overview" ? `<div class="alert alert-success" role="status">Soumission exécutée avec succès.</div>` : ""}
            ${this.renderWorkspace(selected, result, displayedVersion, config, protectedForms)}
          </main>
        </div>
      </div>
    `;
    this.syncFixedHeaderOffset();
    this.bindEvents();
    this.focusMainContentIfRequested();
  }

  focusMainContentIfRequested() {
    if (!this.pendingMainFocus) {
      return;
    }
    this.pendingMainFocus = false;
    document.getElementById("openinfra-main-content")?.focus({ preventScroll: false });
  }

  renderWorkspace(selected, result, displayedVersion, config, protectedForms) {
    if (this.state.activeModuleId === "overview") {
      return `${this.renderOverviewRuntimeMetrics(displayedVersion, config, protectedForms)}${this.renderOverviewDashboard()}`;
    }
    return `<section class="card openinfra-operation-card"><div class="card-body">${this.renderOperationPanel(selected, result)}</div></section>`;
  }

  renderOverviewRuntimeMetrics(displayedVersion, config, protectedForms) {
    const operationsCount = OPENINFRA_MODULES.reduce((total, module) => total + module.operations.length, 0);
    return `<div class="row g-3 mb-4 openinfra-dashboard-metrics" aria-label="Métriques du dashboard">
      ${this.metric("Version", this.escape(displayedVersion))}
      ${this.metric("API", this.escape(config?.apiBaseUrl || "/api"))}
      ${this.metric("Trust", this.escape(config?.webBackendTrust || "server-side"))}
      ${this.metric("Formulaires", this.escape(protectedForms))}
      ${this.metric("Modules", `${operationsCount} opérations`)}
    </div>`;
  }

  renderOverviewDashboard() {
    const components = this.componentModules();
    const totalOperations = components.reduce((total, module) => total + module.operations.length, 0);
    const totalFields = components.reduce((total, module) => total + this.moduleStatistics(module).fields, 0);
    const totalRequiredFields = components.reduce((total, module) => total + this.moduleStatistics(module).requiredFields, 0);
    return `<section class="openinfra-overview" aria-label="Statistiques des composants OpenInfra">
      <div class="card openinfra-overview-summary mb-4">
        <div class="card-body">
          <div class="d-flex flex-wrap justify-content-between align-items-start gap-3">
            <div>
              <h2 class="h4 mb-1">Accueil — statistiques des composants</h2>
              <p class="text-muted mb-0">Vue de synthèse par composant : métriques fonctionnelles, champs métier exposés et camemberts de répartition lecture/mutation.</p>
            </div>
            <div class="text-end">
              <span class="badge text-bg-primary">${components.length} composants</span>
              <span class="badge text-bg-secondary ms-2">${totalOperations} opérations</span>
            </div>
          </div>
          <div class="row g-3 mt-3">
            ${this.metric("Champs métier", String(totalFields))}
            ${this.metric("Champs obligatoires", String(totalRequiredFields))}
            ${this.metric("Navigation", "Accordéons") }
            ${this.metric("Secrets navigateur", "0 exposé")}
          </div>
        </div>
      </div>
      <div class="row g-3">
        ${components.map((module) => this.renderComponentStatsCard(module)).join("")}
      </div>
    </section>`;
  }

  renderComponentStatsCard(module) {
    const stats = this.moduleStatistics(module);
    const readEnd = `${stats.readPercent}%`;
    const writeEnd = `${stats.readPercent + stats.writePercent}%`;
    return `<article class="col-md-6 col-xxl-4">
      <div class="card h-100 openinfra-component-card">
        <div class="card-body">
          <div class="d-flex justify-content-between align-items-start gap-3">
            <div>
              <h3 class="h5 mb-1">${this.escape(module.shortLabel || module.label)}</h3>
              <p class="text-muted small mb-0">${this.escape(module.description)}</p>
            </div>
            ${this.icon(module.icon, "openinfra-component-icon", 28, 28)}
          </div>
          <div class="openinfra-component-visual mt-3">
            <div class="openinfra-pie-chart" role="img" aria-label="Camembert ${this.escape(module.label)} : ${stats.readOperations} lectures et ${stats.writeOperations} mutations" style="--oi-read-end: ${readEnd}; --oi-write-end: ${writeEnd};">
              <span>${stats.operations}</span>
            </div>
            <div class="openinfra-pie-legend small">
              <span><i class="openinfra-legend-read"></i>${stats.readOperations} lectures</span>
              <span><i class="openinfra-legend-write"></i>${stats.writeOperations} mutations</span>
            </div>
          </div>
          <div class="row g-2 mt-3 openinfra-component-metrics">
            <div class="col-6"><strong>${stats.operations}</strong><span>Opérations</span></div>
            <div class="col-6"><strong>${stats.fields}</strong><span>Champs métier</span></div>
            <div class="col-6"><strong>${stats.requiredFields}</strong><span>Obligatoires</span></div>
            <div class="col-6"><strong>${stats.writeOperations}</strong><span>Mutations</span></div>
          </div>
        </div>
      </div>
    </article>`;
  }

  renderSidebar() {
    return OPENINFRA_MODULES.map((module) => {
      if (module.id === "overview") {
        return `<button type="button" class="nav-link openinfra-sidebar-dashboard w-100 text-start ${this.state.activeModuleId === module.id ? "active" : ""}" data-operation-id="${this.escape(module.operations[0].id)}" aria-current="${this.state.activeModuleId === module.id ? "page" : "false"}">${this.icon(module.icon)}Dashboard</button>`;
      }
      const opened = this.state.openedModules.has(module.id);
      const visibleOperations = this.visibleOperations(module);
      if (visibleOperations.length === 0 && !module.label.toLowerCase().includes(this.state.filter.toLowerCase())) {
        return "";
      }
      return `<section class="openinfra-accordion ${opened ? "open" : ""}">
        <button type="button" id="openinfra-accordion-${this.escape(module.id)}" class="openinfra-accordion-toggle ${this.state.activeModuleId === module.id ? "active" : ""}" data-accordion-id="${this.escape(module.id)}" aria-expanded="${opened ? "true" : "false"}" aria-controls="openinfra-panel-${this.escape(module.id)}" aria-current="${this.state.activeModuleId === module.id ? "page" : "false"}">
          <span>${this.icon(module.icon)}${this.escape(module.shortLabel || module.label)}</span><span class="openinfra-chevron">›</span>
        </button>
        <div id="openinfra-panel-${this.escape(module.id)}" class="openinfra-accordion-panel fade ${opened ? "show" : ""}" role="region" aria-labelledby="openinfra-accordion-${this.escape(module.id)}">
          ${visibleOperations.map((operation) => `<button type="button" class="openinfra-sidebar-operation ${this.state.selected.id === operation.id ? "active" : ""}" data-operation-id="${this.escape(operation.id)}" aria-current="${this.state.selected.id === operation.id ? "page" : "false"}">${this.escape(operation.label)}</button>`).join("")}
        </div>
      </section>`;
    }).join("");
  }

  renderOperationPanel(operation, result) {
    const module = this.moduleForOperation(operation);
    const fields = [...(operation.query || []), ...(operation.body || [])];
    return `<div class="row g-4">
      <section class="col-12 col-xxl-8">
        <h2 class="h4">${this.escape(operation.label)}</h2>
        <p class="text-muted">${this.escape(module.description)}</p>
        <div class="row g-3 mb-3"><label class="col-md-4 form-label">Tenant<input id="openinfra-tenant" class="form-control" value="${this.escape(this.state.tenant)}" autocomplete="off"></label></div>
        <div class="row g-3">${fields.map((field) => this.renderField(field)).join("") || "<p>Aucun paramètre requis.</p>"}</div>
        <button class="btn btn-primary mt-3" type="button" id="openinfra-execute">Exécuter</button>
      </section>
      <aside class="col-12 col-xxl-4">
        <h3 class="h6 text-uppercase text-muted">Résultat</h3>
        <pre class="openinfra-result" aria-live="polite" aria-label="Résultat de l’opération">${this.escape(result ? JSON.stringify(result, null, 2) : "Résultat en attente.")}</pre>
      </aside>
    </div>`;
  }

  renderField(field) {
    const required = field.required ? " required" : "";
    const requiredText = field.required ? " *" : "";
    const value = field.defaultValue || "";
    if (field.type === "select") {
      const options = this.selectOptionsForField(field);
      const source = field.optionsByField ? ` data-options-by-field="${this.escape(field.optionsByField)}"` : "";
      const map = field.optionsMap ? ` data-options-map="${this.escape(JSON.stringify(field.optionsMap))}"` : "";
      return `<label class="col-md-6 col-xl-4 form-label">${this.escape(field.label || field.name)}${requiredText}<select class="form-select" data-field="${this.escape(field.name)}"${source}${map}${required}><option value=""></option>${this.renderOptions(options, value)}</select></label>`;
    }
    if (field.type === "boolean") {
      return `<label class="col-md-6 col-xl-4 form-label">${this.escape(field.label || field.name)}<select class="form-select" data-field="${this.escape(field.name)}"><option value="false">Non</option><option value="true">Oui</option></select></label>`;
    }
    const inputType = field.type === "number" ? "number" : "text";
    return `<label class="col-md-6 col-xl-4 form-label">${this.escape(field.label || field.name)}${requiredText}<input class="form-control" type="${inputType}" data-field="${this.escape(field.name)}" value="${this.escape(value)}" placeholder="${this.escape(field.placeholder || "")}"${required}></label>`;
  }

  selectOptionsForField(field) {
    if (!field.optionsByField || !field.optionsMap) {
      return field.options || [];
    }
    const controller = field.defaultControllerValue || this.optionValue((field.controllerOptions || [])[0]) || Object.keys(field.optionsMap)[0];
    return field.optionsMap[controller] || [];
  }

  renderOptions(options, selectedValue = "") {
    return options.map((option) => {
      const value = this.optionValue(option);
      const label = this.optionLabel(option);
      return `<option value="${this.escape(value)}" ${selectedValue === value ? "selected" : ""}>${this.escape(label)}</option>`;
    }).join("");
  }

  optionValue(option) {
    if (option && typeof option === "object" && Object.hasOwn(option, "value")) {
      return String(option.value);
    }
    return String(option || "");
  }

  optionLabel(option) {
    if (option && typeof option === "object" && Object.hasOwn(option, "label")) {
      return String(option.label);
    }
    return String(option || "");
  }

  bindDependentSelects() {
    for (const dependent of document.querySelectorAll("select[data-options-by-field]")) {
      const source = document.querySelector(`[data-field="${dependent.dataset.optionsByField}"]`);
      if (!source) {
        continue;
      }
      const refresh = () => {
        const selected = dependent.value;
        const optionsMap = JSON.parse(dependent.dataset.optionsMap || "{}");
        const options = optionsMap[source.value] || [];
        dependent.innerHTML = `<option value=""></option>${this.renderOptions(options, selected)}`;
        if (options.some((option) => this.optionValue(option) === selected)) {
          dependent.value = selected;
        } else if (options.length === 1) {
          dependent.value = this.optionValue(options[0]);
        }
      };
      source.addEventListener("change", refresh);
      refresh();
    }
  }

  bindEvents() {
    document.getElementById("openinfra-execute")?.addEventListener("click", () => this.executeSelected());
    document.getElementById("openinfra-tenant")?.addEventListener("input", (event) => {
      this.state = { ...this.state, tenant: event.target.value };
    });
    const globalSearchInput = document.getElementById("openinfra-global-search");
    globalSearchInput?.addEventListener("input", (event) => this.updateGlobalSearch(event.target.value));
    globalSearchInput?.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        this.updateGlobalSearch("");
      }
    });
    this.bindSearchResultButtons();
    this.bindDependentSelects();
    for (const button of document.querySelectorAll("[data-module-id]")) {
      button.addEventListener("click", () => this.selectModule(button.dataset.moduleId));
    }
    for (const button of document.querySelectorAll("[data-accordion-id]")) {
      button.addEventListener("click", () => this.toggleAccordion(button.dataset.accordionId));
    }
    for (const button of document.querySelectorAll("[data-operation-id]")) {
      button.addEventListener("click", () => this.selectOperation(button.dataset.operationId));
    }
  }

  updateGlobalSearch(value) {
    this.state = { ...this.state, globalSearchQuery: value };
    const input = document.getElementById("openinfra-global-search");
    const results = document.getElementById("openinfra-global-search-results");
    const hasQuery = value.trim() !== "";
    if (input) {
      input.setAttribute("aria-expanded", hasQuery ? "true" : "false");
      input.value = value;
    }
    if (results) {
      results.hidden = !hasQuery;
      results.innerHTML = this.renderGlobalSearchResults();
      this.bindSearchResultButtons();
    }
    this.refreshBackendGlobalSearch(value);
  }

  async refreshBackendGlobalSearch(value) {
    const query = value.trim();
    if (query.length < 2) {
      this.state = { ...this.state, globalSearchBackend: null, globalSearchLoading: false, globalSearchError: null };
      return;
    }
    const requestId = (this.latestGlobalSearchRequest || 0) + 1;
    this.latestGlobalSearchRequest = requestId;
    this.state = { ...this.state, globalSearchLoading: true, globalSearchError: null };
    try {
      const response = await fetch(this.globalSearchUrl(query, 6), {
        credentials: "same-origin",
        headers: { Accept: "application/json" }
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const payload = await response.json();
      if (this.latestGlobalSearchRequest !== requestId) {
        return;
      }
      this.state = { ...this.state, globalSearchBackend: payload, globalSearchLoading: false, globalSearchError: null };
    } catch (error) {
      if (this.latestGlobalSearchRequest !== requestId) {
        return;
      }
      this.state = { ...this.state, globalSearchBackend: null, globalSearchLoading: false, globalSearchError: "backend_unavailable" };
    }
    const results = document.getElementById("openinfra-global-search-results");
    if (results && this.state.globalSearchQuery.trim() === query) {
      results.innerHTML = this.renderGlobalSearchResults();
      this.bindSearchResultButtons();
    }
  }

  bindSearchResultButtons() {
    for (const button of document.querySelectorAll("[data-search-operation-id]")) {
      button.addEventListener("click", () => this.selectSearchOperation(button.dataset.searchOperationId));
    }
    for (const button of document.querySelectorAll("[data-search-route]")) {
      button.addEventListener("click", () => this.selectSearchRoute(button.dataset.searchRoute));
    }
  }

  toggleAccordion(moduleId) {
    const opened = new Set(this.state.openedModules);
    if (opened.has(moduleId)) {
      opened.delete(moduleId);
    } else {
      opened.add(moduleId);
    }
    this.state = { ...this.state, openedModules: opened };
    this.render();
  }

  selectModule(moduleId) {
    const module = OPENINFRA_MODULES.find((item) => item.id === moduleId);
    if (!module) {
      return;
    }
    const opened = new Set(this.state.openedModules);
    if (module.id !== "overview") {
      opened.add(module.id);
    }
    this.state = { ...this.state, activeModuleId: module.id, selected: module.operations[0], openedModules: opened, result: null, error: null };
    this.render();
  }

  async selectSearchRoute(route) {
    if (!route) {
      return;
    }
    try {
      const response = await fetch(route, { credentials: "same-origin", headers: { Accept: "application/json" } });
      const payload = await response.json();
      this.pendingMainFocus = true;
      this.state = { ...this.state, result: JSON.stringify(payload, null, 2), globalSearchQuery: "", globalSearchBackend: null };
      this.render();
    } catch (error) {
      this.pendingMainFocus = true;
      this.state = { ...this.state, error, globalSearchQuery: "", globalSearchBackend: null };
      this.render();
    }
  }

  selectSearchOperation(operationId) {
    for (const module of OPENINFRA_MODULES) {
      const operation = module.operations.find((item) => item.id === operationId);
      if (operation) {
        const opened = new Set(this.state.openedModules);
        if (module.id !== "overview") {
          opened.add(module.id);
        }
        this.state = {
          ...this.state,
          activeModuleId: module.id,
          selected: operation,
          openedModules: opened,
          result: null,
          error: null,
          globalSearchQuery: ""
        };
        this.pendingMainFocus = true;
        this.render();
        return;
      }
    }
  }

  selectOperation(operationId) {
    for (const module of OPENINFRA_MODULES) {
      const operation = module.operations.find((item) => item.id === operationId);
      if (operation) {
        const opened = new Set(this.state.openedModules);
        if (module.id !== "overview") {
          opened.add(module.id);
        }
        this.state = { ...this.state, activeModuleId: module.id, selected: operation, openedModules: opened, result: null, error: null };
        this.render();
        return;
      }
    }
  }

  async executeSelected() {
    try {
      const payload = {};
      for (const input of document.querySelectorAll("[data-field]")) {
        payload[input.dataset.field] = input.value;
      }
      const data = await this.client().request(this.state.selected, payload);
      this.state = { ...this.state, result: data, error: null };
    } catch (error) {
      this.state = { ...this.state, error, result: null };
    }
    this.render();
  }

  moduleForOperation(operation) {
    return OPENINFRA_MODULES.find((module) => module.operations.some((item) => item.id === operation.id)) || OPENINFRA_MODULES[0];
  }

  metric(title, body) {
    return `<article class="col-md-6 col-xl-3"><div class="card h-100 openinfra-metric"><div class="card-body"><h2 class="h6 text-muted">${this.escape(title)}</h2><p class="openinfra-metric-value mb-0">${body}</p></div></div></article>`;
  }

  icon(name, className = "bi", width = 16, height = 16) {
    return `<svg class="${this.escape(className)}" width="${width}" height="${height}" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="${OPENINFRA_ICONS[name] || OPENINFRA_ICONS.grid}"></path></svg>`;
  }

  escape(value) {
    return String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\"/g, "&quot;").replace(/'/g, "&#039;");
  }
}

new OpenInfraDashboard(document.getElementById("openinfra-root")).start();
