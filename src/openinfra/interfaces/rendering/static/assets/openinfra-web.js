import { OpenInfraI18n, localizeOpenInfraCatalog } from "./openinfra-i18n.js?v=0.31.1";
import {
  fieldValidationMessage,
  formCountryCode,
  inputAttributesForField,
  inputTypeForField,
  normalizeFieldDefinition,
  normalizeFieldValue,
  validateControl
} from "./openinfra-form-fields.js?v=0.31.1";

class OpenInfraApiClient {
  constructor(apiBaseUrl, tenantProvider, i18n = null) {
    this.i18n = i18n;
    this.apiBaseUrl = apiBaseUrl.replace(/\/$/, "");
    this.tenantProvider = tenantProvider;
  }

  async request(operation, payload) {
    const path = this.interpolatePath(operation.path, payload);
    this.currentOperationId = operation.id || "";
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
    if (operation.download) {
      const blob = await response.blob();
      if (!response.ok) {
        const errorText = await blob.text();
        throw new Error(errorText || `Download failed with status ${response.status}`);
      }
      const disposition = response.headers.get("content-disposition") || "";
      const filename = this.downloadFilename(disposition, operation.downloadFilename || "openinfra-export.bin");
      const objectUrl = URL.createObjectURL(blob);
      try {
        const anchor = document.createElement("a");
        anchor.href = objectUrl;
        anchor.download = filename;
        anchor.hidden = true;
        document.body.append(anchor);
        anchor.click();
        anchor.remove();
      } finally {
        URL.revokeObjectURL(objectUrl);
      }
      return {
        downloaded: true,
        filename,
        content_type: contentType || blob.type || "application/octet-stream",
        size_bytes: blob.size
      };
    }
    const data = contentType.includes("application/json") ? await response.json() : await response.text();
    if (!response.ok) {
      throw new Error(typeof data === "string" ? data : JSON.stringify(data));
    }
    return data;
  }

  downloadFilename(disposition, fallback) {
    const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (encoded) {
      try {
        return decodeURIComponent(encoded[1].trim().replace(/^"|"$/g, ""));
      } catch (_error) {
        return fallback;
      }
    }
    const simple = disposition.match(/filename="?([^";]+)"?/i);
    return simple ? simple[1].trim() : fallback;
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
      const value = this.normalizedFieldValue(field, payload[field.name], payload);
      if (value !== undefined && value !== null && String(value).trim() !== "") {
        query.set(field.name, String(value));
      }
    }
    const tenant = this.tenantProvider();
    if (this.isTenantScopedOperation({ id: this.currentOperationId || "" }) && tenant && !query.has("tenant_id")) {
      query.set("tenant_id", tenant);
    }
    return query.toString() ? `?${query.toString()}` : "";
  }

  buildBody(operation, payload) {
    const body = {};
    for (const field of operation.body || []) {
      const raw = payload[field.name];
      if (field.type === "file") {
        if (!raw) {
          if (field.required) {
            throw new Error(this.i18n?.t("requiredField", { field: field.label || field.name }) || `Missing required field: ${field.label || field.name}`);
          }
          continue;
        }
        this.assignBodyValue(body, "filename", raw.filename);
        this.assignBodyValue(body, "media_type", raw.media_type);
        this.assignBodyValue(body, "content_base64", raw.content_base64);
        continue;
      }
      const value = this.normalizedFieldValue(field, raw, payload);
      if (value === undefined || value === null || String(value).trim?.() === "") {
        if (field.required) {
          throw new Error(this.i18n?.t("requiredField", { field: field.label || field.name }) || `Missing required field: ${field.label || field.name}`);
        }
        continue;
      }
      this.assignBodyValue(body, field.target || field.name, value);
    }
    const tenant = this.tenantProvider();
    if (this.isTenantScopedOperation(operation) && tenant && operation.body && !Object.prototype.hasOwnProperty.call(body, "tenant_id")) {
      body.tenant_id = tenant;
    }
    return body;
  }

  isTenantScopedOperation(operation) {
    const id = String(operation?.id || this.currentOperationId || "");
    return !id.startsWith("itam-organization");
  }

  normalizedFieldValue(field, raw, payload = {}) {
    try {
      const value = normalizeFieldValue(field, raw, {
        countryCode: payload.country_code || payload.country || ""
      });
      if (value === undefined) {
        return undefined;
      }
      if (field.type === "boolean") {
        return ["1", "true", "yes", "oui"].includes(String(value).toLowerCase());
      }
      return value;
    } catch (error) {
      if (error instanceof Error && error.code) {
        throw new Error(fieldValidationMessage(this.i18n, { code: error.code }, error.field || field));
      }
      throw error;
    }
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
  menu: "M2 4h12v1.4H2V4zm0 3.3h12v1.4H2V7.3zm0 3.3h12V12H2v-1.4z",
  speedometer2: "M8 4a.5.5 0 0 1 .5.5V6a.5.5 0 0 1-1 0V4.5A.5.5 0 0 1 8 4zM3.732 5.732a.5.5 0 0 1 .707 0l.915.914a.5.5 0 1 1-.708.708l-.914-.915a.5.5 0 0 1 0-.707zM2 10a.5.5 0 0 1 .5-.5h1.586a.5.5 0 0 1 0 1H2.5A.5.5 0 0 1 2 10zm9.5 0a.5.5 0 0 1 .5-.5h1.5a.5.5 0 0 1 0 1H12a.5.5 0 0 1-.5-.5zm.754-4.246a.5.5 0 0 1 0 .707l-.94.94a.5.5 0 1 1-.707-.708l.94-.94a.5.5 0 0 1 .707 0zM9.67 11.71a2 2 0 1 1-3.34-2.19l3.95-3.95a.5.5 0 0 1 .8.6l-1.41 5.54zM8 1a7 7 0 0 0-7 7c0 1.71.61 3.28 1.63 4.5a.5.5 0 0 0 .38.17h9.98a.5.5 0 0 0 .38-.17A6.97 6.97 0 0 0 15 8a7 7 0 0 0-7-7z",
  table: "M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V2zm15 2h-4v3h4V4zm0 4h-4v3h4V8zm0 4h-4v3h3a1 1 0 0 0 1-1v-2zm-5 3v-3H6v3h4zm-5 0v-3H1v2a1 1 0 0 0 1 1h3zm-4-4h4V8H1v3zm0-4h4V4H1v3zm5-3v3h4V4H6zm4 4H6v3h4V8z",
  reference: "M1 2a2 2 0 0 1 2-2h1.6a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V2zm6.7 0a2 2 0 0 1 2-2h1.6a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H9.7a2 2 0 0 1-2-2V2zm6.25.55A1.8 1.8 0 0 1 15 4.18v7.64a1.8 1.8 0 0 1-1.05 1.63V2.55z",
  asset: "M2 1a2 2 0 0 1 2-2h5.6a2 2 0 0 1 1.414.586l2.4 2.4A2 2 0 0 1 14 3.4V14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V1zm2 .8a.8.8 0 0 0-.8.8v10.8a.8.8 0 0 0 .8.8h8a.8.8 0 0 0 .8-.8V4.4h-2.2a1.8 1.8 0 0 1-1.8-1.8V.8H4zm1.25 5.05a.85.85 0 1 0 0-1.7.85.85 0 0 0 0 1.7zm2.05-.6a.6.6 0 0 0 0 1.2h3.9a.6.6 0 1 0 0-1.2H7.3zm-2.05 4.6a.85.85 0 1 0 0-1.7.85.85 0 0 0 0 1.7zm2.05-.6a.6.6 0 1 0 0 1.2h3.9a.6.6 0 1 0 0-1.2H7.3z",
  grid: "M1 2.5A1.5 1.5 0 0 1 2.5 1h3A1.5 1.5 0 0 1 7 2.5v3A1.5 1.5 0 0 1 5.5 7h-3A1.5 1.5 0 0 1 1 5.5v-3zm8 0A1.5 1.5 0 0 1 10.5 1h3A1.5 1.5 0 0 1 15 2.5v3A1.5 1.5 0 0 1 13.5 7h-3A1.5 1.5 0 0 1 9 5.5v-3zm-8 8A1.5 1.5 0 0 1 2.5 9h3A1.5 1.5 0 0 1 7 10.5v3A1.5 1.5 0 0 1 5.5 15h-3A1.5 1.5 0 0 1 1 13.5v-3zm8 0A1.5 1.5 0 0 1 10.5 9h3a1.5 1.5 0 0 1 1.5 1.5v3a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 9 13.5v-3z",
  people: "M11 6a3 3 0 1 1-6 0 3 3 0 0 1 6 0zm-1.559 4.27A4.985 4.985 0 0 0 8 10c-2.67 0-4.9 2.1-4.99 4.71A1 1 0 0 0 4 15h8a1 1 0 0 0 .99-1.29 5.002 5.002 0 0 0-3.549-3.44zM13.5 7a2.5 2.5 0 0 1-1.18 2.12 6.01 6.01 0 0 1 2.2 2.56A1 1 0 0 0 15.5 10.5 3.5 3.5 0 0 0 12 7h1.5z",
  sliders: "M3 4h10v1H3V4zm2 3h6v1H5V7zm-2 3h10v1H3v-1z",
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
const DCIM_REFERENCE_FIELDS = new Set(["site", "site_code", "building", "building_code", "floor", "floor_code", "room", "room_code", "zone", "zone_code", "rack", "row", "column"]);
const DCIM_REFERENCE_LABELS = { site: "Site", site_code: "Site", building: "Bâtiment", building_code: "Bâtiment", floor: "Étage", floor_code: "Étage", room: "Salle", room_code: "Salle", zone: "Zone", zone_code: "Zone", rack: "Rack", row: "Ligne salle", column: "Colonne salle" };

const FIELD_SETS = {
  tenant: { name: "tenant_id", label: "Filiale/Subdivision", type: "tenant-select", defaultValue: "default", placeholder: "default" },
  limit: { name: "limit", label: "Limite", type: "number", placeholder: "100" },
  cursor: { name: "cursor", label: "Curseur", placeholder: "Curseur de pagination" },
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
  riKey: { name: "key", label: "Clé RSOT", required: true, placeholder: "server/srv-db-01" },
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
  featureCapability: { name: "capability", label: "Capacité", type: "select", options: ["core_rsot", "dcim", "ipam", "rbac", "audit", "import_export", "distributed_discovery_agents", "installer_agent_scope"], defaultValue: "ipam" },
  quotaResource: { name: "resource", label: "Ressource quota", type: "select", options: ["equipment", "subnet_vlan", "ip_dns_record", "user", "discovery_collector"], defaultValue: "equipment" },
  requestedIncrement: { name: "requested_increment", label: "Incrément demandé", type: "number", defaultValue: "1", placeholder: "1" }
};

const OPENINFRA_MODULES = [
  { id: "overview", label: "Dashboard", icon: "speedometer2", description: "Vue de synthèse, readiness backend, version package, trust web-backend et opérations rapides.", operations: [
    { id: "version", label: "Version runtime", method: "GET", path: "/v1/version", query: [] },
    { id: "schema", label: "Statut schéma DB", method: "GET", path: "/v1/database/schema", query: [] }
  ] },
  { id: "rsot", label: "RSOT (Ressource Source of Truth)", shortLabel: "RSOT", icon: "reference", description: "Inventaire canonique, relations, versions, gouvernance et certification.", operations: [
    { id: "rsot-taxonomy", label: "Catalogue catégories / types", method: "GET", path: "/v1/rsot/resource-taxonomy", query: [] },
    { id: "rsot-list", label: "Lister les objets RSOT", method: "GET", path: "/v1/rsot/objects", query: [FIELD_SETS.resourceCategoryFilter, FIELD_SETS.resourceTypeFilter, FIELD_SETS.tag, FIELD_SETS.limit] },
    { id: "rsot-upsert", label: "Créer / mettre à jour une ressource", method: "POST", path: "/v1/rsot/objects", body: [FIELD_SETS.actor, FIELD_SETS.riKey, { ...FIELD_SETS.resourceCategory, required: true }, { ...FIELD_SETS.resourceType, required: true }, FIELD_SETS.displayName, FIELD_SETS.source, FIELD_SETS.serial, FIELD_SETS.vendor, FIELD_SETS.model, FIELD_SETS.site, FIELD_SETS.building, FIELD_SETS.room, FIELD_SETS.row, FIELD_SETS.column, FIELD_SETS.rack, FIELD_SETS.managementIp, FIELD_SETS.lifecycle, FIELD_SETS.tags] },
    { id: "rsot-relations", label: "Lister les relations", method: "GET", path: "/v1/rsot/relations", query: [{ name: "source_key", label: "Ressource source" }, { name: "target_key", label: "Ressource cible" }, { name: "relation_type", label: "Type de relation" }, { ...FIELD_SETS.asOf, required: false }, FIELD_SETS.limit] },
    { id: "rsot-as-of", label: "Restituer une ressource à date", method: "GET", path: "/v1/rsot/object-as-of", query: [FIELD_SETS.riKey, FIELD_SETS.asOf] },
    { id: "rsot-object-audit", label: "Audit d’une ressource", method: "GET", path: "/v1/rsot/object-audit", query: [FIELD_SETS.riKey, FIELD_SETS.limit] },
    { id: "rsot-quality-object", label: "Évaluer la qualité d’une ressource", method: "GET", path: "/v1/rsot/quality/object", query: [FIELD_SETS.riKey] },
    { id: "rsot-quality-summary", label: "Synthèse qualité / certification", method: "GET", path: "/v1/rsot/quality/summary", query: [FIELD_SETS.resourceCategoryFilter, FIELD_SETS.resourceTypeFilter, FIELD_SETS.tag, FIELD_SETS.limit] },
    { id: "rsot-governance", label: "Évaluer une règle de gouvernance", method: "POST", path: "/v1/rsot/governance/evaluate", body: [
      { name: "object_kind", label: "Catégorie d’objet", required: true, type: "select", options: RESOURCE_CATEGORY_OPTIONS },
      { name: "incoming_source", label: "Source entrante", required: true, type: "select", options: SOURCE_OPTIONS },
      { name: "existing_serial", label: "Serial existant", target: "existing_attributes.serial" },
      { name: "incoming_serial", label: "Serial entrant", target: "incoming_attributes.serial" },
      { name: "existing_site", label: "Site existant", target: "existing_attributes.site" },
      { name: "incoming_site", label: "Site entrant", target: "incoming_attributes.site" }
    ] },
    { id: "rsot-reconcile", label: "Réconcilier une ressource", method: "POST", path: "/v1/rsot/reconcile-object", body: [
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
    ] },
    { id: "graph-traverse", label: "Explorer le graphe de dépendances", method: "GET", path: "/v1/graph/traverse", query: [
      { name: "root_key", label: "Clé racine", required: true, placeholder: "application/portail" },
      { name: "direction", label: "Direction", type: "select", options: ["outgoing", "incoming", "both"], defaultValue: "both" },
      { name: "max_depth", label: "Profondeur maximale", type: "number", defaultValue: "3", placeholder: "3" },
      { name: "max_nodes", label: "Nombre maximal de nœuds", type: "number", defaultValue: "500", placeholder: "500" },
      { name: "relation_type", label: "Type de relation", placeholder: "depends_on" },
      { ...FIELD_SETS.asOf, required: false }
    ] },
    { id: "graph-impact", label: "Analyser les impacts", method: "GET", path: "/v1/graph/impact", query: [
      { name: "root_key", label: "Clé racine", required: true, placeholder: "server/db-01" },
      { name: "direction", label: "Direction", type: "select", options: ["incoming", "outgoing", "both"], defaultValue: "incoming" },
      { name: "max_depth", label: "Profondeur maximale", type: "number", defaultValue: "6", placeholder: "6" },
      { name: "max_nodes", label: "Nombre maximal de nœuds", type: "number", defaultValue: "1000", placeholder: "1000" },
      { name: "relation_type", label: "Type de relation", placeholder: "depends_on" },
      { ...FIELD_SETS.asOf, required: false }
    ] },
    { id: "graph-path", label: "Trouver le chemin le plus court", method: "GET", path: "/v1/graph/path", query: [
      { name: "source_key", label: "Ressource source", required: true, placeholder: "application/portail" },
      { name: "target_key", label: "Ressource cible", required: true, placeholder: "server/db-01" },
      { name: "direction", label: "Direction", type: "select", options: ["outgoing", "incoming", "both"], defaultValue: "outgoing" },
      { name: "max_depth", label: "Profondeur maximale", type: "number", defaultValue: "8", placeholder: "8" },
      { name: "max_nodes", label: "Nombre maximal de nœuds", type: "number", defaultValue: "1000", placeholder: "1000" },
      { name: "relation_type", label: "Type de relation", placeholder: "depends_on" },
      { ...FIELD_SETS.asOf, required: false }
    ] },
    { id: "graph-spof", label: "Détecter les points uniques de défaillance", method: "GET", path: "/v1/graph/spof", query: [
      { name: "root_key", label: "Clé racine", required: true, placeholder: "application/portail" },
      { name: "direction", label: "Direction", type: "select", options: ["outgoing", "incoming", "both"], defaultValue: "both" },
      { name: "max_depth", label: "Profondeur maximale", type: "number", min: "1", max: "12", defaultValue: "8" },
      { name: "max_nodes", label: "Nombre maximal de nœuds", type: "number", min: "2", max: "5000", defaultValue: "2000" },
      { name: "relation_type", label: "Type de relation", placeholder: "depends_on" },
      { ...FIELD_SETS.asOf, required: false },
      { name: "candidate_kind", label: "Type de candidat", placeholder: "server" },
      { name: "candidate_resource_category", label: "Catégorie ressource candidate", placeholder: "network-device" },
      { name: "candidate_resource_type", label: "Type de ressource candidat", placeholder: "switch" },
      { name: "candidate_status", label: "Statut candidat", placeholder: "active" },
      { name: "minimum_affected_nodes", label: "Nombre minimal d’objets affectés", type: "number", min: "1", max: "4999", defaultValue: "1" },
      { name: "affected_sample_limit", label: "Limite échantillon affecté", type: "number", min: "1", max: "200", defaultValue: "25" },
      { name: "limit", label: "Limite", type: "number", min: "1", max: "500", defaultValue: "100" },
      { name: "cursor", label: "Curseur", placeholder: "Curseur opaque retourné par l’API" }
    ] },
    { id: "graph-export", label: "Exporter le graphe de dépendances", method: "GET", path: "/v1/graph/export", download: true, downloadFilename: "openinfra-graph-export.json", query: [
      { name: "root_key", label: "Clé racine", required: true, placeholder: "application/portail" },
      { name: "format", label: "Format d’export", type: "select", options: ["json", "csv", "graphml"], defaultValue: "json" },
      { name: "direction", label: "Direction", type: "select", options: ["outgoing", "incoming", "both"], defaultValue: "both" },
      { name: "max_depth", label: "Profondeur maximale", type: "number", min: "1", max: "12", defaultValue: "8" },
      { name: "max_nodes", label: "Nombre maximal de nœuds", type: "number", min: "2", max: "5000", defaultValue: "2000" },
      { name: "relation_type", label: "Type de relation", placeholder: "depends_on" },
      { ...FIELD_SETS.asOf, required: false },
      { name: "include_spof", label: "Inclure les SPOF", type: "boolean", defaultValue: "true" },
      { name: "candidate_kind", label: "Type de candidat", placeholder: "server" },
      { name: "candidate_resource_category", label: "Catégorie ressource candidate", placeholder: "network-device" },
      { name: "candidate_resource_type", label: "Type de ressource candidat", placeholder: "switch" },
      { name: "candidate_status", label: "Statut candidat", placeholder: "active" },
      { name: "minimum_affected_nodes", label: "Nombre minimal d’objets affectés", type: "number", min: "1", max: "4999", defaultValue: "1" }
    ] },
    { id: "simulation-create", label: "Créer un scénario de changement", method: "POST", path: "/v1/simulation-scenarios/create", body: [
      FIELD_SETS.actor,
      { name: "name", label: "Nom du scénario", required: true },
      { name: "description", label: "Description", type: "textarea", rows: 4, required: true },
      { name: "owner", label: "Propriétaire", required: true },
      { name: "idempotency_key", label: "Clé d’idempotence", required: true },
      { name: "site", label: "Site" },
      { name: "environment", label: "Environnement" },
      { name: "criticality", label: "Criticité", type: "select", options: ["low", "medium", "high", "critical"] },
      { name: "changes", label: "Changements JSON", type: "json", required: true, defaultValue: "[]" }
    ] },
    { id: "simulation-list", label: "Lister les scénarios", method: "GET", path: "/v1/simulation-scenarios", query: [
      { name: "status", label: "Statut", type: "select", options: ["draft", "queued", "running", "completed", "failed", "cancelled"] },
      { name: "site", label: "Site" }, FIELD_SETS.limit, { name: "cursor", label: "Curseur" }
    ] },
    { id: "simulation-run", label: "Calculer l’impact d’un scénario", method: "POST", path: "/v1/simulation-scenarios/run", body: [
      FIELD_SETS.actor, { name: "scenario_id", label: "ID scénario", required: true },
      { name: "max_depth", label: "Profondeur maximale", type: "number", min: "1", max: "12", defaultValue: "8" },
      { name: "max_nodes", label: "Nombre maximal de nœuds", type: "number", min: "2", max: "5000", defaultValue: "2000" }
    ] },
    { id: "simulation-reports", label: "Lister les rapports d’impact", method: "GET", path: "/v1/impact-reports", query: [
      { name: "scenario_id", label: "ID scénario" }, FIELD_SETS.limit, { name: "cursor", label: "Curseur" }
    ] },
    { id: "simulation-compare", label: "Comparer deux rapports", method: "POST", path: "/v1/scenario-comparisons/create", body: [
      FIELD_SETS.actor, { name: "left_report_id", label: "ID rapport gauche", required: true },
      { name: "right_report_id", label: "ID rapport droit", required: true }
    ] },
    { id: "simulation-comparisons", label: "Lister les comparaisons", method: "GET", path: "/v1/scenario-comparisons", query: [
      FIELD_SETS.limit, { name: "cursor", label: "Curseur" }
    ] }    ,{ id: "rag-document-upsert", label: "Indexer un document gouverné", method: "POST", path: "/v1/rag/documents/upsert", body: [
      { name: "source_type", label: "Type de source", type: "select", options: ["rsot", "documentation", "runbook", "policy", "other"], defaultValue: "documentation", required: true },
      { name: "source_ref", label: "Référence source", required: true }, { name: "title", label: "Titre", required: true },
      { name: "content", label: "Contenu", type: "textarea", required: true }, { name: "source_uri", label: "URI source" },
      { name: "required_permissions", label: "Permissions requises", type: "csv", defaultValue: "rag.read" },
      { name: "tags", label: "Tags", type: "csv" }, { name: "metadata", label: "Métadonnées JSON", type: "json", defaultValue: "{}" }, FIELD_SETS.actor
    ] },
    { id: "rag-documents", label: "Lister les documents gouvernés", method: "GET", path: "/v1/rag/documents", query: [
      { name: "source_type", label: "Type de source" }, { name: "active", label: "Actif", type: "boolean" }, FIELD_SETS.limit, FIELD_SETS.cursor
    ] },
    { id: "rag-document-get", label: "Consulter un document gouverné", method: "GET", path: "/v1/rag/documents/get", query: [{ name: "document_id", label: "ID document", required: true }] },
    { id: "rag-document-deactivate", label: "Désactiver un document gouverné", method: "POST", path: "/v1/rag/documents/deactivate", body: [{ name: "document_id", label: "ID document", required: true }, FIELD_SETS.actor] },
    { id: "rag-rsot-sync", label: "Synchroniser l’index depuis RSOT", method: "POST", path: "/v1/rag/index/rsot", body: [
      { name: "max_objects", label: "Nombre maximal d’objets", type: "number", defaultValue: "5000" },
      { name: "deactivate_missing", label: "Désactiver les objets absents", type: "boolean", defaultValue: "false" }, FIELD_SETS.actor
    ] },
    { id: "rag-query", label: "Interroger l’assistant gouverné", method: "POST", path: "/v1/rag/query", body: [
      { name: "question", label: "Question", type: "textarea", required: true },
      { name: "limit", label: "Nombre maximal de citations", type: "number", defaultValue: "6" }, FIELD_SETS.actor
    ] },
    { id: "rag-answers", label: "Lister les réponses citées", method: "GET", path: "/v1/rag/answers", query: [FIELD_SETS.limit, FIELD_SETS.cursor] },
    { id: "rag-answer-get", label: "Consulter une réponse citée", method: "GET", path: "/v1/rag/answers/get", query: [{ name: "answer_id", label: "ID réponse", required: true }] },
    { id: "rag-job-create", label: "Créer un job RAG", method: "POST", path: "/v1/rag/jobs/create", body: [
      { name: "kind", label: "Type de job", type: "select", options: ["document-import", "answer-export"], required: true },
      { name: "idempotency_key", label: "Clé d’idempotence", required: true }, { name: "payload", label: "Charge utile JSON", type: "json", required: true, defaultValue: "{}" },
      { name: "batch_size", label: "Taille de lot", type: "number", defaultValue: "100" }, FIELD_SETS.actor
    ] },
    { id: "rag-jobs", label: "Lister les jobs RAG", method: "GET", path: "/v1/rag/jobs", query: [FIELD_SETS.limit, FIELD_SETS.cursor] },
    { id: "rag-job-get", label: "Consulter un job RAG", method: "GET", path: "/v1/rag/jobs/get", query: [{ name: "job_id", label: "ID job", required: true }] },
    { id: "rag-job-run", label: "Exécuter une tranche de job RAG", method: "POST", path: "/v1/rag/jobs/run", body: [{ name: "job_id", label: "ID job", required: true }, FIELD_SETS.actor] },
    { id: "rag-job-artifact", label: "Télécharger un export RAG", method: "GET", path: "/v1/rag/jobs/artifact", download: true, query: [{ name: "job_id", label: "ID job", required: true }] }

  ] },
  { id: "ipam", label: "IPAM", icon: "grid", description: "IPv4/IPv6, VRF, préfixes, plages, VLAN/VXLAN, ASN/BGP, DNS/DHCP, DDI, conflits, capacité et allocations.", operations: [
    { id: "ipam-dashboard", label: "Dashboard IPAM", method: "GET", path: "/v1/ipam/ui-dashboard", query: [{ name: "vrf", label: "VRF", placeholder: "global" }] },
    { id: "ipam-search", label: "Rechercher dans l’IPAM", method: "GET", path: "/v1/ipam/ui-search", query: [{ name: "query", label: "Recherche", required: true, placeholder: "10.20.0.0/24 ou srv-db" }, { name: "vrf", label: "VRF", placeholder: "global" }] },
    { id: "ipam-define-vrf", label: "Définir une VRF", method: "POST", path: "/v1/ipam/vrfs", body: [FIELD_SETS.actor, { name: "name", label: "Nom VRF", required: true, placeholder: "global" }, { name: "route_distinguisher", label: "Route distinguisher", placeholder: "65000:100" }] },
    { id: "ipam-define-aggregate", label: "Définir un agrégat IP", method: "POST", path: "/v1/ipam/aggregates", body: [FIELD_SETS.actor, { name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "cidr", label: "CIDR agrégat", required: true, placeholder: "10.20.0.0/16" }, { name: "description", label: "Description", placeholder: "Bloc site PAR1" }] },
    { id: "ipam-define-prefix", label: "Définir un préfixe IP", method: "POST", path: "/v1/ipam/prefixes", body: [FIELD_SETS.actor, { name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "cidr", label: "CIDR préfixe", required: true, placeholder: "10.20.30.2/24" }, { name: "description", label: "Description", placeholder: "Réseau serveurs" }] },
    { id: "ipam-list-prefixes", label: "Lister les préfixes", method: "GET", path: "/v1/ipam/prefixes", query: [{ name: "vrf", label: "VRF", required: true, placeholder: "global" }] },
    { id: "ipam-define-range", label: "Définir une plage IP", method: "POST", path: "/v1/ipam/ranges", body: [FIELD_SETS.actor, { name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "prefix", label: "Préfixe", required: true, placeholder: "10.20.30.2/24" }, { name: "start", label: "Début plage", required: true, placeholder: "10.20.30.20" }, { name: "end", label: "Fin plage", required: true, placeholder: "10.20.30.200" }, { name: "purpose", label: "Usage plage", type: "select", options: [{ value: "allocation", label: "Allocation" }, { value: "reservation", label: "Réservation" }, { value: "exclusion", label: "Exclusion" }], defaultValue: "allocation" }, { name: "description", label: "Description", placeholder: "Pool applicatif" }] },
    { id: "ipam-register-address", label: "Enregistrer une adresse IP", method: "POST", path: "/v1/ipam/addresses", body: [FIELD_SETS.actor, { name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "prefix", label: "Préfixe", required: true, placeholder: "10.20.30.2/24" }, { name: "address", label: "Adresse IP", required: true, placeholder: "10.20.30.21" }, { name: "hostname", label: "Nom DNS / équipement", required: true, placeholder: "srv-app-01" }, { name: "interface_name", label: "Interface", placeholder: "eth0" }, { name: "status", label: "Statut adresse", type: "select", options: [{ value: "planned", label: "Planifiée" }, { value: "reserved", label: "Réservée" }, { value: "active", label: "Active" }, { value: "deprecated", label: "Dépréciée" }], defaultValue: "reserved" }] },
    { id: "ipam-allocate", label: "Allouer une adresse IP", method: "POST", path: "/v1/ipam/allocate", body: [FIELD_SETS.actor, { name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "prefix", label: "Préfixe", required: true, placeholder: "10.20.30.2/24" }, { name: "hostname", label: "Nom DNS / équipement", required: true, placeholder: "srv-app-01" }, { name: "idempotency_key", label: "Clé d’idempotence", required: true, placeholder: "ipam-alloc-srv-app-01" }] },
    { id: "ipam-reservation-wizard", label: "Assistant de réservation IP", method: "POST", path: "/v1/ipam/reservation-wizard", body: [FIELD_SETS.actor, { name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "prefix", label: "Préfixe", required: true, placeholder: "10.20.30.2/24" }, { name: "hostname", label: "Nom DNS / équipement", required: true, placeholder: "srv-app-02" }, { name: "idempotency_key", label: "Clé d’idempotence", required: true, placeholder: "ipam-wizard-srv-app-02" }, { name: "apply", label: "Appliquer la réservation", type: "boolean" }] },
    { id: "ipam-capacity", label: "Calculer la capacité d’un préfixe", method: "GET", path: "/v1/ipam/capacity", query: [{ name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "prefix", label: "Préfixe", required: true, placeholder: "10.20.30.2/24" }] },
    { id: "ipam-network-bindings", label: "Afficher les bindings réseau", method: "GET", path: "/v1/ipam/network-bindings", query: [{ name: "vrf", label: "VRF", placeholder: "global" }] },
    { id: "ipam-topology", label: "Topologie opérationnelle IPAM", method: "GET", path: "/v1/ipam/topology", query: [{ name: "vrf", label: "VRF", placeholder: "global" }] },
    { id: "ipam-define-vlan-group", label: "Définir un groupe VLAN", method: "POST", path: "/v1/ipam/vlan-groups", body: [FIELD_SETS.actor, { name: "name", label: "Groupe VLAN", required: true, placeholder: "dc-par1" }, { name: "scope", label: "Scope VLAN", placeholder: "site/PAR1" }, { name: "description", label: "Description", placeholder: "VLAN datacenter PAR1" }] },
    { id: "ipam-define-vxlan-vni", label: "Définir un VXLAN VNI", method: "POST", path: "/v1/ipam/vxlan-vnis", body: [FIELD_SETS.actor, { name: "vni", label: "VNI", type: "number", required: true, placeholder: "10010" }, { name: "name", label: "Nom VNI", required: true, placeholder: "prod-app" }, { name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "route_targets_import", label: "RT import", type: "csv", placeholder: "65000:10010" }, { name: "route_targets_export", label: "RT export", type: "csv", placeholder: "65000:10010" }, { name: "description", label: "Description", placeholder: "Segment applicatif" }] },
    { id: "ipam-define-vlan", label: "Définir un VLAN", method: "POST", path: "/v1/ipam/vlans", body: [FIELD_SETS.actor, { name: "group", label: "Groupe VLAN", required: true, placeholder: "dc-par1" }, { name: "vlan_id", label: "VLAN ID", type: "number", required: true, placeholder: "210" }, { name: "name", label: "Nom VLAN", required: true, placeholder: "prod-app" }, { name: "vrf", label: "VRF", placeholder: "global" }, { name: "vni", label: "VNI", type: "number", placeholder: "10010" }, { name: "description", label: "Description", placeholder: "Réseau applicatif" }] },
    { id: "ipam-define-asn", label: "Définir un ASN", method: "POST", path: "/v1/ipam/asns", body: [FIELD_SETS.actor, { name: "asn", label: "ASN", type: "number", required: true, placeholder: "65000" }, { name: "name", label: "Nom AS", required: true, placeholder: "OpenInfra Core" }, { name: "description", label: "Description", placeholder: "Autonomous system interne" }] },
    { id: "ipam-define-bgp-peer", label: "Définir un peer BGP", method: "POST", path: "/v1/ipam/bgp-peers", body: [FIELD_SETS.actor, { name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "local_asn", label: "ASN local", type: "number", required: true, placeholder: "65000" }, { name: "remote_asn", label: "ASN distant", type: "number", required: true, placeholder: "65010" }, { name: "peer_address", label: "Adresse peer", required: true, placeholder: "192.0.2.2" }, { name: "address_family", label: "Famille d’adresses", type: "select", options: [{ value: "ipv4", label: "IPv4" }, { value: "ipv6", label: "IPv6" }] }, { name: "route_targets_import", label: "RT import", type: "csv", placeholder: "65000:10010" }, { name: "route_targets_export", label: "RT export", type: "csv", placeholder: "65000:10010" }, { name: "description", label: "Description", placeholder: "Peer datacenter" }] },
    { id: "ipam-observe-dns", label: "Observer un enregistrement DNS", method: "POST", path: "/v1/ipam/dns-observations", body: [FIELD_SETS.actor, { name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "hostname", label: "Nom DNS", required: true, placeholder: "srv-app-01.example.net" }, { name: "address", label: "Adresse IP", required: true, placeholder: "10.20.30.21" }, { name: "ptr_hostname", label: "Nom PTR", placeholder: "srv-app-01.example.net" }, { name: "source", label: "Source observation", placeholder: "bind" }] },
    { id: "ipam-observe-dhcp", label: "Observer un bail DHCP", method: "POST", path: "/v1/ipam/dhcp-leases", body: [FIELD_SETS.actor, { name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "prefix", label: "Préfixe", required: true, placeholder: "10.20.30.2/24" }, { name: "address", label: "Adresse IP", required: true, placeholder: "10.20.31.14" }, { name: "mac_address", label: "Adresse MAC", required: true, placeholder: "00:11:22:33:44:55" }, { name: "hostname", label: "Nom DHCP", required: true, placeholder: "srv-dhcp-01" }, { name: "source", label: "Source observation", placeholder: "kea" }, { name: "active", label: "Bail actif", type: "boolean", defaultValue: "true" }] },
    { id: "ipam-conflicts", label: "Détecter les conflits", method: "GET", path: "/v1/ipam/conflicts", query: [{ name: "vrf", label: "VRF", placeholder: "global" }] },
    { id: "ipam-ddi-preview", label: "Prévisualiser DDI", method: "POST", path: "/v1/ipam/ddi-preview", body: [FIELD_SETS.actor, { name: "vrf", label: "VRF", required: true, placeholder: "global" }, { name: "idempotency_key", label: "Clé d’idempotence", required: true, placeholder: "ipam-alloc-srv-app-01" }, { name: "providers", label: "Fournisseurs DDI", type: "csv", placeholder: "bind,kea" }, { name: "dns_zone", label: "Zone DNS", placeholder: "example.net" }, { name: "mac_address", label: "Adresse MAC", placeholder: "00:11:22:33:44:55" }, { name: "ttl", label: "TTL", type: "number", placeholder: "300" }, { name: "apply_preview", label: "Appliquer la prévisualisation", type: "boolean" }] },
    { id: "network-config-baseline-upsert", label: "Créer ou réviser une golden configuration", method: "POST", path: "/v1/network-config/baselines/upsert", body: [FIELD_SETS.actor, { name: "code", label: "Code", required: true }, { name: "device_object_key", label: "Objet équipement RSOT", required: true }, { name: "platform", label: "Plateforme réseau", required: true }, { name: "expected_config", label: "Configuration attendue JSON", type: "textarea", required: true }, { name: "ignored_paths", label: "Chemins ignorés", type: "csv" }, { name: "critical_paths", label: "Chemins critiques", type: "csv" }, { name: "owner", label: "Propriétaire", required: true }, { name: "justification", label: "Justification", required: true }] },
    { id: "network-config-baseline-list", label: "Lister les golden configurations", method: "GET", path: "/v1/network-config/baselines", query: [{ name: "limit", label: "Limite", type: "number", defaultValue: "100" }, { name: "cursor", label: "Curseur" }, { name: "include_retired", label: "Inclure retirés", type: "boolean" }] },
    { id: "network-config-baseline-retire", label: "Retirer une golden configuration", method: "POST", path: "/v1/network-config/baselines/retire", body: [FIELD_SETS.actor, { name: "baseline_id", label: "ID baseline", required: true }] },
    { id: "network-config-observation-submit", label: "Ingérer une configuration découverte", method: "POST", path: "/v1/network-config/observations/submit", body: [FIELD_SETS.actor, { name: "idempotency_key", label: "Clé d’idempotence", required: true }, { name: "source", label: "Source observation", type: "select", options: ["ssh", "api", "netconf", "restconf", "gnmi", "discovery", "import", "manual"], required: true }, { name: "collector", label: "Collecteur", required: true }, { name: "device_object_key", label: "Objet équipement RSOT", required: true }, { name: "platform", label: "Plateforme réseau", required: true }, { name: "observed_config", label: "Configuration observée JSON", type: "textarea", required: true }, { name: "observed_at", label: "Observé le (ISO-8601)", required: true }] },
    { id: "network-config-observation-list", label: "Lister les configurations découvertes", method: "GET", path: "/v1/network-config/observations", query: [{ name: "device_object_key", label: "Objet équipement RSOT" }, { name: "platform", label: "Plateforme réseau" }, { name: "observed_before", label: "Observé avant" }, { name: "limit", label: "Limite", type: "number", defaultValue: "100" }, { name: "cursor", label: "Curseur" }] },
    { id: "network-config-assessment", label: "Évaluer la dérive réseau", method: "GET", path: "/v1/network-config/assessment", query: [{ name: "actor", label: "Opérateur", defaultValue: "web" }, { name: "baseline_code", label: "Code baseline" }, { name: "as_of", label: "Date de référence", format: "date-time" }, { name: "status", label: "Statut conformité", type: "select", options: ["compliant", "drift", "missing-observation"] }, { name: "limit", label: "Limite", type: "number", defaultValue: "100" }, { name: "cursor", label: "Curseur" }] },
    { id: "flow-declaration-upsert", label: "Créer ou réviser un flux déclaré", method: "POST", path: "/v1/flows/declarations/upsert", body: [
      FIELD_SETS.actor,
      { name: "code", label: "Code", required: true, placeholder: "APP-WEB-HTTPS" },
      { name: "source_selector", label: "Sélecteur source", required: true, placeholder: "object:application/portail" },
      { name: "destination_selector", label: "Sélecteur destination", required: true, placeholder: "cidr:10.20.30.2/24" },
      { name: "protocol", label: "Protocole", type: "select", options: ["any", "tcp", "udp", "sctp", "icmp", "icmpv6", "esp", "ah", "gre"], defaultValue: "tcp" },
      { name: "destination_port_start", label: "Port destination début", type: "number", placeholder: "443" },
      { name: "destination_port_end", label: "Port destination fin", type: "number", placeholder: "443" },
      { name: "decision", label: "Décision", type: "select", options: ["allow", "deny"], defaultValue: "allow" },
      { name: "priority", label: "Priorité", type: "number", defaultValue: "100" },
      { name: "owner", label: "Propriétaire", required: true, placeholder: "Équipe réseau" },
      { name: "justification", label: "Justification", required: true, placeholder: "Flux applicatif approuvé" },
      { name: "valid_from", label: "Début validité", placeholder: "2026-07-10T00:00:00Z" },
      { name: "valid_to", label: "Fin validité", placeholder: "2027-07-10T00:00:00Z" }
    ] },
    { id: "flow-declaration-list", label: "Lister les flux déclarés", method: "GET", path: "/v1/flows/declarations", query: [
      { name: "limit", label: "Limite", type: "number", defaultValue: "100" },
      { name: "cursor", label: "Curseur" },
      { name: "include_retired", label: "Inclure retirés", type: "boolean" }
    ] },
    { id: "flow-declaration-retire", label: "Retirer un flux déclaré", method: "POST", path: "/v1/flows/declarations/retire", body: [
      FIELD_SETS.actor,
      { name: "declaration_id", label: "ID déclaration", required: true }
    ] },
    { id: "flow-observation-submit", label: "Ingérer un flux observé", method: "POST", path: "/v1/flows/observations/submit", body: [
      FIELD_SETS.actor,
      { name: "idempotency_key", label: "Clé d’idempotence", required: true, placeholder: "collector-01:20260710:000001" },
      { name: "source", label: "Source observation", type: "select", options: ["netflow", "sflow", "ipfix", "firewall-log", "application-log", "import", "manual"], defaultValue: "netflow" },
      { name: "collector", label: "Collecteur", required: true, placeholder: "netflow-par-01" },
      { name: "source_ip", label: "IP source", required: true, placeholder: "10.10.1.10" },
      { name: "destination_ip", label: "IP destination", required: true, placeholder: "10.20.31.10" },
      { name: "source_object_key", label: "Objet source", placeholder: "application/portail" },
      { name: "destination_object_key", label: "Objet destination", placeholder: "server/web-01" },
      { name: "protocol", label: "Protocole", type: "select", options: ["tcp", "udp", "sctp", "icmp", "icmpv6", "esp", "ah", "gre"], defaultValue: "tcp" },
      { name: "destination_port", label: "Port destination", type: "number", placeholder: "443" },
      { name: "packets", label: "Paquets", type: "number", required: true, placeholder: "10" },
      { name: "bytes", label: "Octets", type: "number", required: true, placeholder: "2048" },
      { name: "first_seen", label: "Premier événement", required: true, placeholder: "2026-07-10T12:00:00Z" },
      { name: "last_seen", label: "Dernier événement", required: true, placeholder: "2026-07-10T12:05:00Z" }
    ] },
    { id: "flow-observation-list", label: "Lister les flux observés", method: "GET", path: "/v1/flows/observations", query: [
      { name: "window_start", label: "Début fenêtre", required: true, placeholder: "2026-07-10T00:00:00Z" },
      { name: "window_end", label: "Fin fenêtre", required: true, placeholder: "2026-07-11T00:00:00Z" },
      { name: "source", label: "Source observation", type: "select", options: ["", "netflow", "sflow", "ipfix", "firewall-log", "application-log", "import", "manual"] },
      { name: "limit", label: "Limite", type: "number", defaultValue: "100" },
      { name: "cursor", label: "Curseur" }
    ] },
    { id: "flow-matrix", label: "Comparer flux déclarés et observés", method: "GET", path: "/v1/flows/matrix", query: [
      { name: "window_start", label: "Début fenêtre", placeholder: "2026-07-10T00:00:00Z" },
      { name: "window_end", label: "Fin fenêtre", placeholder: "2026-07-11T00:00:00Z" },
      { name: "status", label: "Statut conformité", type: "select", options: ["", "compliant", "denied-observed", "undeclared-observed", "declared-unobserved"] },
      { name: "source", label: "Source observation", type: "select", options: ["", "netflow", "sflow", "ipfix", "firewall-log", "application-log", "import", "manual"] },
      { name: "limit", label: "Limite", type: "number", defaultValue: "100" },
      { name: "cursor", label: "Curseur" }
    ] }

  ] },
  { id: "dcim", label: "DCIM", icon: "home", description: "Sites, salles, zones, racks, ports, câbles, énergie et localisation terrain.", operations: [
    { id: "dcim-sites", label: "Lister les sites DCIM", method: "GET", path: "/v1/dcim/sites", query: [{ name: "include_retired", label: "Inclure retirés", type: "boolean" }] },
    { id: "dcim-site", label: "Consulter un site DCIM", method: "GET", path: "/v1/dcim/site", query: [{ name: "code", label: "Site", required: true, defaultValue: "PAR1" }] },
    { id: "multisite-grant-upsert", label: "Affecter un accès à un site", method: "POST", path: "/v1/multisite/site-access/grants/upsert", body: [FIELD_SETS.actor, { name: "subject", label: "Identité", required: true, placeholder: "prenom.nom@example.net" }, { name: "site_code", label: "Site", required: true, defaultValue: "PAR1" }, { name: "access_level", label: "Niveau d’accès", type: "select", required: true, options: [{ value: "viewer", label: "Lecture" }, { value: "operator", label: "Opérateur" }, { value: "admin", label: "Administrateur local" }], defaultValue: "viewer" }] },
    { id: "multisite-grant-revoke", label: "Révoquer un accès à un site", method: "POST", path: "/v1/multisite/site-access/grants/revoke", body: [FIELD_SETS.actor, { name: "subject", label: "Identité", required: true }, { name: "site_code", label: "Site", required: true, defaultValue: "PAR1" }] },
    { id: "multisite-grants", label: "Lister les accès par site", method: "GET", path: "/v1/multisite/site-access/grants", query: [{ name: "subject", label: "Identité" }, { name: "site_code", label: "Site" }, { name: "active_only", label: "Accès actifs uniquement", type: "boolean", defaultValue: "true" }, FIELD_SETS.limit, FIELD_SETS.cursor] },
    { id: "multisite-sites", label: "Lister les sites accessibles", method: "GET", path: "/v1/multisite/sites", query: [{ name: "subject", label: "Identité" }, { name: "required_level", label: "Niveau minimal", type: "select", options: ["viewer", "operator", "admin"], defaultValue: "viewer" }] },
    { id: "multisite-report-generate", label: "Générer un rapport multisite", method: "POST", path: "/v1/multisite/reports/generate", body: [FIELD_SETS.actor, { name: "subject", label: "Identité" }, { name: "site_codes", label: "Sites (JSON)", type: "json", defaultValue: "[]" }] },
    { id: "multisite-reports", label: "Lister les rapports multisites", method: "GET", path: "/v1/multisite/reports", query: [FIELD_SETS.limit, FIELD_SETS.cursor] },
    { id: "multisite-report-get", label: "Consulter un rapport multisite", method: "GET", path: "/v1/multisite/reports/get", query: [{ name: "report_id", label: "ID rapport", required: true }] },
    { id: "multisite-dr-plan-configure", label: "Configurer un plan de reprise multisite", method: "POST", path: "/v1/multisite/disaster-recovery/plans/configure", body: [FIELD_SETS.actor, { name: "name", label: "Nom du plan", required: true, placeholder: "Reprise PAR1 vers LON1" }, { name: "primary_site_code", label: "Site primaire", required: true, defaultValue: "PAR1" }, { name: "recovery_site_code", label: "Site de secours", required: true, placeholder: "LON1" }, { name: "replication_mode", label: "Mode de réplication", type: "select", required: true, options: [{ value: "asynchronous", label: "Asynchrone" }, { value: "synchronous", label: "Synchrone" }], defaultValue: "asynchronous" }, { name: "rpo_seconds", label: "RPO (secondes)", type: "number", required: true, defaultValue: "300", min: "1", max: "86400" }, { name: "rto_seconds", label: "RTO (secondes)", type: "number", required: true, defaultValue: "1800", min: "1", max: "604800" }, { name: "max_backup_age_seconds", label: "Âge maximal sauvegarde (secondes)", type: "number", required: true, defaultValue: "86400", min: "60", max: "2592000" }] },
    { id: "multisite-dr-plan-disable", label: "Désactiver un plan de reprise multisite", method: "POST", path: "/v1/multisite/disaster-recovery/plans/disable", body: [FIELD_SETS.actor, { name: "plan_id", label: "ID plan", required: true }] },
    { id: "multisite-dr-plans", label: "Lister les plans de reprise multisites", method: "GET", path: "/v1/multisite/disaster-recovery/plans", query: [{ name: "active_only", label: "Plans actifs uniquement", type: "boolean", defaultValue: "true" }, FIELD_SETS.limit, FIELD_SETS.cursor] },
    { id: "multisite-dr-plan-get", label: "Consulter un plan de reprise multisite", method: "GET", path: "/v1/multisite/disaster-recovery/plans/get", query: [{ name: "plan_id", label: "ID plan", required: true }] },
    { id: "multisite-dr-drill-execute", label: "Enregistrer un exercice de perte du site primaire", method: "POST", path: "/v1/multisite/disaster-recovery/drills/execute", body: [FIELD_SETS.actor, { name: "plan_id", label: "ID plan", required: true }, { name: "replication_lag_seconds", label: "Retard réplication (secondes)", type: "number", required: true, min: "0" }, { name: "backup_age_seconds", label: "Âge sauvegarde (secondes)", type: "number", required: true, min: "0" }, { name: "measured_rto_seconds", label: "RTO mesuré (secondes)", type: "number", required: true, min: "0" }, { name: "restore_verified", label: "Restauration vérifiée", type: "boolean", required: true, defaultValue: "false" }, { name: "recovery_available", label: "Site de secours disponible", type: "boolean", required: true, defaultValue: "false" }, { name: "vip_reachable", label: "DNS/VIP joignable", type: "boolean", required: true, defaultValue: "false" }, { name: "operator_confirmed", label: "Validation opérateur", type: "boolean", required: true, defaultValue: "false" }] },
    { id: "multisite-dr-drills", label: "Lister les exercices de reprise multisites", method: "GET", path: "/v1/multisite/disaster-recovery/drills", query: [{ name: "plan_id", label: "ID plan" }, { name: "status", label: "Statut", type: "select", options: ["", "passed", "failed"] }, FIELD_SETS.limit, FIELD_SETS.cursor] },
    { id: "multisite-dr-drill-get", label: "Consulter un exercice de reprise multisite", method: "GET", path: "/v1/multisite/disaster-recovery/drills/get", query: [{ name: "drill_id", label: "ID exercice", required: true }] },
    { id: "multisite-route-configure", label: "Configurer une route Discovery régionale", method: "POST", path: "/v1/multisite/regional-discovery/routes/configure", body: [FIELD_SETS.actor, { name: "region_code", label: "Région", required: true, placeholder: "EU-WEST" }, { name: "site_code", label: "Site", required: true, defaultValue: "PAR1" }, { name: "vrf_code", label: "VRF", required: true, placeholder: "PROD" }, { name: "collector_id", label: "ID agent régional", required: true }] },
    { id: "multisite-route-disable", label: "Désactiver une route Discovery régionale", method: "POST", path: "/v1/multisite/regional-discovery/routes/disable", body: [FIELD_SETS.actor, { name: "route_id", label: "ID route", required: true }] },
    { id: "multisite-routes", label: "Lister les routes Discovery régionales", method: "GET", path: "/v1/multisite/regional-discovery/routes", query: [{ name: "region_code", label: "Région" }, { name: "site_code", label: "Site" }, { name: "active_only", label: "Routes actives uniquement", type: "boolean", defaultValue: "true" }, FIELD_SETS.limit, FIELD_SETS.cursor] },
    { id: "multisite-route-get", label: "Consulter une route Discovery régionale", method: "GET", path: "/v1/multisite/regional-discovery/routes/get", query: [{ name: "route_id", label: "ID route", required: true }] },
    { id: "multisite-job-route", label: "Router un job Discovery régional", method: "POST", path: "/v1/multisite/regional-discovery/jobs/route", body: [FIELD_SETS.actor, { name: "region_code", label: "Région", required: true, placeholder: "EU-WEST" }, { name: "site_code", label: "Site", required: true, defaultValue: "PAR1" }, { name: "vrf_code", label: "VRF", required: true, placeholder: "PROD" }, { name: "job_type", label: "Type de job", required: true, placeholder: "network-inventory" }, { name: "target", label: "Cible", required: true, placeholder: "10.20.0.0/24" }, { name: "idempotency_key", label: "Clé d’idempotence", required: true }, { name: "max_attempts", label: "Tentatives maximales", type: "number", defaultValue: "3", min: "1", max: "10" }] },
    { id: "dcim-site-create", label: "Créer un site DCIM", method: "POST", path: "/v1/dcim/site/create", body: [FIELD_SETS.actor, { name: "code", label: "Code site", required: true, placeholder: "PAR1" }, { name: "name", label: "Nom site", required: true, placeholder: "Paris 1" }, { name: "country", label: "Pays", type: "country-select", required: true }, { name: "region", label: "Région", placeholder: "Île-de-France" }, { name: "city", label: "Ville", required: true, placeholder: "Paris" }, { name: "street_address", label: "Rue", required: true, placeholder: "111 Quai du Président Roosevelt" }, { name: "postal_code", label: "Code postal", required: true, placeholder: "92130" }, { name: "contact_email", label: "Email", required: true, placeholder: "site-par1@example.net" }, { name: "phone", label: "Téléphone", required: true, placeholder: "+33123456789" }] },
    { id: "dcim-site-update", label: "Modifier un site DCIM", method: "POST", path: "/v1/dcim/site/update", body: [FIELD_SETS.actor, { name: "code", label: "Site", required: true, defaultValue: "PAR1" }, { name: "name", label: "Nom site", placeholder: "Paris 1" }, { name: "country", label: "Pays", type: "country-select" }, { name: "region", label: "Région", placeholder: "Île-de-France" }, { name: "city", label: "Ville", placeholder: "Paris" }, { name: "street_address", label: "Rue", placeholder: "111 Quai du Président Roosevelt" }, { name: "postal_code", label: "Code postal", placeholder: "92130" }, { name: "contact_email", label: "Email", placeholder: "site-par1@example.net" }, { name: "phone", label: "Téléphone", placeholder: "+33123456789" }, { name: "status", label: "Statut", type: "select", options: ["", "active", "suspended", "retired"] }] },
    { id: "dcim-site-delete", label: "Retirer un site DCIM", method: "POST", path: "/v1/dcim/site/delete", body: [FIELD_SETS.actor, { name: "code", label: "Site", required: true, defaultValue: "PAR1" }] },
    { id: "dcim-buildings", label: "Lister les bâtiments", method: "GET", path: "/v1/dcim/buildings", query: [{ name: "site", label: "Site", required: true }, { name: "include_retired", label: "Inclure retirés", type: "boolean" }] },
    { id: "dcim-building", label: "Consulter un bâtiment", method: "GET", path: "/v1/dcim/building", query: [{ name: "site", label: "Site", required: true }, { name: "code", label: "Code bâtiment", required: true, placeholder: "BAT-A" }] },
    { id: "dcim-building-create", label: "Créer un bâtiment", method: "POST", path: "/v1/dcim/building/create", body: [FIELD_SETS.actor, { name: "site", label: "Site", required: true }, { name: "code", label: "Code bâtiment", required: true, placeholder: "BAT-A" }, { name: "name", label: "Nom bâtiment", required: true, placeholder: "Bâtiment A" }, { name: "building_type", label: "Type Batiment", type: "select", required: true, options: [{ value: "floors", label: "Etages" }, { value: "simple", label: "Simple" }], defaultValue: "simple" }, { name: "initial_level", label: "Niveau Initial", type: "number", required: true, defaultValue: "0", min: "-20", max: "0", step: "1", visibleWhen: { field: "building_type", value: "floors" } }, { name: "final_level", label: "Niveau Final", type: "number", required: true, defaultValue: "1", min: "1", max: "150", step: "1", visibleWhen: { field: "building_type", value: "floors" } }] },
    { id: "dcim-building-update", label: "Modifier un bâtiment", method: "POST", path: "/v1/dcim/building/update", body: [FIELD_SETS.actor, { name: "site", label: "Site", required: true }, { name: "code", label: "Code bâtiment", required: true, placeholder: "BAT-A" }, { name: "name", label: "Nom bâtiment", placeholder: "Bâtiment A" }, { name: "status", label: "Statut", type: "select", options: ["", "active", "suspended", "retired"] }] },
    { id: "dcim-building-delete", label: "Retirer un bâtiment", method: "POST", path: "/v1/dcim/building/delete", body: [FIELD_SETS.actor, { name: "site", label: "Site", required: true }, { name: "code", label: "Code bâtiment", required: true, placeholder: "BAT-A" }] },
    { id: "dcim-floors", label: "Lister les étages", method: "GET", path: "/v1/dcim/floors", query: [{ name: "site", label: "Site", required: true }, { name: "building", label: "Bâtiment", required: true }, { name: "include_retired", label: "Inclure retirés", type: "boolean" }] },
    { id: "dcim-floor", label: "Consulter un étage", method: "GET", path: "/v1/dcim/floor", query: [{ name: "site", label: "Site", required: true }, { name: "building", label: "Bâtiment", required: true }, { name: "code", label: "Étage", required: true, placeholder: "L01" }] },
    { id: "dcim-rooms-list", label: "Lister les salles", method: "GET", path: "/v1/dcim/rooms", query: [{ name: "site", label: "Site", required: true }, { name: "building", label: "Bâtiment", required: true }, { name: "include_retired", label: "Inclure retirés", type: "boolean" }] },
    { id: "dcim-room", label: "Consulter une salle", method: "GET", path: "/v1/dcim/room", query: [{ name: "site", label: "Site", required: true }, { name: "building", label: "Bâtiment", required: true }, { name: "code", label: "Code salle", required: true, placeholder: "MMR1" }] },
    { id: "dcim-room-create", label: "Créer une salle", method: "POST", path: "/v1/dcim/room/create", body: [FIELD_SETS.actor, { name: "site", label: "Site", required: true }, { name: "building", label: "Bâtiment", required: true }, { name: "floor", label: "Étage", placeholder: "Obligatoire si Type Batiment = Etages" }, { name: "code", label: "Code salle", required: true, placeholder: "MMR1" }, { name: "name", label: "Nom salle", required: true, placeholder: "Meet-Me Room" }, { name: "rows", label: "Plage lignes salle", type: "csv", required: true, placeholder: "0-12" }, { name: "columns", label: "Plage colonnes salle", type: "csv", required: true, placeholder: "A-F" }] },
    { id: "dcim-define-room", label: "Créer une hiérarchie physique", method: "POST", path: "/v1/dcim/rooms", body: [FIELD_SETS.actor, { name: "site_code", label: "Code site", required: true, placeholder: "PAR1" }, { name: "site_name", label: "Nom site", required: true, placeholder: "Paris 1" }, { name: "country", label: "Pays", type: "country-select", required: true }, { name: "region", label: "Région", placeholder: "Île-de-France" }, { name: "city", label: "Ville", required: true, placeholder: "Paris" }, { name: "building_code", label: "Code bâtiment", required: true, placeholder: "BAT-A" }, { name: "building_name", label: "Nom bâtiment", required: true, placeholder: "Bâtiment A" }, { name: "floor_index", label: "Niveau", type: "number", required: true, defaultValue: "1", min: "-20", max: "150", step: "1" }, { name: "room_code", label: "Code salle", required: true, placeholder: "MMR1" }, { name: "room_name", label: "Nom salle", required: true, placeholder: "Meet-Me Room" }, { name: "rows", label: "Plage lignes salle", type: "csv", required: true, placeholder: "0-12" }, { name: "columns", label: "Plage colonnes salle", type: "csv", required: true, placeholder: "A-F" }, { name: "zone_code", label: "Code zone", placeholder: "Z1" }, { name: "zone_name", label: "Nom zone", placeholder: "Zone froide 1" }, { name: "zone_rows", label: "Lignes zone", type: "csv", placeholder: "A" }, { name: "zone_columns", label: "Colonnes zone", type: "csv", placeholder: "01" }] },
    { id: "dcim-room-update", label: "Modifier une salle", method: "POST", path: "/v1/dcim/room/update", body: [FIELD_SETS.actor, { name: "site", label: "Site", required: true }, { name: "building", label: "Bâtiment", required: true }, { name: "code", label: "Code salle", required: true, placeholder: "MMR1" }, { name: "name", label: "Nom salle", placeholder: "Meet-Me Room" }, { name: "rows", label: "Plage lignes salle", type: "csv", placeholder: "0-12" }, { name: "columns", label: "Plage colonnes salle", type: "csv", placeholder: "A-F" }, { name: "status", label: "Statut", type: "select", options: ["", "active", "suspended", "retired"] }] },
    { id: "dcim-room-delete", label: "Retirer une salle", method: "POST", path: "/v1/dcim/room/delete", body: [FIELD_SETS.actor, { name: "site", label: "Site", required: true }, { name: "building", label: "Bâtiment", required: true }, { name: "code", label: "Code salle", required: true, placeholder: "MMR1" }] },
    { id: "dcim-racks", label: "Lister les chassis/racks", method: "GET", path: "/v1/dcim/racks", query: [{ name: "site", label: "Site", required: true }, { name: "building", label: "Bâtiment", required: true }, { name: "room", label: "Salle", required: true }, { name: "include_retired", label: "Inclure retirés", type: "boolean" }] },
    { id: "dcim-rack", label: "Consulter un chassis/rack", method: "GET", path: "/v1/dcim/rack", query: [{ name: "site", label: "Site", required: true }, { name: "building", label: "Bâtiment", required: true }, { name: "room", label: "Salle", required: true }, { name: "rack", label: "Chassis/Rack", required: true, placeholder: "R01" }] },
    { id: "dcim-rack-create", label: "Créer un chassis/rack", method: "POST", path: "/v1/dcim/racks", body: [FIELD_SETS.actor, { name: "site", label: "Site", required: true }, { name: "building", label: "Bâtiment", required: true }, { name: "floor", label: "Étage" }, { name: "room", label: "Salle", required: true }, { name: "rack", label: "Code chassis/rack", required: true, placeholder: "R01" }, { name: "row", label: "Ligne salle", required: true }, { name: "column", label: "Colonne salle", required: true }, { name: "units", label: "Capacité U", type: "number", required: true, defaultValue: "42" }, { name: "usable_faces", label: "Faces utilisables", type: "csv", defaultValue: "front", placeholder: "front,rear" }, { name: "max_weight_kg", label: "Poids max kg", type: "number" }, { name: "power_capacity_watts", label: "Puissance max watts", type: "number" }] },
    { id: "dcim-rack-update", label: "Modifier un chassis/rack", method: "POST", path: "/v1/dcim/rack/update", body: [FIELD_SETS.actor, { name: "site", label: "Site", required: true }, { name: "building", label: "Bâtiment", required: true }, { name: "room", label: "Salle", required: true }, { name: "rack", label: "Chassis/Rack", required: true }, { name: "row", label: "Ligne salle" }, { name: "column", label: "Colonne salle" }, { name: "units", label: "Capacité U", type: "number" }, { name: "usable_faces", label: "Faces utilisables", type: "csv" }, { name: "max_weight_kg", label: "Poids max kg", type: "number" }, { name: "power_capacity_watts", label: "Puissance max watts", type: "number" }, { name: "status", label: "Statut", type: "select", options: ["", "active", "suspended", "retired"] }] },
    { id: "dcim-rack-delete", label: "Retirer un chassis/rack", method: "POST", path: "/v1/dcim/rack/delete", body: [FIELD_SETS.actor, { name: "site", label: "Site", required: true }, { name: "building", label: "Bâtiment", required: true }, { name: "room", label: "Salle", required: true }, { name: "rack", label: "Chassis/Rack", required: true }] },
    { id: "dcim-zones", label: "Lister les zones", method: "GET", path: "/v1/dcim/zones", query: [{ name: "site", label: "Site", required: true }, { name: "building", label: "Bâtiment", required: true }, { name: "room", label: "Salle", required: true }, { name: "include_retired", label: "Inclure retirés", type: "boolean" }] },
    { id: "dcim-zone", label: "Consulter une zone", method: "GET", path: "/v1/dcim/zone", query: [{ name: "site", label: "Site", required: true }, { name: "building", label: "Bâtiment", required: true }, { name: "room", label: "Salle", required: true }, { name: "code", label: "Code zone", required: true, placeholder: "Z1" }] },
    { id: "dcim-zone-create", label: "Créer une zone", method: "POST", path: "/v1/dcim/zone/create", body: [FIELD_SETS.actor, { name: "site", label: "Site", required: true }, { name: "building", label: "Bâtiment", required: true }, { name: "room", label: "Salle", required: true }, { name: "code", label: "Code zone", required: true, placeholder: "Z1" }, { name: "name", label: "Nom zone", required: true, placeholder: "Zone froide 1" }, { name: "rows", label: "Lignes zone", type: "csv", required: true, placeholder: "A" }, { name: "columns", label: "Colonnes zone", type: "csv", required: true, placeholder: "01" }] },
    { id: "dcim-zone-update", label: "Modifier une zone", method: "POST", path: "/v1/dcim/zone/update", body: [FIELD_SETS.actor, { name: "site", label: "Site", required: true }, { name: "building", label: "Bâtiment", required: true }, { name: "room", label: "Salle", required: true }, { name: "code", label: "Code zone", required: true, placeholder: "Z1" }, { name: "name", label: "Nom zone", placeholder: "Zone froide 1" }, { name: "rows", label: "Lignes zone", type: "csv", placeholder: "A" }, { name: "columns", label: "Colonnes zone", type: "csv", placeholder: "01" }, { name: "status", label: "Statut", type: "select", options: ["", "active", "suspended", "retired"] }] },
    { id: "dcim-zone-delete", label: "Retirer une zone", method: "POST", path: "/v1/dcim/zone/delete", body: [FIELD_SETS.actor, { name: "site", label: "Site", required: true }, { name: "building", label: "Bâtiment", required: true }, { name: "room", label: "Salle", required: true }, { name: "code", label: "Code zone", required: true, placeholder: "Z1" }] },
    { id: "dcim-topology-catalog", label: "Catalogue dépendances DCIM", method: "GET", path: "/v1/dcim/topology-catalog", query: [{ name: "include_retired", label: "Inclure retirés", type: "boolean" }] },
    { id: "dcim-locate-equipment", label: "Localiser un équipement", method: "POST", path: "/v1/dcim/locations", body: [
      FIELD_SETS.actor,
      { name: "asset_tag", label: "Numéro d’actif", required: true, placeholder: "PAR-SRV-001" },
      { name: "equipment_name", label: "Nom équipement", required: true, placeholder: "srv-app-01" },
      { name: "site", label: "Site", required: true, placeholder: "PAR1" },
      { name: "building", label: "Bâtiment", required: true, placeholder: "BAT-A" },
      { name: "floor", label: "Étage", placeholder: "L01" },
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
    { id: "field-sheet-list", label: "Lister les fiches d’intervention", method: "GET", path: "/v1/field-operation-sheets", query: [{ name: "status", label: "Statut", type: "select", options: ["ready", "in-progress", "completed", "cancelled"] }, { name: "target_type", label: "Type de cible", type: "select", options: ["equipment", "rack", "cable", "power-device", "certificate"] }, { name: "site", label: "Site" }, { name: "limit", label: "Limite", type: "number", defaultValue: "100", min: 1, max: 500 }, { name: "cursor", label: "Curseur" }] },
    { id: "field-sheet-get", label: "Consulter une fiche d’intervention", method: "GET", path: "/v1/field-operation-sheets/get", query: [{ name: "sheet_id", label: "ID fiche", required: true }] },
    { id: "field-sheet-generate", label: "Générer une fiche d’intervention", method: "POST", path: "/v1/field-operation-sheets/generate", body: [FIELD_SETS.actor, { name: "target_type", label: "Type de cible", type: "select", options: ["equipment", "rack", "cable", "power-device", "certificate"], required: true }, { name: "target_id", label: "Identifiant cible", required: true }, { name: "title", label: "Titre", required: true }, { name: "purpose", label: "Objet de l’intervention", type: "textarea", rows: 4, required: true }, { name: "owner", label: "Responsable", required: true }, { name: "operator", label: "Intervenant", required: true }, { name: "source_object_key", label: "Clé objet RSOT" }, { name: "site", label: "Site" }, { name: "building", label: "Bâtiment" }, { name: "room", label: "Salle" }, { name: "location_target_type", label: "Type de cible physique", type: "select", options: ["equipment", "rack", "cable", "power-device"] }, { name: "location_target_id", label: "Identifiant cible physique" }] },
    { id: "field-lock-acquire", label: "Verrouiller la cible", method: "POST", path: "/v1/intervention-locks/acquire", body: [FIELD_SETS.actor, { name: "sheet_id", label: "ID fiche", required: true }, { name: "idempotency_key", label: "Clé d’idempotence", required: true }, { name: "ttl_seconds", label: "Durée du verrou (secondes)", type: "number", defaultValue: "3600", min: 60, max: 86400 }] },
    { id: "field-operation-start", label: "Démarrer l’intervention", method: "POST", path: "/v1/field-operation-sheets/start", body: [FIELD_SETS.actor, { name: "sheet_id", label: "ID fiche", required: true }] },
    { id: "field-checklist-record", label: "Renseigner une étape de checklist", method: "POST", path: "/v1/field-operation-sheets/checklist", body: [FIELD_SETS.actor, { name: "sheet_id", label: "ID fiche", required: true }, { name: "item_id", label: "ID étape", required: true }, { name: "result", label: "Résultat", type: "select", options: ["passed", "failed", "not-applicable"], required: true }, { name: "operator_note", label: "Note intervenant", type: "textarea", rows: 3 }] },
    { id: "field-evidence-attach", label: "Joindre une preuve terrain", method: "POST", path: "/v1/field-evidence/attach", body: [FIELD_SETS.actor, { name: "sheet_id", label: "ID fiche", required: true }, { name: "phase", label: "Phase", type: "select", options: ["before", "after"], required: true }, { name: "evidence_file", label: "Photo ou document", type: "file", accept: "image/jpeg,image/png,image/webp,application/pdf", capture: "environment", required: true }, { name: "caption", label: "Description de la preuve", type: "textarea", rows: 3, required: true }] },
    { id: "field-evidence-list", label: "Lister les preuves terrain", method: "GET", path: "/v1/field-evidence", query: [{ name: "sheet_id", label: "ID fiche", required: true }] },
    { id: "field-evidence-validate", label: "Valider une preuve terrain", method: "POST", path: "/v1/field-evidence/validate", body: [FIELD_SETS.actor, { name: "evidence_id", label: "ID preuve", required: true }] },
    { id: "field-operation-complete", label: "Clôturer l’intervention", method: "POST", path: "/v1/field-operation-sheets/complete", body: [FIELD_SETS.actor, { name: "sheet_id", label: "ID fiche", required: true }] },
    { id: "field-operation-cancel", label: "Annuler l’intervention", method: "POST", path: "/v1/field-operation-sheets/cancel", body: [FIELD_SETS.actor, { name: "sheet_id", label: "ID fiche", required: true }] },
    { id: "field-qr-verify", label: "Vérifier un QR code terrain", method: "POST", path: "/v1/qr-codes/verify", body: [{ name: "sheet_id", label: "ID fiche", required: true }, { name: "payload", label: "Contenu QR", type: "textarea", rows: 4, required: true }] },
    { id: "field-lock-release", label: "Libérer le verrou terrain", method: "POST", path: "/v1/intervention-locks/release", body: [FIELD_SETS.actor, { name: "lock_id", label: "ID verrou", required: true }] },
    { id: "field-offline-create", label: "Créer un paquet hors ligne", method: "POST", path: "/v1/offline-sync-packages/create", body: [FIELD_SETS.actor, { name: "sheet_id", label: "ID fiche", required: true }, { name: "idempotency_key", label: "Clé d’idempotence", required: true }, { name: "ttl_seconds", label: "Validité hors ligne (secondes)", type: "number", defaultValue: "86400", min: 300, max: 604800 }] },
    { id: "field-offline-list", label: "Lister les paquets hors ligne", method: "GET", path: "/v1/offline-sync-packages", query: [{ name: "sheet_id", label: "ID fiche" }, { name: "limit", label: "Limite", type: "number", defaultValue: "100", min: 1, max: 500 }, { name: "cursor", label: "Curseur" }] },
    { id: "field-offline-get", label: "Consulter un paquet hors ligne", method: "GET", path: "/v1/offline-sync-packages/get", query: [{ name: "package_id", label: "ID paquet", required: true }, { name: "include_payload", label: "Inclure le contenu", type: "boolean", defaultValue: "true" }] },
    { id: "field-offline-sync", label: "Synchroniser un paquet hors ligne", method: "POST", path: "/v1/offline-sync-packages/synchronize", body: [FIELD_SETS.actor, { name: "package_id", label: "ID paquet", required: true }, { name: "payload_sha256", label: "Empreinte SHA-256 du paquet", required: true, maxLength: 64 }] },
    { id: "greenops-source-create", label: "Enregistrer une source de mesure", method: "POST", path: "/v1/greenops/measurement-sources/create", body: [
      FIELD_SETS.actor, { name: "code", label: "Code source", required: true }, { name: "name", label: "Nom source", required: true },
      { name: "source_type", label: "Type de source", required: true }, { name: "owner", label: "Responsable", required: true },
      { name: "active", label: "Source active", type: "boolean", defaultValue: "true" }
    ] },
    { id: "greenops-sources", label: "Lister les sources de mesure", method: "GET", path: "/v1/greenops/measurement-sources", query: [
      { name: "active_only", label: "Sources actives uniquement", type: "boolean", defaultValue: "false" }, FIELD_SETS.limit,
      { name: "cursor", label: "Curseur" }
    ] },
    { id: "greenops-policy-upsert", label: "Configurer la politique GreenOps d’un site", method: "POST", path: "/v1/greenops/policies/upsert", body: [
      FIELD_SETS.actor, { name: "site_code", label: "Site", required: true },
      { name: "default_pue", label: "PUE par défaut", type: "number", step: "0.000001", required: true },
      { name: "energy_cost_per_kwh", label: "Coût énergie par kWh", type: "number", step: "0.000001", required: true },
      { name: "currency", label: "Devise ISO-4217", required: true, maxLength: 3 },
      { name: "carbon_factor_code", label: "Code facteur carbone", required: true },
      { name: "underutilized_percent", label: "Seuil de sous-utilisation (%)", type: "number", defaultValue: "20", min: 0, max: 100 },
      { name: "warning_capacity_percent", label: "Seuil capacité avertissement (%)", type: "number", defaultValue: "80", min: 0, max: 100 },
      { name: "critical_capacity_percent", label: "Seuil capacité critique (%)", type: "number", defaultValue: "90", min: 0, max: 100 },
      { name: "minimum_samples", label: "Échantillons minimaux", type: "number", defaultValue: "3", min: 2, max: 1000 }
    ] },
    { id: "greenops-policy-get", label: "Consulter la politique GreenOps", method: "GET", path: "/v1/greenops/policies/get", query: [{ name: "site_code", label: "Site", required: true }] },
    { id: "greenops-factor-create", label: "Enregistrer un facteur carbone", method: "POST", path: "/v1/greenops/carbon-factors/create", body: [
      FIELD_SETS.actor, { name: "code", label: "Code facteur", required: true }, { name: "region", label: "Région", required: true },
      { name: "grams_co2e_per_kwh", label: "gCO₂e par kWh", type: "number", step: "0.000001", required: true },
      { name: "source_name", label: "Source du facteur", required: true }, { name: "source_uri", label: "URL de provenance", type: "url" },
      { name: "period_start", label: "Début de validité", type: "date", required: true }, { name: "period_end", label: "Fin de validité", type: "date", required: true }
    ] },
    { id: "greenops-factors", label: "Lister les facteurs carbone", method: "GET", path: "/v1/greenops/carbon-factors", query: [
      { name: "code", label: "Code facteur" }, { name: "region", label: "Région" }, FIELD_SETS.limit, { name: "cursor", label: "Curseur" }
    ] },
    { id: "greenops-measurement-ingest", label: "Ingérer une mesure énergétique", method: "POST", path: "/v1/greenops/energy-measurements/ingest", body: [
      FIELD_SETS.actor, { name: "idempotency_key", label: "Clé d’idempotence", required: true },
      { name: "source_code", label: "Code source", required: true }, { name: "kind", label: "Nature de la mesure", type: "select", options: ["observed", "estimated"], required: true },
      { name: "scope", label: "Périmètre", type: "select", options: ["site", "room", "rack", "pdu", "asset", "application"], required: true },
      { name: "scope_key", label: "Identifiant du périmètre", required: true }, { name: "site_code", label: "Site", required: true },
      { name: "application_key", label: "Application associée" },
      { name: "period_start", label: "Début de mesure", type: "datetime-local", required: true }, { name: "period_end", label: "Fin de mesure", type: "datetime-local", required: true },
      { name: "energy_kwh", label: "Énergie (kWh)", type: "number", step: "0.000001", required: true },
      { name: "it_energy_kwh", label: "Énergie IT (kWh)", type: "number", step: "0.000001" }, { name: "facility_energy_kwh", label: "Énergie totale site (kWh)", type: "number", step: "0.000001" },
      { name: "utilization_percent", label: "Utilisation (%)", type: "number", min: 0, max: 100, step: "0.0001" },
      { name: "energy_capacity_percent", label: "Capacité énergie utilisée (%)", type: "number", min: 0, max: 100, step: "0.0001" },
      { name: "cooling_capacity_percent", label: "Capacité refroidissement utilisée (%)", type: "number", min: 0, max: 100, step: "0.0001" },
      { name: "space_capacity_percent", label: "Capacité espace utilisée (%)", type: "number", min: 0, max: 100, step: "0.0001" },
      { name: "weight_capacity_percent", label: "Capacité poids utilisée (%)", type: "number", min: 0, max: 100, step: "0.0001" },
      { name: "metadata", label: "Métadonnées JSON sans secret", type: "json", defaultValue: "{}" }
    ] },
    { id: "greenops-measurements", label: "Lister les mesures énergétiques", method: "GET", path: "/v1/greenops/energy-measurements", query: [
      { name: "period_start", label: "Début de période", type: "datetime-local" }, { name: "period_end", label: "Fin de période", type: "datetime-local" },
      { name: "site_code", label: "Site" }, { name: "scope", label: "Périmètre", type: "select", options: ["site", "room", "rack", "pdu", "asset", "application"] },
      { name: "scope_key", label: "Identifiant du périmètre" }, { name: "kind", label: "Nature", type: "select", options: ["observed", "estimated"] },
      FIELD_SETS.limit, { name: "cursor", label: "Curseur" }
    ] },
    { id: "greenops-report-generate", label: "Générer un rapport de durabilité", method: "POST", path: "/v1/greenops/reports/generate", body: [
      FIELD_SETS.actor, { name: "site_code", label: "Site", required: true },
      { name: "period_start", label: "Début de période", type: "date", required: true }, { name: "period_end", label: "Fin de période", type: "date", required: true },
      { name: "scope", label: "Périmètre", type: "select", options: ["site", "room", "rack", "pdu", "asset", "application"], defaultValue: "site" },
      { name: "scope_key", label: "Identifiant du périmètre" }
    ] },
    { id: "greenops-report-get", label: "Consulter un rapport de durabilité", method: "GET", path: "/v1/greenops/reports/get", query: [{ name: "report_id", label: "ID rapport", required: true }] },
    { id: "greenops-reports", label: "Lister les rapports de durabilité", method: "GET", path: "/v1/greenops/reports", query: [
      { name: "site_code", label: "Site" }, { name: "scope", label: "Périmètre" }, FIELD_SETS.limit, { name: "cursor", label: "Curseur" }
    ] },
    { id: "greenops-report-export", label: "Exporter un rapport de durabilité", method: "GET", path: "/v1/greenops/reports/export", download: true, downloadFilename: "openinfra-greenops-report.json", query: [
      { name: "report_id", label: "ID rapport", required: true }, { name: "format", label: "Format", type: "select", options: ["json", "csv"], defaultValue: "json" }
    ] },
    { id: "greenops-anomalies", label: "Lister les anomalies énergétiques", method: "GET", path: "/v1/greenops/anomalies", query: [
      { name: "site_code", label: "Site" }, { name: "severity", label: "Sévérité", type: "select", options: ["info", "warning", "error", "critical"] },
      FIELD_SETS.limit, { name: "cursor", label: "Curseur" }
    ] },
    { id: "greenops-forecasts", label: "Lister les prévisions de capacité", method: "GET", path: "/v1/greenops/capacity-forecasts", query: [
      { name: "site_code", label: "Site" }, { name: "dimension", label: "Dimension", type: "select", options: ["energy", "cooling", "space", "weight"] },
      FIELD_SETS.limit, { name: "cursor", label: "Curseur" }
    ] },
    { id: "greenops-candidates", label: "Lister les recommandations de consolidation", method: "GET", path: "/v1/greenops/consolidation-candidates", query: [
      { name: "site_code", label: "Site" }, { name: "risk_level", label: "Niveau de risque", type: "select", options: ["info", "warning", "error", "critical"] },
      FIELD_SETS.limit, { name: "cursor", label: "Curseur" }
    ] },
    { id: "greenops-scores", label: "Lister les scores GreenOps", method: "GET", path: "/v1/greenops/green-scores", query: [
      { name: "scope", label: "Périmètre" }, FIELD_SETS.limit, { name: "cursor", label: "Curseur" }
    ] },
    { id: "dcim-digital-twin", label: "Jumeau numérique salle", method: "GET", path: "/v1/dcim/digital-twin", query: [{ name: "site", label: "Site", required: true, placeholder: "PAR1" }, { name: "building", label: "Bâtiment", required: true, placeholder: "BAT-A" }, { name: "room", label: "Salle", required: true, placeholder: "MMR1" }] },
    { id: "dcim-energy-cooling-capacity", label: "Capacité énergie/refroidissement", method: "GET", path: "/v1/dcim/energy-cooling-capacity", query: [{ name: "site", label: "Site", required: true, placeholder: "PAR1" }, { name: "building", label: "Bâtiment", required: true, placeholder: "BAT-A" }, { name: "room", label: "Salle", required: true, placeholder: "MMR1" }, { name: "rack", label: "Rack", required: true, placeholder: "R01" }] }
  ] },
  { id: "itam", label: "IT Asset Management", shortLabel: "ITAM", icon: "asset", description: "Inventaire financier et opérationnel des actifs, garanties constructeur, supports tiers et couverture renouvellement.", operations: [
    { id: "itam-organizations", label: "Lister les organisations", method: "GET", path: "/v1/itam/organizations", query: [{ name: "include_retired", label: "Inclure retirées", type: "boolean" }] },
    { id: "itam-organization", label: "Voir une organisation", method: "GET", path: "/v1/itam/organization", query: [{ name: "organization_id", label: "Organisation", type: "organization-select", required: true }] },
    { id: "itam-organization-create", label: "Créer une organisation", method: "POST", path: "/v1/itam/organization/create", body: [{ name: "organization_id", label: "Code organisation", required: true, placeholder: "orange" }, FIELD_SETS.actor, { name: "legal_name", label: "Raison sociale", required: true, placeholder: "Orange SA" }, { name: "display_name", label: "Nom d’usage", placeholder: "Orange" }, { name: "registration_number", label: "N° immatriculation", required: true, placeholder: "RCS Paris ..." }, { name: "tax_identifier", label: "Identifiant fiscal / TVA", required: true, placeholder: "FR..." }, { name: "country_code", label: "Pays", type: "country-select", required: true }, { name: "city", label: "Ville", required: true, placeholder: "Paris" }, { name: "postal_code", label: "Code postal", required: true, placeholder: "92130" }, { name: "address", label: "Adresse siège", required: true, placeholder: "111 Quai du Président Roosevelt" }, { name: "contact_email", label: "Email", required: true, placeholder: "contact@orange.com" }, { name: "phone", label: "Téléphone", required: true, placeholder: "+33123456789" }, { name: "support_contact", label: "Contact support", required: true, placeholder: "support@orange.com" }, { name: "status", label: "Statut", type: "select", options: ["active", "suspended", "retired"], defaultValue: "active" }, { name: "description", label: "Description", placeholder: "Carte d’identité entreprise" }] },
    { id: "itam-organization-update", label: "Modifier une organisation", method: "POST", path: "/v1/itam/organization/update", body: [{ name: "organization_id", label: "Organisation", type: "organization-select", required: true }, FIELD_SETS.actor, { name: "legal_name", label: "Raison sociale" }, { name: "display_name", label: "Nom d’usage" }, { name: "registration_number", label: "N° immatriculation" }, { name: "tax_identifier", label: "Identifiant fiscal / TVA" }, { name: "country_code", label: "Pays", type: "country-select" }, { name: "city", label: "Ville" }, { name: "postal_code", label: "Code postal" }, { name: "address", label: "Adresse siège" }, { name: "contact_email", label: "Email" }, { name: "phone", label: "Téléphone" }, { name: "support_contact", label: "Contact support" }, { name: "status", label: "Statut", type: "select", options: ["", "active", "suspended", "retired"] }, { name: "description", label: "Description" }] },
    { id: "itam-organization-delete", label: "Retirer une organisation", method: "POST", path: "/v1/itam/organization/delete", body: [{ name: "organization_id", label: "Organisation", type: "organization-select", required: true }, FIELD_SETS.actor] },
    { id: "itam-partners", label: "Lister les partenaires", method: "GET", path: "/v1/itam/partners", query: [{ name: "organization_id", label: "Organisation", type: "organization-select" }, { name: "kind", label: "Type partenaire", type: "select", options: ["", "manufacturer", "software_publisher", "third_party_support"] }, { name: "include_retired", label: "Inclure retirés", type: "boolean" }] },
    { id: "itam-partner", label: "Voir un partenaire", method: "GET", path: "/v1/itam/partner", query: [{ name: "organization_id", label: "Organisation", type: "organization-select", required: true }, { name: "partner_id", label: "Partenaire", type: "partner-select", required: true }] },
    { id: "itam-partner-create", label: "Créer un partenaire", method: "POST", path: "/v1/itam/partner/create", body: [{ name: "organization_id", label: "Organisation", type: "organization-select", required: true }, { name: "partner_id", label: "Code partenaire", required: true, placeholder: "dell" }, { name: "kind", label: "Type partenaire", type: "select", required: true, options: ["manufacturer", "software_publisher", "third_party_support"], defaultValue: "manufacturer" }, FIELD_SETS.actor, { name: "legal_name", label: "Raison sociale", required: true, placeholder: "Dell SAS" }, { name: "display_name", label: "Nom d’usage", placeholder: "Dell" }, { name: "registration_number", label: "N° immatriculation", required: true }, { name: "tax_identifier", label: "Identifiant fiscal / TVA", required: true }, { name: "country_code", label: "Pays", type: "country-select", required: true }, { name: "city", label: "Ville", required: true }, { name: "postal_code", label: "Code postal", required: true }, { name: "address", label: "Adresse siège", required: true }, { name: "contact_email", label: "Email contact", required: true }, { name: "phone", label: "Téléphone", required: true, placeholder: "+33123456789" }, { name: "support_contact", label: "Contact support", required: true }, { name: "website", label: "Site web", placeholder: "https://example.com" }, { name: "status", label: "Statut", type: "select", options: ["active", "suspended", "retired"], defaultValue: "active" }, { name: "description", label: "Description" }] },
    { id: "itam-partner-update", label: "Modifier un partenaire", method: "POST", path: "/v1/itam/partner/update", body: [{ name: "organization_id", label: "Organisation", type: "organization-select", required: true }, { name: "partner_id", label: "Partenaire", type: "partner-select", required: true }, FIELD_SETS.actor, { name: "kind", label: "Type partenaire", type: "select", options: ["", "manufacturer", "software_publisher", "third_party_support"] }, { name: "legal_name", label: "Raison sociale" }, { name: "display_name", label: "Nom d’usage" }, { name: "registration_number", label: "N° immatriculation" }, { name: "tax_identifier", label: "Identifiant fiscal / TVA" }, { name: "country_code", label: "Pays", type: "country-select" }, { name: "city", label: "Ville" }, { name: "postal_code", label: "Code postal" }, { name: "address", label: "Adresse siège" }, { name: "contact_email", label: "Email contact" }, { name: "phone", label: "Téléphone" }, { name: "support_contact", label: "Contact support" }, { name: "website", label: "Site web" }, { name: "status", label: "Statut", type: "select", options: ["", "active", "suspended", "retired"] }, { name: "description", label: "Description" }] },
    { id: "itam-partner-delete", label: "Retirer un partenaire", method: "POST", path: "/v1/itam/partner/delete", body: [{ name: "organization_id", label: "Organisation", type: "organization-select", required: true }, { name: "partner_id", label: "Partenaire", type: "partner-select", required: true }, FIELD_SETS.actor] },
    { id: "itam-tenants", label: "Lister les filiales/subdivisions", method: "GET", path: "/v1/itam/tenants", query: [{ name: "include_retired", label: "Inclure retirés", type: "boolean" }] },
    { id: "itam-tenant", label: "Voir une filiale/subdivision", method: "GET", path: "/v1/itam/tenant", query: [{ name: "organization_id", label: "Organisation", type: "organization-select", required: true }, { name: "tenant_id", label: "Filiale/Subdivision", type: "tenant-select", required: true }] },
    { id: "itam-tenant-create", label: "Créer une filiale/subdivision", method: "POST", path: "/v1/itam/tenant/create", body: [{ name: "organization_id", label: "Organisation", type: "organization-select", required: true }, { name: "tenant_id", label: "Filiale/Subdivision", required: true, placeholder: "dsi" }, FIELD_SETS.actor, { name: "name", label: "Nom filiale/subdivision", required: true, placeholder: "DSI" }, { name: "status", label: "Statut", type: "select", options: ["active", "suspended", "retired"], defaultValue: "active" }, { name: "is_default", label: "Filiale/Subdivision par défaut", type: "boolean" }, { name: "description", label: "Description", placeholder: "Périmètre interne de la filiale/subdivision" }] },
    { id: "itam-tenant-update", label: "Modifier une filiale/subdivision", method: "POST", path: "/v1/itam/tenant/update", body: [{ name: "organization_id", label: "Organisation", type: "organization-select", required: true }, { name: "tenant_id", label: "Filiale/Subdivision à modifier", type: "tenant-select", required: true }, FIELD_SETS.actor, { name: "name", label: "Nom filiale/subdivision", placeholder: "DSI" }, { name: "status", label: "Statut", type: "select", options: ["", "active", "suspended", "retired"] }, { name: "is_default", label: "Filiale/Subdivision par défaut", type: "boolean" }, { name: "description", label: "Description", placeholder: "Périmètre interne de la filiale/subdivision" }] },
    { id: "itam-tenant-delete", label: "Retirer une filiale/subdivision", method: "POST", path: "/v1/itam/tenant/delete", body: [{ name: "organization_id", label: "Organisation", type: "organization-select", required: true }, { name: "tenant_id", label: "Filiale/Subdivision à retirer", type: "tenant-select", required: true }, FIELD_SETS.actor] },
    { id: "itam-support-profile", label: "Profil support actif", method: "GET", path: "/v1/itam/support-profile", query: [{ name: "asset_tag", label: "Numéro d’actif", required: true, placeholder: "PAR-SRV-001" }] },
    { id: "itam-support-coverage", label: "Couverture support actif", method: "GET", path: "/v1/itam/support-coverage", query: [{ name: "asset_tag", label: "Numéro d’actif", required: true, placeholder: "PAR-SRV-001" }, { name: "as_of", label: "Date de référence", placeholder: "2026-07-07" }] },
    { id: "itam-register-manufacturer", label: "Déclarer garantie constructeur", method: "POST", path: "/v1/itam/support-profile/manufacturer", body: [FIELD_SETS.actor, { name: "asset_tag", label: "Numéro d’actif", required: true, placeholder: "PAR-SRV-001" }, { name: "manufacturer_partner_id", label: "Constructeur accrédité", type: "partner-select", partnerKind: "manufacturer", required: true }, { name: "manufacturer", label: "Constructeur", type: "hidden", defaultValue: "accredited" }, { name: "warranty_reference", label: "Référence garantie", required: true, placeholder: "WR-123" }, { name: "warranty_level", label: "Niveau garantie", required: true, placeholder: "ProSupport" }, { name: "warranty_start", label: "Début garantie", required: true, placeholder: "2026-01-01" }, { name: "warranty_end", label: "Fin garantie", required: true, placeholder: "2029-01-01" }, { name: "support_reference", label: "Référence support", required: true, placeholder: "SUP-123" }, { name: "support_level", label: "Niveau support", required: true, placeholder: "24x7" }, { name: "support_contact", label: "Contact support", required: true, placeholder: "support@example.com" }] },
    { id: "itam-add-third-party", label: "Ajouter support tiers", method: "POST", path: "/v1/itam/support-profile/third-party", body: [FIELD_SETS.actor, { name: "asset_tag", label: "Numéro d’actif", required: true, placeholder: "PAR-SRV-001" }, { name: "provider_partner_id", label: "Support tiers accrédité", type: "partner-select", partnerKind: "third_party_support", required: true }, { name: "provider", label: "Prestataire", type: "hidden", defaultValue: "accredited" }, { name: "contract_reference", label: "Référence contrat", required: true, placeholder: "TP-123" }, { name: "support_level", label: "Niveau support", required: true, placeholder: "8x5" }, { name: "support_start", label: "Début support", required: true, placeholder: "2029-01-02" }, { name: "support_end", label: "Fin support", required: true, placeholder: "2030-01-01" }, { name: "support_contact", label: "Contact support", required: true, placeholder: "n2@example.com" }, { name: "status", label: "Statut", type: "select", options: ["planned", "active", "expired", "terminated"], defaultValue: "active" }, { name: "notes", label: "Notes", placeholder: "Périmètre support" }] },
    { id: "itam-software-license", label: "Licence logicielle", method: "GET", path: "/v1/itam/software-license", query: [{ name: "license_reference", label: "Référence licence", required: true, placeholder: "LIC-OPENINFRA-001" }] },
    { id: "itam-software-compliance", label: "Conformité licence", method: "GET", path: "/v1/itam/software-license/compliance", query: [{ name: "license_reference", label: "Référence licence", required: true, placeholder: "LIC-OPENINFRA-001" }, { name: "as_of", label: "Date de référence", placeholder: "2026-07-08" }] },
    { id: "itam-register-software", label: "Déclarer licence logicielle", method: "POST", path: "/v1/itam/software-license", body: [FIELD_SETS.actor, { name: "product_name", label: "Produit", required: true, placeholder: "PostgreSQL Enterprise Support" }, { name: "vendor_partner_id", label: "Éditeur accrédité", type: "partner-select", partnerKind: "software_publisher", required: true }, { name: "vendor", label: "Éditeur", type: "hidden", defaultValue: "accredited" }, { name: "license_reference", label: "Référence licence", required: true, placeholder: "LIC-OPENINFRA-001" }, { name: "contract_reference", label: "Référence contrat", placeholder: "CTR-SW-001" }, { name: "metric", label: "Métrique", type: "select", required: true, options: ["device", "user", "core", "socket", "instance", "subscription"], defaultValue: "device" }, { name: "purchased_quantity", label: "Quantité achetée", required: true, placeholder: "100" }, { name: "assigned_quantity", label: "Quantité assignée", placeholder: "0" }, { name: "entitlement_start", label: "Début droit", required: true, placeholder: "2026-01-01" }, { name: "entitlement_end", label: "Fin droit", required: true, placeholder: "2027-01-01" }, { name: "version", label: "Version", placeholder: "2026" }, { name: "status", label: "Statut", type: "select", options: ["planned", "active", "expired", "terminated"], defaultValue: "active" }, { name: "owner", label: "Propriétaire", placeholder: "DSI" }, { name: "notes", label: "Notes", placeholder: "Périmètre licence" }] },
    { id: "itam-update-license-assignment", label: "Mettre à jour affectation licence", method: "POST", path: "/v1/itam/software-license/assignment", body: [FIELD_SETS.actor, { name: "license_reference", label: "Référence licence", required: true, placeholder: "LIC-OPENINFRA-001" }, { name: "assigned_quantity", label: "Quantité assignée", required: true, placeholder: "75" }, { name: "notes", label: "Notes", placeholder: "Ajustement inventaire" }] },

    { id: "finops-rule-create", label: "Créer une règle d’allocation", path: "/v1/finops/allocation-rules/create", method: "POST", body: [
      "Opérateur", { name: "name", label: "Nom de la règle", required: true }, { name: "priority", label: "Priorité", type: "number", defaultValue: "100" },
      { name: "dimension", label: "Dimension", type: "select", options: ["asset", "application", "business-service", "tenant", "owner", "tag", "cost-center", "environment", "dependency"], required: true },
      { name: "selector_key", label: "Clé de sélection", required: true }, { name: "fixed_target", label: "Cible fixe" },
      { name: "percentage", label: "Pourcentage", type: "number", required: true }, { name: "category", label: "Catégorie de coût" },
      { name: "source", label: "Source de coût" }, { name: "active", label: "Règle active", type: "boolean", defaultValue: "true" },
    ] },
    { id: "finops-rules", label: "Lister les règles d’allocation", path: "/v1/finops/allocation-rules", method: "GET", query: [
      { name: "active_only", label: "Uniquement actives", type: "boolean" }, { name: "limit", label: "Limite", type: "number", defaultValue: "100" }, { name: "cursor", label: "Curseur" },
    ] },
    { id: "finops-import-submit", label: "Importer des coûts", path: "/v1/finops/import-jobs/submit", method: "POST", body: [
      "Opérateur", { name: "idempotency_key", label: "Clé d’idempotence", required: true }, { name: "source", label: "Source", required: true },
      { name: "records", label: "Enregistrements de coûts JSON", type: "json", required: true, defaultValue: "[]" },
    ] },
    { id: "finops-import-get", label: "Consulter un import de coûts", path: "/v1/finops/import-jobs/get", method: "GET", query: [
      { name: "job_id", label: "ID import", required: true }, { name: "include_records", label: "Inclure les enregistrements", type: "boolean" },
    ] },
    { id: "finops-imports", label: "Lister les imports de coûts", path: "/v1/finops/import-jobs", method: "GET", query: [
      { name: "status", label: "Statut" }, { name: "limit", label: "Limite", type: "number", defaultValue: "100" }, { name: "cursor", label: "Curseur" },
    ] },
    { id: "finops-import-run", label: "Exécuter un import de coûts", path: "/v1/finops/import-jobs/run", method: "POST", body: ["Opérateur", { name: "job_id", label: "ID import", required: true }] },
    { id: "finops-import-cancel", label: "Annuler un import de coûts", path: "/v1/finops/import-jobs/cancel", method: "POST", body: ["Opérateur", { name: "job_id", label: "ID import", required: true }] },
    { id: "finops-costs", label: "Lister les coûts normalisés", path: "/v1/finops/cost-records", method: "GET", query: [
      { name: "period_start", label: "Début de période", type: "date" }, { name: "period_end", label: "Fin de période", type: "date" },
      { name: "currency", label: "Devise ISO-4217" }, { name: "category", label: "Catégorie" }, { name: "source", label: "Source" },
      { name: "quality_status", label: "Qualité d’allocation" }, { name: "limit", label: "Limite", type: "number", defaultValue: "100" }, { name: "cursor", label: "Curseur" },
    ] },
    { id: "finops-budget-upsert", label: "Créer ou modifier un budget", path: "/v1/finops/budgets/upsert", method: "POST", body: [
      "Opérateur", { name: "dimension", label: "Dimension", required: true }, { name: "target", label: "Cible", required: true },
      { name: "period_start", label: "Début de période", type: "date", required: true }, { name: "period_end", label: "Fin de période", type: "date", required: true },
      { name: "currency", label: "Devise ISO-4217", required: true }, { name: "amount", label: "Montant", type: "number", required: true },
      { name: "warning_threshold_percent", label: "Seuil d’alerte (%)", type: "number", required: true }, { name: "owner", label: "Propriétaire", required: true },
    ] },
    { id: "finops-budgets", label: "Lister les budgets", path: "/v1/finops/budgets", method: "GET", query: [
      { name: "dimension", label: "Dimension" }, { name: "target", label: "Cible" }, { name: "currency", label: "Devise" },
      { name: "limit", label: "Limite", type: "number", defaultValue: "100" }, { name: "cursor", label: "Curseur" },
    ] },
    { id: "finops-period-close", label: "Clôturer une période financière", path: "/v1/finops/periods/close", method: "POST", body: [
      "Opérateur", { name: "period_start", label: "Début de période", type: "date", required: true }, { name: "period_end", label: "Fin de période", type: "date", required: true },
      { name: "currency", label: "Devise ISO-4217", required: true },
    ] },
    { id: "finops-periods", label: "Lister les périodes financières", path: "/v1/finops/periods", method: "GET", query: [
      { name: "status", label: "Statut" }, { name: "limit", label: "Limite", type: "number", defaultValue: "100" }, { name: "cursor", label: "Curseur" },
    ] },
    { id: "finops-report-generate", label: "Générer un showback / chargeback", path: "/v1/finops/reports/generate", method: "POST", body: [
      "Opérateur", { name: "kind", label: "Type de rapport", type: "select", options: ["showback", "chargeback"], required: true },
      { name: "period_start", label: "Début de période", type: "date", required: true }, { name: "period_end", label: "Fin de période", type: "date", required: true },
      { name: "group_by", label: "Regroupement", required: true }, { name: "currency", label: "Devise ISO-4217", required: true },
      { name: "chargeback_markup_percent", label: "Marge chargeback (%)", type: "number", defaultValue: "0" },
    ] },
    { id: "finops-report-get", label: "Consulter un rapport financier", path: "/v1/finops/reports/get", method: "GET", query: [
      { name: "report_id", label: "ID rapport", required: true },
    ] },
    { id: "finops-reports", label: "Lister les rapports financiers", path: "/v1/finops/reports", method: "GET", query: [
      { name: "kind", label: "Type de rapport" }, { name: "currency", label: "Devise" }, { name: "limit", label: "Limite", type: "number", defaultValue: "100" }, { name: "cursor", label: "Curseur" },
    ] },
    { id: "finops-report-export", label: "Exporter un rapport financier", path: "/v1/finops/reports/export", method: "GET", query: [
      { name: "report_id", label: "ID rapport", required: true }, { name: "format", label: "Format", type: "select", options: ["json", "csv"], defaultValue: "json" },
    ] },
    { id: "finops-anomalies", label: "Lister les anomalies de coûts", path: "/v1/finops/anomalies", method: "GET", query: [
      { name: "severity", label: "Sévérité" }, { name: "limit", label: "Limite", type: "number", defaultValue: "100" }, { name: "cursor", label: "Curseur" },
    ] },
    { id: "finops-forecasts", label: "Lister les prévisions de coûts", path: "/v1/finops/forecasts", method: "GET", query: [
      { name: "dimension", label: "Dimension" }, { name: "target", label: "Cible" }, { name: "limit", label: "Limite", type: "number", defaultValue: "100" }, { name: "cursor", label: "Curseur" },
    ] },

  ] },
  { id: "discovery", label: "Discovery", icon: "activity", description: "Collecte backend locale en Lite/Pro ; agents proxy collectors Enterprise uniquement en topologie étoile.", operations: [
    { id: "discovery-evidence-list", label: "Lister les preuves immuables", method: "GET", path: "/v1/discovery/evidence-list", query: [{ name: "object_key", label: "Clé objet" }, FIELD_SETS.limit] },
    { id: "discovery-evidence", label: "Voir une preuve immuable", method: "GET", path: "/v1/discovery/evidence", query: [{ name: "evidence_id", label: "ID preuve", required: true }] },
    { id: "discovery-evidence-submit", label: "Enregistrer une preuve Discovery", method: "POST", path: "/v1/discovery/evidence", body: [FIELD_SETS.actor, { name: "evidence_id", label: "ID preuve imposé" }, { name: "object_key", label: "Clé objet", required: true, placeholder: "server/srv-app-01" }, { name: "object_kind", label: "Type objet", required: true, placeholder: "server" }, { name: "source", label: "Source", required: true, type: "select", options: ["snmp", "ssh", "winrm", "vmware", "proxmox", "hyperv", "kubernetes", "aws", "azure", "gcp", "openstack", "cloud", "import", "manual"] }, { name: "source_ref", label: "Référence source", required: true, placeholder: "vcenter-par1" }, { name: "scope", label: "Scope", required: true, placeholder: "site/par1" }, { name: "external_id", label: "ID externe", required: true }, { name: "confidence", label: "Confiance (0 à 1)", required: true, type: "number", defaultValue: "0.9" }, { name: "observed_at", label: "Observé le (ISO-8601)" }, { name: "payload", label: "Preuve JSON sans secret", required: true, type: "json", defaultValue: "{}" }] },
    { id: "discovery-reconciliation-list", label: "Lister les rapprochements", method: "GET", path: "/v1/discovery/reconciliation-list", query: [{ name: "status", label: "Statut", type: "select", options: ["", "ready", "conflict", "resolved"] }, FIELD_SETS.limit] },
    { id: "discovery-reconciliation", label: "Voir un rapprochement", method: "GET", path: "/v1/discovery/reconciliation", query: [{ name: "case_id", label: "ID rapprochement", required: true }] },
    { id: "discovery-reconcile", label: "Rapprocher plusieurs preuves", method: "POST", path: "/v1/discovery/reconciliation", body: [FIELD_SETS.actor, { name: "object_key", label: "Clé objet", required: true }, { name: "evidence_ids", label: "IDs preuves", required: true, type: "csv" }, { name: "max_age_seconds", label: "Âge maximal (secondes)", type: "number", defaultValue: "86400" }] },
    { id: "discovery-reconciliation-resolve", label: "Résoudre les conflits", method: "POST", path: "/v1/discovery/reconciliation/resolve", body: [FIELD_SETS.actor, { name: "case_id", label: "ID rapprochement", required: true }, { name: "selected_evidence_by_path", label: "Sélections par chemin JSON", required: true, type: "json", defaultValue: "{}" }, { name: "justification", label: "Justification", required: true }] },
    { id: "discovery-protocol-profiles", label: "Lister les profils protocoles", method: "GET", path: "/v1/discovery/protocol-profiles", query: [{ name: "include_inactive", label: "Inclure inactifs", type: "boolean" }, FIELD_SETS.limit] },
    { id: "discovery-protocol-profile-create", label: "Créer un profil SNMP/SSH/WinRM", method: "POST", path: "/v1/discovery/protocol-profile/create", body: [FIELD_SETS.actor, { name: "name", label: "Nom profil", required: true, placeholder: "SNMPv3 PAR1 Core" }, { name: "protocol", label: "Protocole", required: true, type: "select", options: ["snmp", "ssh", "winrm"] }, { name: "scope", label: "Scope", required: true, placeholder: "site/par1" }, { name: "credential_secret_ref", label: "Référence secret vault", required: true, placeholder: "vault://openinfra/discovery/snmp/par1" }, { name: "port", label: "Port", type: "number" }, { name: "timeout_seconds", label: "Timeout secondes", type: "number", defaultValue: "30" }, { name: "max_concurrency", label: "Concurrence max", type: "number", defaultValue: "4" }, { name: "rate_limit_per_minute", label: "Rate limit/min", type: "number", defaultValue: "120" }, { name: "retry_count", label: "Tentatives", type: "number", defaultValue: "1" }] },
    { id: "discovery-protocol-profile-update", label: "Modifier un profil protocole", method: "POST", path: "/v1/discovery/protocol-profile/update", body: [{ name: "profile_id", label: "Profil", required: true }, FIELD_SETS.actor, { name: "name", label: "Nom profil" }, { name: "scope", label: "Scope" }, { name: "credential_secret_ref", label: "Référence secret vault" }, { name: "port", label: "Port", type: "number" }, { name: "timeout_seconds", label: "Timeout secondes", type: "number" }, { name: "max_concurrency", label: "Concurrence max", type: "number" }, { name: "rate_limit_per_minute", label: "Rate limit/min", type: "number" }, { name: "retry_count", label: "Tentatives", type: "number" }] },
    { id: "discovery-protocol-profile-delete", label: "Désactiver un profil protocole", method: "POST", path: "/v1/discovery/protocol-profile/delete", body: [{ name: "profile_id", label: "Profil", required: true }, FIELD_SETS.actor, { name: "reason", label: "Motif", required: true, placeholder: "rotation secret" }] },

    { id: "discovery-integration-profiles", label: "Lister profils virtualisation/cloud", method: "GET", path: "/v1/discovery/integration-profiles", query: [{ name: "include_inactive", label: "Inclure inactifs", type: "boolean" }, FIELD_SETS.limit] },
    { id: "discovery-integration-profile-create", label: "Créer profil VMware/Cloud/Kubernetes", method: "POST", path: "/v1/discovery/integration-profile/create", body: [FIELD_SETS.actor, { name: "name", label: "Nom profil", required: true, placeholder: "vCenter PAR1" }, { name: "kind", label: "Type plateforme", required: true, type: "select", options: ["vmware", "proxmox", "hyperv", "kubernetes", "aws", "azure", "gcp", "openstack"] }, { name: "scope", label: "Scope", required: true, placeholder: "site/par1" }, { name: "endpoint_url", label: "Endpoint HTTPS", placeholder: "https://vcenter.example.local" }, { name: "credential_secret_ref", label: "Référence secret vault", required: true, placeholder: "vault://openinfra/discovery/vcenter/par1" }, { name: "verify_tls", label: "Vérifier TLS", type: "boolean", defaultValue: "true" }, { name: "inventory_enabled", label: "Inventaire activé", type: "boolean", defaultValue: "true" }, { name: "max_concurrency", label: "Concurrence max", type: "number", defaultValue: "4" }, { name: "rate_limit_per_minute", label: "Rate limit/min", type: "number", defaultValue: "120" }] },
    { id: "discovery-integration-profile-update", label: "Modifier profil virtualisation/cloud", method: "POST", path: "/v1/discovery/integration-profile/update", body: [{ name: "profile_id", label: "Profil", required: true }, FIELD_SETS.actor, { name: "name", label: "Nom profil" }, { name: "scope", label: "Scope" }, { name: "endpoint_url", label: "Endpoint HTTPS" }, { name: "credential_secret_ref", label: "Référence secret vault" }, { name: "verify_tls", label: "Vérifier TLS", type: "boolean" }, { name: "inventory_enabled", label: "Inventaire activé", type: "boolean" }, { name: "max_concurrency", label: "Concurrence max", type: "number" }, { name: "rate_limit_per_minute", label: "Rate limit/min", type: "number" }] },
    { id: "discovery-integration-profile-delete", label: "Désactiver profil virtualisation/cloud", method: "POST", path: "/v1/discovery/integration-profile/delete", body: [{ name: "profile_id", label: "Profil", required: true }, FIELD_SETS.actor, { name: "reason", label: "Motif", required: true, placeholder: "rotation secret" }] },
    { id: "local-discovery-plan", label: "Plan discovery locale Lite/Pro", method: "POST", path: "/v1/discovery/local-plan", body: [FIELD_SETS.actor, { name: "name", label: "Nom plan", required: true, placeholder: "Discovery locale PAR1" }, { name: "scope", label: "Scope", required: true, placeholder: "site/par1" }, { name: "protocol", label: "Protocole", required: true, type: "select", options: ["snmp", "ssh", "winrm"] }, { name: "targets", label: "Cibles", type: "csv", required: true, placeholder: "10.20.30.20,srv-app-01" }, { name: "credential_secret_ref", label: "Référence secret", required: true, placeholder: "vault://openinfra/discovery/local/par1" }, { name: "protocol_profile_id", label: "Profil protocole" }, { name: "max_concurrency", label: "Concurrence max", type: "number", defaultValue: "4" }, { name: "rate_limit_per_minute", label: "Rate limit/min", type: "number", defaultValue: "120" }] },
    { id: "agent-bootstrap-plan", label: "Plan bootstrap agent Enterprise", method: "POST", path: "/v1/discovery/agent-bootstrap-plan", body: [FIELD_SETS.actor, { name: "name", label: "Nom agent", required: true, placeholder: "Agent Enterprise PAR1" }, { name: "role", label: "Rôle agent", required: true, type: "select", options: ["site", "regional", "datacenter"], defaultValue: "site" }, { name: "scopes", label: "Scopes autorisés", type: "csv", required: true, placeholder: "site/paris,network/core" }, { name: "backend_url", label: "URL backend HTTPS", required: true, placeholder: "https://openinfra-api.example.com" }, { name: "certificate_fingerprint", label: "Empreinte certificat", required: true }, { name: "enrollment_secret_ref", label: "Référence secret enrollment", required: true, placeholder: "vault://openinfra/discovery/agent/par1" }, { name: "agent_version", label: "Version agent", required: true, defaultValue: "0.29.68" }, { name: "service_user", label: "Compte service", defaultValue: "openinfra-agent" }, { name: "config_path", label: "Chemin configuration", defaultValue: "/etc/openinfra/agent.yaml" }, { name: "state_directory", label: "Répertoire état", defaultValue: "/var/lib/openinfra-agent" }, { name: "log_directory", label: "Répertoire logs", defaultValue: "/var/log/openinfra-agent" }] },
    { id: "collectors-list", label: "Lister les agents proxy Enterprise", method: "GET", path: "/v1/discovery/collectors", query: [{ name: "scope", label: "Scope autorisé" }, FIELD_SETS.limit] },
    { id: "collectors-register", label: "Enregistrer un agent proxy Enterprise", method: "POST", path: "/v1/discovery/collectors", body: [FIELD_SETS.actor, { name: "name", label: "Nom agent proxy", required: true }, { name: "kind", label: "Type", required: true, type: "select", options: ["site-proxy", "network-proxy", "datacenter-proxy"] }, { name: "certificate_fingerprint", label: "Empreinte certificat", required: true }, { name: "scopes", label: "Scopes autorisés", type: "csv", required: true, placeholder: "site/paris,network/core" }, { name: "version", label: "Version agent", required: true, defaultValue: "1.0.0" }, { name: "endpoint_url", label: "Endpoint mTLS", required: true, placeholder: "https://collector-paris.openinfra.local" }] },
    { id: "discovery-job-list", label: "Lister les jobs Discovery", method: "GET", path: "/v1/discovery/jobs", query: [{ name: "status", label: "État", type: "select", options: ["", "queued", "leased", "retry-wait", "completed", "dead-letter"] }, FIELD_SETS.limit, { name: "cursor", label: "Curseur" }] },
    { id: "discovery-job", label: "Voir un job Discovery", method: "GET", path: "/v1/discovery/job", query: [{ name: "job_id", label: "ID job", required: true }] },
    { id: "discovery-job-submit", label: "Soumettre un job idempotent", method: "POST", path: "/v1/discovery/jobs", body: [FIELD_SETS.actor, { name: "collector_id", label: "ID agent proxy", required: true }, { name: "requested_scope", label: "Scope demandé", required: true, placeholder: "site/par1" }, { name: "job_type", label: "Type de job", required: true, type: "select", options: ["snmp", "ssh", "winrm", "vmware", "proxmox", "hyperv", "kubernetes", "aws", "azure", "gcp", "openstack"] }, { name: "target", label: "Cible", required: true, placeholder: "10.20.30.20" }, { name: "idempotency_key", label: "Clé d’idempotence", required: true, placeholder: "scan-par1-core-20260710" }, { name: "max_attempts", label: "Tentatives maximales", type: "number", required: true, defaultValue: "3" }] },
    { id: "discovery-job-claim", label: "Réserver le prochain job", method: "POST", path: "/v1/discovery/jobs/claim", body: [{ name: "collector_id", label: "ID agent proxy", required: true }, { name: "certificate_fingerprint", label: "Empreinte certificat", required: true }, { name: "worker_id", label: "ID worker", required: true, placeholder: "worker-par1-01" }, { name: "lease_seconds", label: "Durée du bail (secondes)", type: "number", required: true, defaultValue: "60" }] },
    { id: "discovery-job-renew", label: "Renouveler le bail d’un job", method: "POST", path: "/v1/discovery/jobs/renew", body: [{ name: "collector_id", label: "ID agent proxy", required: true }, { name: "certificate_fingerprint", label: "Empreinte certificat", required: true }, { name: "job_id", label: "ID job", required: true }, { name: "worker_id", label: "ID worker", required: true }, { name: "lease_token", label: "Jeton de fencing", type: "number", required: true }, { name: "lease_seconds", label: "Durée du bail (secondes)", type: "number", required: true, defaultValue: "60" }] },
    { id: "discovery-job-complete", label: "Terminer un job", method: "POST", path: "/v1/discovery/jobs/complete", body: [{ name: "collector_id", label: "ID agent proxy", required: true }, { name: "certificate_fingerprint", label: "Empreinte certificat", required: true }, { name: "job_id", label: "ID job", required: true }, { name: "worker_id", label: "ID worker", required: true }, { name: "lease_token", label: "Jeton de fencing", type: "number", required: true }, { name: "result_hash", label: "Empreinte SHA-256 du résultat", required: true, placeholder: "64 caractères hexadécimaux" }] },
    { id: "discovery-job-fail", label: "Déclarer l’échec d’un job", method: "POST", path: "/v1/discovery/jobs/fail", body: [{ name: "collector_id", label: "ID agent proxy", required: true }, { name: "certificate_fingerprint", label: "Empreinte certificat", required: true }, { name: "job_id", label: "ID job", required: true }, { name: "worker_id", label: "ID worker", required: true }, { name: "lease_token", label: "Jeton de fencing", type: "number", required: true }, { name: "error", label: "Erreur", required: true }, { name: "retry_delay_seconds", label: "Délai avant reprise (secondes)", type: "number", required: true, defaultValue: "30" }] },
    { id: "discovery-job-replay", label: "Réexécuter un job en DLQ", method: "POST", path: "/v1/discovery/jobs/replay", body: [FIELD_SETS.actor, { name: "job_id", label: "ID job", required: true }] },
    { id: "job-authorize", label: "Autoriser un job collector", method: "POST", path: "/v1/discovery/jobs/authorize", body: [{ name: "collector_id", label: "ID agent proxy", required: true }, { name: "certificate_fingerprint", label: "Empreinte certificat", required: true }, { name: "requested_scope", label: "Scope demandé", required: true }, { name: "job_type", label: "Type de job", required: true, type: "select", options: ["snmp", "ssh", "winrm", "vmware", "kubernetes"] }, { name: "target", label: "Cible", required: true, placeholder: "10.20.30.20" }] }
  ] },
  { id: "data", label: "Imports / Exports", shortLabel: "Data", icon: "table", description: "Imports massifs reprenables, rollback conflict-aware, exports asynchrones signés et lecture streaming par chunks.", operations: [
    { id: "import-bulk-progress", label: "Progression import massif", method: "GET", path: "/v1/imports/bulk-progress", query: [FIELD_SETS.jobId] },
    { id: "import-bulk-rollback", label: "Rollback import massif", method: "POST", path: "/v1/imports/bulk-rollback", body: [FIELD_SETS.actor, FIELD_SETS.jobId, { name: "file_path", label: "Fichier source relu", required: true, placeholder: "/var/lib/openinfra/imports/bulk.csv" }, { name: "format", label: "Format", type: "select", options: ["csv", "json", "xlsx"], defaultValue: "csv" }, { name: "mapping", label: "Mapping JSON", type: "json", required: true, placeholder: "{\"key\":\"asset_key\",\"kind\":\"kind\",\"display_name\":\"name\",\"source\":\"source\"}" }, { name: "apply", label: "Appliquer le rollback", type: "boolean" }, { name: "conflict_policy", label: "Politique conflit", type: "select", options: ["fail", "skip"], defaultValue: "fail" }] },
    { id: "import-migration-guide", label: "Guide migration données", method: "GET", path: "/v1/imports/migration-guide", query: [{ name: "source", label: "Source migration", type: "select", options: ["device42", "netbox", "nautobot", "glpi", "csv"], defaultValue: "device42" }] },
    { id: "export-artifact-chunk", label: "Chunk export signé", method: "GET", path: "/v1/exports/artifact-chunk", query: [FIELD_SETS.exportJobId, FIELD_SETS.chunkOffset, FIELD_SETS.chunkSize] }
  ] },
  { id: "integrations", label: "Intégrations externes", shortLabel: "Intégrations", icon: "grid", description: "Connecteurs externes ITSM sans ticketing natif : ServiceNow CMDB, Jira Service Management Assets, GLPI Inventory, Freshservice Assets, enrichissement et liens externes auditables.", operations: [
    { id: "itsm-providers", label: "Politiques connecteurs ITSM", method: "GET", path: "/v1/integrations/itsm/providers", query: [] },
    { id: "servicenow-validate", label: "Valider connecteur ServiceNow", method: "POST", path: "/v1/integrations/itsm/servicenow/validate", body: [FIELD_SETS.actor, { name: "instance_url", label: "URL instance HTTPS", required: true, placeholder: "https://instance.service-now.com" }, { name: "table_name", label: "Table CI", type: "select", options: ["cmdb_ci", "cmdb_ci_server", "cmdb_ci_netgear", "cmdb_ci_computer"], defaultValue: "cmdb_ci" }, { name: "auth_secret_ref", label: "Référence secret", required: true, placeholder: "vault://openinfra/servicenow/oauth" }, { name: "enabled", label: "Connecteur actif", type: "boolean" }] },
    { id: "servicenow-ci-sync-plan", label: "Plan synchro CI ServiceNow", method: "POST", path: "/v1/integrations/itsm/servicenow/ci-sync-plan", body: [FIELD_SETS.actor, { name: "resource_key", label: "Clé ressource RSOT", required: true, placeholder: "SRV-PAR1-001" }, { name: "direction", label: "Direction", type: "select", options: ["push_ci", "enrich_external_ticket", "link_external_ticket"], defaultValue: "push_ci" }, { name: "target_table", label: "Table cible", type: "select", options: ["cmdb_ci", "cmdb_ci_server", "cmdb_ci_netgear", "cmdb_ci_computer"], defaultValue: "cmdb_ci" }] },
    { id: "jira-validate", label: "Valider connecteur Jira Assets", method: "POST", path: "/v1/integrations/itsm/jira/validate", body: [FIELD_SETS.actor, { name: "instance_url", label: "URL Jira HTTPS", required: true, placeholder: "https://tenant.atlassian.net" }, { name: "object_type", label: "Type objet Assets", type: "select", options: ["object", "server", "network_device", "computer", "software"], defaultValue: "object" }, { name: "auth_secret_ref", label: "Référence secret", required: true, placeholder: "vault://openinfra/jira/api-token" }, { name: "enabled", label: "Connecteur actif", type: "boolean" }] },
    { id: "jira-asset-sync-plan", label: "Plan synchro Assets Jira", method: "POST", path: "/v1/integrations/itsm/jira/asset-sync-plan", body: [FIELD_SETS.actor, { name: "resource_key", label: "Clé ressource RSOT", required: true, placeholder: "SRV-PAR1-001" }, { name: "direction", label: "Direction", type: "select", options: ["push_ci", "enrich_external_ticket", "link_external_ticket"], defaultValue: "push_ci" }, { name: "object_type", label: "Type objet Assets", type: "select", options: ["object", "server", "network_device", "computer", "software"], defaultValue: "object" }] },
    { id: "glpi-validate", label: "Valider connecteur GLPI Inventory", method: "POST", path: "/v1/integrations/itsm/glpi/validate", body: [FIELD_SETS.actor, { name: "instance_url", label: "URL GLPI HTTPS", required: true, placeholder: "https://glpi.example.com" }, { name: "item_type", label: "Type élément GLPI", type: "select", options: ["computer", "network_equipment", "monitor", "printer", "software", "rack"], defaultValue: "computer" }, { name: "auth_secret_ref", label: "Référence secret", required: true, placeholder: "vault://openinfra/glpi/tokens" }, { name: "enabled", label: "Connecteur actif", type: "boolean" }] },
    { id: "glpi-asset-sync-plan", label: "Plan synchro inventaire GLPI", method: "POST", path: "/v1/integrations/itsm/glpi/asset-sync-plan", body: [FIELD_SETS.actor, { name: "resource_key", label: "Clé ressource RSOT", required: true, placeholder: "SRV-PAR1-001" }, { name: "direction", label: "Direction", type: "select", options: ["push_ci", "enrich_external_ticket", "link_external_ticket"], defaultValue: "push_ci" }, { name: "item_type", label: "Type élément GLPI", type: "select", options: ["computer", "network_equipment", "monitor", "printer", "software", "rack"], defaultValue: "computer" }] },
    { id: "freshservice-validate", label: "Valider connecteur Freshservice Assets", method: "POST", path: "/v1/integrations/itsm/freshservice/validate", body: [FIELD_SETS.actor, { name: "instance_url", label: "URL Freshservice HTTPS", required: true, placeholder: "https://tenant.freshservice.com" }, { name: "asset_type", label: "Type asset Freshservice", type: "select", options: ["asset", "hardware", "server", "network_device", "software"], defaultValue: "asset" }, { name: "auth_secret_ref", label: "Référence secret", required: true, placeholder: "vault://openinfra/freshservice/api-token" }, { name: "enabled", label: "Connecteur actif", type: "boolean" }] },
    { id: "freshservice-asset-sync-plan", label: "Plan synchro Assets Freshservice", method: "POST", path: "/v1/integrations/itsm/freshservice/asset-sync-plan", body: [FIELD_SETS.actor, { name: "resource_key", label: "Clé ressource RSOT", required: true, placeholder: "SRV-PAR1-001" }, { name: "direction", label: "Direction", type: "select", options: ["push_ci", "enrich_external_ticket", "link_external_ticket"], defaultValue: "push_ci" }, { name: "asset_type", label: "Type asset Freshservice", type: "select", options: ["asset", "hardware", "server", "network_device", "software"], defaultValue: "asset" }] }
  ] },
  { id: "security", label: "Sécurité / RBAC / Audit", shortLabel: "Sécurité", icon: "shield", description: "Identité, RBAC, tokens, politiques d’accès, audit, éditions et quotas runtime.", operations: [
    { id: "edition-policies", label: "Politiques éditions et quotas", method: "GET", path: "/v1/editions/policies", query: [] },
    { id: "edition-feature-check", label: "Vérifier une capacité édition", method: "GET", path: "/v1/editions/feature-check", query: [FIELD_SETS.edition, FIELD_SETS.featureCapability] },
    { id: "edition-quota-check", label: "Vérifier un quota édition", method: "GET", path: "/v1/editions/quota-check", query: [FIELD_SETS.edition, FIELD_SETS.quotaResource, FIELD_SETS.requestedIncrement] },
    { id: "tokens-list", label: "Lister les tokens techniques", method: "GET", path: "/v1/security/tokens", query: [FIELD_SETS.limit, { name: "include_inactive", label: "Inclure inactifs", type: "boolean" }] },
    { id: "effective-identity", label: "Identité effective", method: "GET", path: "/v1/identity/effective", query: [{ name: "subject", label: "Sujet", placeholder: "user@example.com" }] },
    { id: "access-rules", label: "Politiques d’accès", method: "GET", path: "/v1/access/rules", query: [FIELD_SETS.limit, { name: "include_inactive", label: "Inclure inactives", type: "boolean" }] },
    { id: "audit-events", label: "Événements d’audit", method: "GET", path: "/v1/audit/events", query: [{ name: "action", label: "Action" }, { name: "target_type", label: "Type cible" }, FIELD_SETS.limit] },
    { id: "audit-integrity", label: "Intégrité audit", method: "GET", path: "/v1/audit/integrity", query: [FIELD_SETS.limit] },
    { id: "certificate-import", label: "Importer une chaîne PEM", method: "POST", path: "/v1/certificates/import", body: [
      FIELD_SETS.actor,
      { name: "pem_bundle", label: "Chaîne PEM", type: "textarea", required: true, placeholder: "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----" },
      { name: "owner", label: "Propriétaire", required: true, placeholder: "Équipe PKI" },
      { name: "environment", label: "Environnement", required: true, placeholder: "production" },
      { name: "source", label: "Source", type: "select", options: ["manual", "discovery", "import", "acme", "internal-pki", "external-pki"], defaultValue: "manual" },
      { name: "object_key", label: "Objet RSOT", placeholder: "application/portail" }
    ] },
    { id: "certificate-get", label: "Consulter un certificat", method: "GET", path: "/v1/certificates/get", query: [
      { name: "fingerprint", label: "Empreinte SHA-256", required: true, placeholder: "64 caractères hexadécimaux" }
    ] },
    { id: "certificate-list", label: "Lister les certificats", method: "GET", path: "/v1/certificates", query: [
      { name: "limit", label: "Limite", type: "number", defaultValue: "100" },
      { name: "cursor", label: "Curseur" },
      { name: "include_retired", label: "Inclure retirés", type: "boolean" }
    ] },
    { id: "certificate-retire", label: "Retirer un certificat", method: "POST", path: "/v1/certificates/retire", body: [
      FIELD_SETS.actor,
      { name: "fingerprint", label: "Empreinte SHA-256", required: true }
    ] },
    { id: "certificate-endpoint-observe", label: "Observer un endpoint TLS", method: "POST", path: "/v1/certificates/endpoints/observe", body: [
      FIELD_SETS.actor,
      { name: "idempotency_key", label: "Clé d’idempotence", required: true, placeholder: "scanner-01:20260710:443" },
      { name: "protocol", label: "Protocole", type: "select", options: ["https", "tls", "ldaps", "smtps", "imaps", "pop3s", "mqtts", "custom"], defaultValue: "https" },
      { name: "host", label: "Hôte", required: true, placeholder: "portal.example.net" },
      { name: "port", label: "Port", type: "number", required: true, defaultValue: "443" },
      { name: "service", label: "Service", required: true, placeholder: "Portail OpenInfra" },
      { name: "certificate_fingerprint", label: "Empreinte du certificat", required: true },
      { name: "observed_at", label: "Observé le", required: true, placeholder: "2026-07-10T12:00:00Z" },
      { name: "source", label: "Source observation", required: true, placeholder: "tls-scanner" },
      { name: "collector", label: "Collecteur", required: true, placeholder: "scanner-par-01" },
      { name: "object_key", label: "Objet RSOT", placeholder: "application/portail" },
      { name: "tls_version", label: "Version TLS", placeholder: "TLSv1.3" },
      { name: "cipher", label: "Suite cryptographique", placeholder: "TLS_AES_256_GCM_SHA384" }
    ] },
    { id: "certificate-endpoint-list", label: "Lister les endpoints TLS", method: "GET", path: "/v1/certificates/endpoints", query: [
      { name: "certificate_fingerprint", label: "Empreinte du certificat" },
      { name: "limit", label: "Limite", type: "number", defaultValue: "100" },
      { name: "cursor", label: "Curseur" }
    ] },
    { id: "certificate-assessment", label: "Évaluer la conformité PKI", method: "GET", path: "/v1/certificates/assessment", query: [
      { name: "as_of", label: "Date de référence", placeholder: "2026-07-10T12:00:00Z" },
      { name: "critical_days", label: "Seuil critique (jours)", type: "number", defaultValue: "14" },
      { name: "warning_days", label: "Seuil avertissement (jours)", type: "number", defaultValue: "30" },
      { name: "health", label: "État de santé", type: "select", options: ["", "retired", "not-yet-valid", "expired", "critical", "warning", "healthy"] },
      { name: "limit", label: "Limite", type: "number", defaultValue: "100" },
      { name: "cursor", label: "Curseur" }
    ] },
    { id: "sbom-import", label: "Importer une SBOM", method: "POST", path: "/v1/sbom/documents/import", body: [
      { name: "application", label: "Application", required: true }, { name: "release", label: "Version / release", required: true }, { name: "environment", label: "Environnement", required: true },
      { name: "source_name", label: "Source", required: true, defaultValue: "ci-cd" }, { name: "source_uri", label: "URI de provenance", type: "url" },
      { name: "sbom", label: "Document CycloneDX ou SPDX (JSON)", type: "json", required: true }
    ] },
    { id: "sbom-documents", label: "Lister les SBOM", method: "GET", path: "/v1/sbom/documents", query: [
      { name: "application", label: "Application" }, { name: "environment", label: "Environnement" }, { name: "format", label: "Format", type: "select", options: ["", "cyclonedx", "spdx"] }, FIELD_SETS.limit, FIELD_SETS.cursor
    ] },
    { id: "sbom-document-get", label: "Consulter une SBOM", method: "GET", path: "/v1/sbom/documents/get", query: [{ name: "document_id", label: "ID SBOM", required: true }] },
    { id: "sbom-vulnerability-import", label: "Importer une vulnérabilité", method: "POST", path: "/v1/sbom/vulnerabilities/import", body: [
      { name: "cve_id", label: "Identifiant CVE", required: true, placeholder: "CVE-2026-12345" }, { name: "component_name", label: "Composant", required: true },
      { name: "component_version", label: "Version", required: true }, { name: "component_purl", label: "Package URL (PURL)", placeholder: "pkg:pypi/example@1.0.0" },
      { name: "cvss_score", label: "Score CVSS", type: "number", required: true, min: "0", max: "10", step: "0.1" }, { name: "known_exploited", label: "Exploitation connue", type: "boolean" },
      { name: "exploit_maturity", label: "Maturité de l’exploit", type: "select", options: ["unknown", "proof-of-concept", "functional", "weaponized"], defaultValue: "unknown" },
      { name: "source_name", label: "Source", required: true, defaultValue: "external-scanner" }, { name: "published_at", label: "Publication", type: "datetime-local" },
      { name: "modified_at", label: "Modification", type: "datetime-local" }, { name: "references", label: "Références (JSON)", type: "json", defaultValue: "[]" }, { name: "metadata", label: "Métadonnées (JSON)", type: "json", defaultValue: "{}" }
    ] },
    { id: "sbom-vulnerabilities", label: "Lister les vulnérabilités", method: "GET", path: "/v1/sbom/vulnerabilities", query: [
      { name: "cve_id", label: "Identifiant CVE" }, { name: "component", label: "Composant ou PURL" }, { name: "known_exploited", label: "Exploitation connue", type: "boolean" }, FIELD_SETS.limit, FIELD_SETS.cursor
    ] },
    { id: "sbom-exposure-upsert", label: "Définir le contexte d’exposition", method: "POST", path: "/v1/sbom/exposures/upsert", body: [
      { name: "application", label: "Application", required: true }, { name: "environment", label: "Environnement", required: true }, { name: "internet_exposed", label: "Exposé à Internet", type: "boolean" },
      { name: "flow_exposed", label: "Accessible par les flux", type: "boolean" }, { name: "business_criticality", label: "Criticité métier (1-5)", type: "number", required: true, min: "1", max: "5", defaultValue: "3" },
      { name: "compensating_controls", label: "Contrôles compensatoires (JSON)", type: "json", defaultValue: "[]" }, { name: "asset_ids", label: "Actifs associés (JSON)", type: "json", defaultValue: "[]" }, { name: "service_ids", label: "Services associés (JSON)", type: "json", defaultValue: "[]" }
    ] },
    { id: "sbom-exposures", label: "Lister les contextes d’exposition", method: "GET", path: "/v1/sbom/exposures", query: [FIELD_SETS.limit, FIELD_SETS.cursor] },
    { id: "sbom-exposure-get", label: "Consulter un contexte d’exposition", method: "GET", path: "/v1/sbom/exposures/get", query: [{ name: "application", label: "Application", required: true }, { name: "environment", label: "Environnement", required: true }] },
    { id: "sbom-risk-assess", label: "Évaluer le risque contextualisé", method: "POST", path: "/v1/sbom/risk/assess", body: [{ name: "document_id", label: "ID SBOM", required: true }] },
    { id: "sbom-findings", label: "Lister les constats de risque", method: "GET", path: "/v1/sbom/findings", query: [
      { name: "document_id", label: "ID SBOM" }, { name: "priority", label: "Priorité", type: "select", options: ["", "critical", "high", "medium", "low"] },
      { name: "status", label: "Statut", type: "select", options: ["", "open", "accepted", "mitigated", "false-positive"] }, FIELD_SETS.limit, FIELD_SETS.cursor
    ] },
    { id: "sbom-risk-export", label: "Exporter le risque SBOM", method: "GET", path: "/v1/sbom/risk/export", download: true, query: [{ name: "document_id", label: "ID SBOM", required: true }, { name: "format", label: "Format", type: "select", options: ["json", "csv"], defaultValue: "json" }] },
    { id: "sbom-compare", label: "Comparer deux releases SBOM", method: "POST", path: "/v1/sbom/comparisons/create", body: [{ name: "base_document_id", label: "SBOM de référence", required: true }, { name: "target_document_id", label: "SBOM cible", required: true }] },
    { id: "sbom-comparisons", label: "Lister les comparaisons SBOM", method: "GET", path: "/v1/sbom/comparisons", query: [FIELD_SETS.limit, FIELD_SETS.cursor] },
    { id: "sbom-comparison-get", label: "Consulter une comparaison SBOM", method: "GET", path: "/v1/sbom/comparisons/get", query: [{ name: "comparison_id", label: "ID comparaison", required: true }] }

  ] }
];

const OPENINFRA_SIDEBAR_CONTEXTS = {
  rsot: [
    { label: "Référentiel", operationIds: ["rsot-taxonomy", "rsot-list", "rsot-upsert"] },
    { label: "Relations & historique", operationIds: ["rsot-relations", "rsot-as-of", "rsot-object-audit"] },
    { label: "Qualité & gouvernance", operationIds: ["rsot-quality-object", "rsot-quality-summary", "rsot-governance", "rsot-reconcile"] },
    { label: "Exploration", operationIds: ["graph-traverse", "graph-path"] },
    { label: "Analyse d’impact", operationIds: ["graph-impact", "graph-spof"] },
    { label: "Exports", operationIds: ["graph-export"] },
    { label: "Simulation & migrations", operationIds: ["simulation-create", "simulation-list", "simulation-run", "simulation-reports", "simulation-compare", "simulation-comparisons"] },
    { label: "Assistant gouverné", operationIds: ["rag-query", "rag-answers", "rag-answer-get"] },
    { label: "Index de connaissances", operationIds: ["rag-document-upsert", "rag-documents", "rag-document-get", "rag-document-deactivate", "rag-rsot-sync"] },
    { label: "Imports / exports RAG", operationIds: ["rag-job-create", "rag-jobs", "rag-job-get", "rag-job-run", "rag-job-artifact"] }
  ],
  ipam: [
    { label: "Vue & recherche", operationIds: ["ipam-dashboard", "ipam-search"] },
    { label: "Adressage IP", operationIds: ["ipam-define-vrf", "ipam-define-aggregate", "ipam-define-prefix", "ipam-list-prefixes", "ipam-define-range", "ipam-register-address", "ipam-allocate", "ipam-reservation-wizard", "ipam-capacity"] },
    { label: "Réseau L2/L3", operationIds: ["ipam-network-bindings", "ipam-topology", "ipam-define-vlan-group", "ipam-define-vxlan-vni", "ipam-define-vlan", "ipam-define-asn", "ipam-define-bgp-peer"] },
    { label: "Observations & DDI", operationIds: ["ipam-observe-dns", "ipam-observe-dhcp", "ipam-conflicts", "ipam-ddi-preview"] },
    { label: "Conformité réseau", operationIds: ["network-config-baseline-upsert", "network-config-baseline-list", "network-config-baseline-retire", "network-config-observation-submit", "network-config-observation-list", "network-config-assessment"] },
    { label: "Flux déclarés", operationIds: ["flow-declaration-upsert", "flow-declaration-list", "flow-declaration-retire"] },
    { label: "Flux observés", operationIds: ["flow-observation-submit", "flow-observation-list"] },
    { label: "Conformité des flux", operationIds: ["flow-matrix"] },
  ],
  dcim: [
    { label: "Sites & dépendances", operationIds: ["dcim-sites", "dcim-site", "dcim-site-create", "dcim-site-update", "dcim-site-delete", "dcim-buildings", "dcim-building", "dcim-building-create", "dcim-building-update", "dcim-building-delete", "dcim-floors", "dcim-floor", "dcim-rooms-list", "dcim-room", "dcim-room-create", "dcim-room-update", "dcim-room-delete", "dcim-racks", "dcim-rack", "dcim-rack-create", "dcim-rack-update", "dcim-rack-delete", "dcim-zones", "dcim-zone", "dcim-zone-create", "dcim-zone-update", "dcim-zone-delete", "dcim-topology-catalog", "dcim-define-room"] },
    { label: "Pilotage multisite", operationIds: ["multisite-sites", "multisite-grants", "multisite-grant-upsert", "multisite-grant-revoke", "multisite-report-generate", "multisite-reports", "multisite-report-get", "multisite-dr-plan-configure", "multisite-dr-plan-disable", "multisite-dr-plans", "multisite-dr-plan-get", "multisite-dr-drill-execute", "multisite-dr-drills", "multisite-dr-drill-get", "multisite-routes", "multisite-route-get", "multisite-route-configure", "multisite-route-disable", "multisite-job-route"] },
    { label: "Localisation & capacité", operationIds: ["dcim-locate-equipment", "dcim-rack-capacity", "dcim-room-plan", "dcim-rack-elevation"] },
    { label: "Connectivité", operationIds: ["dcim-patch-panel", "dcim-port", "dcim-cable", "dcim-cable-trace"] },
    { label: "Énergie & refroidissement", operationIds: ["dcim-power-device", "dcim-power-circuit", "dcim-cooling-zone", "dcim-power-reservation", "dcim-energy-cooling-capacity"] },
    { label: "GreenOps — sources & politiques", operationIds: ["greenops-source-create", "greenops-sources", "greenops-policy-upsert", "greenops-policy-get", "greenops-factor-create", "greenops-factors"] },
    { label: "GreenOps — mesures", operationIds: ["greenops-measurement-ingest", "greenops-measurements"] },
    { label: "GreenOps — rapports & empreinte", operationIds: ["greenops-report-generate", "greenops-report-get", "greenops-reports", "greenops-report-export", "greenops-scores"] },
    { label: "GreenOps — capacité & recommandations", operationIds: ["greenops-anomalies", "greenops-forecasts", "greenops-candidates"] },
    { label: "Opérations terrain", operationIds: ["field-sheet-list", "field-sheet-get", "field-sheet-generate", "field-lock-acquire", "field-operation-start", "field-checklist-record", "field-evidence-attach", "field-evidence-list", "field-evidence-validate", "field-operation-complete", "field-operation-cancel", "field-qr-verify", "field-lock-release", "field-offline-create", "field-offline-list", "field-offline-get", "field-offline-sync"] },
    { label: "Jumeau numérique", operationIds: ["dcim-digital-twin"] }
  ],
  itam: [
    { label: "Organisations", operationIds: ["itam-organizations", "itam-organization", "itam-organization-create", "itam-organization-update", "itam-organization-delete", "itam-tenants", "itam-tenant", "itam-tenant-create", "itam-tenant-update", "itam-tenant-delete"] },
    { label: "Partenaires", operationIds: ["itam-partners", "itam-partner", "itam-partner-create", "itam-partner-update", "itam-partner-delete"] },
    { label: "Support matériel", operationIds: ["itam-support-profile", "itam-support-coverage", "itam-register-manufacturer", "itam-add-third-party"] },
    { label: "Licences logicielles", operationIds: ["itam-software-license", "itam-software-compliance", "itam-register-software", "itam-update-license-assignment"] },
    { label: "Règles d’allocation", operationIds: ["finops-rule-create", "finops-rules"] },
    { label: "Imports & coûts", operationIds: ["finops-import-submit", "finops-import-get", "finops-imports", "finops-import-run", "finops-import-cancel", "finops-costs"] },
    { label: "Budgets & périodes", operationIds: ["finops-budget-upsert", "finops-budgets", "finops-period-close", "finops-periods"] },
    { label: "Showback / chargeback", operationIds: ["finops-report-generate", "finops-report-get", "finops-reports", "finops-report-export"] },
    { label: "Prévisions & anomalies", operationIds: ["finops-anomalies", "finops-forecasts"] },
  ],
  discovery: [
    { label: "Locale Lite/Pro", operationIds: ["local-discovery-plan"] },
    { label: "Agents Enterprise", operationIds: ["agent-bootstrap-plan", "collectors-list", "collectors-register", "job-authorize"] }
  ],
  data: [
    { label: "Imports", operationIds: ["import-bulk-progress", "import-bulk-rollback"] },
    { label: "Migration", operationIds: ["import-migration-guide"] },
    { label: "Exports", operationIds: ["export-artifact-chunk"] }
  ],
  integrations: [
    { label: "Gouvernance ITSM", operationIds: ["itsm-providers"] },
    { label: "ServiceNow", operationIds: ["servicenow-validate", "servicenow-ci-sync-plan"] },
    { label: "Jira Assets", operationIds: ["jira-validate", "jira-asset-sync-plan"] },
    { label: "GLPI Inventory", operationIds: ["glpi-validate", "glpi-asset-sync-plan"] },
    { label: "Freshservice Assets", operationIds: ["freshservice-validate", "freshservice-asset-sync-plan"] }
  ],
  security: [
    { label: "Éditions & quotas", operationIds: ["edition-policies", "edition-feature-check", "edition-quota-check"] },
    { label: "Identité & accès", operationIds: ["tokens-list", "effective-identity", "access-rules"] },
    { label: "Audit", operationIds: ["audit-events", "audit-integrity"] },
    { label: "Inventaire PKI", operationIds: ["certificate-import", "certificate-get", "certificate-list", "certificate-retire"] },
    { label: "Endpoints TLS", operationIds: ["certificate-endpoint-observe", "certificate-endpoint-list"] },
    { label: "Conformité PKI", operationIds: ["certificate-assessment"] },
    { label: "SBOM — inventaire & versions", operationIds: ["sbom-import", "sbom-documents", "sbom-document-get", "sbom-compare", "sbom-comparisons", "sbom-comparison-get"] },
    { label: "Vulnérabilités & exposition", operationIds: ["sbom-vulnerability-import", "sbom-vulnerabilities", "sbom-exposure-upsert", "sbom-exposures", "sbom-exposure-get"] },
    { label: "Risque contextualisé", operationIds: ["sbom-risk-assess", "sbom-findings", "sbom-risk-export"] },
  ]
};


function validateOperationCatalog(modules) {
  if (!Array.isArray(modules) || modules.length === 0) {
    throw new Error("Le catalogue des opérations OpenInfra est vide ou invalide.");
  }
  const operationIds = new Set();
  for (const module of modules) {
    if (!module || typeof module !== "object" || !Array.isArray(module.operations)) {
      throw new Error("Un composant du catalogue OpenInfra est invalide.");
    }
    for (const operation of module.operations) {
      if (!operation || typeof operation !== "object" || !operation.id || !operation.path || !operation.method) {
        throw new Error(`Une opération du composant ${module.id || "inconnu"} est invalide.`);
      }
      if (operationIds.has(operation.id)) {
        throw new Error(`Identifiant d’opération dupliqué : ${operation.id}.`);
      }
      operationIds.add(operation.id);
      const fields = [...(operation.query || []), ...(operation.body || [])];
      for (const [fieldIndex, field] of fields.entries()) {
        const validLegacyLabel = typeof field === "string" && field.trim() !== "";
        const validDefinition = field && typeof field === "object" && Boolean(field.name);
        if (!validLegacyLabel && !validDefinition) {
          throw new Error(`Champ invalide dans ${operation.id} à l’index ${fieldIndex}.`);
        }
      }
    }
  }
}

function renderFatalStartupError(root, error) {
  const message = error instanceof Error ? error.message : String(error || "Erreur inconnue");
  console.error("OpenInfra web startup failed", error);
  if (!root) {
    return;
  }
  const wrapper = document.createElement("main");
  wrapper.className = "container py-5";
  wrapper.setAttribute("role", "main");
  const alert = document.createElement("div");
  alert.className = "alert alert-danger";
  alert.setAttribute("role", "alert");
  const title = document.createElement("h1");
  title.className = "h4";
  title.textContent = "OpenInfra Web ne peut pas démarrer";
  const detail = document.createElement("p");
  detail.className = "mb-0";
  detail.textContent = message;
  alert.append(title, detail);
  wrapper.append(alert);
  root.replaceChildren(wrapper);
}

class OpenInfraDashboard {
  constructor(root) {
    if (!root) {
      throw new Error("Le point de montage #openinfra-root est introuvable.");
    }
    validateOperationCatalog(OPENINFRA_MODULES);
    this.root = root;
    this.i18n = new OpenInfraI18n();
    this.applyLanguage();
    this.state = {
      activeModuleId: "overview",
      activeNavigationModuleId: "overview",
      selected: OPENINFRA_MODULES[0].operations[0],
      openedModules: new Set(),
      openedContexts: new Set(),
      organization: "default",
      organizationCatalog: null,
      organizationCatalogError: null,
      tenant: "default",
      tenantCatalog: null,
      tenantCatalogError: null,
      partnerCatalog: null,
      partnerCatalogError: null,
      countryCatalog: null,
      countryCatalogError: null,
      dcimCatalog: null,
      dcimCatalogError: null,
      config: null,
      ready: null,
      status: null,
      version: null,
      result: null,
      error: null,
      globalSearchQuery: "",
      globalSearchBackend: null,
      globalSearchLoading: false,
      globalSearchError: null,
      catalogLoading: false,
      mobileSidebarOpen: false,
      megaMenuModuleId: null
    };
    this.catalogPromises = new Map();
    this.catalogLoadSequence = 0;
    this.handleResize = () => {
      this.syncFixedHeaderOffset();
      if (!this.isMegamenuViewport() && this.state.megaMenuModuleId !== null) {
        this.state = { ...this.state, megaMenuModuleId: null };
        this.render();
      }
      if (!this.isCompactViewport() && this.state.mobileSidebarOpen) {
        this.state = { ...this.state, mobileSidebarOpen: false };
        this.render();
      }
    };
    this.handleDocumentKeydown = (event) => {
      if (event.key === "Escape" && (this.state.mobileSidebarOpen || this.state.megaMenuModuleId)) {
        event.preventDefault();
        this.closeResponsiveNavigation(true);
      }
    };
  }


  applyLanguage() {
    localizeOpenInfraCatalog({
      modules: OPENINFRA_MODULES,
      contexts: OPENINFRA_SIDEBAR_CONTEXTS,
      resourceTaxonomy: RESOURCE_TAXONOMY,
      resourceCategories: RESOURCE_CATEGORY_OPTIONS,
      dcimReferenceLabels: DCIM_REFERENCE_LABELS
    }, this.i18n.language);
  }

  setLanguage(language) {
    this.i18n.setLanguage(language);
    document.documentElement.lang = this.i18n.language;
    this.applyLanguage();
    this.render();
  }

  async start() {
    document.documentElement.lang = this.i18n.language;
    window.addEventListener("resize", this.handleResize);
    document.addEventListener("keydown", this.handleDocumentKeydown);
    this.render();
    await this.refreshRuntime();
    this.render();
    void this.refreshReadiness();
  }

  async refreshRuntime() {
    try {
      const response = await fetch("/bootstrap.json", { credentials: "same-origin", headers: { Accept: "application/json" } });
      if (!response.ok) {
        throw new Error(`Bootstrap unavailable: ${response.status}`);
      }
      const bootstrap = await response.json();
      this.state = {
        ...this.state,
        config: bootstrap.config || null,
        version: bootstrap.version || null,
        status: bootstrap.status || null,
        error: null
      };
    } catch (error) {
      this.state = { ...this.state, error };
    }
  }

  async refreshReadiness() {
    try {
      const response = await fetch("/ready", { credentials: "same-origin", headers: { Accept: "application/json" } });
      this.state = { ...this.state, ready: response.ok ? await response.json() : { ready: false } };
    } catch (_error) {
      this.state = { ...this.state, ready: { ready: false } };
    }
    this.updateRuntimeStatus();
  }

  updateRuntimeStatus() {
    const markup = this.renderRuntimeStatus();
    for (const element of document.querySelectorAll(".openinfra-runtime-status")) {
      element.outerHTML = markup;
    }
  }

  operationCatalogDependencies(operation) {
    if (!operation || operation.id === "overview") {
      return [];
    }
    const fields = [...(operation.query || []), ...(operation.body || [])];
    const dependencies = new Set();
    const fieldTypes = new Set(fields.map((field) => String(field?.type || "")));
    const fieldNames = new Set(fields.map((field) => String(field?.name || "").toLowerCase()));
    if (this.operationNeedsGlobalScopeSelectors(operation)
      || fieldTypes.has("organization-select")
      || fieldTypes.has("tenant-select")
      || fieldTypes.has("partner-select")) {
      dependencies.add("scope");
    }
    if (fieldTypes.has("country-select") || fieldNames.has("country") || fieldNames.has("country_code")) {
      dependencies.add("countries");
    }
    if (fieldTypes.has("partner-select")) {
      dependencies.add("partners");
    }
    if (fields.some((field) => this.isDcimReferenceField(field))) {
      dependencies.add("dcim");
    }
    return [...dependencies];
  }

  catalogDependencyLoaded(dependency) {
    if (dependency === "scope") return Boolean(this.state.organizationCatalog && this.state.tenantCatalog);
    if (dependency === "countries") return Boolean(this.state.countryCatalog);
    if (dependency === "partners") return Boolean(this.state.partnerCatalog);
    if (dependency === "dcim") return Boolean(this.state.dcimCatalog);
    return true;
  }

  operationCatalogsNeedLoading(operation) {
    return this.operationCatalogDependencies(operation).some((dependency) => !this.catalogDependencyLoaded(dependency));
  }

  async loadCatalogsForOperation(operation) {
    const dependencies = this.operationCatalogDependencies(operation);
    if (dependencies.length === 0 || !this.operationCatalogsNeedLoading(operation)) {
      return;
    }
    const sequence = ++this.catalogLoadSequence;
    const independent = [];
    if (dependencies.includes("scope") && !this.catalogDependencyLoaded("scope")) {
      independent.push(this.catalogPromise("scope", () => this.refreshScopeCatalogs()));
    }
    if (dependencies.includes("countries") && !this.catalogDependencyLoaded("countries")) {
      independent.push(this.catalogPromise("countries", () => this.refreshCountryCatalog()));
    }
    if (dependencies.includes("dcim") && !this.catalogDependencyLoaded("dcim")) {
      independent.push(this.catalogPromise("dcim", () => this.refreshDcimCatalog()));
    }
    await Promise.all(independent);
    if (dependencies.includes("partners") && !this.catalogDependencyLoaded("partners")) {
      await this.catalogPromise("partners", () => this.refreshPartnerCatalog());
    }
    if (sequence !== this.catalogLoadSequence || this.state.selected.id !== operation.id) {
      return;
    }
    this.state = { ...this.state, catalogLoading: false };
    this.render();
  }

  catalogPromise(key, loader) {
    const current = this.catalogPromises.get(key);
    if (current) {
      return current;
    }
    const promise = Promise.resolve().then(loader).finally(() => this.catalogPromises.delete(key));
    this.catalogPromises.set(key, promise);
    return promise;
  }

  async refreshScopeCatalogs() {
    const base = String(this.state.config?.apiBaseUrl || "/api").replace(/\/$/, "");
    const tenantId = encodeURIComponent(this.state.tenant || "default");
    const [organizationResult, tenantResult] = await Promise.allSettled([
      fetch(`${base}/v1/itam/organizations?tenant_id=${tenantId}`, {
        credentials: "same-origin",
        headers: { Accept: "application/json" }
      }).then((response) => {
        if (!response.ok) throw new Error(`ITAM organization catalog returned ${response.status}`);
        return response.json();
      }),
      fetch(`${base}/v1/itam/tenants?tenant_id=${tenantId}`, {
        credentials: "same-origin",
        headers: { Accept: "application/json" }
      }).then((response) => {
        if (!response.ok) throw new Error(`ITAM tenant catalog returned ${response.status}`);
        return response.json();
      })
    ]);
    let organization = this.state.organization;
    let tenant = this.state.tenant;
    const updates = {};
    if (organizationResult.status === "fulfilled") {
      const catalog = organizationResult.value;
      const selectable = (catalog.items || []).filter((item) => item.selectable !== false && item.status === "active");
      const selected = catalog.auto_selected_organization_id || catalog.default_organization_id || organization;
      organization = selectable.some((item) => item.organization_id === selected) ? selected : organization;
      Object.assign(updates, { organizationCatalog: catalog, organizationCatalogError: null, organization });
    } else {
      Object.assign(updates, { organizationCatalog: null, organizationCatalogError: organizationResult.reason });
    }
    if (tenantResult.status === "fulfilled") {
      const catalog = tenantResult.value;
      const selectable = (catalog.items || []).filter((item) => item.selectable !== false && item.status === "active" && item.organization_id === organization);
      const selected = catalog.auto_selected_tenant_id || catalog.default_tenant_id || tenant;
      tenant = selectable.some((item) => item.tenant_id === selected)
        ? selected
        : (selectable[0]?.tenant_id || organization || tenant);
      Object.assign(updates, { tenantCatalog: catalog, tenantCatalogError: null, tenant });
    } else {
      Object.assign(updates, { tenantCatalog: null, tenantCatalogError: tenantResult.reason });
    }
    this.state = { ...this.state, ...updates };
  }


  async refreshCountryCatalog() {
    try {
      const base = String(this.state.config?.apiBaseUrl || "/api").replace(/\/$/, "");
      const response = await fetch(`${base}/v1/reference/countries`, {
        credentials: "same-origin",
        headers: { Accept: "application/json" }
      });
      if (!response.ok) {
        throw new Error(`Country catalog returned ${response.status}`);
      }
      const catalog = await response.json();
      this.state = { ...this.state, countryCatalog: catalog, countryCatalogError: null };
    } catch (error) {
      this.state = { ...this.state, countryCatalog: null, countryCatalogError: error };
    }
  }


  async refreshOrganizationCatalog() {
    try {
      const base = String(this.state.config?.apiBaseUrl || "/api").replace(/\/$/, "");
      const response = await fetch(`${base}/v1/itam/organizations?tenant_id=${encodeURIComponent(this.state.tenant || "default")}`, {
        credentials: "same-origin",
        headers: { Accept: "application/json" }
      });
      if (!response.ok) {
        throw new Error(`ITAM organization catalog returned ${response.status}`);
      }
      const catalog = await response.json();
      const selectable = (catalog.items || []).filter((item) => item.selectable !== false && item.status === "active");
      const selected = catalog.auto_selected_organization_id || catalog.default_organization_id || this.state.organization;
      const organization = selectable.some((item) => item.organization_id === selected) ? selected : this.state.organization;
      this.state = { ...this.state, organizationCatalog: catalog, organizationCatalogError: null, organization };
    } catch (error) {
      this.state = { ...this.state, organizationCatalog: null, organizationCatalogError: error };
    }
  }

  async refreshTenantCatalog() {
    try {
      const base = String(this.state.config?.apiBaseUrl || "/api").replace(/\/$/, "");
      const response = await fetch(`${base}/v1/itam/tenants?tenant_id=${encodeURIComponent(this.state.tenant || "default")}`, {
        credentials: "same-origin",
        headers: { Accept: "application/json" }
      });
      if (!response.ok) {
        throw new Error(`ITAM tenant catalog returned ${response.status}`);
      }
      const catalog = await response.json();
      const selectable = (catalog.items || []).filter((item) => {
        return item.selectable !== false && item.status === "active" && item.organization_id === this.state.organization;
      });
      const selected = catalog.auto_selected_tenant_id || catalog.default_tenant_id || this.state.tenant;
      const tenant = selectable.some((item) => item.tenant_id === selected)
        ? selected
        : (selectable[0]?.tenant_id || this.state.organization || this.state.tenant);
      this.state = {
        ...this.state,
        tenantCatalog: catalog,
        tenantCatalogError: null,
        tenant
      };
    } catch (error) {
      this.state = { ...this.state, tenantCatalog: null, tenantCatalogError: error };
    }
  }

  async refreshPartnerCatalog() {
    try {
      const base = String(this.state.config?.apiBaseUrl || "/api").replace(/\/$/, "");
      const params = new URLSearchParams({ tenant_id: this.state.tenant || "default" });
      if (this.state.organization) {
        params.set("organization_id", this.state.organization);
      }
      const response = await fetch(`${base}/v1/itam/partners?${params.toString()}`, {
        credentials: "same-origin",
        headers: { Accept: "application/json" }
      });
      if (!response.ok) {
        throw new Error(`ITAM partner catalog returned ${response.status}`);
      }
      const catalog = await response.json();
      this.state = { ...this.state, partnerCatalog: catalog, partnerCatalogError: null };
    } catch (error) {
      this.state = { ...this.state, partnerCatalog: null, partnerCatalogError: error };
    }
  }

  async refreshDcimCatalog() {
    try {
      const base = String(this.state.config?.apiBaseUrl || "/api").replace(/\/$/, "");
      const params = new URLSearchParams({ tenant_id: this.state.tenant || "default" });
      const response = await fetch(`${base}/v1/dcim/topology-catalog?${params.toString()}`, {
        credentials: "same-origin",
        headers: { Accept: "application/json" }
      });
      if (!response.ok) {
        throw new Error(`DCIM topology catalog returned ${response.status}`);
      }
      const catalog = await response.json();
      this.state = { ...this.state, dcimCatalog: catalog, dcimCatalogError: null };
    } catch (error) {
      this.state = { ...this.state, dcimCatalog: null, dcimCatalogError: error };
    }
  }

  organizationOptions() {
    return (this.state.organizationCatalog?.items || [])
      .filter((organization) => organization.selectable !== false && organization.status === "active")
      .map((organization) => ({
        value: organization.organization_id,
        label: `${organization.display_name || organization.legal_name || organization.organization_id} — ${organization.organization_id}`
      }));
  }

  organizationLabel(organizationId) {
    const organization = (this.state.organizationCatalog?.items || []).find((item) => item.organization_id === organizationId);
    return organization?.display_name || organization?.legal_name || organizationId;
  }

  tenantOptions(organizationId = this.state.organization) {
    const tenants = (this.state.tenantCatalog?.items || [])
      .filter((tenant) => tenant.selectable !== false && tenant.status === "active" && tenant.organization_id === organizationId)
      .map((tenant) => ({
        value: tenant.tenant_id,
        label: `${tenant.name || tenant.tenant_id}${tenant.is_default ? ` — ${this.i18n.t("defaultMarker")}` : ""}`
      }));
    if (tenants.length > 0) {
      return tenants;
    }
    if (organizationId) {
      return [{ value: organizationId, label: `${this.organizationLabel(organizationId)} — ${this.i18n.t("implicitTenant")}` }];
    }
    return [];
  }

  partnerOptions(kind = null, organizationId = this.state.organization) {
    return (this.state.partnerCatalog?.items || [])
      .filter((partner) => {
        return partner.selectable !== false
          && partner.status === "active"
          && partner.organization_id === organizationId
          && (!kind || partner.kind === kind);
      })
      .map((partner) => ({
        value: partner.partner_id,
        label: `${partner.display_name || partner.legal_name || partner.partner_id} — ${partner.kind}`
      }));
  }

  renderOrganizationSelector() {
    const options = this.organizationOptions();
    const fallback = this.state.organization || "default";
    const renderedOptions = options.length > 0 ? options : [{ value: fallback, label: fallback }];
    return `<label class="col-md-4 form-label">${this.escape(this.i18n.t("organization"))}<select id="openinfra-organization" class="form-select">${this.renderOptions(renderedOptions, fallback)}</select></label>`;
  }

  renderTenantSelector() {
    const options = this.tenantOptions(this.state.organization);
    const fallback = this.state.tenant || this.state.organization || "default";
    const renderedOptions = options.length > 0 ? options : [{ value: fallback, label: fallback }];
    return `<label class="col-md-4 form-label">${this.escape(this.i18n.t("tenant"))}<select id="openinfra-tenant" class="form-select">${this.renderOptions(renderedOptions, fallback)}</select></label>`;
  }

  client() {
    return new OpenInfraApiClient(this.state.config?.apiBaseUrl || "/api", () => this.state.tenant, this.i18n);
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

  isMegamenuViewport() {
    return typeof window !== "undefined"
      && window.matchMedia("(min-width: 768px) and (max-width: 1199.98px)").matches;
  }

  isCompactViewport() {
    return typeof window !== "undefined"
      && window.matchMedia("(max-width: 767.98px)").matches;
  }

  closeResponsiveNavigation(restoreFocus = false) {
    const focusId = restoreFocus && this.lastNavigationModuleId ? `openinfra-component-${this.lastNavigationModuleId}` : null;
    this.state = {
      ...this.state,
      activeNavigationModuleId: this.state.activeModuleId,
      mobileSidebarOpen: false,
      megaMenuModuleId: null
    };
    this.render();
    this.announce(this.i18n.t("navigationClosed"));
    if (focusId) {
      window.requestAnimationFrame(() => document.getElementById(focusId)?.focus());
    }
  }

  openMegaMenu(moduleId, trigger = null) {
    const module = OPENINFRA_MODULES.find((item) => item.id === moduleId);
    if (!module || module.id === "overview" || !this.isMegamenuViewport()) {
      return;
    }
    if (trigger instanceof HTMLElement) {
      this.lastNavigationModuleId = module.id;
    }
    if (this.state.megaMenuModuleId === module.id) {
      return;
    }
    this.state = {
      ...this.state,
      activeNavigationModuleId: module.id,
      megaMenuModuleId: module.id,
      mobileSidebarOpen: false
    };
    this.render();
    this.announce(this.i18n.t("navigationOpened", { component: module.shortLabel || module.label }));
  }

  handleModuleNavigation(moduleId) {
    const module = OPENINFRA_MODULES.find((item) => item.id === moduleId);
    if (!module) {
      return;
    }
    if (module.id === "overview" || !this.isMegamenuViewport()) {
      this.selectModule(moduleId);
      return;
    }
    this.openMegaMenu(moduleId);
  }

  visibleOperations(module) {
    return module.operations;
  }

  sidebarOperationGroups(module, operations) {
    const configuredGroups = OPENINFRA_SIDEBAR_CONTEXTS[module.id] || [];
    const byId = new Map(operations.map((operation) => [operation.id, operation]));
    const groupedIds = new Set();
    const groups = configuredGroups.map((group) => {
      const groupOperations = group.operationIds.map((id) => byId.get(id)).filter(Boolean);
      for (const operation of groupOperations) {
        groupedIds.add(operation.id);
      }
      return { label: group.label, operations: groupOperations };
    }).filter((group) => group.operations.length > 0);
    const remaining = operations.filter((operation) => !groupedIds.has(operation.id));
    if (remaining.length > 0) {
      groups.push({ label: "Autres", operations: remaining });
    }
    return groups;
  }

  sidebarContextKey(moduleId, label) {
    return `${moduleId}::${label}`;
  }

  contextForOperation(module, operationId) {
    return this.sidebarOperationGroups(module, module.operations).find((group) => {
      return group.operations.some((operation) => operation.id === operationId);
    });
  }

  removeModuleContexts(openedContexts, moduleId) {
    for (const key of Array.from(openedContexts)) {
      if (key.startsWith(`${moduleId}::`)) {
        openedContexts.delete(key);
      }
    }
  }

  renderSidebarOperationGroup(module, group, surface = "sidebar") {
    const contextKey = this.sidebarContextKey(module.id, group.label);
    const contextId = `openinfra-${surface}-context-${module.id}-${this.slugify(group.label)}`;
    const opened = this.state.openedContexts.has(contextKey);
    return `<section class="openinfra-sidebar-context ${opened ? "open" : ""}" role="group" aria-label="${this.escape(group.label)}">
      <button type="button" class="openinfra-sidebar-context-title ${opened && this.state.activeNavigationModuleId === module.id ? "active" : ""}" data-context-module-id="${this.escape(module.id)}" data-context-label="${this.escape(group.label)}" aria-expanded="${opened ? "true" : "false"}" aria-controls="${this.escape(contextId)}">${this.escape(group.label)}</button>
      <div id="${this.escape(contextId)}" class="openinfra-sidebar-context-panel ${opened ? "show" : ""}" role="region" aria-label="${this.escape(group.label)}">
        <div class="openinfra-sidebar-context-panel-inner">
          ${group.operations.map((operation) => `<button type="button" class="openinfra-sidebar-operation ${this.state.selected.id === operation.id ? "active" : ""}" data-operation-id="${this.escape(operation.id)}" aria-current="${this.state.selected.id === operation.id ? "page" : "false"}">${this.escape(operation.label)}</button>`).join("")}
        </div>
      </div>
    </section>`;
  }

  renderMegaMenu() {
    const module = OPENINFRA_MODULES.find((item) => item.id === this.state.megaMenuModuleId);
    if (!module || module.id === "overview") {
      return "";
    }
    const groups = this.sidebarOperationGroups(module, this.visibleOperations(module));
    return `<section id="openinfra-mega-menu" class="openinfra-mega-menu" aria-label="${this.escape(module.shortLabel || module.label)}">
      <div class="openinfra-mega-menu-header">
        <div>${this.icon(module.icon, "openinfra-mega-menu-icon", 22, 22)}<strong>${this.escape(module.label)}</strong></div>
        <button type="button" id="openinfra-mega-menu-close" class="openinfra-navigation-close" aria-label="${this.escape(this.i18n.t("closeNavigation"))}">×</button>
      </div>
      <div class="openinfra-mega-menu-grid">
        ${groups.map((group) => `<section class="openinfra-mega-menu-group" role="group" aria-label="${this.escape(group.label)}">
          <h2>${this.escape(group.label)}</h2>
          <div>${group.operations.map((operation) => `<button type="button" class="openinfra-sidebar-operation ${this.state.selected.id === operation.id ? "active" : ""}" data-operation-id="${this.escape(operation.id)}" aria-current="${this.state.selected.id === operation.id ? "page" : "false"}">${this.escape(operation.label)}</button>`).join("")}</div>
        </section>`).join("")}
      </div>
    </section>`;
  }

  renderCompactNavigation() {
    if (!this.state.mobileSidebarOpen) {
      return "";
    }
    return `<nav id="openinfra-compact-navigation" class="openinfra-compact-navigation" aria-label="${this.escape(this.i18n.t("navigation"))}">
      <div class="openinfra-compact-navigation-header">
        <strong>${this.escape(this.i18n.t("navigation"))}</strong>
        <button type="button" id="openinfra-compact-navigation-close" class="openinfra-navigation-close" aria-label="${this.escape(this.i18n.t("closeNavigation"))}">×</button>
      </div>
      <div class="openinfra-compact-navigation-body">
        <div class="openinfra-sidebar-heading">${this.escape(this.i18n.t("control"))}</div>
        ${this.renderSidebar("compact")}
        <div class="openinfra-sidebar-heading">${this.escape(this.i18n.t("runtimeStatus"))}</div>
        ${this.renderRuntimeStatus()}
      </div>
    </nav>`;
  }

  renderRuntimeStatus() {
    const displayedVersion = this.state.version?.version || this.state.config?.version || this.i18n.t("unavailable");
    const protectedForms = this.state.status?.protectedForms === "enabled" ? this.i18n.t("active") : this.i18n.t("configure");
    return `<div class="px-2 small text-muted openinfra-runtime-status" role="status" aria-live="polite" aria-atomic="true">
      <p><span class="openinfra-status-dot ${this.state.ready?.ready === true ? "ready" : "warning"}"></span>${this.escape(this.state.ready?.ready === true ? this.i18n.t("backendReady") : this.i18n.t("backendCheck"))}</p>
      <p>${this.escape(this.i18n.t("version"))} : <strong>${this.escape(displayedVersion)}</strong></p>
      <p>Trust web/backend : <strong>${this.escape(this.state.config?.webBackendTrust || "server-side")}</strong></p>
      <p>${this.escape(this.i18n.t("protectedForms"))} : <strong>${this.escape(protectedForms)}</strong></p>
    </div>`;
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
      return total + [...(operation.query || []), ...(operation.body || [])].filter((field) => field?.required).length;
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
        <form class="openinfra-global-search-form" role="search" aria-label="${this.escape(this.i18n.t("globalSearch"))}" autocomplete="off">
          <label class="visually-hidden" for="openinfra-global-search">${this.escape(this.i18n.t("globalSearch"))}</label>
          <div class="openinfra-global-search-control">
            ${this.icon("search", "openinfra-global-search-icon", 18, 18)}
            <input type="search" id="openinfra-global-search" class="form-control" placeholder="${this.escape(this.i18n.t("globalSearchPlaceholder"))}" aria-label="${this.escape(this.i18n.t("globalSearch"))}" role="combobox" aria-autocomplete="list" aria-haspopup="listbox" aria-controls="openinfra-global-search-results" aria-expanded="${hasQuery ? "true" : "false"}" value="${this.escape(query)}">
          </div>
          <div id="openinfra-global-search-results" class="openinfra-global-search-results" role="listbox" aria-label="${this.escape(this.i18n.t("globalSearchResults"))}" aria-live="polite" aria-atomic="false" aria-busy="${this.state.globalSearchLoading ? "true" : "false"}" ${hasQuery ? "" : "hidden"}>${this.renderGlobalSearchResults()}</div>
        </form>
        <div class="openinfra-toolbar-actions">
          <div class="openinfra-language-control">
            <label for="openinfra-language" class="visually-hidden">${this.i18n.t("language")}</label>
            <select id="openinfra-language" class="form-select form-select-sm" aria-label="${this.escape(this.i18n.t("language"))}">
              <option value="en" ${this.i18n.language === "en" ? "selected" : ""}>EN</option>
              <option value="fr" ${this.i18n.language === "fr" ? "selected" : ""}>FR</option>
            </select>
          </div>
          <div class="text-end openinfra-api-doc-actions">
            <a class="btn btn-light text-dark" href="${this.escape(docs.swaggerUrl)}" target="_blank" rel="noopener noreferrer" aria-label="${this.escape(`${this.i18n.t("openSwagger")} — ${this.i18n.t("opensNewWindow")}`)}">Swagger</a>
            <a class="btn btn-primary" href="${this.escape(docs.redocUrl)}" target="_blank" rel="noopener noreferrer" aria-label="${this.escape(`${this.i18n.t("openRedoc")} — ${this.i18n.t("opensNewWindow")}`)}">ReDoc</a>
          </div>
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
      return `<div class="openinfra-global-search-empty">${this.escape(this.i18n.t("loadingSearch", { query }))}</div>`;
    }
    if (backend && backend.query === query) {
      return this.renderBackendGlobalSearchResults(backend, query, groups);
    }
    if (this.state.globalSearchError) {
      return `<div class="openinfra-global-search-empty">${this.escape(this.i18n.t("backendSearchUnavailable"))}</div>${this.renderOperationSearchResults(groups, query)}`;
    }
    return this.renderOperationSearchResults(groups, query);
  }

  renderBackendGlobalSearchResults(backend, query, operationGroups) {
    const groups = Array.isArray(backend.groups) ? backend.groups : [];
    const visibleGroups = groups.filter((group) => group.status === "ok" && Array.isArray(group.items) && group.items.length > 0);
    const skipped = groups.filter((group) => group.status === "skipped");
    const sections = visibleGroups.map((group) => `<section class="openinfra-global-search-group" role="group" aria-label="${this.escape(this.i18n.t("globalSearchResults"))} ${this.escape(group.label || group.component)}">
      <div class="openinfra-global-search-group-title"><span>${this.escape(group.label || group.component)}</span><span>${this.escape(this.i18n.count(group.total, "result", "results"))}</span></div>
      ${group.items.map((item) => `<button type="button" class="openinfra-global-search-item" role="option" aria-selected="false" data-search-route="${this.escape(item.route || "")}">
        <span>${this.escape(item.label || item.kind || this.i18n.t("result"))}</span><small>${this.escape(item.kind || group.component)} · ${this.escape(item.description || "")}</small>
      </button>`).join("")}
      ${group.total > group.items.length ? `<div class="openinfra-global-search-more">${this.escape(this.i18n.t(group.total - group.items.length === 1 ? "additionalResults" : "additionalResultsPlural", { count: group.total - group.items.length }))}</div>` : ""}
    </section>`);
    const skippedNotice = skipped.length > 0
      ? `<div class="openinfra-global-search-empty">${this.escape(this.i18n.t("skippedComponents", { components: skipped.map((group) => group.label || group.component).join(", ") }))}</div>`
      : "";
    if (sections.length === 0) {
      return `<div class="openinfra-global-search-empty">${this.escape(this.i18n.t("noGlobalResult", { query }))}</div>${skippedNotice}${this.renderOperationSearchResults(operationGroups, query)}`;
    }
    return sections.join("") + skippedNotice;
  }

  renderOperationSearchResults(groups, query) {
    if (groups.length === 0) {
      return `<div class="openinfra-global-search-empty">${this.escape(this.i18n.t("noGlobalResult", { query }))}</div>`;
    }
    return groups.map(({ module, operations, total }) => `<section class="openinfra-global-search-group" role="group" aria-label="${this.escape(this.i18n.t("globalSearchResults"))} ${this.escape(module.shortLabel || module.label)}">
      <div class="openinfra-global-search-group-title"><span>${this.escape(module.shortLabel || module.label)}</span><span>${this.escape(this.i18n.count(total, "result", "results"))}</span></div>
      ${operations.map((operation) => `<button type="button" class="openinfra-global-search-item" role="option" aria-selected="false" data-search-operation-id="${this.escape(operation.id)}">
        <span>${this.escape(operation.label)}</span><small>${this.escape(operation.method)} ${this.escape(operation.path)}</small>
      </button>`).join("")}
      ${total > operations.length ? `<div class="openinfra-global-search-more">${this.escape(this.i18n.t(total - operations.length === 1 ? "additionalResults" : "additionalResultsPlural", { count: total - operations.length }))}</div>` : ""}
    </section>`).join("");
  }

  render() {
    const { activeModuleId, activeNavigationModuleId, selected, config, ready, status, version, error, result } = this.state;
    const displayedVersion = version?.version || config?.version || this.i18n.t("unavailable");
    const protectedForms = status?.protectedForms === "enabled" ? this.i18n.t("active") : this.i18n.t("configure");
    const activeModule = OPENINFRA_MODULES.find((module) => module.id === activeModuleId) || OPENINFRA_MODULES[0];
    const pageTitle = activeModuleId === "overview" ? "Dashboard" : activeModule.shortLabel || activeModule.label;
    const pageSubtitle = activeModuleId === "overview"
      ? this.i18n.t("dashboardSubtitle")
      : this.i18n.t("operationSubtitle", { operation: selected.label });
    this.root.innerHTML = `
      <div class="openinfra-skip-links" aria-label="${this.escape(this.i18n.t("accessibilityStatus"))}">
        <a class="openinfra-skip-link" href="#openinfra-main-content">${this.escape(this.i18n.t("skipToContent"))}</a>
        <a class="openinfra-skip-link" href="#openinfra-component-navigation">${this.escape(this.i18n.t("skipToNavigation"))}</a>
        <a class="openinfra-skip-link" href="#openinfra-global-search">${this.escape(this.i18n.t("skipToSearch"))}</a>
      </div>
      <div id="openinfra-live-region" class="openinfra-live-region" role="status" aria-live="polite" aria-atomic="true"></div>
      <header class="openinfra-header-stack" role="banner">
        <div class="px-3 py-2 bg-dark text-white openinfra-top-header">
          <div class="container-fluid">
            <div class="d-flex align-items-center openinfra-top-header-inner">
              <a href="/" class="d-flex align-items-center openinfra-brand-link text-white text-decoration-none" aria-label="${this.escape(this.i18n.t("home"))}">
                <span class="openinfra-brand-mark me-2">OI</span><span class="fs-5 fw-semibold openinfra-brand-name">OpenInfra</span><span class="badge openinfra-edition-badge ms-3">${this.escape(config?.edition || "runtime")}</span>
              </a>
              <nav id="openinfra-component-navigation" class="openinfra-component-navigation" aria-label="${this.escape(this.i18n.t("navigation"))}" aria-describedby="openinfra-component-navigation-instructions">
                <p id="openinfra-component-navigation-instructions" class="openinfra-component-navigation-instructions">${this.escape(this.i18n.t("componentNavigationInstructions"))}</p>
                <ul class="nav justify-content-center text-small openinfra-component-nav">
                  ${OPENINFRA_MODULES.map((module, index) => `
                    <li><button id="openinfra-component-${this.escape(module.id)}" data-component-index="${index}" type="button" class="nav-link border-0 bg-transparent openinfra-component-link ${activeNavigationModuleId === module.id ? "active" : ""}" data-module-id="${this.escape(module.id)}" aria-current="${activeNavigationModuleId === module.id ? "page" : "false"}" ${module.id === "overview" ? "" : `aria-haspopup="true" aria-expanded="${this.state.megaMenuModuleId === module.id ? "true" : "false"}" aria-controls="openinfra-mega-menu"`}>
                      ${this.icon(module.icon, "bi d-block mx-auto mb-1 openinfra-top-icon", 24, 24)}<span>${this.escape(module.shortLabel || module.label)}</span>
                    </button></li>
                  `).join("")}
                </ul>
              </nav>
              <button type="button" id="openinfra-compact-menu-button" class="btn btn-primary openinfra-compact-menu-button" aria-label="${this.escape(this.i18n.t(this.state.mobileSidebarOpen ? "closeNavigation" : "openNavigation"))}" aria-expanded="${this.state.mobileSidebarOpen ? "true" : "false"}" aria-controls="openinfra-compact-navigation">
                ${this.icon("menu", "openinfra-mobile-menu-icon", 20, 20)}<span class="visually-hidden">Menu</span>
              </button>
            </div>
          </div>
        </div>
        ${this.renderGlobalSearchToolbar()}
        ${this.renderMegaMenu()}
        ${this.renderCompactNavigation()}
      </header>
      ${this.state.mobileSidebarOpen || this.state.megaMenuModuleId ? `<button type="button" class="openinfra-navigation-backdrop" id="openinfra-navigation-backdrop" aria-label="${this.escape(this.i18n.t("closeNavigation"))}"></button>` : ""}
      <div class="container-fluid">
        <div class="row">
          <nav id="openinfra-sidebar" class="col-xl-2 openinfra-sidebar" aria-label="${this.escape(this.i18n.t("navigation"))}">
            <div class="openinfra-sidebar-heading">${this.escape(this.i18n.t("control"))}</div>
            ${this.renderSidebar()}
            <div class="openinfra-sidebar-heading">${this.escape(this.i18n.t("runtimeStatus"))}</div>
            ${this.renderRuntimeStatus()}
          </nav>
          <main id="openinfra-main-content" class="col-xl-10 ms-sm-auto openinfra-main" tabindex="-1">
            <div class="pb-2 mb-3 openinfra-titlebar">
              <h1 class="h2">${this.escape(pageTitle)}</h1><p class="text-muted mb-0">${this.escape(pageSubtitle)}</p>
            </div>
            ${error ? `<div class="alert alert-warning openinfra-error-summary" role="alert" tabindex="-1">${this.escape(error.message)}</div>` : ""}
            ${result && activeModuleId !== "overview" ? `<div class="alert alert-success" role="status">${this.escape(this.i18n.t("success"))}</div>` : ""}
            ${this.renderWorkspace(selected, result, displayedVersion, config, protectedForms)}
          </main>
        </div>
      </div>
    `;
    this.i18n.translateDom(this.root);
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
    if (this.state.catalogLoading) {
      return `<section class="card openinfra-operation-card"><div class="card-body"><div class="d-flex align-items-center gap-3" role="status" aria-live="polite"><span class="spinner-border spinner-border-sm" aria-hidden="true"></span><span>${this.escape(this.i18n.t("loadingFormReferences"))}</span></div></div></section>`;
    }
    return `<section class="card openinfra-operation-card"><div class="card-body">${this.renderOperationPanel(selected, result)}</div></section>`;
  }

  renderOverviewRuntimeMetrics(displayedVersion, config, protectedForms) {
    const operationsCount = OPENINFRA_MODULES.reduce((total, module) => total + module.operations.length, 0);
    return `<div class="row g-3 mb-4 openinfra-dashboard-metrics" aria-label="${this.escape(this.i18n.t("componentStatistics"))}">
      ${this.metric(this.i18n.t("version"), this.escape(displayedVersion))}
      ${this.metric("API", this.escape(config?.apiBaseUrl || "/api"))}
      ${this.metric(this.i18n.t("trust"), this.escape(config?.webBackendTrust || "server-side"))}
      ${this.metric(this.i18n.t("forms"), this.escape(protectedForms))}
      ${this.metric(this.i18n.t("modules"), `${operationsCount} ${this.i18n.t("operations")}`)}
    </div>`;
  }

  renderOverviewDashboard() {
    const components = this.componentModules();
    const totalOperations = components.reduce((total, module) => total + module.operations.length, 0);
    const totalFields = components.reduce((total, module) => total + this.moduleStatistics(module).fields, 0);
    const totalRequiredFields = components.reduce((total, module) => total + this.moduleStatistics(module).requiredFields, 0);
    return `<section class="openinfra-overview" aria-label="${this.escape(this.i18n.t("componentStatistics"))}">
      <div class="card openinfra-overview-summary mb-4">
        <div class="card-body">
          <div class="d-flex flex-wrap justify-content-between align-items-start gap-3">
            <div>
              <h2 class="h4 mb-1">${this.escape(this.i18n.t("overviewTitle"))}</h2>
              <p class="text-muted mb-0">${this.escape(this.i18n.t("overviewDescription"))}</p>
            </div>
            <div class="text-end">
              <span class="badge text-bg-primary">${components.length} ${this.escape(this.i18n.t("components"))}</span>
              <span class="badge text-bg-secondary ms-2">${totalOperations} ${this.escape(this.i18n.t("operations"))}</span>
            </div>
          </div>
          <div class="row g-3 mt-3">
            ${this.metric(this.i18n.t("fields"), String(totalFields))}
            ${this.metric(this.i18n.t("requiredFields"), String(totalRequiredFields))}
            ${this.metric(this.i18n.t("navigationMode"), this.i18n.t("accordions")) }
            ${this.metric(this.i18n.t("browserSecrets"), this.i18n.t("noneExposed"))}
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
            <div class="openinfra-pie-chart" role="img" aria-label="${this.escape(this.i18n.t("distributionChart", { module: module.label, reads: stats.readOperations, mutations: stats.writeOperations }))}" style="--oi-read-end: ${readEnd}; --oi-write-end: ${writeEnd};">
              <span>${stats.operations}</span>
            </div>
            <div class="openinfra-pie-legend small">
              <span><i class="openinfra-legend-read"></i>${stats.readOperations} ${this.escape(this.i18n.t("reads").toLowerCase())}</span>
              <span><i class="openinfra-legend-write"></i>${stats.writeOperations} ${this.escape(this.i18n.t("mutations").toLowerCase())}</span>
            </div>
          </div>
          <div class="row g-2 mt-3 openinfra-component-metrics">
            <div class="col-6"><strong>${stats.operations}</strong><span>${this.escape(this.i18n.t("operations"))}</span></div>
            <div class="col-6"><strong>${stats.fields}</strong><span>${this.escape(this.i18n.t("fields"))}</span></div>
            <div class="col-6"><strong>${stats.requiredFields}</strong><span>${this.escape(this.i18n.t("required"))}</span></div>
            <div class="col-6"><strong>${stats.writeOperations}</strong><span>${this.escape(this.i18n.t("mutations"))}</span></div>
          </div>
        </div>
      </div>
    </article>`;
  }

  renderSidebar(surface = "sidebar") {
    return OPENINFRA_MODULES.map((module) => {
      if (module.id === "overview") {
        return `<button type="button" class="nav-link openinfra-sidebar-dashboard w-100 text-start ${this.state.activeNavigationModuleId === module.id ? "active" : ""}" data-operation-id="${this.escape(module.operations[0].id)}" aria-current="${this.state.activeNavigationModuleId === module.id ? "page" : "false"}">${this.icon(module.icon)}Dashboard</button>`;
      }
      const opened = this.state.openedModules.has(module.id);
      const visibleOperations = this.visibleOperations(module);
      if (visibleOperations.length === 0 && !module.label.toLowerCase().includes(this.state.filter.toLowerCase())) {
        return "";
      }
      return `<section class="openinfra-accordion ${opened ? "open" : ""}">
        <button type="button" id="openinfra-${surface}-accordion-${this.escape(module.id)}" class="openinfra-accordion-toggle ${this.state.activeNavigationModuleId === module.id ? "active" : ""}" data-accordion-id="${this.escape(module.id)}" aria-expanded="${opened ? "true" : "false"}" aria-controls="openinfra-${surface}-panel-${this.escape(module.id)}" aria-current="${this.state.activeNavigationModuleId === module.id ? "page" : "false"}">
          <span>${this.icon(module.icon)}${this.escape(module.shortLabel || module.label)}</span><span class="openinfra-chevron">›</span>
        </button>
        <div id="openinfra-${surface}-panel-${this.escape(module.id)}" class="openinfra-accordion-panel fade ${opened ? "show" : ""}" role="region" aria-labelledby="openinfra-${surface}-accordion-${this.escape(module.id)}">
          <div class="openinfra-accordion-panel-inner">
            ${this.sidebarOperationGroups(module, visibleOperations).map((group) => this.renderSidebarOperationGroup(module, group, surface)).join("")}
          </div>
        </div>
      </section>`;
    }).join("");
  }

  operationNeedsGlobalScopeSelectors(operation) {
    const id = String(operation?.id || "");
    if (id.startsWith("itam-organization") || id.startsWith("itam-partner") || id.startsWith("itam-tenant")) {
      return false;
    }
    return true;
  }

  renderOperationScopeSelectors(operation) {
    if (!this.operationNeedsGlobalScopeSelectors(operation)) {
      return "";
    }
    return `<div class="row g-3 mb-3">${this.renderOrganizationSelector()}${this.renderTenantSelector()}</div>`;
  }

  renderOperationPanel(operation, result) {
    const module = this.moduleForOperation(operation);
    const fields = [...(operation.query || []), ...(operation.body || [])];
    const hasRequiredFields = fields.some((field) => field.required);
    return `<div class="row g-4">
      <section class="col-12 col-xxl-8" aria-labelledby="openinfra-operation-title">
        <h2 id="openinfra-operation-title" class="h4">${this.escape(operation.label)}</h2>
        <p class="text-muted">${this.escape(module.description)}</p>
        <form id="openinfra-operation-form" novalidate ${hasRequiredFields ? 'aria-describedby="openinfra-required-fields-notice"' : ""}>
          ${hasRequiredFields ? `<p id="openinfra-required-fields-notice" class="openinfra-required-notice">${this.escape(this.i18n.t("requiredFieldsNotice"))}</p>` : ""}
          ${this.renderOperationScopeSelectors(operation)}
          <div class="row g-3">${fields.map((field) => this.renderField(field)).join("") || `<p>${this.escape(this.i18n.t("noParameters"))}</p>`}</div>
          <button class="btn btn-primary mt-3" type="submit" id="openinfra-execute">${this.escape(this.i18n.t("execute"))}</button>
        </form>
      </section>
      <aside class="col-12 col-xxl-4" aria-labelledby="openinfra-result-title">
        <h3 id="openinfra-result-title" class="h6 text-uppercase text-muted">${this.escape(this.i18n.t("resultTitle"))}</h3>
        ${this.renderGraphResult(operation, result)}
        <details class="openinfra-raw-result" ${result ? "" : "open"}>
          <summary>${this.escape(this.i18n.t("rawResult"))}</summary>
          <pre class="openinfra-result" role="status" aria-live="polite" aria-atomic="true" aria-label="${this.escape(this.i18n.t("operationResult"))}">${this.escape(result ? JSON.stringify(result, null, 2) : this.i18n.t("pendingResult"))}</pre>
        </details>
      </aside>
    </div>`;
  }

  renderGraphResult(operation, result) {
    if (!result || !String(operation?.id || "").startsWith("graph-")) {
      return "";
    }
    if (operation.id === "graph-export") {
      return `<div class="alert alert-success openinfra-download-result" role="status"><strong>${this.escape(this.i18n.t("downloadReady"))}</strong><br>${this.escape(result.filename || "")} · ${this.escape(String(result.size_bytes || 0))} octets</div>`;
    }
    if (operation.id === "graph-spof") {
      return this.renderSpofRanking(result);
    }
    return this.renderDependencyGraph(result);
  }

  renderDependencyGraph(result) {
    const nodes = Array.isArray(result.nodes) ? result.nodes : [];
    const edges = Array.isArray(result.edges) ? result.edges : [];
    if (nodes.length === 0) {
      return `<p class="text-muted">${this.escape(this.i18n.t("noGraphData"))}</p>`;
    }
    const maxVisible = 80;
    const visibleNodes = nodes.slice(0, maxVisible);
    const visibleKeys = new Set(visibleNodes.map((node) => String(node.key || "")));
    const visibleEdges = edges.filter((edge) => visibleKeys.has(String(edge.source_key || "")) && visibleKeys.has(String(edge.target_key || ""))).slice(0, 160);
    const depthGroups = new Map();
    for (const node of visibleNodes) {
      const depth = Number.isFinite(Number(node.depth)) ? Number(node.depth) : 0;
      if (!depthGroups.has(depth)) depthGroups.set(depth, []);
      depthGroups.get(depth).push(node);
    }
    const depths = [...depthGroups.keys()].sort((left, right) => left - right);
    const width = 720;
    const layerGap = Math.max(145, Math.floor(width / Math.max(depths.length, 1)));
    const maxLayer = Math.max(...[...depthGroups.values()].map((group) => group.length), 1);
    const height = Math.max(280, maxLayer * 76 + 56);
    const coordinates = new Map();
    depths.forEach((depth, layerIndex) => {
      const group = depthGroups.get(depth) || [];
      group.sort((left, right) => String(left.key || "").localeCompare(String(right.key || "")));
      group.forEach((node, rowIndex) => {
        coordinates.set(String(node.key || ""), {
          x: 70 + layerIndex * layerGap,
          y: 46 + rowIndex * 76
        });
      });
    });
    const lines = visibleEdges.map((edge) => {
      const source = coordinates.get(String(edge.source_key || ""));
      const target = coordinates.get(String(edge.target_key || ""));
      if (!source || !target) return "";
      return `<line x1="${source.x}" y1="${source.y}" x2="${target.x}" y2="${target.y}" marker-end="url(#openinfra-graph-arrow)"><title>${this.escape(edge.relation_type || "relation")}: ${this.escape(edge.source_key || "")} → ${this.escape(edge.target_key || "")}</title></line>`;
    }).join("");
    const circles = visibleNodes.map((node) => {
      const position = coordinates.get(String(node.key || ""));
      const label = String(node.display_name || node.key || "");
      const short = label.length > 16 ? `${label.slice(0, 15)}…` : label;
      const root = String(node.key || "") === String(result.root_key || result.source_key || "");
      return `<g class="openinfra-graph-node${root ? " is-root" : ""}" transform="translate(${position.x},${position.y})" role="listitem" aria-label="${this.escape(`${label}, ${node.resource_type || node.kind || "object"}, profondeur ${node.depth ?? 0}`)}"><circle r="24"></circle><text text-anchor="middle" y="4">${this.escape(short)}</text><title>${this.escape(label)} (${this.escape(node.key || "")})</title></g>`;
    }).join("");
    const omitted = nodes.length - visibleNodes.length;
    return `<section class="openinfra-graph-visualization" aria-labelledby="openinfra-graph-visualization-title"><h4 id="openinfra-graph-visualization-title" class="h6">${this.escape(this.i18n.t("graphVisualization"))}</h4><p class="small text-muted">${this.escape(this.i18n.t("graphVisualizationDescription"))}</p><div class="openinfra-graph-canvas" role="region" aria-label="${this.escape(this.i18n.t("graphVisualization"))}" tabindex="0"><svg viewBox="0 0 ${Math.max(width, 120 + (depths.length - 1) * layerGap)} ${height}" role="img" aria-label="${this.escape(`${nodes.length} nœuds, ${edges.length} relations`)}"><defs><marker id="openinfra-graph-arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z"></path></marker></defs><g class="openinfra-graph-edges">${lines}</g><g class="openinfra-graph-nodes" role="list">${circles}</g></svg></div><ul class="visually-hidden" aria-label="${this.escape(this.i18n.t("graphVisualization"))}">${visibleNodes.map((node) => `<li>${this.escape(`${node.display_name || node.key}, ${node.resource_type || node.kind || "object"}, profondeur ${node.depth ?? 0}`)}</li>`).join("")}</ul>${omitted > 0 ? `<p class="small text-muted">${this.escape(this.i18n.t("graphNodesOmitted", { count: omitted }))}</p>` : ""}</section>`;
  }

  renderSpofRanking(result) {
    const items = Array.isArray(result.items) ? result.items : [];
    const complete = result.complete !== false;
    const rows = items.map((item) => {
      const node = item.node || {};
      const ratio = Math.max(0, Math.min(1, Number(item.affected_ratio || 0)));
      const sample = Array.isArray(item.affected_sample) ? item.affected_sample.join(", ") : "";
      return `<tr><td>${this.escape(item.rank)}</td><th scope="row">${this.escape(node.display_name || node.key || "")}<small>${this.escape(node.key || "")}</small></th><td>${this.escape(item.affected_count)}</td><td>${this.escape(item.direct_affected_count)}</td><td><span class="openinfra-spof-ratio" aria-label="${this.escape(`${Math.round(ratio * 100)} %`)}"><span style="width:${Math.round(ratio * 100)}%"></span></span>${Math.round(ratio * 100)} %</td><td>${this.escape(sample || "—")}</td></tr>`;
    }).join("");
    return `<section class="openinfra-spof-ranking" aria-labelledby="openinfra-spof-ranking-title"><div class="d-flex flex-wrap justify-content-between gap-2"><h4 id="openinfra-spof-ranking-title" class="h6">${this.escape(this.i18n.t("spofRanking"))}</h4><span class="badge ${complete ? "text-bg-success" : "text-bg-warning"}">${this.escape(complete ? this.i18n.t("completeAnalysis") : this.i18n.t("boundedAnalysis"))}</span></div><p class="small text-muted">${this.escape(`${result.spof_count || 0} SPOF · ${result.node_count || 0} nœuds · ${result.edge_count || 0} relations`)}</p><div class="table-responsive"><table class="table table-sm align-middle"><caption class="visually-hidden">${this.escape(this.i18n.t("spofRanking"))}</caption><thead><tr><th scope="col">#</th><th scope="col">${this.escape(this.i18n.t("candidate"))}</th><th scope="col">${this.escape(this.i18n.t("affectedNodes"))}</th><th scope="col">${this.escape(this.i18n.t("directAffected"))}</th><th scope="col">${this.escape(this.i18n.t("impactRatio"))}</th><th scope="col">${this.escape(this.i18n.t("affectedSample"))}</th></tr></thead><tbody>${rows || `<tr><td colspan="6">${this.escape(this.i18n.t("noSpofDetected"))}</td></tr>`}</tbody></table></div></section>`;
  }

  renderField(rawField) {
    const field = normalizeFieldDefinition(rawField);
    const required = field.required ? " required" : "";
    const requiredText = field.required ? `<span class="openinfra-required-marker" aria-hidden="true">*</span><span class="visually-hidden"> (${this.escape(this.i18n.t("requiredIndicator"))})</span>` : "";
    const value = field.defaultValue ?? "";
    const visibility = this.fieldVisibilityAttributes(field);
    const common = ` name="${this.escape(field.name)}" data-field="${this.escape(field.name)}" aria-invalid="false"`;
    if (this.isCountryField(field)) {
      const selected = field.defaultValue || "";
      return `<label${visibility} class="col-md-6 col-xl-4 form-label">${this.escape(this.i18n.label(field.label || "Pays"))}${requiredText}<select class="form-select"${common}${required}><option value=""></option>${this.renderCountryOptionGroups(selected)}</select></label>`;
    }
    if (field.type === "organization-select") {
      const options = this.organizationOptions();
      const fallback = field.defaultValue || this.state.organization || "default";
      const renderedOptions = options.length > 0 ? options : [{ value: fallback, label: fallback }];
      return `<label${visibility} class="col-md-6 col-xl-4 form-label">${this.escape(field.label || "Organisation")}${requiredText}<select class="form-select"${common}${required}>${this.renderOptions(renderedOptions, fallback)}</select></label>`;
    }
    if (field.type === "partner-select") {
      const options = this.partnerOptions(field.partnerKind || null);
      const fallback = field.defaultValue || "";
      const renderedOptions = options.length > 0 ? options : (fallback ? [{ value: fallback, label: fallback }] : []);
      const selectedValue = renderedOptions.length === 1 ? this.optionValue(renderedOptions[0]) : fallback;
      return `<label${visibility} class="col-md-6 col-xl-4 form-label">${this.escape(field.label || "Partenaire")}${requiredText}<select class="form-select"${common}${required}><option value=""></option>${this.renderOptions(renderedOptions, selectedValue)}</select></label>`;
    }
    if (field.type === "hidden") {
      return `<input type="hidden"${common} value="${this.escape(value)}">`;
    }
    if (field.type === "file") {
      const attributes = inputAttributesForField(field);
      const accept = attributes.accept ? ` accept="${this.escape(attributes.accept)}"` : "";
      const capture = attributes.capture ? ` capture="${this.escape(attributes.capture)}"` : "";
      return `<label${visibility} class="col-12 form-label">${this.escape(this.i18n.label(field.label || field.name))}${requiredText}<input class="form-control" type="file"${common}${accept}${capture}${required}><span class="form-text">JPEG, PNG, WebP ou PDF — 2 Mio maximum.</span></label>`;
    }
    if (field.type === "tenant-select") {
      const options = this.tenantOptions();
      const fallback = field.defaultValue || this.state.tenant || this.state.organization || "default";
      const renderedOptions = options.length > 0 ? options : [{ value: fallback, label: fallback }];
      return `<label${visibility} class="col-md-6 col-xl-4 form-label">${this.escape(this.i18n.label(field.label || "Filiale/Subdivision"))}${requiredText}<select class="form-select"${common}${required}>${this.renderOptions(renderedOptions, field.defaultValue || this.state.tenant || fallback)}</select></label>`;
    }
    if (this.isDcimReferenceField(field)) {
      const options = this.dcimOptions(field);
      const fallback = field.defaultValue || "";
      const renderedOptions = options.length > 0 ? options : (fallback ? [{ value: fallback, label: fallback }] : []);
      const selectedValue = renderedOptions.length === 1 ? this.optionValue(renderedOptions[0]) : fallback;
      return `<label${visibility} class="col-md-6 col-xl-4 form-label">${this.escape(this.i18n.label(field.label || DCIM_REFERENCE_LABELS[this.dcimReferenceLevel(field)] || field.name))}${requiredText}<select class="form-select"${common}${required}><option value=""></option>${this.renderOptions(renderedOptions, selectedValue)}</select></label>`;
    }
    if (field.type === "select") {
      const options = this.selectOptionsForField(field);
      const source = field.optionsByField ? ` data-options-by-field="${this.escape(field.optionsByField)}"` : "";
      const map = field.optionsMap ? ` data-options-map="${this.escape(JSON.stringify(field.optionsMap))}"` : "";
      return `<label${visibility} class="col-md-6 col-xl-4 form-label">${this.escape(this.i18n.label(field.label || field.name))}${requiredText}<select class="form-select"${common}${source}${map}${required}><option value=""></option>${this.renderOptions(options, value)}</select></label>`;
    }
    if (field.type === "boolean") {
      const defaultBoolean = field.defaultValue === true || String(field.defaultValue).toLowerCase() === "true";
      return `<label${visibility} class="col-md-6 col-xl-4 form-label">${this.escape(this.i18n.label(field.label || field.name))}<select class="form-select"${common}><option value="false"${defaultBoolean ? "" : " selected"}>${this.escape(this.i18n.t("no"))}</option><option value="true"${defaultBoolean ? " selected" : ""}>${this.escape(this.i18n.t("yes"))}</option></select></label>`;
    }
    const attributes = inputAttributesForField(field);
    const htmlAttributes = Object.entries(attributes).map(([key, attributeValue]) => {
      if (attributeValue === undefined || attributeValue === null || attributeValue === false) {
        return "";
      }
      const htmlName = { maxLength: "maxlength", inputMode: "inputmode", autoComplete: "autocomplete" }[key] || key;
      return attributeValue === true ? ` ${htmlName}` : ` ${htmlName}="${this.escape(attributeValue)}"`;
    }).join("");
    if (field.type === "textarea" || field.type === "json") {
      return `<label${visibility} class="col-12 form-label">${this.escape(this.i18n.label(field.label || field.name))}${requiredText}<textarea class="form-control font-monospace" rows="10"${common} placeholder="${this.escape(this.i18n.label(field.placeholder || ""))}"${htmlAttributes}${required}>${this.escape(value)}</textarea></label>`;
    }
    const inputType = inputTypeForField(field);
    return `<label${visibility} class="col-md-6 col-xl-4 form-label">${this.escape(this.i18n.label(field.label || field.name))}${requiredText}<input class="form-control" type="${this.escape(inputType)}"${common} value="${this.escape(value)}" placeholder="${this.escape(this.i18n.label(field.placeholder || ""))}"${htmlAttributes}${required}></label>`;
  }

  fieldVisibilityAttributes(field) {
    if (!field.visibleWhen) {
      return "";
    }
    return ` data-visible-when-field="${this.escape(field.visibleWhen.field)}" data-visible-when-value="${this.escape(field.visibleWhen.value)}"`;
  }

  isCountryField(field) {
    const normalized = String(field.name || "").toLowerCase();
    return field.type === "country-select" || normalized === "country" || normalized === "country_code";
  }

  renderCountryOptionGroups(selectedValue = "") {
    const groups = Array.isArray(this.state.countryCatalog?.items) ? this.state.countryCatalog.items : [];
    if (groups.length === 0) {
      return this.renderOptions([
        { value: "FR", label: this.i18n.countryName("FR", "France") },
        { value: "GB", label: this.i18n.countryName("GB", "United Kingdom") },
        { value: "US", label: this.i18n.countryName("US", "United States") }
      ], selectedValue);
    }
    return groups.map((group) => {
      const continent = this.escape(this.i18n.continentName(group.continent));
      const countries = Array.isArray(group.countries) ? group.countries : [];
      const options = countries.map((country) => {
        const code = String(country.code || "");
        const label = this.i18n.countryName(code, country.name || code);
        return `<option value="${this.escape(code)}" ${selectedValue === code ? "selected" : ""}>${this.escape(label)}</option>`;
      }).join("");
      return `<optgroup label="${continent}">${options}</optgroup>`;
    }).join("");
  }

  dcimReferenceLevel(field) {
    const name = String(field.name || "").toLowerCase();
    const normalized = name.replace(/_code$/, "");
    if (["site"].includes(normalized)) return "site";
    if (["building"].includes(normalized)) return "building";
    if (["floor"].includes(normalized)) return "floor";
    if (["room"].includes(normalized)) return "room";
    if (["zone"].includes(normalized)) return "zone";
    if (["rack"].includes(normalized)) return "rack";
    if (["row", "line"].includes(normalized)) return "row";
    if (["column"].includes(normalized)) return "column";
    return normalized;
  }

  isDcimReferenceField(field) {
    return DCIM_REFERENCE_FIELDS.has(String(field.name || "").toLowerCase());
  }

  dcimOptions(field) {
    const level = this.dcimReferenceLevel(field);
    const sites = Array.isArray(this.state.dcimCatalog?.sites) ? this.state.dcimCatalog.sites : [];
    const options = [];
    const seen = new Set();
    const selectable = (item) => item && item.selectable !== false && item.status !== "retired";
    const push = (value, label) => {
      const normalized = String(value || "").trim();
      if (!normalized || seen.has(`${level}:${normalized}`)) {
        return;
      }
      seen.add(`${level}:${normalized}`);
      options.push({ value: normalized, label: label || normalized });
    };
    for (const site of sites) {
      if (!selectable(site)) {
        continue;
      }
      const siteCode = site.code;
      if (level === "site") {
        push(siteCode, `${site.code}${site.name ? ` — ${site.name}` : ""}`);
      }
      for (const building of Array.isArray(site.buildings) ? site.buildings : []) {
        if (!selectable(building)) {
          continue;
        }
        const buildingCode = building.code;
        if (level === "building") {
          push(buildingCode, `${building.code}${building.name ? ` — ${building.name}` : ""} (${siteCode})`);
        }
        for (const floor of Array.isArray(building.floors) ? building.floors : []) {
          if (!selectable(floor)) {
            continue;
          }
          if (level === "floor") {
            push(floor.code, `${floor.code} — ${this.i18n.floorName(floor.level_index, floor.name)} (${siteCode}/${buildingCode})`);
          }
        }
        for (const room of Array.isArray(building.rooms) ? building.rooms : []) {
          if (!selectable(room)) {
            continue;
          }
          const roomCode = room.code;
          if (level === "room") {
            push(roomCode, `${room.code}${room.name ? ` — ${room.name}` : ""} (${siteCode}/${buildingCode})`);
          }
          for (const zone of Array.isArray(room.zones) ? room.zones : []) {
            if (selectable(zone) && level === "zone") {
              push(zone.code, `${zone.code}${zone.name ? ` — ${zone.name}` : ""} (${siteCode}/${buildingCode}/${roomCode})`);
            }
          }
          for (const rack of Array.isArray(room.racks) ? room.racks : []) {
            const rackCode = rack.code || rack.rack || rack.name;
            if (selectable(rack) && level === "rack") {
              push(rackCode, `${rackCode}${rack.label ? ` — ${rack.label}` : ""} (${siteCode}/${buildingCode}/${roomCode})`);
            }
          }
          for (const row of Array.isArray(room.rows) ? room.rows : []) {
            if (level === "row") {
              push(row, `${row} (${siteCode}/${buildingCode}/${roomCode})`);
            }
          }
          for (const column of Array.isArray(room.columns) ? room.columns : []) {
            if (level === "column") {
              push(column, `${column} (${siteCode}/${buildingCode}/${roomCode})`);
            }
          }
        }
      }
    }
    return options;
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
      return this.i18n.label(String(option.label));
    }
    return this.i18n.optionLabel(String(option || ""));
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

  bindConditionalFields() {
    for (const target of document.querySelectorAll("[data-visible-when-field]")) {
      const source = document.querySelector(`[data-field="${target.dataset.visibleWhenField}"]`);
      if (!source) {
        continue;
      }
      const refresh = () => {
        const visible = source.value === target.dataset.visibleWhenValue;
        target.hidden = !visible;
        for (const input of target.querySelectorAll("[data-field]")) {
          input.disabled = !visible;
        }
      };
      source.addEventListener("change", refresh);
      refresh();
    }
  }

  operationFieldDefinitions() {
    const operation = this.state.selected || {};
    return [...(operation.query || []), ...(operation.body || [])].map((field, index) => normalizeFieldDefinition(field, index));
  }

  validateOperationForm(form) {
    const fields = this.operationFieldDefinitions();
    const countryCode = formCountryCode(form);
    let valid = true;
    for (const field of fields) {
      const control = [...form.querySelectorAll("[data-field]")].find((candidate) => candidate.dataset.field === field.name);
      if (!control || control.disabled) {
        continue;
      }
      if (field.type === "file") {
        const file = control.files?.[0];
        const accepted = new Set(["image/jpeg", "image/png", "image/webp", "application/pdf"]);
        let message = "";
        if (file && file.size > 2 * 1024 * 1024) {
          message = "Le fichier dépasse la limite de 2 Mio.";
        } else if (file && !accepted.has(file.type)) {
          message = "Le format de fichier n’est pas autorisé.";
        }
        control.setCustomValidity(message);
        valid = valid && !message;
      } else if (!validateControl(control, field, this.i18n, { countryCode })) {
        valid = false;
      }
    }
    for (const control of form.querySelectorAll("input, select, textarea")) {
      const controlValid = control.disabled || control.checkValidity();
      control.setAttribute("aria-invalid", controlValid ? "false" : "true");
      valid = valid && controlValid;
    }
    return valid;
  }

  bindOperationFieldValidation() {
    const form = document.getElementById("openinfra-operation-form");
    if (!form) {
      return;
    }
    const fieldMap = new Map(this.operationFieldDefinitions().map((field) => [field.name, field]));
    const validateOne = (control) => {
      const field = fieldMap.get(control.dataset.field);
      if (field && !control.disabled) {
        if (field.type === "file") {
          control.setCustomValidity("");
          control.setAttribute("aria-invalid", "false");
        } else {
          validateControl(control, field, this.i18n, { countryCode: formCountryCode(form) });
        }
      }
    };
    const validateAll = () => {
      for (const control of form.querySelectorAll("[data-field]")) {
        validateOne(control);
      }
    };
    for (const control of form.querySelectorAll("[data-field]")) {
      control.addEventListener("input", () => validateOne(control));
      control.addEventListener("change", () => {
        validateOne(control);
        if (["country", "country_code"].includes(control.dataset.field)) {
          validateAll();
        }
      });
      control.addEventListener("blur", () => validateOne(control));
    }
  }

  bindEvents() {
    this.bindConditionalFields();
    this.bindOperationFieldValidation();
    document.getElementById("openinfra-language")?.addEventListener("change", (event) => {
      this.setLanguage(event.target.value);
    });
    document.getElementById("openinfra-operation-form")?.addEventListener("submit", (event) => {
      event.preventDefault();
      const form = event.currentTarget;
      if (!this.validateOperationForm(form)) {
        form.reportValidity();
        return;
      }
      this.executeSelected();
    });
    document.getElementById("openinfra-organization")?.addEventListener("change", async (event) => {
      const organization = event.target.value;
      const tenant = this.tenantOptions(organization)[0]?.value || organization;
      this.state = { ...this.state, organization, tenant };
      await this.refreshTenantCatalog();
      await this.refreshPartnerCatalog();
      await this.refreshDcimCatalog();
      this.render();
    });
    document.getElementById("openinfra-tenant")?.addEventListener("input", (event) => {
      this.state = { ...this.state, tenant: event.target.value };
    });
    document.getElementById("openinfra-tenant")?.addEventListener("change", async (event) => {
      this.state = { ...this.state, tenant: event.target.value };
      await this.refreshDcimCatalog();
      this.render();
    });
    for (const selector of document.querySelectorAll('select[data-field="organization_id"]')) {
      selector.addEventListener("change", async (event) => {
        const organization = event.target.value;
        const tenant = this.tenantOptions(organization)[0]?.value || organization;
        this.state = { ...this.state, organization, tenant };
        await this.refreshTenantCatalog();
        await this.refreshPartnerCatalog();
        await this.refreshDcimCatalog();
        this.render();
      });
    }
    for (const selector of document.querySelectorAll('select[data-field="tenant_id"]')) {
      selector.addEventListener("change", (event) => {
        this.state = { ...this.state, tenant: event.target.value };
      });
    }
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
    document.getElementById("openinfra-compact-menu-button")?.addEventListener("click", () => {
      this.state = { ...this.state, mobileSidebarOpen: !this.state.mobileSidebarOpen, megaMenuModuleId: null };
      this.render();
    });
    document.getElementById("openinfra-navigation-backdrop")?.addEventListener("click", () => this.closeResponsiveNavigation());
    document.getElementById("openinfra-mega-menu-close")?.addEventListener("click", () => this.closeResponsiveNavigation(true));
    document.getElementById("openinfra-compact-navigation-close")?.addEventListener("click", () => this.closeResponsiveNavigation(true));
    const componentButtons = Array.from(document.querySelectorAll("[data-module-id]"));
    componentButtons.forEach((button, index) => {
      button.addEventListener("mouseenter", () => this.openMegaMenu(button.dataset.moduleId, button));
      button.addEventListener("focus", () => this.openMegaMenu(button.dataset.moduleId, button));
      button.addEventListener("click", () => {
        this.lastNavigationModuleId = button.dataset.moduleId;
        this.handleModuleNavigation(button.dataset.moduleId);
      });
      button.addEventListener("keydown", (event) => {
        const focusAt = (targetIndex) => componentButtons[targetIndex]?.focus();
        if (event.key === "ArrowRight") {
          event.preventDefault();
          focusAt((index + 1) % componentButtons.length);
        } else if (event.key === "ArrowLeft") {
          event.preventDefault();
          focusAt((index - 1 + componentButtons.length) % componentButtons.length);
        } else if (event.key === "Home") {
          event.preventDefault();
          focusAt(0);
        } else if (event.key === "End") {
          event.preventDefault();
          focusAt(componentButtons.length - 1);
        } else if (event.key === "ArrowDown" && button.dataset.moduleId !== "overview") {
          event.preventDefault();
          this.openMegaMenu(button.dataset.moduleId, button);
          window.requestAnimationFrame(() => document.querySelector(".openinfra-mega-menu .openinfra-sidebar-operation")?.focus());
        }
      });
    });
    for (const button of document.querySelectorAll("[data-accordion-id]")) {
      button.addEventListener("click", () => this.toggleAccordion(button.dataset.accordionId));
    }
    for (const button of document.querySelectorAll("[data-context-module-id]")) {
      button.addEventListener("click", () => this.toggleSidebarContext(button.dataset.contextModuleId, button.dataset.contextLabel));
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
    const module = OPENINFRA_MODULES.find((item) => item.id === moduleId);
    if (!module) {
      return;
    }
    const wasOpen = this.state.openedModules.has(moduleId);
    this.state = {
      ...this.state,
      activeNavigationModuleId: module.id,
      openedModules: wasOpen ? new Set() : new Set([moduleId]),
      openedContexts: new Set()
    };
    this.render();
  }

  toggleSidebarContext(moduleId, contextLabel) {
    const module = OPENINFRA_MODULES.find((item) => item.id === moduleId);
    if (!module || !contextLabel) {
      return;
    }
    const contextKey = this.sidebarContextKey(moduleId, contextLabel);
    const wasOpen = this.state.openedContexts.has(contextKey);
    const openedContexts = new Set();
    if (!wasOpen) {
      openedContexts.add(contextKey);
    }
    this.state = {
      ...this.state,
      activeNavigationModuleId: module.id,
      openedModules: new Set([moduleId]),
      openedContexts
    };
    this.render();
  }

  selectModule(moduleId) {
    const module = OPENINFRA_MODULES.find((item) => item.id === moduleId);
    if (!module) {
      return;
    }
    const openedModules = new Set(this.state.openedModules);
    const openedContexts = new Set(this.state.openedContexts);
    if (module.id === "overview") {
      openedModules.clear();
      openedContexts.clear();
    } else {
      openedModules.add(module.id);
      this.removeModuleContexts(openedContexts, module.id);
      const defaultContext = this.contextForOperation(module, module.operations[0].id);
      if (defaultContext) {
        openedContexts.add(this.sidebarContextKey(module.id, defaultContext.label));
      }
    }
    const operation = module.operations[0];
    const catalogLoading = module.id !== "overview" && this.operationCatalogsNeedLoading(operation);
    this.state = { ...this.state, activeModuleId: module.id, activeNavigationModuleId: module.id, selected: operation, openedModules, openedContexts, result: null, error: null, catalogLoading, mobileSidebarOpen: false, megaMenuModuleId: null };
    this.render();
    if (catalogLoading) {
      void this.loadCatalogsForOperation(operation);
    }
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
        const openedModules = new Set(this.state.openedModules);
        const openedContexts = new Set(this.state.openedContexts);
        if (module.id === "overview") {
          openedModules.clear();
          openedContexts.clear();
        } else {
          openedModules.add(module.id);
          this.removeModuleContexts(openedContexts, module.id);
          const context = this.contextForOperation(module, operation.id);
          if (context) {
            openedContexts.add(this.sidebarContextKey(module.id, context.label));
          }
        }
        const catalogLoading = module.id !== "overview" && this.operationCatalogsNeedLoading(operation);
        this.state = {
          ...this.state,
          activeModuleId: module.id,
          activeNavigationModuleId: module.id,
          selected: operation,
          openedModules,
          openedContexts,
          result: null,
          error: null,
          catalogLoading,
          globalSearchQuery: "",
          mobileSidebarOpen: false, megaMenuModuleId: null
        };
        this.pendingMainFocus = true;
        this.render();
        if (catalogLoading) {
          void this.loadCatalogsForOperation(operation);
        }
        return;
      }
    }
  }

  selectOperation(operationId) {
    for (const module of OPENINFRA_MODULES) {
      const operation = module.operations.find((item) => item.id === operationId);
      if (operation) {
        const openedModules = new Set(this.state.openedModules);
        const openedContexts = new Set(this.state.openedContexts);
        if (module.id === "overview") {
          openedModules.clear();
          openedContexts.clear();
        } else {
          openedModules.add(module.id);
          this.removeModuleContexts(openedContexts, module.id);
          const context = this.contextForOperation(module, operation.id);
          if (context) {
            openedContexts.add(this.sidebarContextKey(module.id, context.label));
          }
        }
        const catalogLoading = module.id !== "overview" && this.operationCatalogsNeedLoading(operation);
        this.state = { ...this.state, activeModuleId: module.id, activeNavigationModuleId: module.id, selected: operation, openedModules, openedContexts, result: null, error: null, catalogLoading, mobileSidebarOpen: false, megaMenuModuleId: null };
        this.render();
        if (catalogLoading) {
          void this.loadCatalogsForOperation(operation);
        }
        return;
      }
    }
  }

  filePayload(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error("Impossible de lire la preuve sélectionnée."));
      reader.onload = () => {
        const result = String(reader.result || "");
        const separator = result.indexOf(",");
        if (separator < 0) {
          reject(new Error("Le fichier sélectionné est invalide."));
          return;
        }
        resolve({
          filename: file.name,
          media_type: file.type,
          content_base64: result.slice(separator + 1)
        });
      };
      reader.readAsDataURL(file);
    });
  }

  async executeSelected() {
    try {
      const payload = {};
      for (const input of document.querySelectorAll("[data-field]")) {
        if (input.disabled) {
          continue;
        }
        if (input.type === "file") {
          const file = input.files?.[0];
          payload[input.dataset.field] = file ? await this.filePayload(file) : undefined;
        } else {
          payload[input.dataset.field] = input.value;
        }
      }
      const data = await this.client().request(this.state.selected, payload);
      if (this.state.selected.id.startsWith("itam-organization")) {
        await this.refreshOrganizationCatalog();
        await this.refreshTenantCatalog();
      }
      if (this.state.selected.id.startsWith("itam-tenant")) {
        await this.refreshTenantCatalog();
      }
      if (this.state.selected.id.startsWith("itam-partner")) {
        await this.refreshPartnerCatalog();
      }
      if (this.state.selected.id.startsWith("dcim-")) {
        await this.refreshDcimCatalog();
      }
      this.state = { ...this.state, result: data, error: null };
    } catch (error) {
      this.state = { ...this.state, error, result: null };
    }
    this.render();
  }

  moduleForOperation(operation) {
    return OPENINFRA_MODULES.find((module) => module.operations.some((item) => item.id === operation.id)) || OPENINFRA_MODULES[0];
  }

  announce(message) {
    const region = document.getElementById("openinfra-live-region");
    if (!region) {
      return;
    }
    region.textContent = "";
    window.requestAnimationFrame(() => {
      region.textContent = String(message || "");
    });
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

  slugify(value) {
    return String(value ?? "context")
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "context";
  }
}

const openInfraRoot = document.getElementById("openinfra-root");
try {
  const dashboard = new OpenInfraDashboard(openInfraRoot);
  dashboard.start().catch((error) => renderFatalStartupError(openInfraRoot, error));
} catch (error) {
  renderFatalStartupError(openInfraRoot, error);
}
