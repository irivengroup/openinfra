from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar, Self

from openinfra.domain.common import ValidationError


@dataclass(frozen=True, slots=True)
class ResourceTypeDefinition:
    value: str
    label: str

    def as_dict(self) -> dict[str, str]:
        return {"value": self.value, "label": self.label}


@dataclass(frozen=True, slots=True)
class ResourceCategoryDefinition:
    value: str
    label: str
    types: tuple[ResourceTypeDefinition, ...]

    @property
    def default_type(self) -> str:
        return self.types[0].value

    def as_dict(self) -> dict[str, object]:
        return {
            "value": self.value,
            "label": self.label,
            "default_type": self.default_type,
            "types": [resource_type.as_dict() for resource_type in self.types],
        }


@dataclass(frozen=True, slots=True)
class ResourceClassification:
    category: str
    resource_type: str

    def as_dict(self) -> dict[str, str]:
        return {"resource_category": self.category, "resource_type": self.resource_type}


class ResourceTaxonomy:
    _CATEGORY_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"[a-z][a-z0-9-]{1,63}")
    _TYPE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"[a-z][a-z0-9-]{1,63}")

    CATEGORIES: ClassVar[tuple[ResourceCategoryDefinition, ...]] = (
        ResourceCategoryDefinition(
            "server",
            "Server",
            (
                ResourceTypeDefinition("physical-server", "Physical server"),
                ResourceTypeDefinition("rack-server", "Rack server"),
                ResourceTypeDefinition("blade-server", "Blade server"),
                ResourceTypeDefinition("tower-server", "Tower server"),
                ResourceTypeDefinition("hypervisor-host", "Hypervisor host"),
                ResourceTypeDefinition("virtual-machine", "Virtual machine"),
                ResourceTypeDefinition("container-host", "Container host"),
                ResourceTypeDefinition("compute-appliance", "Compute appliance"),
            ),
        ),
        ResourceCategoryDefinition(
            "personal-computer",
            "Personal computer",
            (
                ResourceTypeDefinition("laptop", "Laptop"),
                ResourceTypeDefinition("desktop", "Desktop"),
                ResourceTypeDefinition("workstation", "Workstation"),
                ResourceTypeDefinition("thin-client", "Thin client"),
                ResourceTypeDefinition("all-in-one", "All-in-one"),
                ResourceTypeDefinition("tablet", "Tablet"),
                ResourceTypeDefinition("kiosk", "Kiosk"),
            ),
        ),
        ResourceCategoryDefinition(
            "monitor-peripheral",
            "Monitor and peripheral",
            (
                ResourceTypeDefinition("monitor", "Monitor"),
                ResourceTypeDefinition("keyboard", "Keyboard"),
                ResourceTypeDefinition("mouse", "Mouse"),
                ResourceTypeDefinition("docking-station", "Docking station"),
                ResourceTypeDefinition("webcam", "Webcam"),
                ResourceTypeDefinition("headset", "Headset"),
                ResourceTypeDefinition("printer", "Printer"),
                ResourceTypeDefinition("scanner", "Scanner"),
                ResourceTypeDefinition("barcode-scanner", "Barcode scanner"),
                ResourceTypeDefinition("kvm-console", "KVM console"),
            ),
        ),
        ResourceCategoryDefinition(
            "network-device",
            "Network device",
            (
                ResourceTypeDefinition("switch", "Switch"),
                ResourceTypeDefinition("core-switch", "Core switch"),
                ResourceTypeDefinition("distribution-switch", "Distribution switch"),
                ResourceTypeDefinition("access-switch", "Access switch"),
                ResourceTypeDefinition("router", "Router"),
                ResourceTypeDefinition("firewall", "Firewall"),
                ResourceTypeDefinition("load-balancer", "Load balancer"),
                ResourceTypeDefinition("vpn-gateway", "VPN gateway"),
                ResourceTypeDefinition("sdwan-edge", "SD-WAN edge"),
                ResourceTypeDefinition("wireless-controller", "Wireless controller"),
                ResourceTypeDefinition("wireless-access-point", "Wireless access point"),
                ResourceTypeDefinition("proxy-appliance", "Proxy appliance"),
                ResourceTypeDefinition("wan-accelerator", "WAN accelerator"),
                ResourceTypeDefinition("network-tap", "Network TAP"),
                ResourceTypeDefinition("packet-broker", "Packet broker"),
                ResourceTypeDefinition("network-interface", "Network interface"),
            ),
        ),
        ResourceCategoryDefinition(
            "storage",
            "Storage",
            (
                ResourceTypeDefinition("storage-array", "Storage array"),
                ResourceTypeDefinition("nas-appliance", "NAS appliance"),
                ResourceTypeDefinition("san-switch", "SAN switch"),
                ResourceTypeDefinition("storage-controller", "Storage controller"),
                ResourceTypeDefinition("storage-shelf", "Storage shelf"),
                ResourceTypeDefinition("disk", "Disk"),
                ResourceTypeDefinition("hdd", "HDD"),
                ResourceTypeDefinition("ssd", "SSD"),
                ResourceTypeDefinition("nvme-drive", "NVMe drive"),
                ResourceTypeDefinition("tape-library", "Tape library"),
                ResourceTypeDefinition("backup-appliance", "Backup appliance"),
                ResourceTypeDefinition("object-storage-node", "Object storage node"),
            ),
        ),
        ResourceCategoryDefinition(
            "power-supply",
            "Power supply",
            (
                ResourceTypeDefinition("ups", "UPS"),
                ResourceTypeDefinition("pdu", "PDU"),
                ResourceTypeDefinition("ats", "Automatic transfer switch"),
                ResourceTypeDefinition("sts", "Static transfer switch"),
                ResourceTypeDefinition("rectifier", "Rectifier"),
                ResourceTypeDefinition("inverter", "Inverter"),
                ResourceTypeDefinition("battery-pack", "Battery pack"),
                ResourceTypeDefinition("power-shelf", "Power shelf"),
                ResourceTypeDefinition("generator", "Generator"),
                ResourceTypeDefinition("busway", "Busway"),
                ResourceTypeDefinition("power-meter", "Power meter"),
            ),
        ),
        ResourceCategoryDefinition(
            "rack-facility",
            "Rack and facility",
            (
                ResourceTypeDefinition("rack", "Rack"),
                ResourceTypeDefinition("cabinet", "Cabinet"),
                ResourceTypeDefinition("patch-panel", "Patch panel"),
                ResourceTypeDefinition("fiber-panel", "Fiber panel"),
                ResourceTypeDefinition("cable-management", "Cable management"),
                ResourceTypeDefinition("containment", "Containment"),
                ResourceTypeDefinition("raised-floor-tile", "Raised floor tile"),
                ResourceTypeDefinition("sensor-probe", "Sensor probe"),
                ResourceTypeDefinition("rack-accessory", "Rack accessory"),
            ),
        ),
        ResourceCategoryDefinition(
            "cooling",
            "Cooling",
            (
                ResourceTypeDefinition("crac", "CRAC"),
                ResourceTypeDefinition("crah", "CRAH"),
                ResourceTypeDefinition("in-row-cooler", "In-row cooler"),
                ResourceTypeDefinition("rear-door-heat-exchanger", "Rear-door heat exchanger"),
                ResourceTypeDefinition("chiller", "Chiller"),
                ResourceTypeDefinition("cooling-tower", "Cooling tower"),
                ResourceTypeDefinition("heat-exchanger", "Heat exchanger"),
                ResourceTypeDefinition("humidifier", "Humidifier"),
                ResourceTypeDefinition("environmental-sensor", "Environmental sensor"),
            ),
        ),
        ResourceCategoryDefinition(
            "security-safety",
            "Security and safety",
            (
                ResourceTypeDefinition("cctv-camera", "CCTV camera"),
                ResourceTypeDefinition("access-control-reader", "Access control reader"),
                ResourceTypeDefinition("door-controller", "Door controller"),
                ResourceTypeDefinition("biometric-reader", "Biometric reader"),
                ResourceTypeDefinition("fire-panel", "Fire panel"),
                ResourceTypeDefinition("smoke-detector", "Smoke detector"),
                ResourceTypeDefinition("leak-detector", "Leak detector"),
                ResourceTypeDefinition("alarm-siren", "Alarm siren"),
            ),
        ),
        ResourceCategoryDefinition(
            "telecom",
            "Telecom",
            (
                ResourceTypeDefinition("pbx", "PBX"),
                ResourceTypeDefinition("voip-gateway", "VoIP gateway"),
                ResourceTypeDefinition("ip-phone", "IP phone"),
                ResourceTypeDefinition("conference-phone", "Conference phone"),
                ResourceTypeDefinition("modem", "Modem"),
                ResourceTypeDefinition("optical-transponder", "Optical transponder"),
                ResourceTypeDefinition("mux", "Multiplexer"),
                ResourceTypeDefinition("radio-link", "Radio link"),
            ),
        ),
        ResourceCategoryDefinition(
            "cloud-virtualization",
            "Cloud and virtualization",
            (
                ResourceTypeDefinition("cloud-account", "Cloud account"),
                ResourceTypeDefinition("cloud-region", "Cloud region"),
                ResourceTypeDefinition("vpc", "VPC"),
                ResourceTypeDefinition("cloud-subnet", "Cloud subnet"),
                ResourceTypeDefinition("security-group", "Security group"),
                ResourceTypeDefinition("cloud-load-balancer", "Cloud load balancer"),
                ResourceTypeDefinition("cloud-instance", "Cloud instance"),
                ResourceTypeDefinition("cloud-volume", "Cloud volume"),
                ResourceTypeDefinition("kubernetes-cluster", "Kubernetes cluster"),
                ResourceTypeDefinition("kubernetes-node", "Kubernetes node"),
                ResourceTypeDefinition("container", "Container"),
                ResourceTypeDefinition("namespace", "Namespace"),
            ),
        ),
        ResourceCategoryDefinition(
            "software-service",
            "Software and service",
            (
                ResourceTypeDefinition("application", "Application"),
                ResourceTypeDefinition("service", "Service"),
                ResourceTypeDefinition("api-service", "API service"),
                ResourceTypeDefinition("web-service", "Web service"),
                ResourceTypeDefinition("database-instance", "Database instance"),
                ResourceTypeDefinition("middleware", "Middleware"),
                ResourceTypeDefinition("message-broker", "Message broker"),
                ResourceTypeDefinition("license", "License"),
                ResourceTypeDefinition("certificate", "Certificate"),
                ResourceTypeDefinition("dns-zone", "DNS zone"),
            ),
        ),
        ResourceCategoryDefinition(
            "cable-connectivity",
            "Cable and connectivity",
            (
                ResourceTypeDefinition("copper-cable", "Copper cable"),
                ResourceTypeDefinition("fiber-cable", "Fiber cable"),
                ResourceTypeDefinition("patch-cord", "Patch cord"),
                ResourceTypeDefinition("trunk-cable", "Trunk cable"),
                ResourceTypeDefinition("transceiver", "Transceiver"),
                ResourceTypeDefinition("sfp-module", "SFP module"),
                ResourceTypeDefinition("qsfp-module", "QSFP module"),
                ResourceTypeDefinition("patch-cassette", "Patch cassette"),
            ),
        ),
        ResourceCategoryDefinition(
            "mobile-iot",
            "Mobile and IoT",
            (
                ResourceTypeDefinition("smartphone", "Smartphone"),
                ResourceTypeDefinition("rugged-handheld", "Rugged handheld"),
                ResourceTypeDefinition("iot-gateway", "IoT gateway"),
                ResourceTypeDefinition("industrial-controller", "Industrial controller"),
                ResourceTypeDefinition("plc", "PLC"),
                ResourceTypeDefinition("sensor", "Sensor"),
                ResourceTypeDefinition("actuator", "Actuator"),
            ),
        ),
        ResourceCategoryDefinition(
            "other",
            "Other",
            (
                ResourceTypeDefinition("generic-asset", "Generic asset"),
                ResourceTypeDefinition("unknown-device", "Unknown device"),
                ResourceTypeDefinition("external-resource", "External resource"),
            ),
        ),
    )

    LEGACY_KIND_MAP: ClassVar[dict[str, ResourceClassification]] = {
        "generic": ResourceClassification("other", "generic-asset"),
        "device": ResourceClassification("other", "unknown-device"),
        "interface": ResourceClassification("network-device", "network-interface"),
        "application": ResourceClassification("software-service", "application"),
        "database": ResourceClassification("software-service", "database-instance"),
        "service": ResourceClassification("software-service", "service"),
        "virtual-machine": ResourceClassification("server", "virtual-machine"),
    }

    @classmethod
    def categories(cls) -> tuple[ResourceCategoryDefinition, ...]:
        return cls.CATEGORIES

    @classmethod
    def as_dict(cls) -> dict[str, object]:
        return {
            "version": "2026.07",
            "categories": [category.as_dict() for category in cls.CATEGORIES],
            "legacy_kind_aliases": {
                name: classification.as_dict()
                for name, classification in sorted(cls.LEGACY_KIND_MAP.items())
            },
        }

    @classmethod
    def category_values(cls) -> tuple[str, ...]:
        return tuple(category.value for category in cls.CATEGORIES)

    @classmethod
    def all_type_values(cls) -> tuple[str, ...]:
        return tuple(
            resource_type.value
            for category in cls.CATEGORIES
            for resource_type in category.types
        )

    @classmethod
    def normalize_token(cls, value: str, label: str) -> str:
        normalized = value.strip().lower().replace("_", "-")
        normalized = re.sub(r"\s+", "-", normalized)
        pattern = cls._CATEGORY_PATTERN if label == "resource category" else cls._TYPE_PATTERN
        if not pattern.fullmatch(normalized):
            raise ValidationError(label + " must use 2 to 64 lowercase safe characters")
        return normalized

    @classmethod
    def type_values_for_category(cls, category: str) -> tuple[str, ...]:
        normalized_category = cls.normalize_token(category, "resource category")
        definition = cls._category_by_value().get(normalized_category)
        if definition is None:
            raise ValidationError("unsupported resource category: " + normalized_category)
        return tuple(resource_type.value for resource_type in definition.types)

    @classmethod
    def default_type_for_category(cls, category: str) -> str:
        normalized_category = cls.normalize_token(category, "resource category")
        definition = cls._category_by_value().get(normalized_category)
        if definition is None:
            raise ValidationError("unsupported resource category: " + normalized_category)
        return definition.default_type

    @classmethod
    def classify(
        cls,
        *,
        kind: str | None,
        resource_category: str | None,
        resource_type: str | None,
        attributes: dict[str, Any] | None = None,
    ) -> ResourceClassification:
        payload = attributes or {}
        requested_category = cls._optional_text(resource_category) or cls._optional_text(
            payload.get("resource_category")
        )
        requested_type = cls._optional_text(resource_type) or cls._optional_text(
            payload.get("resource_type")
        )
        requested_kind = cls._optional_text(kind)

        if requested_category is None and requested_kind in cls.LEGACY_KIND_MAP:
            legacy = cls.LEGACY_KIND_MAP[requested_kind]
            requested_category = legacy.category
            requested_type = requested_type or legacy.resource_type
        elif requested_category is None and requested_kind is not None:
            normalized_kind = cls.normalize_token(requested_kind, "resource category")
            if normalized_kind in cls._category_by_value():
                requested_category = normalized_kind
            elif normalized_kind in cls._type_to_category():
                requested_category = cls._type_to_category()[normalized_kind]
                requested_type = requested_type or normalized_kind
            else:
                raise ValidationError("unsupported resource category or type: " + normalized_kind)

        if requested_category is None:
            raise ValidationError("resource category is mandatory")
        category = cls.normalize_token(requested_category, "resource category")
        if category not in cls._category_by_value():
            raise ValidationError("unsupported resource category: " + category)

        if requested_type is None:
            resource_type = cls.default_type_for_category(category)
        else:
            resource_type = cls.normalize_token(requested_type, "resource type")
        allowed_types = set(cls.type_values_for_category(category))
        if resource_type not in allowed_types:
            raise ValidationError(
                "resource type " + resource_type + " is not allowed for category " + category
            )
        return ResourceClassification(category=category, resource_type=resource_type)

    @classmethod
    def _optional_text(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        return text.lower().replace("_", "-")

    @classmethod
    def _category_by_value(cls) -> dict[str, ResourceCategoryDefinition]:
        return {category.value: category for category in cls.CATEGORIES}

    @classmethod
    def _type_to_category(cls) -> dict[str, str]:
        return {
            resource_type.value: category.value
            for category in cls.CATEGORIES
            for resource_type in category.types
        }
