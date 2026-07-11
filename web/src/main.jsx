import 'bootstrap/dist/css/bootstrap.min.css';
import './openinfra-theme.css';
import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { OpenInfraI18n, localizeOpenInfraCatalog } from './i18n.js';
import { formCountryCode, inputAttributesForField, inputTypeForField, normalizeFieldDefinition, normalizeFieldValue, validateControl } from './form-fields.js';

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
  sliders: 'M3 4h10v1H3V4zm2 3h6v1H5V7zm-2 3h10v1H3v-1z',
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
    { id: 'rsot-upsert', label: 'Créer / mettre à jour une ressource', path: '/v1/rsot/objects', method: 'POST', fields: ['Opérateur', 'Clé RSOT', 'Catégorie', 'Type de ressource', 'Nom affiché', 'Source autoritative', 'Numéro de série', 'Constructeur accrédité', 'Modèle', 'Site', 'Bâtiment', 'Salle', 'Ligne salle', 'Colonne salle', 'Rack', 'IP de management', 'État cycle de vie', 'Tags'] },
    { id: 'rsot-as-of', label: 'Restituer une ressource à date', path: '/v1/rsot/object-as-of', method: 'GET', fields: ['Clé RSOT', 'Date ISO-8601'] },
    { id: 'rsot-object-audit', label: 'Audit d’une ressource', path: '/v1/rsot/object-audit', method: 'GET', fields: ['Clé RSOT', 'Limite'] },
    { id: 'rsot-reconcile', label: 'Réconcilier une ressource', path: '/v1/rsot/reconcile-object', method: 'POST', fields: ['Opérateur', 'Clé RSOT', 'Source entrante', 'Catégorie', 'Type de ressource', 'Nom affiché cible', 'Numéro de série', 'Constructeur accrédité', 'Modèle', 'Site', 'Rack', 'Tags', 'Appliquer le plan'] },
    { id: 'graph-traverse', label: 'Explorer le graphe de dépendances', path: '/v1/graph/traverse', method: 'GET', fields: [
      { name: 'root_key', label: 'Clé racine', required: true }, { name: 'direction', label: 'Direction', type: 'select', options: ['outgoing', 'incoming', 'both'], defaultValue: 'both' },
      { name: 'max_depth', label: 'Profondeur maximale', type: 'number', defaultValue: '3' }, { name: 'max_nodes', label: 'Nombre maximal de nœuds', type: 'number', defaultValue: '500' },
      { name: 'relation_type', label: 'Type de relation' }, { name: 'as_of', label: 'Date ISO-8601' },
    ] },
    { id: 'graph-impact', label: 'Analyser les impacts', path: '/v1/graph/impact', method: 'GET', fields: [
      { name: 'root_key', label: 'Clé racine', required: true }, { name: 'direction', label: 'Direction', type: 'select', options: ['incoming', 'outgoing', 'both'], defaultValue: 'incoming' },
      { name: 'max_depth', label: 'Profondeur maximale', type: 'number', defaultValue: '6' }, { name: 'max_nodes', label: 'Nombre maximal de nœuds', type: 'number', defaultValue: '1000' },
      { name: 'relation_type', label: 'Type de relation' }, { name: 'as_of', label: 'Date ISO-8601' },
    ] },
    { id: 'graph-path', label: 'Trouver le chemin le plus court', path: '/v1/graph/path', method: 'GET', fields: [
      { name: 'source_key', label: 'Ressource source', required: true }, { name: 'target_key', label: 'Ressource cible', required: true },
      { name: 'direction', label: 'Direction', type: 'select', options: ['outgoing', 'incoming', 'both'], defaultValue: 'outgoing' },
      { name: 'max_depth', label: 'Profondeur maximale', type: 'number', defaultValue: '8' }, { name: 'max_nodes', label: 'Nombre maximal de nœuds', type: 'number', defaultValue: '1000' },
      { name: 'relation_type', label: 'Type de relation' }, { name: 'as_of', label: 'Date ISO-8601' },
    ] },
    { id: 'graph-spof', label: 'Détecter les points uniques de défaillance', path: '/v1/graph/spof', method: 'GET', fields: [
      { name: 'root_key', label: 'Clé racine', required: true }, { name: 'direction', label: 'Direction', type: 'select', options: ['outgoing', 'incoming', 'both'], defaultValue: 'both' },
      { name: 'max_depth', label: 'Profondeur maximale', type: 'number', defaultValue: '8' }, { name: 'max_nodes', label: 'Nombre maximal de nœuds', type: 'number', defaultValue: '2000' },
      { name: 'relation_type', label: 'Type de relation' }, { name: 'as_of', label: 'Date ISO-8601' },
      { name: 'candidate_kind', label: 'Type de candidat' }, { name: 'candidate_resource_category', label: 'Catégorie ressource candidate' },
      { name: 'candidate_resource_type', label: 'Type de ressource candidat' }, { name: 'candidate_status', label: 'Statut candidat' },
      { name: 'minimum_affected_nodes', label: 'Nombre minimal d’objets affectés', type: 'number', defaultValue: '1' },
      { name: 'affected_sample_limit', label: 'Limite échantillon affecté', type: 'number', defaultValue: '25' },
      { name: 'limit', label: 'Limite', type: 'number', defaultValue: '100' }, { name: 'cursor', label: 'Curseur' },
    ] },
    { id: 'graph-export', label: 'Exporter le graphe de dépendances', path: '/v1/graph/export', method: 'GET', download: true, fields: [
      { name: 'root_key', label: 'Clé racine', required: true }, { name: 'format', label: 'Format d’export', type: 'select', options: ['json', 'csv', 'graphml'], defaultValue: 'json' },
      { name: 'direction', label: 'Direction', type: 'select', options: ['outgoing', 'incoming', 'both'], defaultValue: 'both' },
      { name: 'max_depth', label: 'Profondeur maximale', type: 'number', defaultValue: '8' }, { name: 'max_nodes', label: 'Nombre maximal de nœuds', type: 'number', defaultValue: '2000' },
      { name: 'relation_type', label: 'Type de relation' }, { name: 'as_of', label: 'Date ISO-8601' },
      { name: 'include_spof', label: 'Inclure les SPOF', type: 'boolean', defaultValue: 'true' }, { name: 'candidate_kind', label: 'Type de candidat' },
      { name: 'candidate_resource_category', label: 'Catégorie ressource candidate' }, { name: 'candidate_resource_type', label: 'Type de ressource candidat' },
      { name: 'candidate_status', label: 'Statut candidat' }, { name: 'minimum_affected_nodes', label: 'Nombre minimal d’objets affectés', type: 'number', defaultValue: '1' },
    ] },
  ] },
  { id: 'flows', label: 'Matrice de flux', shortLabel: 'Flux', icon: 'activity', operations: [
    { id: 'flow-declaration-upsert', label: 'Créer ou réviser un flux déclaré', path: '/v1/flows/declarations/upsert', method: 'POST', fields: ['Opérateur', 'Code', 'Sélecteur source', 'Sélecteur destination', 'Protocole', 'Port destination début', 'Port destination fin', 'Décision', 'Priorité', 'Propriétaire', 'Justification', 'Début validité', 'Fin validité'] },
    { id: 'flow-declaration-list', label: 'Lister les flux déclarés', path: '/v1/flows/declarations', method: 'GET', fields: ['Limite', 'Curseur', 'Inclure retirés'] },
    { id: 'flow-declaration-retire', label: 'Retirer un flux déclaré', path: '/v1/flows/declarations/retire', method: 'POST', fields: ['Opérateur', 'ID déclaration'] },
    { id: 'flow-observation-submit', label: 'Ingérer un flux observé', path: '/v1/flows/observations/submit', method: 'POST', fields: ['Opérateur', 'Clé d’idempotence', 'Source observation', 'Collecteur', 'IP source', 'IP destination', 'Objet source', 'Objet destination', 'Protocole', 'Port destination', 'Paquets', 'Octets', 'Premier événement', 'Dernier événement'] },
    { id: 'flow-observation-list', label: 'Lister les flux observés', path: '/v1/flows/observations', method: 'GET', fields: ['Début fenêtre', 'Fin fenêtre', 'Source observation', 'Limite', 'Curseur'] },
    { id: 'flow-matrix', label: 'Comparer flux déclarés et observés', path: '/v1/flows/matrix', method: 'GET', fields: ['Début fenêtre', 'Fin fenêtre', 'Statut conformité', 'Source observation', 'Limite', 'Curseur'] },
  ] },
  { id: 'network-config', label: 'Conformité réseau', shortLabel: 'Config', icon: 'sliders', operations: [
    { id: 'network-config-baseline-upsert', label: 'Créer ou réviser une golden configuration', path: '/v1/network-config/baselines/upsert', method: 'POST', fields: ['Opérateur', 'Code', 'Objet équipement RSOT', 'Plateforme réseau', 'Configuration attendue JSON', 'Chemins ignorés', 'Chemins critiques', 'Propriétaire', 'Justification'] },
    { id: 'network-config-baseline-list', label: 'Lister les golden configurations', path: '/v1/network-config/baselines', method: 'GET', fields: ['Limite', 'Curseur', 'Inclure retirés'] },
    { id: 'network-config-baseline-retire', label: 'Retirer une golden configuration', path: '/v1/network-config/baselines/retire', method: 'POST', fields: ['Opérateur', 'ID baseline'] },
    { id: 'network-config-observation-submit', label: 'Ingérer une configuration découverte', path: '/v1/network-config/observations/submit', method: 'POST', fields: ['Opérateur', 'Clé d’idempotence', 'Source observation', 'Collecteur', 'Objet équipement RSOT', 'Plateforme réseau', 'Configuration observée JSON', 'Observé le (ISO-8601)'] },
    { id: 'network-config-observation-list', label: 'Lister les configurations découvertes', path: '/v1/network-config/observations', method: 'GET', fields: ['Objet équipement RSOT', 'Plateforme réseau', 'Observé avant', 'Limite', 'Curseur'] },
    { id: 'network-config-assessment', label: 'Évaluer la dérive réseau', path: '/v1/network-config/assessment', method: 'GET', fields: ['Opérateur', 'Code baseline', 'Date de référence', 'Statut conformité', 'Limite', 'Curseur'] },
  ] },
  { id: 'certificates', label: 'Certificats et PKI', shortLabel: 'Certificats', icon: 'shield', operations: [
    { id: 'certificate-import', label: 'Importer une chaîne PEM', path: '/v1/certificates/import', method: 'POST', fields: ['Opérateur', 'Chaîne de certificats PEM', 'Propriétaire', 'Environnement', 'Source certificat', 'Objet RSOT associé'] },
    { id: 'certificate-get', label: 'Consulter un certificat', path: '/v1/certificates/get', method: 'GET', fields: ['Empreinte SHA-256'] },
    { id: 'certificate-list', label: 'Lister les certificats', path: '/v1/certificates', method: 'GET', fields: ['Limite', 'Curseur', 'Inclure retirés'] },
    { id: 'certificate-retire', label: 'Retirer un certificat', path: '/v1/certificates/retire', method: 'POST', fields: ['Opérateur', 'Empreinte SHA-256'] },
    { id: 'certificate-endpoint-observe', label: 'Observer un endpoint TLS', path: '/v1/certificates/endpoints/observe', method: 'POST', fields: ['Opérateur', 'Clé d’idempotence', 'Protocole endpoint', 'Hôte endpoint', 'Port', 'Service', 'Empreinte certificat', 'Observé le (ISO-8601)', 'Source observation', 'Collecteur', 'Objet RSOT associé', 'Version TLS', 'Suite cryptographique'] },
    { id: 'certificate-endpoint-list', label: 'Lister les endpoints TLS', path: '/v1/certificates/endpoints', method: 'GET', fields: ['Empreinte certificat', 'Limite', 'Curseur'] },
    { id: 'certificate-assessment', label: 'Évaluer l’état PKI', path: '/v1/certificates/assessment', method: 'GET', fields: ['Date de référence', 'Seuil critique (jours)', 'Seuil avertissement (jours)', 'État certificat', 'Limite', 'Curseur'] },
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
    { id: 'dcim-buildings', label: 'Lister les bâtiments', path: '/v1/dcim/buildings', method: 'GET', fields: ['Site', 'Inclure retirés'] },
    { id: 'dcim-building', label: 'Consulter un bâtiment', path: '/v1/dcim/building', method: 'GET', fields: ['Site', 'Code bâtiment'] },
    { id: 'dcim-building-create', label: 'Créer un bâtiment', path: '/v1/dcim/building/create', method: 'POST', fields: ['Opérateur', 'Site', 'Code bâtiment', 'Nom bâtiment'] },
    { id: 'dcim-building-update', label: 'Modifier un bâtiment', path: '/v1/dcim/building/update', method: 'POST', fields: ['Opérateur', 'Site', 'Code bâtiment', 'Nom bâtiment', 'Statut'] },
    { id: 'dcim-building-delete', label: 'Retirer un bâtiment', path: '/v1/dcim/building/delete', method: 'POST', fields: ['Opérateur', 'Site', 'Code bâtiment'] },
    { id: 'dcim-floors', label: 'Lister les étages', path: '/v1/dcim/floors', method: 'GET', fields: ['Site', 'Bâtiment', 'Inclure retirés'] },
    { id: 'dcim-floor', label: 'Consulter un étage', path: '/v1/dcim/floor', method: 'GET', fields: ['Site', 'Bâtiment', 'Code étage'] },
    { id: 'dcim-rooms-list', label: 'Lister les salles', path: '/v1/dcim/rooms', method: 'GET', fields: ['Site', 'Bâtiment', 'Inclure retirés'] },
    { id: 'dcim-room', label: 'Consulter une salle', path: '/v1/dcim/room', method: 'GET', fields: ['Site', 'Bâtiment', 'Code salle'] },
    { id: 'dcim-room-create', label: 'Créer une salle', path: '/v1/dcim/room/create', method: 'POST', fields: ['Opérateur', 'Site', 'Bâtiment', 'Étage', 'Code salle', 'Nom salle', 'Lignes salle', 'Colonnes salle'] },
    { id: 'dcim-room-update', label: 'Modifier une salle', path: '/v1/dcim/room/update', method: 'POST', fields: ['Opérateur', 'Site', 'Bâtiment', 'Code salle', 'Nom salle', 'Lignes salle', 'Colonnes salle', 'Statut'] },
    { id: 'dcim-room-delete', label: 'Retirer une salle', path: '/v1/dcim/room/delete', method: 'POST', fields: ['Opérateur', 'Site', 'Bâtiment', 'Code salle'] },
    { id: 'dcim-zones', label: 'Lister les zones', path: '/v1/dcim/zones', method: 'GET', fields: ['Site', 'Bâtiment', 'Salle', 'Inclure retirés'] },
    { id: 'dcim-zone', label: 'Consulter une zone', path: '/v1/dcim/zone', method: 'GET', fields: ['Site', 'Bâtiment', 'Salle', 'Code zone'] },
    { id: 'dcim-zone-create', label: 'Créer une zone', path: '/v1/dcim/zone/create', method: 'POST', fields: ['Opérateur', 'Site', 'Bâtiment', 'Salle', 'Code zone', 'Nom zone', 'Lignes zone', 'Colonnes zone'] },
    { id: 'dcim-zone-update', label: 'Modifier une zone', path: '/v1/dcim/zone/update', method: 'POST', fields: ['Opérateur', 'Site', 'Bâtiment', 'Salle', 'Code zone', 'Nom zone', 'Lignes zone', 'Colonnes zone', 'Statut'] },
    { id: 'dcim-zone-delete', label: 'Retirer une zone', path: '/v1/dcim/zone/delete', method: 'POST', fields: ['Opérateur', 'Site', 'Bâtiment', 'Salle', 'Code zone'] },
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
    { id: 'field-sheet-list', label: 'Lister les fiches d’intervention', path: '/v1/field-operation-sheets', method: 'GET', fields: [
      { name: 'status', label: 'Statut', type: 'select', options: ['ready', 'in-progress', 'completed', 'cancelled'] },
      { name: 'target_type', label: 'Type de cible', type: 'select', options: ['equipment', 'rack', 'cable', 'power-device', 'certificate'] },
      { name: 'site', label: 'Site' }, { name: 'limit', label: 'Limite', type: 'number', defaultValue: '100', min: 1, max: 500 }, { name: 'cursor', label: 'Curseur' },
    ] },
    { id: 'field-sheet-get', label: 'Consulter une fiche d’intervention', path: '/v1/field-operation-sheets/get', method: 'GET', fields: [{ name: 'sheet_id', label: 'ID fiche', required: true }] },
    { id: 'field-sheet-generate', label: 'Générer une fiche d’intervention', path: '/v1/field-operation-sheets/generate', method: 'POST', fields: [
      { name: 'actor', label: 'Opérateur', required: true },
      { name: 'target_type', label: 'Type de cible', type: 'select', options: ['equipment', 'rack', 'cable', 'power-device', 'certificate'], required: true },
      { name: 'target_id', label: 'Identifiant cible', required: true }, { name: 'title', label: 'Titre', required: true },
      { name: 'purpose', label: 'Objet de l’intervention', type: 'textarea', rows: 4, required: true },
      { name: 'owner', label: 'Responsable', required: true }, { name: 'operator', label: 'Intervenant', required: true },
      { name: 'source_object_key', label: 'Clé objet RSOT' }, { name: 'site', label: 'Site' }, { name: 'building', label: 'Bâtiment' }, { name: 'room', label: 'Salle' },
      { name: 'location_target_type', label: 'Type de cible physique', type: 'select', options: ['equipment', 'rack', 'cable', 'power-device'] },
      { name: 'location_target_id', label: 'Identifiant cible physique' },
    ] },
    { id: 'field-lock-acquire', label: 'Verrouiller la cible', path: '/v1/intervention-locks/acquire', method: 'POST', fields: [
      { name: 'actor', label: 'Opérateur', required: true }, { name: 'sheet_id', label: 'ID fiche', required: true },
      { name: 'idempotency_key', label: 'Clé d’idempotence', required: true }, { name: 'ttl_seconds', label: 'Durée du verrou (secondes)', type: 'number', defaultValue: '3600', min: 60, max: 86400 },
    ] },
    { id: 'field-operation-start', label: 'Démarrer l’intervention', path: '/v1/field-operation-sheets/start', method: 'POST', fields: [{ name: 'actor', label: 'Opérateur', required: true }, { name: 'sheet_id', label: 'ID fiche', required: true }] },
    { id: 'field-checklist-record', label: 'Renseigner une étape de checklist', path: '/v1/field-operation-sheets/checklist', method: 'POST', fields: [
      { name: 'actor', label: 'Opérateur', required: true }, { name: 'sheet_id', label: 'ID fiche', required: true }, { name: 'item_id', label: 'ID étape', required: true },
      { name: 'result', label: 'Résultat', type: 'select', options: ['passed', 'failed', 'not-applicable'], required: true }, { name: 'operator_note', label: 'Note intervenant', type: 'textarea', rows: 3 },
    ] },
    { id: 'field-evidence-attach', label: 'Joindre une preuve terrain', path: '/v1/field-evidence/attach', method: 'POST', fields: [
      { name: 'actor', label: 'Opérateur', required: true }, { name: 'sheet_id', label: 'ID fiche', required: true },
      { name: 'phase', label: 'Phase', type: 'select', options: ['before', 'after'], required: true },
      { name: 'evidence_file', label: 'Photo ou document', type: 'file', accept: 'image/jpeg,image/png,image/webp,application/pdf', capture: 'environment', required: true },
      { name: 'caption', label: 'Description de la preuve', type: 'textarea', rows: 3, required: true },
    ] },
    { id: 'field-evidence-list', label: 'Lister les preuves terrain', path: '/v1/field-evidence', method: 'GET', fields: [{ name: 'sheet_id', label: 'ID fiche', required: true }] },
    { id: 'field-evidence-validate', label: 'Valider une preuve terrain', path: '/v1/field-evidence/validate', method: 'POST', fields: [{ name: 'actor', label: 'Opérateur', required: true }, { name: 'evidence_id', label: 'ID preuve', required: true }] },
    { id: 'field-operation-complete', label: 'Clôturer l’intervention', path: '/v1/field-operation-sheets/complete', method: 'POST', fields: [{ name: 'actor', label: 'Opérateur', required: true }, { name: 'sheet_id', label: 'ID fiche', required: true }] },
    { id: 'field-operation-cancel', label: 'Annuler l’intervention', path: '/v1/field-operation-sheets/cancel', method: 'POST', fields: [{ name: 'actor', label: 'Opérateur', required: true }, { name: 'sheet_id', label: 'ID fiche', required: true }] },
    { id: 'field-qr-verify', label: 'Vérifier un QR code terrain', path: '/v1/qr-codes/verify', method: 'POST', fields: [{ name: 'sheet_id', label: 'ID fiche', required: true }, { name: 'payload', label: 'Contenu QR', type: 'textarea', rows: 4, required: true }] },
    { id: 'field-lock-release', label: 'Libérer le verrou terrain', path: '/v1/intervention-locks/release', method: 'POST', fields: [{ name: 'actor', label: 'Opérateur', required: true }, { name: 'lock_id', label: 'ID verrou', required: true }] },
    { id: 'field-offline-create', label: 'Créer un paquet hors ligne', path: '/v1/offline-sync-packages/create', method: 'POST', fields: [
      { name: 'actor', label: 'Opérateur', required: true }, { name: 'sheet_id', label: 'ID fiche', required: true },
      { name: 'idempotency_key', label: 'Clé d’idempotence', required: true }, { name: 'ttl_seconds', label: 'Validité hors ligne (secondes)', type: 'number', defaultValue: '86400', min: 300, max: 604800 },
    ] },
    { id: 'field-offline-list', label: 'Lister les paquets hors ligne', path: '/v1/offline-sync-packages', method: 'GET', fields: [{ name: 'sheet_id', label: 'ID fiche' }, { name: 'limit', label: 'Limite', type: 'number', defaultValue: '100', min: 1, max: 500 }, { name: 'cursor', label: 'Curseur' }] },
    { id: 'field-offline-get', label: 'Consulter un paquet hors ligne', path: '/v1/offline-sync-packages/get', method: 'GET', fields: [{ name: 'package_id', label: 'ID paquet', required: true }, { name: 'include_payload', label: 'Inclure le contenu', type: 'boolean', defaultValue: 'true' }] },
    { id: 'field-offline-sync', label: 'Synchroniser un paquet hors ligne', path: '/v1/offline-sync-packages/synchronize', method: 'POST', fields: [{ name: 'actor', label: 'Opérateur', required: true }, { name: 'package_id', label: 'ID paquet', required: true }, { name: 'payload_sha256', label: 'Empreinte SHA-256 du paquet', required: true, maxLength: 64 }] },
    { id: 'dcim-digital-twin', label: 'Jumeau numérique salle', path: '/v1/dcim/digital-twin', method: 'GET', fields: ['Site', 'Bâtiment', 'Salle'] },
    { id: 'dcim-energy-cooling-capacity', label: 'Capacité énergie/refroidissement', path: '/v1/dcim/energy-cooling-capacity', method: 'GET', fields: ['Site', 'Bâtiment', 'Salle', 'Rack'] },
  ] },
  { id: 'itam', label: 'IT Asset Management', shortLabel: 'ITAM', icon: 'asset', operations: [
    { id: 'itam-organizations', label: 'Lister les organisations', path: '/v1/itam/organizations', method: 'GET', fields: ['Inclure retirées'] },
    { id: 'itam-organization', label: 'Voir une organisation', path: '/v1/itam/organization', method: 'GET', fields: ['Organisation'] },
    { id: 'itam-organization-create', label: 'Créer une organisation', path: '/v1/itam/organization/create', method: 'POST', fields: ['Code organisation', 'Opérateur', 'Raison sociale', 'N° immatriculation', 'Identifiant fiscal / TVA', 'Pays', 'Ville', 'Adresse siège', 'Email contact', 'Contact support'] },
    { id: 'itam-organization-update', label: 'Modifier une organisation', path: '/v1/itam/organization/update', method: 'POST', fields: ['Organisation', 'Opérateur', 'Raison sociale', 'Nom d’usage', 'N° immatriculation', 'Identifiant fiscal / TVA', 'Pays', 'Ville', 'Adresse siège', 'Email contact', 'Contact support', 'Statut', 'Description'] },
    { id: 'itam-organization-delete', label: 'Retirer une organisation', path: '/v1/itam/organization/delete', method: 'POST', fields: ['Organisation', 'Opérateur'] },
    { id: 'itam-partners', label: 'Lister les fournisseurs et supports', path: '/v1/itam/partners', method: 'GET', fields: ['Organisation', 'Type partenaire', 'Inclure retirés'] },
    { id: 'itam-partner', label: 'Voir un partenaire', path: '/v1/itam/partner', method: 'GET', fields: ['Organisation', 'Partenaire'] },
    { id: 'itam-partner-create', label: 'Créer un partenaire', path: '/v1/itam/partner/create', method: 'POST', fields: ['Organisation', 'Code partenaire', 'Type partenaire', 'Opérateur', 'Raison sociale', 'Nom d’usage', 'N° immatriculation', 'Identifiant fiscal / TVA', 'Pays', 'Ville', 'Adresse siège', 'Email contact', 'Téléphone', 'Contact support', 'Site web', 'Statut', 'Description'] },
    { id: 'itam-partner-update', label: 'Modifier un partenaire', path: '/v1/itam/partner/update', method: 'POST', fields: ['Organisation', 'Partenaire', 'Opérateur', 'Type partenaire', 'Raison sociale', 'Nom d’usage', 'N° immatriculation', 'Identifiant fiscal / TVA', 'Pays', 'Ville', 'Adresse siège', 'Email contact', 'Téléphone', 'Contact support', 'Site web', 'Statut', 'Description'] },
    { id: 'itam-partner-delete', label: 'Retirer un partenaire', path: '/v1/itam/partner/delete', method: 'POST', fields: ['Organisation', 'Partenaire', 'Opérateur'] },
    { id: 'itam-tenants', label: 'Lister les tenants', path: '/v1/itam/tenants', method: 'GET', fields: ['Inclure retirés'] },
    { id: 'itam-tenant-create', label: 'Créer un tenant', path: '/v1/itam/tenant/create', method: 'POST', fields: ['Organisation', 'Code tenant', 'Opérateur', 'Nom tenant', 'Statut', 'Tenant par défaut', 'Description'] },
    { id: 'itam-tenant-update', label: 'Modifier un tenant', path: '/v1/itam/tenant/update', method: 'POST', fields: ['Organisation', 'Tenant à modifier', 'Opérateur', 'Nom tenant', 'Statut', 'Tenant par défaut', 'Description'] },
    { id: 'itam-tenant-delete', label: 'Retirer un tenant', path: '/v1/itam/tenant/delete', method: 'POST', fields: ['Organisation', 'Tenant à retirer', 'Opérateur'] },
    { id: 'itam-support-profile', label: 'Profil support actif', path: '/v1/itam/support-profile', method: 'GET', fields: ['Numéro d’actif'] },
    { id: 'itam-support-coverage', label: 'Couverture support actif', path: '/v1/itam/support-coverage', method: 'GET', fields: ['Numéro d’actif', 'Date de référence'] },
    { id: 'itam-register-manufacturer', label: 'Déclarer garantie constructeur', path: '/v1/itam/support-profile/manufacturer', method: 'POST', fields: ['Opérateur', 'Numéro d’actif', 'Constructeur accrédité', 'Référence garantie', 'Niveau garantie', 'Début garantie', 'Fin garantie', 'Référence support', 'Niveau support', 'Contact support'] },
    { id: 'itam-add-third-party', label: 'Ajouter support tiers', path: '/v1/itam/support-profile/third-party', method: 'POST', fields: ['Opérateur', 'Numéro d’actif', 'Support tiers accrédité', 'Référence contrat', 'Niveau support', 'Début support', 'Fin support', 'Contact support', 'Statut', 'Notes'] },
    { id: 'itam-software-license', label: 'Licence logicielle', path: '/v1/itam/software-license', method: 'GET', fields: ['Référence licence'] },
    { id: 'itam-software-compliance', label: 'Conformité licence', path: '/v1/itam/software-license/compliance', method: 'GET', fields: ['Référence licence', 'Date de référence'] },
    { id: 'itam-register-software', label: 'Déclarer licence logicielle', path: '/v1/itam/software-license', method: 'POST', fields: ['Opérateur', 'Produit', 'Éditeur accrédité', 'Référence licence', 'Référence contrat', 'Métrique', 'Quantité achetée', 'Quantité assignée', 'Début droit', 'Fin droit', 'Version', 'Statut', 'Propriétaire', 'Notes'] },
    { id: 'itam-update-license-assignment', label: 'Mettre à jour affectation licence', path: '/v1/itam/software-license/assignment', method: 'POST', fields: ['Opérateur', 'Référence licence', 'Quantité assignée', 'Notes'] },
  ] },
  { id: 'discovery', label: 'Discovery', icon: 'activity', operations: [
    { id: 'discovery-evidence-list', label: 'Lister les preuves immuables', path: '/v1/discovery/evidence-list', method: 'GET', fields: ['Clé objet', 'Limite'] },
    { id: 'discovery-evidence', label: 'Voir une preuve immuable', path: '/v1/discovery/evidence', method: 'GET', fields: ['ID preuve'] },
    { id: 'discovery-evidence-submit', label: 'Enregistrer une preuve Discovery', path: '/v1/discovery/evidence', method: 'POST', fields: ['Opérateur', 'ID preuve imposé', 'Clé objet', 'Type objet', 'Source', 'Référence source', 'Scope', 'ID externe', 'Confiance', 'Observé le', 'Preuve JSON sans secret'] },
    { id: 'discovery-reconciliation-list', label: 'Lister les rapprochements', path: '/v1/discovery/reconciliation-list', method: 'GET', fields: ['Statut', 'Limite'] },
    { id: 'discovery-reconciliation', label: 'Voir un rapprochement', path: '/v1/discovery/reconciliation', method: 'GET', fields: ['ID rapprochement'] },
    { id: 'discovery-reconcile', label: 'Rapprocher plusieurs preuves', path: '/v1/discovery/reconciliation', method: 'POST', fields: ['Opérateur', 'Clé objet', 'IDs preuves', 'Âge maximal'] },
    { id: 'discovery-reconciliation-resolve', label: 'Résoudre les conflits', path: '/v1/discovery/reconciliation/resolve', method: 'POST', fields: ['Opérateur', 'ID rapprochement', 'Sélections par chemin JSON', 'Justification'] },
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
    { label: 'Exploration', operationIds: ['graph-traverse', 'graph-path'] },
    { label: 'Analyse d’impact', operationIds: ['graph-impact', 'graph-spof'] },
    { label: 'Exports', operationIds: ['graph-export'] },
  ],
  flows: [
    { label: 'Flux déclarés', operationIds: ['flow-declaration-upsert', 'flow-declaration-list', 'flow-declaration-retire'] },
    { label: 'Flux observés', operationIds: ['flow-observation-submit', 'flow-observation-list'] },
    { label: 'Conformité des flux', operationIds: ['flow-matrix'] },
  ],
  'network-config': [
    { label: 'Golden configurations', operationIds: ['network-config-baseline-upsert', 'network-config-baseline-list', 'network-config-baseline-retire'] },
    { label: 'Configurations découvertes', operationIds: ['network-config-observation-submit', 'network-config-observation-list'] },
    { label: 'Conformité et drift', operationIds: ['network-config-assessment'] },
  ],
  certificates: [
    { label: 'Inventaire PKI', operationIds: ['certificate-import', 'certificate-get', 'certificate-list', 'certificate-retire'] },
    { label: 'Endpoints TLS', operationIds: ['certificate-endpoint-observe', 'certificate-endpoint-list'] },
    { label: 'Conformité PKI', operationIds: ['certificate-assessment'] },
  ],
  ipam: [
    { label: 'Vue & recherche', operationIds: ['ipam-dashboard', 'ipam-search'] },
    { label: 'Adressage IP', operationIds: ['ipam-define-vrf', 'ipam-define-aggregate', 'ipam-define-prefix', 'ipam-list-prefixes', 'ipam-define-range', 'ipam-register-address', 'ipam-allocate', 'ipam-reservation-wizard', 'ipam-capacity'] },
    { label: 'Réseau L2/L3', operationIds: ['ipam-network-bindings', 'ipam-topology', 'ipam-define-vlan-group', 'ipam-define-vxlan-vni', 'ipam-define-vlan', 'ipam-define-asn', 'ipam-define-bgp-peer'] },
    { label: 'Observations & DDI', operationIds: ['ipam-observe-dns', 'ipam-observe-dhcp', 'ipam-conflicts', 'ipam-ddi-preview'] },
  ],
  dcim: [
    { label: 'Sites & dépendances', operationIds: ['dcim-sites', 'dcim-site', 'dcim-site-create', 'dcim-site-update', 'dcim-site-delete', 'dcim-buildings', 'dcim-building', 'dcim-building-create', 'dcim-building-update', 'dcim-building-delete', 'dcim-floors', 'dcim-floor', 'dcim-rooms-list', 'dcim-room', 'dcim-room-create', 'dcim-room-update', 'dcim-room-delete', 'dcim-zones', 'dcim-zone', 'dcim-zone-create', 'dcim-zone-update', 'dcim-zone-delete', 'dcim-topology-catalog'] },
    { label: 'Localisation & capacité', operationIds: ['dcim-locate-equipment', 'dcim-rack-capacity', 'dcim-room-plan', 'dcim-rack-elevation'] },
    { label: 'Connectivité', operationIds: ['dcim-patch-panel', 'dcim-port', 'dcim-cable', 'dcim-cable-trace'] },
    { label: 'Énergie & refroidissement', operationIds: ['dcim-power-device', 'dcim-power-circuit', 'dcim-cooling-zone', 'dcim-power-reservation', 'dcim-energy-cooling-capacity'] },
    { label: 'Opérations terrain', operationIds: ['field-sheet-list', 'field-sheet-get', 'field-sheet-generate', 'field-lock-acquire', 'field-operation-start', 'field-checklist-record', 'field-evidence-attach', 'field-evidence-list', 'field-evidence-validate', 'field-operation-complete', 'field-operation-cancel', 'field-qr-verify', 'field-lock-release', 'field-offline-create', 'field-offline-list', 'field-offline-get', 'field-offline-sync'] },
    { label: 'Jumeau numérique', operationIds: ['dcim-digital-twin'] },
  ],
  itam: [
    { label: 'Organisations', operationIds: ['itam-organizations', 'itam-organization', 'itam-organization-create', 'itam-organization-update', 'itam-organization-delete'] },
    { label: 'Tenants', operationIds: ['itam-tenants', 'itam-tenant', 'itam-tenant-create', 'itam-tenant-update', 'itam-tenant-delete'] },
    { label: 'Partenaires', operationIds: ['itam-partners', 'itam-partner', 'itam-partner-create', 'itam-partner-update', 'itam-partner-delete'] },
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

function sidebarContextKey(moduleId, label) {
  return `${moduleId}::${label}`;
}

function contextForOperation(module, operationId) {
  return sidebarOperationGroups(module).find((group) => group.operations.some((operation) => operation.id === operationId));
}

function withoutModuleContexts(openedContexts, moduleId) {
  const next = new Set(openedContexts);
  for (const key of Array.from(next)) {
    if (key.startsWith(`${moduleId}::`)) {
      next.delete(key);
    }
  }
  return next;
}

function slugifyContextLabel(value) {
  return String(value ?? 'context')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'context';
}

function isMegamenuViewport() {
  return typeof window !== 'undefined'
    && window.matchMedia('(min-width: 768px) and (max-width: 1199.98px)').matches;
}

function NavigationTree({
  modules,
  activeNavigationModuleId,
  selectedOperationId,
  opened,
  openedContexts,
  chooseOperation,
  toggleAccordion,
  toggleSidebarContext,
  surface = 'sidebar',
}) {
  return modules.map((module) => {
    if (module.id === 'overview') {
      return <button key={module.id} type="button" className={`nav-link openinfra-sidebar-dashboard w-100 text-start ${activeNavigationModuleId === module.id ? 'active' : ''}`} aria-current={activeNavigationModuleId === module.id ? 'page' : undefined} onClick={() => chooseOperation(module, module.operations[0])}><Icon name={module.icon} />Dashboard</button>;
    }
    const moduleOpened = opened.has(module.id);
    const accordionId = `openinfra-${surface}-accordion-${module.id}`;
    const panelId = `openinfra-${surface}-panel-${module.id}`;
    return <section className={`openinfra-accordion ${moduleOpened ? 'open' : ''}`} key={module.id}>
      <button type="button" id={accordionId} className={`openinfra-accordion-toggle ${activeNavigationModuleId === module.id ? 'active' : ''}`} aria-expanded={moduleOpened} aria-controls={panelId} aria-current={activeNavigationModuleId === module.id ? 'page' : undefined} onClick={() => toggleAccordion(module.id)}><span><Icon name={module.icon} />{module.shortLabel || module.label}</span><span className="openinfra-chevron">›</span></button>
      <div id={panelId} className={`openinfra-accordion-panel fade ${moduleOpened ? 'show' : ''}`} role="region" aria-labelledby={accordionId}>
        <div className="openinfra-accordion-panel-inner">
          {sidebarOperationGroups(module).map((group) => {
            const contextKey = sidebarContextKey(module.id, group.label);
            const contextOpened = openedContexts.has(contextKey);
            const contextId = `openinfra-${surface}-context-${module.id}-${slugifyContextLabel(group.label)}`;
            return <section key={`${module.id}-${group.label}`} className={`openinfra-sidebar-context ${contextOpened ? 'open' : ''}`} role="group" aria-label={group.label}>
              <button type="button" className={`openinfra-sidebar-context-title ${contextOpened && activeNavigationModuleId === module.id ? 'active' : ''}`} aria-expanded={contextOpened} aria-controls={contextId} onClick={() => toggleSidebarContext(module.id, group.label)}>{group.label}</button>
              <div id={contextId} className={`openinfra-sidebar-context-panel ${contextOpened ? 'show' : ''}`} role="region" aria-label={group.label}>
                <div className="openinfra-sidebar-context-panel-inner">
                  {group.operations.map((operation) => <button key={operation.id} type="button" className={`openinfra-sidebar-operation ${selectedOperationId === operation.id ? 'active' : ''}`} aria-current={selectedOperationId === operation.id ? 'page' : undefined} onClick={() => chooseOperation(module, operation)}>{operation.label}</button>)}
                </div>
              </div>
            </section>;
          })}
        </div>
      </div>
    </section>;
  });
}

function MegaMenu({ module, selectedOperationId, chooseOperation, close, i18n }) {
  if (!module || module.id === 'overview') {
    return null;
  }
  return <section id="openinfra-mega-menu" className="openinfra-mega-menu" aria-label={module.shortLabel || module.label}>
    <div className="openinfra-mega-menu-header"><div><Icon name={module.icon} className="openinfra-mega-menu-icon" /><strong>{module.label}</strong></div><button type="button" className="openinfra-navigation-close" aria-label={i18n.t('closeNavigation')} onClick={close}>×</button></div>
    <div className="openinfra-mega-menu-grid">
      {sidebarOperationGroups(module).map((group) => <section className="openinfra-mega-menu-group" role="group" aria-label={group.label} key={`${module.id}-${group.label}`}><h2>{group.label}</h2><div>{group.operations.map((operation) => <button key={operation.id} type="button" className={`openinfra-sidebar-operation ${selectedOperationId === operation.id ? 'active' : ''}`} aria-current={selectedOperationId === operation.id ? 'page' : undefined} onClick={() => chooseOperation(module, operation, true)}>{operation.label}</button>)}</div></section>)}
    </div>
  </section>;
}

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('Impossible de lire la preuve sélectionnée.'));
    reader.onload = () => {
      const result = String(reader.result || '');
      const separator = result.indexOf(',');
      if (separator < 0) reject(new Error('Le fichier sélectionné est invalide.'));
      else resolve(result.slice(separator + 1));
    };
    reader.readAsDataURL(file);
  });
}

function OperationField({ entry, index, i18n, language }) {
  const field = normalizeFieldDefinition(entry, index);
  const fieldId = `openinfra-react-field-${index}`;
  const requiredText = field.required ? <span aria-hidden="true"> *</span> : null;
  if (field.type === 'file') {
    const attributes = inputAttributesForField(field);
    return <div className="col-12"><label className="form-label" htmlFor={fieldId}>{i18n.label(field.label)}{requiredText}</label><input id={fieldId} name={field.name} className="form-control" type="file" required={field.required} {...attributes} onChange={(event) => { event.currentTarget.setCustomValidity(''); event.currentTarget.removeAttribute('aria-invalid'); }} /><p className="form-text">JPEG, PNG, WebP ou PDF — 2 Mio maximum.</p></div>;
  }
  if (field.type === 'select' || field.type === 'boolean') {
    const options = field.type === 'boolean' ? ['false', 'true'] : field.options || [];
    return <div className="col-md-6 col-xl-4"><label className="form-label" htmlFor={fieldId}>{i18n.label(field.label)}{requiredText}</label><select id={fieldId} name={field.name} className="form-select" defaultValue={field.defaultValue ?? ''} required={field.required} onInput={(event) => validateControl(event.currentTarget, field, i18n, { countryCode: formCountryCode(event.currentTarget.form) })}><option value=""></option>{options.map((option) => <option value={option} key={option}>{field.type === 'boolean' ? (option === 'true' ? i18n.t('yes') : i18n.t('no')) : i18n.optionLabel(option)}</option>)}</select></div>;
  }
  const attributes = inputAttributesForField(field);
  const common = {
    id: fieldId,
    name: field.name,
    defaultValue: field.defaultValue ?? '',
    required: field.required,
    className: 'form-control',
    lang: language,
    placeholder: field.placeholder ? i18n.label(field.placeholder) : undefined,
    ...attributes,
    onInput: (event) => validateControl(event.currentTarget, field, i18n, { countryCode: formCountryCode(event.currentTarget.form) }),
    onBlur: (event) => validateControl(event.currentTarget, field, i18n, { countryCode: formCountryCode(event.currentTarget.form) }),
  };
  return <div className={field.type === 'textarea' || field.type === 'json' ? 'col-12' : 'col-md-6 col-xl-4'}><label className="form-label" htmlFor={fieldId}>{i18n.label(field.label)}{requiredText}</label>{field.type === 'textarea' || field.type === 'json' ? <textarea {...common} rows={field.rows || 8} className="form-control font-monospace" /> : <input {...common} type={inputTypeForField(field)} />}</div>;
}

function validateOperationForm(form, fields, i18n) {
  const controls = Array.from(form.querySelectorAll('input[name], select[name], textarea[name]'));
  const countryCode = formCountryCode(form);
  let valid = true;
  fields.forEach((entry, index) => {
    const field = normalizeFieldDefinition(entry, index);
    const control = controls.find((candidate) => candidate.name === field.name);
    if (!control) return;
    if (field.type === 'file') {
      const file = control.files?.[0];
      const accepted = new Set(['image/jpeg', 'image/png', 'image/webp', 'application/pdf']);
      let message = '';
      if (file && file.size > 2 * 1024 * 1024) message = 'Le fichier dépasse la limite de 2 Mio.';
      else if (file && !accepted.has(file.type)) message = 'Le format de fichier n’est pas autorisé.';
      control.setCustomValidity(message);
      if (message) {
        control.setAttribute('aria-invalid', 'true');
        valid = false;
      } else control.removeAttribute('aria-invalid');
      return;
    }
    if (!validateControl(control, field, i18n, { countryCode })) valid = false;
  });
  if (!valid || !form.checkValidity()) {
    form.reportValidity();
    return false;
  }
  return true;
}

function OperationForm({ i18n, language, selected, tenant, setTenant, execute }) {
  const fields = selected.fields.map((entry, index) => normalizeFieldDefinition(entry, index));
  return <form aria-describedby="openinfra-required-fields-notice" noValidate onSubmit={(event) => { event.preventDefault(); if (validateOperationForm(event.currentTarget, fields, i18n)) execute(event.currentTarget, fields); }}><p id="openinfra-required-fields-notice" className="openinfra-required-notice">{i18n.t('requiredFieldsNotice')}</p><div className="row g-3 mb-3"><label className="col-md-4 form-label" htmlFor="openinfra-react-tenant">{i18n.t('organization')}</label><select id="openinfra-react-tenant" className="form-select" value={tenant} onChange={(event) => setTenant(event.target.value)}><option value="default">{i18n.t('defaultTenant')}</option></select></div><div className="row g-3">{fields.map((field, index) => <OperationField entry={field} index={index} i18n={i18n} language={language} key={field.name} />)}</div><button type="submit" className="btn btn-primary mt-3">{i18n.t('execute')}</button></form>;
}

function Dashboard() {
  const [i18n] = useState(() => new OpenInfraI18n());
  const [language, setLanguage] = useState(i18n.language);
  localizeOpenInfraCatalog({
    modules: MODULES,
    contexts: SIDEBAR_CONTEXTS,
    resourceTaxonomy: RESOURCE_TAXONOMY,
    resourceCategories: RESOURCE_CATEGORY_OPTIONS,
  }, language);
  const [config, setConfig] = useState({ apiBaseUrl: '/api', apiDocumentation: { swaggerUrl: '/docs', redocUrl: '/redoc', openapiUrl: '/openapi.yaml' }, version: i18n.t('unavailable'), webBackendTrust: 'server-side' });
  const [ready, setReady] = useState(null);
  const [bffStatus, setBffStatus] = useState(null);
  const [version, setVersion] = useState(null);
  const [selected, setSelected] = useState(MODULES[0].operations[0]);
  const [activeModuleId, setActiveModuleId] = useState('overview');
  const [activeNavigationModuleId, setActiveNavigationModuleId] = useState('overview');
  const [opened, setOpened] = useState(new Set());
  const [openedContexts, setOpenedContexts] = useState(new Set());
  const [tenant, setTenant] = useState('default');
  const [result, setResult] = useState(null);
  const [globalSearchQuery, setGlobalSearchQuery] = useState('');
  const [globalSearchBackend, setGlobalSearchBackend] = useState(null);
  const [globalSearchLoading, setGlobalSearchLoading] = useState(false);
  const [globalSearchError, setGlobalSearchError] = useState(null);
  const [shouldFocusMain, setShouldFocusMain] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [megaMenuModuleId, setMegaMenuModuleId] = useState(null);
  const [announcement, setAnnouncement] = useState({ id: 0, text: '' });
  const mainContentRef = useRef(null);
  const lastComponentTriggerRef = useRef(null);
  const businessModules = useMemo(() => componentModules(), []);
  const operationsCount = useMemo(() => MODULES.reduce((total, module) => total + module.operations.length, 0), []);
  const businessFieldsCount = useMemo(() => businessModules.reduce((total, module) => total + moduleStatistics(module).fields, 0), [businessModules]);
  const searchGroups = useMemo(() => globalSearchGroups(globalSearchQuery), [globalSearchQuery, language]);
  const apiDocs = useMemo(() => apiDocumentationLinks(config), [config]);


  useLayoutEffect(() => {
    i18n.translateDom(document.getElementById('openinfra-root'));
    document.documentElement.lang = language;
    document.title = `OpenInfra — ${activeModuleId === 'overview' ? 'Dashboard' : selected.label}`;
  }, [activeModuleId, i18n, language, selected.label]);

  function announce(text) {
    setAnnouncement({ id: Date.now(), text });
  }

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
    const closeResponsiveNavigationFromDocument = (event) => {
      if (event?.type === 'keydown' && event.key !== 'Escape') {
        return;
      }
      if (event?.key === 'Escape' && (mobileSidebarOpen || megaMenuModuleId)) {
        event.preventDefault();
        setMobileSidebarOpen(false);
        setMegaMenuModuleId(null);
        setActiveNavigationModuleId(activeModuleId);
        announce(i18n.t('navigationClosed'));
        window.requestAnimationFrame(() => lastComponentTriggerRef.current?.focus());
      }
    };
    const handleResize = () => {
      if (!isMegamenuViewport()) {
        setMegaMenuModuleId(null);
      }
      if (!window.matchMedia('(max-width: 767.98px)').matches) {
        setMobileSidebarOpen(false);
      }
    };
    document.addEventListener('keydown', closeResponsiveNavigationFromDocument);
    window.addEventListener('resize', handleResize);
    return () => {
      document.removeEventListener('keydown', closeResponsiveNavigationFromDocument);
      window.removeEventListener('resize', handleResize);
    };
  }, [activeModuleId, i18n, megaMenuModuleId, mobileSidebarOpen]);

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
    setActiveNavigationModuleId(module.id);
    setOpened((current) => module.id === 'overview' ? new Set() : new Set([...current, module.id]));
    setOpenedContexts((current) => {
      if (module.id === 'overview') {
        return new Set();
      }
      const next = withoutModuleContexts(current, module.id);
      const context = contextForOperation(module, operation.id);
      if (context) {
        next.add(sidebarContextKey(module.id, context.label));
      }
      return next;
    });
    setResult(null);
    announce(i18n.t('operationSelected', { operation: operation.label }));
    setMobileSidebarOpen(false);
    setMegaMenuModuleId(null);
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
    setActiveNavigationModuleId(module.id);
    setOpened((current) => current.has(moduleId) ? new Set() : new Set([moduleId]));
    setOpenedContexts(new Set());
  }

  function toggleSidebarContext(moduleId, contextLabel) {
    const module = MODULES.find((item) => item.id === moduleId);
    if (!module || !contextLabel) {
      return;
    }
    setActiveNavigationModuleId(module.id);
    setOpened(new Set([moduleId]));
    setOpenedContexts((current) => {
      const contextKey = sidebarContextKey(moduleId, contextLabel);
      const wasOpen = current.has(contextKey);
      const next = new Set();
      if (!wasOpen) {
        next.add(contextKey);
      }
      return next;
    });
  }

  function changeLanguage(nextLanguage) {
    const normalized = i18n.setLanguage(nextLanguage);
    document.documentElement.lang = normalized;
    setLanguage(normalized);
  }

  function openMegaMenu(module, trigger = null) {
    if (module.id === 'overview' || !isMegamenuViewport()) {
      return;
    }
    if (trigger instanceof HTMLElement) {
      lastComponentTriggerRef.current = trigger;
    }
    setActiveNavigationModuleId(module.id);
    setMobileSidebarOpen(false);
    setMegaMenuModuleId(module.id);
    announce(i18n.t('navigationOpened', { component: module.shortLabel || module.label }));
  }

  function handleModuleNavigation(module) {
    if (module.id === 'overview' || !isMegamenuViewport()) {
      chooseOperation(module, module.operations[0]);
      return;
    }
    openMegaMenu(module);
  }

  function closeResponsiveNavigation({ restoreFocus = false } = {}) {
    setMobileSidebarOpen(false);
    setMegaMenuModuleId(null);
    setActiveNavigationModuleId(activeModuleId);
    announce(i18n.t('navigationClosed'));
    if (restoreFocus) {
      window.requestAnimationFrame(() => lastComponentTriggerRef.current?.focus());
    }
  }

  function handleComponentNavigationKeyDown(event, index, module) {
    const buttons = Array.from(document.querySelectorAll('.openinfra-component-link'));
    const focusAt = (targetIndex) => buttons[targetIndex]?.focus();
    if (event.key === 'ArrowRight') {
      event.preventDefault();
      focusAt((index + 1) % buttons.length);
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault();
      focusAt((index - 1 + buttons.length) % buttons.length);
    } else if (event.key === 'Home') {
      event.preventDefault();
      focusAt(0);
    } else if (event.key === 'End') {
      event.preventDefault();
      focusAt(buttons.length - 1);
    } else if (event.key === 'ArrowDown' && module.id !== 'overview') {
      event.preventDefault();
      openMegaMenu(module, event.currentTarget);
      window.requestAnimationFrame(() => document.querySelector('.openinfra-mega-menu .openinfra-sidebar-operation')?.focus());
    }
  }

  async function execute(form, fields) {
    const isLiveOperation = selected.id.startsWith('graph-') || selected.id.startsWith('field-');
    if (!isLiveOperation) {
      setResult({ tenant_id: tenant, action: selected.id, via: config.apiBaseUrl, trust: config.webBackendTrust });
      return;
    }
    try {
      const formData = new FormData(form);
      const countryCode = formCountryCode(form);
      const query = new URLSearchParams();
      const body = { tenant_id: tenant };
      query.set('tenant_id', tenant);
      for (const field of fields) {
        if (field.type === 'file') {
          const file = form.querySelector(`[name="${field.name}"]`)?.files?.[0];
          if (!file) continue;
          body.filename = file.name;
          body.media_type = file.type;
          body.content_base64 = await readFileAsBase64(file);
          continue;
        }
        const normalized = normalizeFieldValue(field, formData.get(field.name), { countryCode });
        if (normalized === undefined) continue;
        if (selected.method === 'GET') query.append(field.name, typeof normalized === 'string' ? normalized : JSON.stringify(normalized));
        else body[field.name] = normalized;
      }
      const apiBase = String(config.apiBaseUrl || '/api').replace(/\/$/, '');
      const requestUrl = selected.method === 'GET' ? `${apiBase}${selected.path}?${query}` : `${apiBase}${selected.path}`;
      const response = await fetch(requestUrl, {
        method: selected.method,
        credentials: 'same-origin',
        headers: selected.method === 'GET'
          ? { Accept: selected.download ? '*/*' : 'application/json' }
          : { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: selected.method === 'GET' ? undefined : JSON.stringify(body),
      });
      if (selected.download) {
        const blob = await response.blob();
        if (!response.ok) throw new Error(await blob.text() || `HTTP ${response.status}`);
        const disposition = response.headers.get('content-disposition') || '';
        const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1] || 'openinfra-graph-export.bin';
        const objectUrl = URL.createObjectURL(blob);
        try {
          const anchor = document.createElement('a');
          anchor.href = objectUrl;
          anchor.download = filename;
          anchor.hidden = true;
          document.body.append(anchor);
          anchor.click();
          anchor.remove();
        } finally {
          URL.revokeObjectURL(objectUrl);
        }
        setResult({ downloaded: true, filename, content_type: blob.type || response.headers.get('content-type'), size_bytes: blob.size });
      } else {
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || JSON.stringify(payload));
        setResult(payload);
      }
      setShouldFocusMain(true);
    } catch (error) {
      setResult({ error: error.message });
      setShouldFocusMain(true);
    }
  }

  const displayedVersion = version?.version || config.version || i18n.t('unavailable');
  const filteredModules = MODULES;
  const submissionCompleted = result !== null;
  const protectedForms = bffStatus?.protectedForms === 'enabled' ? i18n.t('active') : i18n.t('configure');
  const activeModule = MODULES.find((module) => module.id === activeModuleId) || MODULES[0];
  const pageTitle = activeModuleId === 'overview' ? 'Dashboard' : activeModule.shortLabel || activeModule.label;
  const pageSubtitle = activeModuleId === 'overview'
    ? i18n.t('dashboardSubtitle')
    : i18n.t('operationSubtitle', { operation: selected.label });

  const megaMenuModule = MODULES.find((module) => module.id === megaMenuModuleId) || null;
  const runtimeStatus = <div className="px-2 small text-muted openinfra-runtime-status" role="status" aria-live="polite" aria-atomic="true">
    <p><span className={`openinfra-status-dot ${ready?.ready === true ? 'ready' : 'warning'}`} />{ready?.ready === true ? i18n.t('backendReady') : i18n.t('backendCheck')}</p>
    <p>{i18n.t('version')} : <strong>{displayedVersion}</strong></p>
    <p>Trust web/backend : <strong>{config.webBackendTrust || 'server-side'}</strong></p>
    <p>{i18n.t('protectedForms')} : <strong>{protectedForms}</strong></p>
  </div>;

  return <div className="openinfra-shell">
    <div className="openinfra-skip-links" aria-label={i18n.t('accessibilityStatus')}>
      <a className="openinfra-skip-link" href="#openinfra-main-content">{i18n.t('skipToContent')}</a>
      <a className="openinfra-skip-link" href="#openinfra-component-navigation">{i18n.t('skipToNavigation')}</a>
      <a className="openinfra-skip-link" href="#openinfra-global-search">{i18n.t('skipToSearch')}</a>
    </div>
    <div key={announcement.id} className="openinfra-live-region" role="status" aria-live="polite" aria-atomic="true">{announcement.text}</div>
    <header className="openinfra-header-stack" role="banner">
      <div className="px-3 py-2 bg-dark text-white openinfra-top-header">
        <div className="container-fluid">
          <div className="d-flex align-items-center openinfra-top-header-inner">
            <a href="/" className="d-flex align-items-center openinfra-brand-link text-white text-decoration-none" aria-label={i18n.t('home')}>
              <span className="openinfra-brand-mark me-2">OI</span>
              <span className="fs-5 fw-semibold openinfra-brand-name">OpenInfra</span>
              <span className="badge openinfra-edition-badge ms-3">{config.edition || 'runtime'}</span>
            </a>
            <nav id="openinfra-component-navigation" className="openinfra-component-navigation" aria-label={i18n.t('navigation')} aria-describedby="openinfra-component-navigation-instructions">
              <p id="openinfra-component-navigation-instructions" className="openinfra-component-navigation-instructions">{i18n.t('componentNavigationInstructions')}</p>
              <ul className="nav justify-content-center text-small openinfra-component-nav">
                {MODULES.map((module, index) => <li key={module.id}><button id={`openinfra-component-${module.id}`} data-component-index={index} type="button" className={`nav-link border-0 bg-transparent openinfra-component-link ${activeNavigationModuleId === module.id ? 'active' : ''}`} aria-current={activeNavigationModuleId === module.id ? 'page' : undefined} aria-haspopup={module.id === 'overview' ? undefined : 'true'} aria-expanded={module.id === 'overview' ? undefined : megaMenuModuleId === module.id} aria-controls={module.id === 'overview' ? undefined : 'openinfra-mega-menu'} onMouseEnter={(event) => openMegaMenu(module, event.currentTarget)} onFocus={(event) => openMegaMenu(module, event.currentTarget)} onKeyDown={(event) => handleComponentNavigationKeyDown(event, index, module)} onClick={(event) => { lastComponentTriggerRef.current = event.currentTarget; handleModuleNavigation(module); }}><Icon name={module.icon} className="bi d-block mx-auto mb-1 openinfra-top-icon" /><span>{module.shortLabel || module.label}</span></button></li>)}
              </ul>
            </nav>
            <button type="button" id="openinfra-compact-menu-button" className="btn btn-primary openinfra-compact-menu-button" aria-label={i18n.t(mobileSidebarOpen ? 'closeNavigation' : 'openNavigation')} aria-expanded={mobileSidebarOpen} aria-controls="openinfra-compact-navigation" onClick={() => { setMegaMenuModuleId(null); setMobileSidebarOpen((open) => !open); }}><Icon name="menu" className="openinfra-mobile-menu-icon" /><span className="visually-hidden">Menu</span></button>
          </div>
        </div>
      </div>
      <div className="px-3 py-2 border-bottom openinfra-global-toolbar">
        <div className="container-fluid openinfra-global-toolbar-inner">
          <div className="openinfra-global-toolbar-spacer" aria-hidden="true" />
          <form className="openinfra-global-search-form" role="search" aria-label={i18n.t('globalSearch')} autoComplete="off">
            <label className="visually-hidden" htmlFor="openinfra-global-search">{i18n.t('globalSearch')}</label>
            <div className="openinfra-global-search-control"><Icon name="search" className="openinfra-global-search-icon" /><input type="search" id="openinfra-global-search" className="form-control" placeholder={i18n.t('globalSearchPlaceholder')} aria-label={i18n.t('globalSearch')} role="combobox" aria-autocomplete="list" aria-haspopup="listbox" aria-controls="openinfra-global-search-results" aria-expanded={globalSearchQuery.trim() !== ''} value={globalSearchQuery} onChange={(event) => setGlobalSearchQuery(event.target.value)} onKeyDown={(event) => { if (event.key === 'Escape') setGlobalSearchQuery(''); }} /></div>
            {globalSearchQuery.trim() !== '' && <div id="openinfra-global-search-results" className="openinfra-global-search-results" role="listbox" aria-label={i18n.t('globalSearchResults')} aria-live="polite" aria-atomic="false" aria-busy={globalSearchLoading}><GlobalSearchResults i18n={i18n} query={globalSearchQuery} groups={searchGroups} backend={globalSearchBackend} loading={globalSearchLoading} error={globalSearchError} onSelect={selectSearchOperation} onBackendSelect={selectBackendSearchItem} /></div>}
          </form>
          <div className="openinfra-toolbar-actions">
            <div className="openinfra-language-control"><label className="visually-hidden" htmlFor="openinfra-language">{i18n.t('language')}</label><select id="openinfra-language" className="form-select form-select-sm" aria-label={i18n.t('language')} value={language} onChange={(event) => changeLanguage(event.target.value)}><option value="en">EN</option><option value="fr">FR</option></select></div>
            <div className="text-end openinfra-api-doc-actions"><a className="btn btn-light text-dark" href={apiDocs.swaggerUrl} target="_blank" rel="noopener noreferrer" aria-label={`${i18n.t('openSwagger')} — ${i18n.t('opensNewWindow')}`}>Swagger</a><a className="btn btn-primary" href={apiDocs.redocUrl} target="_blank" rel="noopener noreferrer" aria-label={`${i18n.t('openRedoc')} — ${i18n.t('opensNewWindow')}`}>ReDoc</a></div>
          </div>
        </div>
      </div>
      <MegaMenu module={megaMenuModule} selectedOperationId={selected.id} chooseOperation={chooseOperation} close={closeResponsiveNavigation} i18n={i18n} />
      {mobileSidebarOpen && <nav id="openinfra-compact-navigation" className="openinfra-compact-navigation" aria-label={i18n.t('navigation')}>
        <div className="openinfra-compact-navigation-header"><strong>{i18n.t('navigation')}</strong><button type="button" className="openinfra-navigation-close" aria-label={i18n.t('closeNavigation')} onClick={() => closeResponsiveNavigation({ restoreFocus: true })}>×</button></div>
        <div className="openinfra-compact-navigation-body"><div className="openinfra-sidebar-heading">{i18n.t('control')}</div><NavigationTree modules={filteredModules} activeNavigationModuleId={activeNavigationModuleId} selectedOperationId={selected.id} opened={opened} openedContexts={openedContexts} chooseOperation={chooseOperation} toggleAccordion={toggleAccordion} toggleSidebarContext={toggleSidebarContext} surface="compact" /><div className="openinfra-sidebar-heading">{i18n.t('runtimeStatus')}</div>{runtimeStatus}</div>
      </nav>}
    </header>
    {(mobileSidebarOpen || megaMenuModuleId) && <button type="button" className="openinfra-navigation-backdrop" aria-label={i18n.t('closeNavigation')} onClick={() => closeResponsiveNavigation({ restoreFocus: true })} />}
    <div className="container-fluid">
      <div className="row">
        <nav id="openinfra-sidebar" className="col-xl-2 openinfra-sidebar" aria-label={i18n.t('navigation')}>
          <div className="openinfra-sidebar-heading">{i18n.t('control')}</div>
          <NavigationTree modules={filteredModules} activeNavigationModuleId={activeNavigationModuleId} selectedOperationId={selected.id} opened={opened} openedContexts={openedContexts} chooseOperation={chooseOperation} toggleAccordion={toggleAccordion} toggleSidebarContext={toggleSidebarContext} />
          <div className="openinfra-sidebar-heading">{i18n.t('runtimeStatus')}</div>
          {runtimeStatus}
        </nav>
        <main id="openinfra-main-content" ref={mainContentRef} tabIndex={-1} className="col-xl-10 ms-sm-auto openinfra-main">
          <div className="pb-2 mb-3 openinfra-titlebar"><h1 className="h2">{pageTitle}</h1><p className="text-muted mb-0">{pageSubtitle}</p></div>
          {submissionCompleted && activeModuleId !== 'overview' && <div className="alert alert-success" role="status">{i18n.t('success')}</div>}
          {activeModuleId === 'overview' && <div className="row g-3 mb-4 openinfra-dashboard-metrics" aria-label={i18n.t('componentStatistics')}><Metric title={i18n.t('version')} value={displayedVersion} /><Metric title="API" value={config.apiBaseUrl || '/api'} /><Metric title={i18n.t('trust')} value={config.webBackendTrust || 'server-side'} /><Metric title={i18n.t('forms')} value={protectedForms} /><Metric title={i18n.t('modules')} value={`${operationsCount} ${i18n.t('operations')}`} /></div>}
          {activeModuleId === 'overview' ? <OverviewStats i18n={i18n} modules={businessModules} fieldsCount={businessFieldsCount} /> : <section className="card openinfra-operation-card" aria-labelledby="openinfra-operation-title"><div className="card-body"><h2 id="openinfra-operation-title" className="h4">{selected.label}</h2><OperationForm i18n={i18n} language={language} selected={selected} tenant={tenant} setTenant={setTenant} execute={execute} /><GraphResultPanel i18n={i18n} operation={selected} result={result} /></div></section>}
        </main>
      </div>
    </div>
  </div>;
}

function GraphResultPanel({ i18n, operation, result }) {
  const serialized = result === null ? i18n.t('pendingResult') : (typeof result === 'string' ? result : JSON.stringify(result, null, 2));
  if (!operation.id.startsWith('graph-') || result === null || typeof result === 'string' || result.error) {
    return <pre className="openinfra-result mt-3" role="status" aria-live="polite" aria-atomic="true" aria-label={i18n.t('operationResult')}>{serialized}</pre>;
  }
  if (operation.id === 'graph-export') {
    return <><div className="alert alert-success openinfra-download-result mt-3" role="status"><strong>{i18n.t('downloadReady')}</strong><br />{result.filename} · {result.size_bytes || 0} octets</div><RawGraphResult i18n={i18n} value={serialized} /></>;
  }
  return <div className="mt-3">{operation.id === 'graph-spof' ? <SpofRanking i18n={i18n} result={result} /> : <DependencyGraphVisualization i18n={i18n} result={result} />}<RawGraphResult i18n={i18n} value={serialized} /></div>;
}

function RawGraphResult({ i18n, value }) {
  return <details className="openinfra-raw-result"><summary>{i18n.t('rawResult')}</summary><pre className="openinfra-result" role="status" aria-live="polite" aria-atomic="true" aria-label={i18n.t('operationResult')}>{value}</pre></details>;
}

function DependencyGraphVisualization({ i18n, result }) {
  const nodes = Array.isArray(result.nodes) ? result.nodes.slice(0, 80) : [];
  const keys = new Set(nodes.map((node) => String(node.key || '')));
  const edges = (Array.isArray(result.edges) ? result.edges : []).filter((edge) => keys.has(String(edge.source_key || '')) && keys.has(String(edge.target_key || ''))).slice(0, 160);
  if (nodes.length === 0) return <p className="text-muted">{i18n.t('noGraphData')}</p>;
  const layers = new Map();
  for (const node of nodes) {
    const depth = Number.isFinite(Number(node.depth)) ? Number(node.depth) : 0;
    if (!layers.has(depth)) layers.set(depth, []);
    layers.get(depth).push(node);
  }
  const depths = [...layers.keys()].sort((left, right) => left - right);
  const layerGap = Math.max(145, Math.floor(720 / Math.max(depths.length, 1)));
  const positions = new Map();
  depths.forEach((depth, layerIndex) => {
    const layer = layers.get(depth).sort((left, right) => String(left.key).localeCompare(String(right.key)));
    layer.forEach((node, rowIndex) => positions.set(String(node.key), { x: 70 + layerIndex * layerGap, y: 46 + rowIndex * 76 }));
  });
  const maxLayer = Math.max(...[...layers.values()].map((layer) => layer.length), 1);
  const width = Math.max(720, 120 + (depths.length - 1) * layerGap);
  const height = Math.max(280, maxLayer * 76 + 56);
  const omitted = (Array.isArray(result.nodes) ? result.nodes.length : 0) - nodes.length;
  // A scrollable graph region must be keyboard-focusable; a text-equivalent list follows it.
  // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex
  return <section className="openinfra-graph-visualization" aria-labelledby="openinfra-react-graph-title"><h3 id="openinfra-react-graph-title" className="h6">{i18n.t('graphVisualization')}</h3><p className="small text-muted">{i18n.t('graphVisualizationDescription')}</p><div className="openinfra-graph-canvas" role="region" aria-label={i18n.t('graphVisualization')} tabIndex={0}><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${nodes.length} nodes, ${edges.length} relationships`}><defs><marker id="openinfra-react-graph-arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" /></marker></defs><g className="openinfra-graph-edges">{edges.map((edge) => { const source = positions.get(String(edge.source_key)); const target = positions.get(String(edge.target_key)); return source && target ? <line key={edge.id || `${edge.source_key}-${edge.target_key}`} x1={source.x} y1={source.y} x2={target.x} y2={target.y} markerEnd="url(#openinfra-react-graph-arrow)"><title>{`${edge.relation_type || 'relation'}: ${edge.source_key} → ${edge.target_key}`}</title></line> : null; })}</g><g className="openinfra-graph-nodes" role="list">{nodes.map((node) => { const position = positions.get(String(node.key)); const label = String(node.display_name || node.key || ''); const shortLabel = label.length > 16 ? `${label.slice(0, 15)}…` : label; const isRoot = String(node.key) === String(result.root_key || result.source_key || ''); return <g key={node.key} className={`openinfra-graph-node${isRoot ? ' is-root' : ''}`} transform={`translate(${position.x},${position.y})`} role="listitem" aria-label={`${label}, ${node.resource_type || node.kind || 'object'}, depth ${node.depth ?? 0}`}><circle r="24" /><text textAnchor="middle" y="4">{shortLabel}</text><title>{`${label} (${node.key})`}</title></g>; })}</g></svg></div><ul className="visually-hidden" aria-label={i18n.t('graphVisualization')}>{nodes.map((node) => <li key={`accessible-${node.key}`}>{`${node.display_name || node.key}, ${node.resource_type || node.kind || 'object'}, depth ${node.depth ?? 0}`}</li>)}</ul>{omitted > 0 ? <p className="small text-muted">{i18n.t('graphNodesOmitted', { count: omitted })}</p> : null}</section>;
}

function SpofRanking({ i18n, result }) {
  const items = Array.isArray(result.items) ? result.items : [];
  return <section className="openinfra-spof-ranking" aria-labelledby="openinfra-react-spof-title"><div className="d-flex flex-wrap justify-content-between gap-2"><h3 id="openinfra-react-spof-title" className="h6">{i18n.t('spofRanking')}</h3><span className={`badge ${result.complete === false ? 'text-bg-warning' : 'text-bg-success'}`}>{i18n.t(result.complete === false ? 'boundedAnalysis' : 'completeAnalysis')}</span></div><p className="small text-muted">{`${result.spof_count || 0} SPOF · ${result.node_count || 0} nodes · ${result.edge_count || 0} relationships`}</p><div className="table-responsive"><table className="table table-sm align-middle"><caption className="visually-hidden">{i18n.t('spofRanking')}</caption><thead><tr><th scope="col">#</th><th scope="col">{i18n.t('candidate')}</th><th scope="col">{i18n.t('affectedNodes')}</th><th scope="col">{i18n.t('directAffected')}</th><th scope="col">{i18n.t('impactRatio')}</th><th scope="col">{i18n.t('affectedSample')}</th></tr></thead><tbody>{items.length === 0 ? <tr><td colSpan="6">{i18n.t('noSpofDetected')}</td></tr> : items.map((item) => { const node = item.node || {}; const ratio = Math.max(0, Math.min(1, Number(item.affected_ratio || 0))); return <tr key={node.key || item.rank}><td>{item.rank}</td><th scope="row">{node.display_name || node.key}<small>{node.key}</small></th><td>{item.affected_count}</td><td>{item.direct_affected_count}</td><td><span className="openinfra-spof-ratio" aria-label={`${Math.round(ratio * 100)} %`}><span style={{ width: `${Math.round(ratio * 100)}%` }} /></span>{Math.round(ratio * 100)} %</td><td>{Array.isArray(item.affected_sample) && item.affected_sample.length > 0 ? item.affected_sample.join(', ') : '—'}</td></tr>; })}</tbody></table></div></section>;
}

function GlobalSearchResults({ i18n, query, groups, backend, loading, error, onSelect, onBackendSelect }) {
  if (loading) {
    return <div className="openinfra-global-search-empty">{i18n.t('loadingSearch', { query: query.trim() })}</div>;
  }
  if (backend && backend.query === query.trim()) {
    const resultGroups = (backend.groups || []).filter((group) => group.status === 'ok' && Array.isArray(group.items) && group.items.length > 0);
    const skipped = (backend.groups || []).filter((group) => group.status === 'skipped');
    if (resultGroups.length > 0) {
      return <>{resultGroups.map((group) => <section className="openinfra-global-search-group" role="group" aria-label={`${i18n.t('globalSearchResults')} ${group.label || group.component}`} key={group.component}><div className="openinfra-global-search-group-title"><span>{group.label || group.component}</span><span>{i18n.count(group.total, 'result', 'results')}</span></div>{group.items.map((item) => <button type="button" className="openinfra-global-search-item" role="option" aria-selected="false" key={`${group.component}-${item.kind}-${item.label}`} onClick={() => onBackendSelect(item)}><span>{item.label}</span><small>{item.kind} · {item.description}</small></button>)}{group.total > group.items.length && <div className="openinfra-global-search-more">{i18n.t(group.total - group.items.length === 1 ? 'additionalResults' : 'additionalResultsPlural', { count: group.total - group.items.length })}</div>}</section>)}{skipped.length > 0 && <div className="openinfra-global-search-empty">{i18n.t('skippedComponents', { components: skipped.map((group) => group.label || group.component).join(', ') })}</div>}</>;
    }
  }
  if (error) {
    return <><div className="openinfra-global-search-empty">{i18n.t('backendSearchUnavailable')}</div><OperationSearchResults i18n={i18n} query={query} groups={groups} onSelect={onSelect} /></>;
  }
  return <OperationSearchResults i18n={i18n} query={query} groups={groups} onSelect={onSelect} />;
}

function OperationSearchResults({ i18n, query, groups, onSelect }) {
  if (groups.length === 0) {
    return <div className="openinfra-global-search-empty">{i18n.t('noGlobalResult', { query: query.trim() })}</div>;
  }
  return groups.map(({ module, operations, total }) => <section className="openinfra-global-search-group" role="group" aria-label={`${i18n.t('globalSearchResults')} ${module.shortLabel || module.label}`} key={module.id}><div className="openinfra-global-search-group-title"><span>{module.shortLabel || module.label}</span><span>{i18n.count(total, 'result', 'results')}</span></div>{operations.map((operation) => <button type="button" className="openinfra-global-search-item" role="option" aria-selected="false" key={operation.id} onClick={() => onSelect(module, operation)}><span>{operation.label}</span><small>{operation.method} {operation.path}</small></button>)}{total > operations.length && <div className="openinfra-global-search-more">{i18n.t(total - operations.length === 1 ? 'additionalResults' : 'additionalResultsPlural', { count: total - operations.length })}</div>}</section>);
}

function OverviewStats({ i18n, modules, fieldsCount }) {
  const operations = modules.reduce((total, module) => total + module.operations.length, 0);
  return <section className="openinfra-overview" aria-label={i18n.t('componentStatistics')}><div className="card openinfra-overview-summary mb-4"><div className="card-body"><div className="d-flex flex-wrap justify-content-between align-items-start gap-3"><div><h2 className="h4 mb-1">{i18n.t('overviewTitle')}</h2><p className="text-muted mb-0">{i18n.t('overviewDescription')}</p></div><div><span className="badge text-bg-primary">{modules.length} {i18n.t('components')}</span><span className="badge text-bg-secondary ms-2">{operations} {i18n.t('operations')}</span></div></div><div className="row g-3 mt-3"><Metric title={i18n.t('fields')} value={String(fieldsCount)} /><Metric title={i18n.t('navigationMode')} value={i18n.t('accordions')} /><Metric title={i18n.t('browserSecrets')} value={i18n.t('noneExposed')} /><Metric title={i18n.t('uiParity')} value="CLI/API" /></div></div></div><div className="row g-3">{modules.map((module) => <ComponentStatsCard i18n={i18n} key={module.id} module={module} />)}</div></section>;
}

function ComponentStatsCard({ i18n, module }) {
  const stats = moduleStatistics(module);
  const style = { '--oi-read-end': `${stats.readPercent}%`, '--oi-write-end': `${stats.readPercent + stats.writePercent}%` };
  return <article className="col-md-6 col-xxl-4"><div className="card h-100 openinfra-component-card"><div className="card-body"><div className="d-flex justify-content-between align-items-start gap-3"><div><h3 className="h5 mb-1">{module.shortLabel || module.label}</h3><p className="text-muted small mb-0">{i18n.t('operationsExposed', { count: module.operations.length })}</p></div><Icon name={module.icon} className="openinfra-component-icon" /></div><div className="openinfra-component-visual mt-3"><div className="openinfra-pie-chart" role="img" aria-label={i18n.t('distributionChart', { module: module.label, reads: stats.readOperations, mutations: stats.writeOperations })} style={style}><span>{stats.operations}</span></div><div className="openinfra-pie-legend small"><span><i className="openinfra-legend-read" />{stats.readOperations} {i18n.t('reads').toLowerCase()}</span><span><i className="openinfra-legend-write" />{stats.writeOperations} {i18n.t('mutations').toLowerCase()}</span></div></div><div className="row g-2 mt-3 openinfra-component-metrics"><div className="col-6"><strong>{stats.operations}</strong><span>{i18n.t('operations')}</span></div><div className="col-6"><strong>{stats.fields}</strong><span>{i18n.t('fields')}</span></div><div className="col-6"><strong>{stats.readOperations}</strong><span>{i18n.t('reads')}</span></div><div className="col-6"><strong>{stats.writeOperations}</strong><span>{i18n.t('mutations')}</span></div></div></div></div></article>;
}

function Metric({ title, value }) {
  return <article className="col-md-6 col-xl-3"><div className="card h-100 openinfra-metric"><div className="card-body"><h2 className="h6 text-muted">{title}</h2><p className="openinfra-metric-value mb-0">{value}</p></div></div></article>;
}

createRoot(document.getElementById('openinfra-root')).render(<Dashboard />);
