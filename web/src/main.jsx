import 'bootstrap/dist/css/bootstrap.min.css';
import './openinfra-theme.css';
import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';

const ICONS = {
  speedometer2: 'M8 4a.5.5 0 0 1 .5.5V6a.5.5 0 0 1-1 0V4.5A.5.5 0 0 1 8 4z',
  table: 'M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V2z',
  reference: 'M1 2a2 2 0 0 1 2-2h1.6a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V2zm6.7 0a2 2 0 0 1 2-2h1.6a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H9.7a2 2 0 0 1-2-2V2zm6.25.55A1.8 1.8 0 0 1 15 4.18v7.64a1.8 1.8 0 0 1-1.05 1.63V2.55z',
  asset: 'M2 1a2 2 0 0 1 2-2h5.6a2 2 0 0 1 1.414.586l2.4 2.4A2 2 0 0 1 14 3.4V14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V1zm2 .8a.8.8 0 0 0-.8.8v10.8a.8.8 0 0 0 .8.8h8a.8.8 0 0 0 .8-.8V4.4h-2.2a1.8 1.8 0 0 1-1.8-1.8V.8H4zm1.25 5.05a.85.85 0 1 0 0-1.7.85.85 0 0 0 0 1.7zm2.05-.6a.6.6 0 0 0 0 1.2h3.9a.6.6 0 1 0 0-1.2H7.3zm-2.05 4.6a.85.85 0 1 0 0-1.7.85.85 0 0 0 0 1.7zm2.05-.6a.6.6 0 1 0 0 1.2h3.9a.6.6 0 1 0 0-1.2H7.3z',
  grid: 'M1 2.5A1.5 1.5 0 0 1 2.5 1h3A1.5 1.5 0 0 1 7 2.5v3A1.5 1.5 0 0 1 5.5 7h-3A1.5 1.5 0 0 1 1 5.5v-3z',
  home: 'M8 3.293l6 6V15a1 1 0 0 1-1 1h-3v-4H6v4H3a1 1 0 0 1-1-1V9.293l6-6z',
  search: 'M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.099zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z',
  menu: 'M2 4h12v1.4H2V4zm0 3.3h12v1.4H2V7.3zm0 3.3h12V12H2v-1.4z',
  activity: 'M6.5 12a.5.5 0 0 1-.447-.276L3.382 6.382 1.894 9.36A.5.5 0 0 1 1.447 9.636H.5a.5.5 0 0 1 0-1h.638l1.915-3.83a.5.5 0 0 1 .894 0L6.5 9.91l2.553-5.105a.5.5 0 0 1 .894 0l1.915 3.83h3.638a.5.5 0 0 1 0 1h-3.947a.5.5 0 0 1-.447-.276L9.5 6.382l-2.553 5.342A.5.5 0 0 1 6.5 12z',
  shield: 'M5.338 1.59a61.44 61.44 0 0 0-2.837.856.48.48 0 0 0-.328.39c-.554 4.157.726 7.19 2.253 9.188A10.7 10.7 0 0 0 8 15a10.7 10.7 0 0 0 3.574-2.976c1.527-1.998 2.807-5.031 2.253-9.188a.48.48 0 0 0-.328-.39 61.44 61.44 0 0 0-2.837-.856C9.552 1.29 8.531 1.067 8 1.067c-.531 0-1.552.223-2.662.523z',
};

const RESOURCE_TAXONOMY = {
  'server': [
    {
      'value': 'rack-server',
      'label': 'Rack server'
    },
    {
      'value': 'blade-server',
      'label': 'Blade server'
    },
    {
      'value': 'tower-server',
      'label': 'Tower server'
    },
    {
      'value': 'hypervisor-host',
      'label': 'Hypervisor host'
    },
    {
      'value': 'virtual-machine',
      'label': 'Virtual machine'
    },
    {
      'value': 'container-host',
      'label': 'Container host'
    },
    {
      'value': 'compute-appliance',
      'label': 'Compute appliance'
    }
  ],
  'personal-computer': [
    {
      'value': 'laptop',
      'label': 'Laptop'
    },
    {
      'value': 'desktop',
      'label': 'Desktop'
    },
    {
      'value': 'workstation',
      'label': 'Workstation'
    },
    {
      'value': 'thin-client',
      'label': 'Thin client'
    },
    {
      'value': 'all-in-one',
      'label': 'All-in-one'
    },
    {
      'value': 'tablet',
      'label': 'Tablet'
    },
    {
      'value': 'kiosk',
      'label': 'Kiosk'
    }
  ],
  'monitor-peripheral': [
    {
      'value': 'monitor',
      'label': 'Monitor'
    },
    {
      'value': 'keyboard',
      'label': 'Keyboard'
    },
    {
      'value': 'mouse',
      'label': 'Mouse'
    },
    {
      'value': 'docking-station',
      'label': 'Docking station'
    },
    {
      'value': 'webcam',
      'label': 'Webcam'
    },
    {
      'value': 'headset',
      'label': 'Headset'
    },
    {
      'value': 'printer',
      'label': 'Printer'
    },
    {
      'value': 'scanner',
      'label': 'Scanner'
    },
    {
      'value': 'barcode-scanner',
      'label': 'Barcode scanner'
    },
    {
      'value': 'kvm-console',
      'label': 'KVM console'
    }
  ],
  'network-device': [
    {
      'value': 'switch',
      'label': 'Switch'
    },
    {
      'value': 'core-switch',
      'label': 'Core switch'
    },
    {
      'value': 'distribution-switch',
      'label': 'Distribution switch'
    },
    {
      'value': 'access-switch',
      'label': 'Access switch'
    },
    {
      'value': 'router',
      'label': 'Router'
    },
    {
      'value': 'firewall',
      'label': 'Firewall'
    },
    {
      'value': 'load-balancer',
      'label': 'Load balancer'
    },
    {
      'value': 'vpn-gateway',
      'label': 'VPN gateway'
    },
    {
      'value': 'sdwan-edge',
      'label': 'SD-WAN edge'
    },
    {
      'value': 'wireless-controller',
      'label': 'Wireless controller'
    },
    {
      'value': 'wireless-access-point',
      'label': 'Wireless access point'
    },
    {
      'value': 'proxy-appliance',
      'label': 'Proxy appliance'
    },
    {
      'value': 'wan-accelerator',
      'label': 'WAN accelerator'
    },
    {
      'value': 'network-tap',
      'label': 'Network TAP'
    },
    {
      'value': 'packet-broker',
      'label': 'Packet broker'
    },
    {
      'value': 'network-interface',
      'label': 'Network interface'
    }
  ],
  'storage': [
    {
      'value': 'storage-array',
      'label': 'Storage array'
    },
    {
      'value': 'nas-appliance',
      'label': 'NAS appliance'
    },
    {
      'value': 'san-switch',
      'label': 'SAN switch'
    },
    {
      'value': 'storage-controller',
      'label': 'Storage controller'
    },
    {
      'value': 'storage-shelf',
      'label': 'Storage shelf'
    },
    {
      'value': 'hdd',
      'label': 'HDD'
    },
    {
      'value': 'ssd',
      'label': 'SSD'
    },
    {
      'value': 'nvme-drive',
      'label': 'NVMe drive'
    },
    {
      'value': 'tape-library',
      'label': 'Tape library'
    },
    {
      'value': 'backup-appliance',
      'label': 'Backup appliance'
    },
    {
      'value': 'object-storage-node',
      'label': 'Object storage node'
    }
  ],
  'power-supply': [
    {
      'value': 'ups',
      'label': 'UPS'
    },
    {
      'value': 'pdu',
      'label': 'PDU'
    },
    {
      'value': 'ats',
      'label': 'Automatic transfer switch'
    },
    {
      'value': 'sts',
      'label': 'Static transfer switch'
    },
    {
      'value': 'rectifier',
      'label': 'Rectifier'
    },
    {
      'value': 'inverter',
      'label': 'Inverter'
    },
    {
      'value': 'battery-pack',
      'label': 'Battery pack'
    },
    {
      'value': 'power-shelf',
      'label': 'Power shelf'
    },
    {
      'value': 'generator',
      'label': 'Generator'
    },
    {
      'value': 'busway',
      'label': 'Busway'
    },
    {
      'value': 'power-meter',
      'label': 'Power meter'
    }
  ],
  'rack-facility': [
    {
      'value': 'rack',
      'label': 'Rack'
    },
    {
      'value': 'cabinet',
      'label': 'Cabinet'
    },
    {
      'value': 'patch-panel',
      'label': 'Patch panel'
    },
    {
      'value': 'fiber-panel',
      'label': 'Fiber panel'
    },
    {
      'value': 'cable-management',
      'label': 'Cable management'
    },
    {
      'value': 'containment',
      'label': 'Containment'
    },
    {
      'value': 'raised-floor-tile',
      'label': 'Raised floor tile'
    },
    {
      'value': 'sensor-probe',
      'label': 'Sensor probe'
    },
    {
      'value': 'rack-accessory',
      'label': 'Rack accessory'
    }
  ],
  'cooling': [
    {
      'value': 'crac',
      'label': 'CRAC'
    },
    {
      'value': 'crah',
      'label': 'CRAH'
    },
    {
      'value': 'in-row-cooler',
      'label': 'In-row cooler'
    },
    {
      'value': 'rear-door-heat-exchanger',
      'label': 'Rear-door heat exchanger'
    },
    {
      'value': 'chiller',
      'label': 'Chiller'
    },
    {
      'value': 'cooling-tower',
      'label': 'Cooling tower'
    },
    {
      'value': 'heat-exchanger',
      'label': 'Heat exchanger'
    },
    {
      'value': 'humidifier',
      'label': 'Humidifier'
    },
    {
      'value': 'environmental-sensor',
      'label': 'Environmental sensor'
    }
  ],
  'security-safety': [
    {
      'value': 'cctv-camera',
      'label': 'CCTV camera'
    },
    {
      'value': 'access-control-reader',
      'label': 'Access control reader'
    },
    {
      'value': 'door-controller',
      'label': 'Door controller'
    },
    {
      'value': 'biometric-reader',
      'label': 'Biometric reader'
    },
    {
      'value': 'fire-panel',
      'label': 'Fire panel'
    },
    {
      'value': 'smoke-detector',
      'label': 'Smoke detector'
    },
    {
      'value': 'leak-detector',
      'label': 'Leak detector'
    },
    {
      'value': 'alarm-siren',
      'label': 'Alarm siren'
    }
  ],
  'telecom': [
    {
      'value': 'pbx',
      'label': 'PBX'
    },
    {
      'value': 'voip-gateway',
      'label': 'VoIP gateway'
    },
    {
      'value': 'ip-phone',
      'label': 'IP phone'
    },
    {
      'value': 'conference-phone',
      'label': 'Conference phone'
    },
    {
      'value': 'modem',
      'label': 'Modem'
    },
    {
      'value': 'optical-transponder',
      'label': 'Optical transponder'
    },
    {
      'value': 'mux',
      'label': 'Multiplexer'
    },
    {
      'value': 'radio-link',
      'label': 'Radio link'
    }
  ],
  'cloud-virtualization': [
    {
      'value': 'cloud-account',
      'label': 'Cloud account'
    },
    {
      'value': 'cloud-region',
      'label': 'Cloud region'
    },
    {
      'value': 'vpc',
      'label': 'VPC'
    },
    {
      'value': 'cloud-subnet',
      'label': 'Cloud subnet'
    },
    {
      'value': 'security-group',
      'label': 'Security group'
    },
    {
      'value': 'cloud-load-balancer',
      'label': 'Cloud load balancer'
    },
    {
      'value': 'cloud-instance',
      'label': 'Cloud instance'
    },
    {
      'value': 'cloud-volume',
      'label': 'Cloud volume'
    },
    {
      'value': 'kubernetes-cluster',
      'label': 'Kubernetes cluster'
    },
    {
      'value': 'kubernetes-node',
      'label': 'Kubernetes node'
    },
    {
      'value': 'container',
      'label': 'Container'
    },
    {
      'value': 'namespace',
      'label': 'Namespace'
    }
  ],
  'software-service': [
    {
      'value': 'application',
      'label': 'Application'
    },
    {
      'value': 'service',
      'label': 'Service'
    },
    {
      'value': 'api-service',
      'label': 'API service'
    },
    {
      'value': 'web-service',
      'label': 'Web service'
    },
    {
      'value': 'database-instance',
      'label': 'Database instance'
    },
    {
      'value': 'middleware',
      'label': 'Middleware'
    },
    {
      'value': 'message-broker',
      'label': 'Message broker'
    },
    {
      'value': 'license',
      'label': 'License'
    },
    {
      'value': 'certificate',
      'label': 'Certificate'
    },
    {
      'value': 'dns-zone',
      'label': 'DNS zone'
    }
  ],
  'cable-connectivity': [
    {
      'value': 'copper-cable',
      'label': 'Copper cable'
    },
    {
      'value': 'fiber-cable',
      'label': 'Fiber cable'
    },
    {
      'value': 'patch-cord',
      'label': 'Patch cord'
    },
    {
      'value': 'trunk-cable',
      'label': 'Trunk cable'
    },
    {
      'value': 'transceiver',
      'label': 'Transceiver'
    },
    {
      'value': 'sfp-module',
      'label': 'SFP module'
    },
    {
      'value': 'qsfp-module',
      'label': 'QSFP module'
    },
    {
      'value': 'patch-cassette',
      'label': 'Patch cassette'
    }
  ],
  'mobile-iot': [
    {
      'value': 'smartphone',
      'label': 'Smartphone'
    },
    {
      'value': 'rugged-handheld',
      'label': 'Rugged handheld'
    },
    {
      'value': 'iot-gateway',
      'label': 'IoT gateway'
    },
    {
      'value': 'industrial-controller',
      'label': 'Industrial controller'
    },
    {
      'value': 'plc',
      'label': 'PLC'
    },
    {
      'value': 'sensor',
      'label': 'Sensor'
    },
    {
      'value': 'actuator',
      'label': 'Actuator'
    }
  ],
  'other': [
    {
      'value': 'generic-asset',
      'label': 'Generic asset'
    },
    {
      'value': 'unknown-device',
      'label': 'Unknown device'
    },
    {
      'value': 'external-resource',
      'label': 'External resource'
    }
  ]
};

const RESOURCE_CATEGORY_OPTIONS = [
  {
    'value': 'server',
    'label': 'Server'
  },
  {
    'value': 'personal-computer',
    'label': 'Personal computer'
  },
  {
    'value': 'monitor-peripheral',
    'label': 'Monitor and peripheral'
  },
  {
    'value': 'network-device',
    'label': 'Network device'
  },
  {
    'value': 'storage',
    'label': 'Storage'
  },
  {
    'value': 'power-supply',
    'label': 'Power supply'
  },
  {
    'value': 'rack-facility',
    'label': 'Rack and facility'
  },
  {
    'value': 'cooling',
    'label': 'Cooling'
  },
  {
    'value': 'security-safety',
    'label': 'Security and safety'
  },
  {
    'value': 'telecom',
    'label': 'Telecom'
  },
  {
    'value': 'cloud-virtualization',
    'label': 'Cloud and virtualization'
  },
  {
    'value': 'software-service',
    'label': 'Software and service'
  },
  {
    'value': 'cable-connectivity',
    'label': 'Cable and connectivity'
  },
  {
    'value': 'mobile-iot',
    'label': 'Mobile and IoT'
  },
  {
    'value': 'other',
    'label': 'Other'
  }
];

const MODULES = [
  { id: 'overview', label: 'Dashboard', icon: 'speedometer2', operations: [{ id: 'version', label: 'Version runtime', path: '/v1/version', method: 'GET', fields: [] }] },
  { id: 'rsot', label: 'RSOT (Ressource Source of Truth)', shortLabel: 'RSOT', icon: 'reference', operations: [
    { id: 'rsot-taxonomy', label: 'Catalogue catégories / types', path: '/v1/rsot/resource-taxonomy', method: 'GET', fields: [] },
    { id: 'rsot-list', label: 'Lister les objets RSOT', path: '/v1/rsot/objects', method: 'GET', fields: ['Catégorie', 'Type de ressource', 'Tag', 'Limite'] },
    { id: 'rsot-upsert', label: 'Créer / mettre à jour une ressource', path: '/v1/rsot/objects', method: 'POST', fields: ['Opérateur', 'Clé RSOT', 'Catégorie', 'Type de ressource', 'Nom affiché', 'Source autoritative', 'Numéro de série', 'Constructeur', 'Modèle', 'Site', 'Bâtiment', 'Salle', 'Ligne salle', 'Colonne salle', 'Rack', 'IP de management', 'État cycle de vie', 'Tags'] },
    { id: 'rsot-as-of', label: 'Restituer une ressource à date', path: '/v1/rsot/object-as-of', method: 'GET', fields: ['Clé RSOT', 'Date ISO-8601'] },
    { id: 'rsot-object-audit', label: 'Audit d’une ressource', path: '/v1/rsot/object-audit', method: 'GET', fields: ['Clé RSOT', 'Limite'] },
    { id: 'rsot-reconcile', label: 'Réconcilier une ressource', path: '/v1/rsot/reconcile-object', method: 'POST', fields: ['Opérateur', 'Clé RSOT', 'Source entrante', 'Catégorie', 'Type de ressource', 'Nom affiché cible', 'Numéro de série', 'Constructeur', 'Modèle', 'Site', 'Rack', 'Tags', 'Appliquer le plan'] },
  ] },
  { id: 'ipam', label: 'IPAM', icon: 'grid', operations: [
    { id: 'ipam-dashboard', label: 'Dashboard IPAM', path: '/v1/ipam/ui-dashboard', method: 'GET', fields: ['VRF'] },
    { id: 'ipam-search', label: 'Rechercher dans l’IPAM', path: '/v1/ipam/ui-search', method: 'GET', fields: ['Recherche', 'VRF'] },
    { id: 'ipam-define-vrf', label: 'Définir une VRF', path: '/v1/ipam/vrfs', method: 'POST', fields: ['Opérateur', 'Nom VRF', 'Route distinguisher'] },
    { id: 'ipam-define-aggregate', label: 'Définir un agrégat IP', path: '/v1/ipam/aggregates', method: 'POST', fields: ['Opérateur', 'VRF', 'CIDR agrégat', 'Description'] },
    { id: 'ipam-define-prefix', label: 'Définir un préfixe IP', path: '/v1/ipam/prefixes', method: 'POST', fields: ['Opérateur', 'VRF', 'CIDR préfixe', 'Description'] },
    { id: 'ipam-list-prefixes', label: 'Lister les préfixes', path: '/v1/ipam/prefixes', method: 'GET', fields: ['VRF'] },
    { id: 'ipam-define-range', label: 'Définir une plage IP', path: '/v1/ipam/ranges', method: 'POST', fields: ['Opérateur', 'VRF', 'Préfixe', 'Début plage', 'Fin plage', 'Usage plage', 'Description'] },
    { id: 'ipam-register-address', label: 'Enregistrer une adresse IP', path: '/v1/ipam/addresses', method: 'POST', fields: ['Opérateur', 'VRF', 'Préfixe', 'Adresse IP', 'Nom DNS / équipement', 'Interface', 'Statut adresse'] },
    { id: 'ipam-allocate', label: 'Allouer une adresse IP', path: '/v1/ipam/allocate', method: 'POST', fields: ['Opérateur', 'VRF', 'Préfixe', 'Nom DNS / équipement', 'Clé d’idempotence'] },
    { id: 'ipam-reservation-wizard', label: 'Assistant de réservation IP', path: '/v1/ipam/reservation-wizard', method: 'POST', fields: ['Opérateur', 'VRF', 'Préfixe', 'Nom DNS / équipement', 'Clé d’idempotence', 'Appliquer la réservation'] },
    { id: 'ipam-capacity', label: 'Calculer la capacité d’un préfixe', path: '/v1/ipam/capacity', method: 'GET', fields: ['VRF', 'Préfixe'] },
    { id: 'ipam-network-bindings', label: 'Afficher les bindings réseau', path: '/v1/ipam/network-bindings', method: 'GET', fields: ['VRF'] },
    { id: 'ipam-topology', label: 'Topologie opérationnelle IPAM', path: '/v1/ipam/topology', method: 'GET', fields: ['VRF'] },
    { id: 'ipam-define-vlan-group', label: 'Définir un groupe VLAN', path: '/v1/ipam/vlan-groups', method: 'POST', fields: ['Opérateur', 'Groupe VLAN', 'Scope VLAN', 'Description'] },
    { id: 'ipam-define-vxlan-vni', label: 'Définir un VXLAN VNI', path: '/v1/ipam/vxlan-vnis', method: 'POST', fields: ['Opérateur', 'VNI', 'Nom VNI', 'VRF', 'RT import', 'RT export', 'Description'] },
    { id: 'ipam-define-vlan', label: 'Définir un VLAN', path: '/v1/ipam/vlans', method: 'POST', fields: ['Opérateur', 'Groupe VLAN', 'VLAN ID', 'Nom VLAN', 'VRF', 'VNI', 'Description'] },
    { id: 'ipam-define-asn', label: 'Définir un ASN', path: '/v1/ipam/asns', method: 'POST', fields: ['Opérateur', 'ASN', 'Nom AS', 'Description'] },
    { id: 'ipam-define-bgp-peer', label: 'Définir un peer BGP', path: '/v1/ipam/bgp-peers', method: 'POST', fields: ['Opérateur', 'VRF', 'ASN local', 'ASN distant', 'Adresse peer', 'Famille d’adresses', 'RT import', 'RT export', 'Description'] },
    { id: 'ipam-observe-dns', label: 'Observer un enregistrement DNS', path: '/v1/ipam/dns-observations', method: 'POST', fields: ['Opérateur', 'VRF', 'Nom DNS', 'Adresse IP', 'Nom PTR', 'Source observation'] },
    { id: 'ipam-observe-dhcp', label: 'Observer un bail DHCP', path: '/v1/ipam/dhcp-leases', method: 'POST', fields: ['Opérateur', 'VRF', 'Préfixe', 'Adresse IP', 'Adresse MAC', 'Nom DHCP', 'Source observation', 'Bail actif'] },
    { id: 'ipam-conflicts', label: 'Détecter les conflits', path: '/v1/ipam/conflicts', method: 'GET', fields: ['VRF'] },
    { id: 'ipam-ddi-preview', label: 'Prévisualiser DDI', path: '/v1/ipam/ddi-preview', method: 'POST', fields: ['Opérateur', 'VRF', 'Clé d’idempotence', 'Fournisseurs DDI', 'Zone DNS', 'Adresse MAC', 'TTL', 'Appliquer la prévisualisation'] },
  ] },
  { id: 'dcim', label: 'DCIM', icon: 'home', operations: [
    { id: 'dcim-sites', label: 'Lister les sites DCIM', path: '/v1/dcim/sites', method: 'GET', fields: ['Inclure retirés'] },
    { id: 'dcim-site', label: 'Consulter un site DCIM', path: '/v1/dcim/site', method: 'GET', fields: ['Site'] },
    { id: 'dcim-site-create', label: 'Créer un site DCIM', path: '/v1/dcim/site/create', method: 'POST', fields: ['Opérateur', 'Code site', 'Nom site', 'Pays ISO-2', 'Ville', 'Région'] },
    { id: 'dcim-site-update', label: 'Modifier un site DCIM', path: '/v1/dcim/site/update', method: 'POST', fields: ['Opérateur', 'Site', 'Nom site', 'Pays ISO-2', 'Ville', 'Région', 'Statut'] },
    { id: 'dcim-site-delete', label: 'Retirer un site DCIM', path: '/v1/dcim/site/delete', method: 'POST', fields: ['Opérateur', 'Site'] },
    { id: 'dcim-topology-catalog', label: 'Catalogue dépendances DCIM', path: '/v1/dcim/topology-catalog', method: 'GET', fields: ['Inclure retirés'] },
    { id: 'dcim-locate-equipment', label: 'Localiser un équipement', path: '/v1/dcim/locations', method: 'POST', fields: ['Opérateur', 'Numéro d’actif', 'Nom équipement', 'Site', 'Bâtiment', 'Étage', 'Salle', 'Zone', 'Ligne salle', 'Colonne salle', 'Rack', 'Position U', 'Face rack', 'Hauteur U', 'Coordonnée X', 'Coordonnée Y', 'Coordonnée Z'] },
    { id: 'dcim-rack-capacity', label: 'Capacité rack', path: '/v1/dcim/rack-capacity', method: 'GET', fields: ['Site', 'Bâtiment', 'Salle', 'Rack'] },
    { id: 'dcim-room-plan', label: 'Plan de salle', path: '/v1/dcim/room-plan', method: 'GET', fields: ['Site', 'Bâtiment', 'Salle', 'Format rendu'] },
    { id: 'dcim-rack-elevation', label: 'Élévation rack', path: '/v1/dcim/rack-elevation', method: 'GET', fields: ['Site', 'Bâtiment', 'Salle', 'Rack', 'Face rack', 'Format rendu'] },
    { id: 'dcim-patch-panel', label: 'Définir un panneau de brassage', path: '/v1/dcim/patch-panels', method: 'POST', fields: ['Opérateur', 'Site', 'Bâtiment', 'Salle', 'Rack', 'Panneau de brassage', 'Face rack', 'Position U', 'Hauteur U', 'Nombre de ports', 'Connecteur', 'Média câble', 'Libellé', 'Préfixe ports'] },
    { id: 'dcim-port', label: 'Définir un port DCIM', path: '/v1/dcim/ports', method: 'POST', fields: ['Opérateur', 'Type propriétaire', 'Code propriétaire', 'Nom port', 'Connecteur', 'Média câble', 'Site', 'Bâtiment', 'Salle', 'Port actif'] },
    { id: 'dcim-cable', label: 'Connecter un câble', path: '/v1/dcim/cables', method: 'POST', fields: ['Opérateur', 'Identifiant câble', 'Type propriétaire A', 'Code propriétaire A', 'Port A', 'Type propriétaire B', 'Code propriétaire B', 'Port B', 'Média câble', 'Statut câble', 'Chemin câble', 'Longueur m', 'Libellé'] },
    { id: 'dcim-power-device', label: 'Définir un équipement électrique', path: '/v1/dcim/power-devices', method: 'POST', fields: ['Opérateur', 'Code équipement électrique', 'Type équipement électrique', 'Site', 'Bâtiment', 'Salle', 'Rack', 'Chaîne électrique', 'Capacité watts', 'Derating %', 'Source amont', 'Tension sortie V', 'Libellé'] },
    { id: 'dcim-power-circuit', label: 'Définir un circuit électrique', path: '/v1/dcim/power-circuits', method: 'POST', fields: ['Opérateur', 'Identifiant circuit', 'Source électrique', 'Site', 'Bâtiment', 'Salle', 'Rack', 'Chaîne électrique', 'Capacité watts', 'Calibre disjoncteur A', 'Groupe redondance', 'Libellé'] },
    { id: 'dcim-cooling-zone', label: 'Définir une zone de refroidissement', path: '/v1/dcim/cooling-zones', method: 'POST', fields: ['Opérateur', 'Site', 'Bâtiment', 'Salle', 'Zone froid/chaud', 'Rôle refroidissement', 'Capacité froid watts', 'Température soufflage °C', 'Température retour °C', 'Libellé'] },
    { id: 'dcim-power-reservation', label: 'Réserver la puissance équipement', path: '/v1/dcim/power-reservations', method: 'POST', fields: ['Opérateur', 'Numéro d’actif', 'Identifiant circuit', 'Puissance attendue watts', 'Libellé'] },
    { id: 'dcim-digital-twin', label: 'Jumeau numérique salle', path: '/v1/dcim/digital-twin', method: 'GET', fields: ['Site', 'Bâtiment', 'Salle'] },
    { id: 'dcim-energy-cooling-capacity', label: 'Capacité énergie/refroidissement', path: '/v1/dcim/energy-cooling-capacity', method: 'GET', fields: ['Site', 'Bâtiment', 'Salle', 'Rack'] },
  ] },
  { id: 'itam', label: 'IT Asset Management', shortLabel: 'ITAM', icon: 'asset', operations: [
    { id: 'itam-tenants', label: 'Lister les entités propriétaires ITAM', path: '/v1/itam/tenants', method: 'GET', fields: ['Inclure retirés'] },
    { id: 'itam-tenant-create', label: 'Créer une entité propriétaire ITAM', path: '/v1/itam/tenant/create', method: 'POST', fields: ['Organisation', 'Opérateur', 'Entité propriétaire de sécurité', 'Nom entité propriétaire', 'Statut', 'Entité propriétaire par défaut', 'Description'] },
    { id: 'itam-tenant-update', label: 'Modifier une entité propriétaire ITAM', path: '/v1/itam/tenant/update', method: 'POST', fields: ['Opérateur', 'Entité propriétaire de sécurité', 'Nom entité propriétaire', 'Statut', 'Entité propriétaire par défaut', 'Description'] },
    { id: 'itam-tenant-delete', label: 'Retirer une entité propriétaire ITAM', path: '/v1/itam/tenant/delete', method: 'POST', fields: ['Opérateur', 'Entité propriétaire de sécurité'] },
    { id: 'itam-support-profile', label: 'Profil support actif', path: '/v1/itam/support-profile', method: 'GET', fields: ['Numéro d’actif'] },
    { id: 'itam-support-coverage', label: 'Couverture support actif', path: '/v1/itam/support-coverage', method: 'GET', fields: ['Numéro d’actif', 'Date de référence'] },
    { id: 'itam-register-manufacturer', label: 'Déclarer garantie constructeur', path: '/v1/itam/support-profile/manufacturer', method: 'POST', fields: ['Opérateur', 'Numéro d’actif', 'Constructeur', 'Référence garantie', 'Niveau garantie', 'Début garantie', 'Fin garantie', 'Référence support', 'Niveau support', 'Contact support'] },
    { id: 'itam-add-third-party', label: 'Ajouter support tiers', path: '/v1/itam/support-profile/third-party', method: 'POST', fields: ['Opérateur', 'Numéro d’actif', 'Prestataire', 'Référence contrat', 'Niveau support', 'Début support', 'Fin support', 'Contact support', 'Statut', 'Notes'] },
    { id: 'itam-software-license', label: 'Licence logicielle', path: '/v1/itam/software-license', method: 'GET', fields: ['Référence licence'] },
    { id: 'itam-software-compliance', label: 'Conformité licence', path: '/v1/itam/software-license/compliance', method: 'GET', fields: ['Référence licence', 'Date de référence'] },
    { id: 'itam-register-software', label: 'Déclarer licence logicielle', path: '/v1/itam/software-license', method: 'POST', fields: ['Opérateur', 'Produit', 'Éditeur', 'Référence licence', 'Référence contrat', 'Métrique', 'Quantité achetée', 'Quantité assignée', 'Début droit', 'Fin droit', 'Version', 'Statut', 'Propriétaire', 'Notes'] },
    { id: 'itam-update-license-assignment', label: 'Mettre à jour affectation licence', path: '/v1/itam/software-license/assignment', method: 'POST', fields: ['Opérateur', 'Référence licence', 'Quantité assignée', 'Notes'] },
  ] },
  { id: 'discovery', label: 'Discovery', icon: 'activity', operations: [
    { id: 'local-discovery-plan', label: 'Plan discovery locale Lite/Pro', path: '/v1/discovery/local-plan', method: 'POST', fields: ['Opérateur', 'Nom plan', 'Scope', 'Protocole', 'Cibles', 'Référence secret', 'Concurrence max', 'Rate limit/min'] },
    { id: 'agent-bootstrap-plan', label: 'Plan bootstrap agent Enterprise', path: '/v1/discovery/agent-bootstrap-plan', method: 'POST', fields: ['Opérateur', 'Nom agent', 'Rôle agent', 'Scopes autorisés', 'URL backend HTTPS', 'Empreinte certificat', 'Référence secret enrollment', 'Version agent', 'Compte service', 'Chemin configuration', 'Répertoire état', 'Répertoire logs'] },
    { id: 'collectors-register', label: 'Enregistrer un agent proxy Enterprise', path: '/v1/discovery/collectors', method: 'POST', fields: ['Opérateur', 'Nom agent proxy', 'Type', 'Empreinte certificat', 'Scopes autorisés', 'Version agent', 'Endpoint mTLS'] },
  ] },
  { id: 'data', label: 'Imports / Exports', shortLabel: 'Data', icon: 'table', operations: [
    { id: 'import-bulk-progress', label: 'Progression import massif', path: '/v1/imports/bulk-progress', method: 'GET', fields: ['Job ID'] },
    { id: 'import-bulk-rollback', label: 'Rollback import massif', path: '/v1/imports/bulk-rollback', method: 'POST', fields: ['Opérateur', 'Job ID', 'Fichier source', 'Format', 'Mapping JSON', 'Appliquer', 'Politique conflit'] },
    { id: 'import-migration-guide', label: 'Guide migration données', path: '/v1/imports/migration-guide', method: 'GET', fields: ['Source migration'] },
    { id: 'export-artifact-chunk', label: 'Chunk export signé', path: '/v1/exports/artifact-chunk', method: 'GET', fields: ['Job export', 'Offset octets', 'Taille chunk'] },
  ] },
  { id: 'security', label: 'Sécurité / RBAC / Audit', shortLabel: 'Sécurité', icon: 'shield', operations: [
    { id: 'edition-policies', label: 'Politiques éditions et quotas', path: '/v1/editions/policies', method: 'GET', fields: [] },
    { id: 'edition-feature-check', label: 'Vérifier une capacité édition', path: '/v1/editions/feature-check', method: 'GET', fields: ['Édition', 'Capacité'] },
    { id: 'edition-quota-check', label: 'Vérifier un quota édition', path: '/v1/editions/quota-check', method: 'GET', fields: ['Édition', 'Ressource quota', 'Incrément demandé'] },
    { id: 'audit-events', label: 'Événements d’audit', path: '/v1/audit/events', method: 'GET', fields: ['Action', 'Type cible', 'Limite'] },
  ] },
];

const SIDEBAR_CONTEXTS = {
  rsot: [
    { label: 'Référentiel', operationIds: ['rsot-taxonomy', 'rsot-list', 'rsot-upsert'] },
    { label: 'Relations & historique', operationIds: ['rsot-relations', 'rsot-as-of', 'rsot-object-audit'] },
    { label: 'Qualité & gouvernance', operationIds: ['rsot-quality-object', 'rsot-quality-summary', 'rsot-governance', 'rsot-reconcile'] },
  ],
  ipam: [
    { label: 'Vue & recherche', operationIds: ['ipam-dashboard', 'ipam-search'] },
    { label: 'Adressage IP', operationIds: ['ipam-define-vrf', 'ipam-define-aggregate', 'ipam-define-prefix', 'ipam-list-prefixes', 'ipam-define-range', 'ipam-register-address', 'ipam-allocate', 'ipam-reservation-wizard', 'ipam-capacity'] },
    { label: 'Réseau L2/L3', operationIds: ['ipam-network-bindings', 'ipam-topology', 'ipam-define-vlan-group', 'ipam-define-vxlan-vni', 'ipam-define-vlan', 'ipam-define-asn', 'ipam-define-bgp-peer'] },
    { label: 'Observations & DDI', operationIds: ['ipam-observe-dns', 'ipam-observe-dhcp', 'ipam-conflicts', 'ipam-ddi-preview'] },
  ],
  dcim: [
    { label: 'Sites & dépendances', operationIds: ['dcim-sites', 'dcim-site', 'dcim-site-create', 'dcim-site-update', 'dcim-site-delete', 'dcim-topology-catalog'] },
    { label: 'Localisation & capacité', operationIds: ['dcim-locate-equipment', 'dcim-rack-capacity', 'dcim-room-plan', 'dcim-rack-elevation'] },
    { label: 'Connectivité', operationIds: ['dcim-patch-panel', 'dcim-port', 'dcim-cable', 'dcim-cable-trace'] },
    { label: 'Énergie & refroidissement', operationIds: ['dcim-power-device', 'dcim-power-circuit', 'dcim-cooling-zone', 'dcim-power-reservation', 'dcim-energy-cooling-capacity'] },
    { label: 'Jumeau numérique', operationIds: ['dcim-digital-twin'] },
  ],
  itam: [
    { label: 'Entités propriétaires', operationIds: ['itam-tenants', 'itam-tenant', 'itam-tenant-create', 'itam-tenant-update', 'itam-tenant-delete'] },
    { label: 'Support matériel', operationIds: ['itam-support-profile', 'itam-support-coverage', 'itam-register-manufacturer', 'itam-add-third-party'] },
    { label: 'Licences logicielles', operationIds: ['itam-software-license', 'itam-software-compliance', 'itam-register-software', 'itam-update-license-assignment'] },
  ],
  discovery: [
    { label: 'Locale Lite/Pro', operationIds: ['local-discovery-plan'] },
    { label: 'Agents Enterprise', operationIds: ['agent-bootstrap-plan', 'collectors-list', 'collectors-register', 'job-authorize'] },
  ],
  data: [
    { label: 'Imports', operationIds: ['import-bulk-progress', 'import-bulk-rollback'] },
    { label: 'Migration', operationIds: ['import-migration-guide'] },
    { label: 'Exports', operationIds: ['export-artifact-chunk'] },
  ],
  integrations: [
    { label: 'Gouvernance ITSM', operationIds: ['itsm-providers'] },
    { label: 'ServiceNow', operationIds: ['servicenow-validate', 'servicenow-ci-sync-plan'] },
    { label: 'Jira Assets', operationIds: ['jira-validate', 'jira-asset-sync-plan'] },
    { label: 'GLPI Inventory', operationIds: ['glpi-validate', 'glpi-asset-sync-plan'] },
    { label: 'Freshservice Assets', operationIds: ['freshservice-validate', 'freshservice-asset-sync-plan'] },
  ],
  security: [
    { label: 'Éditions & quotas', operationIds: ['edition-policies', 'edition-feature-check', 'edition-quota-check'] },
    { label: 'Identité & accès', operationIds: ['tokens-list', 'effective-identity', 'access-rules'] },
    { label: 'Audit', operationIds: ['audit-events', 'audit-integrity'] },
  ],
};


function Icon({ name, className = 'bi' }) {
  return <svg className={className} width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d={ICONS[name] || ICONS.grid} /></svg>;
}

function componentModules() {
  return MODULES.filter((module) => module.id !== 'overview');
}

function moduleStatistics(module) {
  const operations = module.operations.length;
  const readOperations = module.operations.filter((operation) => operation.method === 'GET').length;
  const writeOperations = operations - readOperations;
  const fields = module.operations.reduce((total, operation) => total + operation.fields.length, 0);
  const readPercent = operations === 0 ? 0 : Math.round((readOperations / operations) * 100);
  return { operations, readOperations, writeOperations, fields, readPercent, writePercent: 100 - readPercent };
}

function normalizeSearchText(value) {
  return String(value || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}


function buildGlobalSearchUrl(apiBaseUrl, tenant, query, limit = 6) {
  const base = String(apiBaseUrl || '/api').replace(/\/$/, '');
  const params = new URLSearchParams({ tenant_id: tenant || 'default', query, limit: String(limit) });
  return `${base}/v1/search/global?${params.toString()}`;
}

function buildApiDocumentationUrl(apiBaseUrl, route) {
  const normalizedRoute = String(route || '/docs').startsWith('/') ? String(route || '/docs') : `/${route}`;
  const value = String(apiBaseUrl || '/api').trim();
  if (/^https?:\/\//i.test(value)) {
    const url = new URL(value);
    return `${url.origin}${normalizedRoute}`;
  }
  return normalizedRoute;
}

function apiDocumentationLinks(config) {
  const published = config?.apiDocumentation || {};
  return {
    swaggerUrl: published.swaggerUrl || buildApiDocumentationUrl(config?.apiBaseUrl, '/docs'),
    redocUrl: published.redocUrl || buildApiDocumentationUrl(config?.apiBaseUrl, '/redoc'),
    openapiUrl: published.openapiUrl || buildApiDocumentationUrl(config?.apiBaseUrl, '/openapi.yaml'),
  };
}

function globalSearchGroups(query) {
  const normalizedQuery = normalizeSearchText(query.trim());
  if (!normalizedQuery) {
    return [];
  }
  return componentModules().map((module) => {
    const matches = module.operations.filter((operation) => {
      const haystack = [
        module.label,
        module.shortLabel,
        operation.id,
        operation.label,
        operation.method,
        operation.path,
        ...operation.fields,
      ].filter(Boolean).join(' ');
      return normalizeSearchText(haystack).includes(normalizedQuery);
    });
    return { module, operations: matches.slice(0, 8), total: matches.length };
  }).filter((group) => group.total > 0);
}

function sidebarOperationGroups(module) {
  const configuredGroups = SIDEBAR_CONTEXTS[module.id] || [];
  const byId = new Map(module.operations.map((operation) => [operation.id, operation]));
  const groupedIds = new Set();
  const groups = configuredGroups.map((group) => {
    const operations = group.operationIds.map((id) => byId.get(id)).filter(Boolean);
    operations.forEach((operation) => groupedIds.add(operation.id));
    return { label: group.label, operations };
  }).filter((group) => group.operations.length > 0);
  const remaining = module.operations.filter((operation) => !groupedIds.has(operation.id));
  if (remaining.length > 0) {
    groups.push({ label: 'Autres', operations: remaining });
  }
  return groups;
}


function Dashboard() {
  const [config, setConfig] = useState({ apiBaseUrl: '/api', apiDocumentation: { swaggerUrl: '/docs', redocUrl: '/redoc', openapiUrl: '/openapi.yaml' }, version: 'indisponible', webBackendTrust: 'server-side' });
  const [ready, setReady] = useState(null);
  const [bffStatus, setBffStatus] = useState(null);
  const [version, setVersion] = useState(null);
  const [selected, setSelected] = useState(MODULES[0].operations[0]);
  const [activeModuleId, setActiveModuleId] = useState('overview');
  const [opened, setOpened] = useState(new Set(['rsot']));
  const [tenant, setTenant] = useState('default');
  const [result, setResult] = useState('Résultat en attente.');
  const [globalSearchQuery, setGlobalSearchQuery] = useState('');
  const [globalSearchBackend, setGlobalSearchBackend] = useState(null);
  const [globalSearchLoading, setGlobalSearchLoading] = useState(false);
  const [globalSearchError, setGlobalSearchError] = useState(null);
  const [shouldFocusMain, setShouldFocusMain] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const mainContentRef = useRef(null);
  const businessModules = useMemo(() => componentModules(), []);
  const operationsCount = useMemo(() => MODULES.reduce((total, module) => total + module.operations.length, 0), []);
  const businessFieldsCount = useMemo(() => businessModules.reduce((total, module) => total + moduleStatistics(module).fields, 0), [businessModules]);
  const searchGroups = useMemo(() => globalSearchGroups(globalSearchQuery), [globalSearchQuery]);
  const apiDocs = useMemo(() => apiDocumentationLinks(config), [config]);


  useLayoutEffect(() => {
    const syncHeaderOffset = () => {
      const header = document.querySelector('.openinfra-header-stack');
      if (header instanceof HTMLElement) {
        const height = Math.ceil(header.getBoundingClientRect().height);
        if (height > 0) {
          document.documentElement.style.setProperty('--openinfra-fixed-header-height', `${height}px`);
        }
      }
    };
    syncHeaderOffset();
    window.addEventListener('resize', syncHeaderOffset);
    return () => window.removeEventListener('resize', syncHeaderOffset);
  });

  useEffect(() => {
    const query = globalSearchQuery.trim();
    if (query.length < 2) {
      setGlobalSearchBackend(null);
      setGlobalSearchError(null);
      setGlobalSearchLoading(false);
      return undefined;
    }
    let cancelled = false;
    setGlobalSearchLoading(true);
    fetch(buildGlobalSearchUrl(config.apiBaseUrl, tenant, query, 6), {
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
    }).then((response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    }).then((payload) => {
      if (!cancelled) {
        setGlobalSearchBackend(payload);
        setGlobalSearchError(null);
      }
    }).catch((error) => {
      if (!cancelled) {
        setGlobalSearchBackend(null);
        setGlobalSearchError('backend_unavailable');
      }
    }).finally(() => {
      if (!cancelled) setGlobalSearchLoading(false);
    });
    return () => { cancelled = true; };
  }, [config.apiBaseUrl, globalSearchQuery, tenant]);

  useEffect(() => {
    if (!shouldFocusMain) {
      return;
    }
    mainContentRef.current?.focus({ preventScroll: false });
    setShouldFocusMain(false);
  }, [activeModuleId, selected.id, shouldFocusMain]);

  useEffect(() => {
    Promise.all([
      fetch('/config.json', { credentials: 'same-origin' }).then((response) => response.json()),
      fetch('/ready', { credentials: 'same-origin' }).then((response) => response.ok ? response.json() : { ready: false }),
      fetch('/version', { credentials: 'same-origin' }).then((response) => response.ok ? response.json() : null),
      fetch('/status', { credentials: 'same-origin' }).then((response) => response.ok ? response.json() : { protectedForms: 'unknown', trust: {} }),
    ]).then(([loadedConfig, loadedReady, loadedVersion, loadedBffStatus]) => {
      setConfig(loadedConfig);
      setReady(loadedReady);
      setVersion(loadedVersion);
      setBffStatus(loadedBffStatus);
    }).catch(() => setReady({ ready: false }));
  }, []);

  function chooseOperation(module, operation, focusMain = false) {
    setSelected(operation);
    setActiveModuleId(module.id);
    setOpened(new Set([...opened, module.id]));
    setResult('Résultat en attente.');
    setMobileSidebarOpen(false);
    if (focusMain) {
      setShouldFocusMain(true);
    }
  }

  function selectSearchOperation(module, operation) {
    chooseOperation(module, operation, true);
    setGlobalSearchQuery('');
  }

  function selectBackendSearchItem(item) {
    if (!item.route) return;
    fetch(item.route, { credentials: 'same-origin', headers: { Accept: 'application/json' } })
      .then((response) => response.json())
      .then((payload) => {
        setResult(JSON.stringify(payload, null, 2));
        setShouldFocusMain(true);
      })
      .catch((error) => {
        setResult(JSON.stringify({ error: error.message }, null, 2));
        setShouldFocusMain(true);
      });
    setGlobalSearchQuery('');
  }

  function toggleAccordion(moduleId) {
    const module = MODULES.find((item) => item.id === moduleId);
    if (!module) {
      return;
    }
    const next = new Set(opened);
    if (next.has(moduleId) && activeModuleId === moduleId) {
      next.delete(moduleId);
    } else {
      next.add(moduleId);
    }
    setOpened(next);
    setSelected(module.operations[0]);
    setActiveModuleId(module.id);
    setResult('Résultat en attente.');
    setMobileSidebarOpen(false);
  }

  function execute() {
    setResult(JSON.stringify({ tenant_id: tenant, action: selected.id, via: config.apiBaseUrl, trust: config.webBackendTrust }, null, 2));
  }

  const displayedVersion = version?.version || config.version || 'indisponible';
  const filteredModules = MODULES;
  const submissionCompleted = result !== 'Résultat en attente.';
  const protectedForms = bffStatus?.protectedForms === 'enabled' ? 'actifs' : 'à configurer';
  const activeModule = MODULES.find((module) => module.id === activeModuleId) || MODULES[0];
  const pageTitle = activeModuleId === 'overview' ? 'Dashboard' : activeModule.shortLabel || activeModule.label;
  const pageSubtitle = activeModuleId === 'overview'
    ? 'Vue de synthèse OpenInfra, readiness backend et état du portail server-side.'
    : `${selected.label} — formulaire métier typé, sans champs génériques ni secrets côté navigateur.`;

  return <div className="openinfra-shell">
    <a className="openinfra-skip-link" href="#openinfra-main-content">Aller au contenu principal</a>
    <header className="openinfra-header-stack">
      <div className="px-3 py-2 bg-dark text-white openinfra-top-header"><div className="container-fluid"><div className="d-flex flex-wrap align-items-center justify-content-center justify-content-lg-start"><a href="/" className="d-flex align-items-center my-2 my-lg-0 me-lg-auto text-white text-decoration-none" aria-label="OpenInfra accueil"><span className="openinfra-brand-mark me-2">OI</span><span className="fs-5 fw-semibold">OpenInfra</span><span className="badge openinfra-edition-badge ms-3">{config.edition || 'runtime'}</span></a><ul className="nav col-12 col-lg-auto my-2 justify-content-center my-md-0 text-small">{MODULES.map((module) => <li key={module.id}><button type="button" className={`nav-link border-0 bg-transparent ${activeModuleId === module.id ? 'text-secondary' : 'text-white'}`} aria-current={activeModuleId === module.id ? 'page' : undefined} onClick={() => chooseOperation(module, module.operations[0])}><Icon name={module.icon} className="bi d-block mx-auto mb-1 openinfra-top-icon" />{module.shortLabel || module.label}</button></li>)}</ul></div></div></div>
      <div className="px-3 py-2 border-bottom openinfra-global-toolbar"><div className="container-fluid openinfra-global-toolbar-inner"><div className="openinfra-global-toolbar-spacer" aria-hidden="true" /><form className="openinfra-global-search-form" role="search" aria-label="Recherche globale OpenInfra" autoComplete="off"><label className="visually-hidden" htmlFor="openinfra-global-search">Recherche globale OpenInfra</label><div className="openinfra-global-search-control"><Icon name="search" className="openinfra-global-search-icon" /><input type="search" id="openinfra-global-search" className="form-control" placeholder="Recherche globale..." aria-label="Recherche globale OpenInfra" role="combobox" aria-autocomplete="list" aria-haspopup="listbox" aria-controls="openinfra-global-search-results" aria-expanded={globalSearchQuery.trim() !== ''} value={globalSearchQuery} onChange={(event) => setGlobalSearchQuery(event.target.value)} onKeyDown={(event) => { if (event.key === 'Escape') setGlobalSearchQuery(''); }} /></div>{globalSearchQuery.trim() !== '' && <div id="openinfra-global-search-results" className="openinfra-global-search-results" role="listbox" aria-label="Résultats de recherche globale" aria-live="polite"><GlobalSearchResults query={globalSearchQuery} groups={searchGroups} backend={globalSearchBackend} loading={globalSearchLoading} error={globalSearchError} onSelect={selectSearchOperation} onBackendSelect={selectBackendSearchItem} /></div>}</form><div className="text-end openinfra-api-doc-actions"><a className="btn btn-light text-dark me-2" href={apiDocs.swaggerUrl} target="_blank" rel="noopener noreferrer" aria-label="Ouvrir Swagger UI backend API">Swagger</a><a className="btn btn-primary" href={apiDocs.redocUrl} target="_blank" rel="noopener noreferrer" aria-label="Ouvrir ReDoc backend API">ReDoc</a></div></div></div>
    </header>
    <div className="container-fluid"><div className="openinfra-mobile-menu-bar"><button type="button" id="openinfra-mobile-menu-button" className="btn btn-primary openinfra-mobile-menu-button" aria-label={mobileSidebarOpen ? "Fermer le menu de navigation" : "Ouvrir le menu de navigation"} aria-expanded={mobileSidebarOpen} aria-controls="openinfra-sidebar" onClick={() => setMobileSidebarOpen((open) => !open)}><Icon name="menu" className="openinfra-mobile-menu-icon" /><span className="visually-hidden">Menu</span></button></div>{mobileSidebarOpen && <button type="button" className="openinfra-mobile-sidebar-backdrop" aria-label="Fermer le menu de navigation" onClick={() => setMobileSidebarOpen(false)} />}<div className="row"><nav id="openinfra-sidebar" className={`col-lg-3 col-xl-2 openinfra-sidebar ${mobileSidebarOpen ? 'mobile-open' : ''}`} aria-label="Sidebar navigation"><div className="openinfra-sidebar-heading">Pilotage</div>{filteredModules.map((module) => module.id === 'overview' ? <button key={module.id} type="button" className={`nav-link openinfra-sidebar-dashboard w-100 text-start ${activeModuleId === module.id ? 'active' : ''}`} aria-current={activeModuleId === module.id ? 'page' : undefined} onClick={() => chooseOperation(module, module.operations[0])}><Icon name={module.icon} />Dashboard</button> : <section className={`openinfra-accordion ${opened.has(module.id) ? 'open' : ''}`} key={module.id}><button type="button" id={`openinfra-accordion-${module.id}`} className={`openinfra-accordion-toggle ${activeModuleId === module.id ? 'active' : ''}`} aria-expanded={opened.has(module.id)} aria-controls={`openinfra-panel-${module.id}`} aria-current={activeModuleId === module.id ? 'page' : undefined} onClick={() => toggleAccordion(module.id)}><span><Icon name={module.icon} />{module.shortLabel || module.label}</span><span className="openinfra-chevron">›</span></button><div id={`openinfra-panel-${module.id}`} className={`openinfra-accordion-panel fade ${opened.has(module.id) ? 'show' : ''}`} role="region" aria-labelledby={`openinfra-accordion-${module.id}`}>{sidebarOperationGroups(module).map((group) => <div key={`${module.id}-${group.label}`} className="openinfra-sidebar-context" role="group" aria-label={group.label}><div className="openinfra-sidebar-context-title">{group.label}</div>{group.operations.map((operation) => <button key={operation.id} type="button" className={`openinfra-sidebar-operation ${selected.id === operation.id ? 'active' : ''}`} aria-current={selected.id === operation.id ? 'page' : undefined} onClick={() => chooseOperation(module, operation)}>{operation.label}</button>)}</div>)}</div></section>)}</nav><main id="openinfra-main-content" ref={mainContentRef} tabIndex={-1} className="col-lg-9 col-xl-10 ms-sm-auto openinfra-main"><div className="pb-2 mb-3 openinfra-titlebar"><h1 className="h2">{pageTitle}</h1><p className="text-muted mb-0">{pageSubtitle}</p></div>{submissionCompleted && activeModuleId !== 'overview' && <div className="alert alert-success" role="status">Soumission exécutée avec succès.</div>}{activeModuleId === 'overview' && <div className="row g-3 mb-4 openinfra-dashboard-metrics" aria-label="Métriques du dashboard"><Metric title="Version" value={displayedVersion} /><Metric title="API" value={config.apiBaseUrl || '/api'} /><Metric title="Trust" value={config.webBackendTrust || 'server-side'} /><Metric title="Formulaires" value={protectedForms} /><Metric title="Modules" value={`${operationsCount} opérations`} /></div>}{activeModuleId === 'overview' ? <OverviewStats modules={businessModules} fieldsCount={businessFieldsCount} /> : <section className="card openinfra-operation-card"><div className="card-body"><h2 className="h4">{selected.label}</h2><div className="row g-3 mb-3"><label className="col-md-4 form-label">Entité propriétaire<select className="form-select" value={tenant} onChange={(event) => setTenant(event.target.value)}><option value="default">Default</option></select></label></div><div className="row g-3">{selected.fields.map((field) => <label className="col-md-6 col-xl-4 form-label" key={field}>{field}<input className="form-control" /></label>)}</div><button type="button" className="btn btn-primary mt-3" onClick={execute}>Exécuter</button><pre className="openinfra-result mt-3" aria-live="polite" aria-label="Résultat de l’opération">{result}</pre></div></section>}</main></div></div>
  </div>;
}

function GlobalSearchResults({ query, groups, backend, loading, error, onSelect, onBackendSelect }) {
  if (loading) {
    return <div className="openinfra-global-search-empty">Recherche backend en cours pour <strong>{query.trim()}</strong>…</div>;
  }
  if (backend && backend.query === query.trim()) {
    const resultGroups = (backend.groups || []).filter((group) => group.status === 'ok' && Array.isArray(group.items) && group.items.length > 0);
    const skipped = (backend.groups || []).filter((group) => group.status === 'skipped');
    if (resultGroups.length > 0) {
      return <>{resultGroups.map((group) => <section className="openinfra-global-search-group" role="group" aria-label={`Résultats ${group.label || group.component}`} key={group.component}><div className="openinfra-global-search-group-title"><span>{group.label || group.component}</span><span>{group.total} résultat{group.total > 1 ? 's' : ''}</span></div>{group.items.map((item) => <button type="button" className="openinfra-global-search-item" role="option" key={`${group.component}-${item.kind}-${item.label}`} onClick={() => onBackendSelect(item)}><span>{item.label}</span><small>{item.kind} · {item.description}</small></button>)}{group.total > group.items.length && <div className="openinfra-global-search-more">{group.total - group.items.length} résultat{group.total - group.items.length > 1 ? 's' : ''} supplémentaire{group.total - group.items.length > 1 ? 's' : ''}</div>}</section>)}{skipped.length > 0 && <div className="openinfra-global-search-empty">Composants ignorés selon les droits : {skipped.map((group) => group.label || group.component).join(', ')}.</div>}</>;
    }
  }
  if (error) {
    return <><div className="openinfra-global-search-empty">Recherche backend temporairement indisponible. Résultats locaux ci-dessous.</div><OperationSearchResults query={query} groups={groups} onSelect={onSelect} /></>;
  }
  return <OperationSearchResults query={query} groups={groups} onSelect={onSelect} />;
}

function OperationSearchResults({ query, groups, onSelect }) {
  if (groups.length === 0) {
    return <div className="openinfra-global-search-empty">Aucun résultat global pour <strong>{query.trim()}</strong>.</div>;
  }
  return groups.map(({ module, operations, total }) => <section className="openinfra-global-search-group" role="group" aria-label={`Résultats ${module.shortLabel || module.label}`} key={module.id}><div className="openinfra-global-search-group-title"><span>{module.shortLabel || module.label}</span><span>{total} résultat{total > 1 ? 's' : ''}</span></div>{operations.map((operation) => <button type="button" className="openinfra-global-search-item" role="option" key={operation.id} onClick={() => onSelect(module, operation)}><span>{operation.label}</span><small>{operation.method} {operation.path}</small></button>)}{total > operations.length && <div className="openinfra-global-search-more">{total - operations.length} résultat{total - operations.length > 1 ? 's' : ''} supplémentaire{total - operations.length > 1 ? 's' : ''}</div>}</section>);
}

function OverviewStats({ modules, fieldsCount }) {
  const operations = modules.reduce((total, module) => total + module.operations.length, 0);
  return <section className="openinfra-overview" aria-label="Statistiques des composants OpenInfra"><div className="card openinfra-overview-summary mb-4"><div className="card-body"><div className="d-flex flex-wrap justify-content-between align-items-start gap-3"><div><h2 className="h4 mb-1">Accueil — statistiques des composants</h2><p className="text-muted mb-0">Vue de synthèse par composant : métriques fonctionnelles et camemberts de répartition lecture/mutation.</p></div><div><span className="badge text-bg-primary">{modules.length} composants</span><span className="badge text-bg-secondary ms-2">{operations} opérations</span></div></div><div className="row g-3 mt-3"><Metric title="Champs métier" value={String(fieldsCount)} /><Metric title="Navigation" value="Accordéons" /><Metric title="Secrets navigateur" value="0 exposé" /><Metric title="Parité UI" value="CLI/API" /></div></div></div><div className="row g-3">{modules.map((module) => <ComponentStatsCard key={module.id} module={module} />)}</div></section>;
}

function ComponentStatsCard({ module }) {
  const stats = moduleStatistics(module);
  const style = { '--oi-read-end': `${stats.readPercent}%`, '--oi-write-end': `${stats.readPercent + stats.writePercent}%` };
  return <article className="col-md-6 col-xxl-4"><div className="card h-100 openinfra-component-card"><div className="card-body"><div className="d-flex justify-content-between align-items-start gap-3"><div><h3 className="h5 mb-1">{module.shortLabel || module.label}</h3><p className="text-muted small mb-0">{module.operations.length} opérations métier exposées</p></div><Icon name={module.icon} className="openinfra-component-icon" /></div><div className="openinfra-component-visual mt-3"><div className="openinfra-pie-chart" role="img" aria-label={`Camembert ${module.label}`} style={style}><span>{stats.operations}</span></div><div className="openinfra-pie-legend small"><span><i className="openinfra-legend-read" />{stats.readOperations} lectures</span><span><i className="openinfra-legend-write" />{stats.writeOperations} mutations</span></div></div><div className="row g-2 mt-3 openinfra-component-metrics"><div className="col-6"><strong>{stats.operations}</strong><span>Opérations</span></div><div className="col-6"><strong>{stats.fields}</strong><span>Champs métier</span></div><div className="col-6"><strong>{stats.readOperations}</strong><span>Lectures</span></div><div className="col-6"><strong>{stats.writeOperations}</strong><span>Mutations</span></div></div></div></div></article>;
}

function Metric({ title, value }) {
  return <article className="col-md-6 col-xl-3"><div className="card h-100 openinfra-metric"><div className="card-body"><h2 className="h6 text-muted">{title}</h2><p className="openinfra-metric-value mb-0">{value}</p></div></div></article>;
}

createRoot(document.getElementById('openinfra-root')).render(<Dashboard />);
