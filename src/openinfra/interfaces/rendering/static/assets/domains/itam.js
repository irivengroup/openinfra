const moduleDefinition = {
  "id": "itam",
  "label": "IT Asset Management",
  "shortLabel": "ITAM",
  "icon": "asset",
  "description": "Inventaire financier et opérationnel des actifs, garanties constructeur, supports tiers et couverture renouvellement.",
  "operations": [
    {
      "id": "itam-organizations",
      "label": "Lister les organisations",
      "method": "GET",
      "path": "/v1/itam/organizations",
      "query": [
        {
          "name": "include_retired",
          "label": "Inclure retirées",
          "type": "boolean"
        }
      ]
    },
    {
      "id": "itam-organization",
      "label": "Voir une organisation",
      "method": "GET",
      "path": "/v1/itam/organization",
      "query": [
        {
          "name": "organization_id",
          "label": "Organisation",
          "type": "organization-select",
          "required": true
        }
      ]
    },
    {
      "id": "itam-organization-create",
      "label": "Créer une organisation",
      "method": "POST",
      "path": "/v1/itam/organization/create",
      "body": [
        {
          "name": "organization_id",
          "label": "Code organisation",
          "required": true,
          "placeholder": "orange"
        },
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "legal_name",
          "label": "Raison sociale",
          "required": true,
          "placeholder": "Orange SA"
        },
        {
          "name": "display_name",
          "label": "Nom d’usage",
          "placeholder": "Orange"
        },
        {
          "name": "registration_number",
          "label": "N° immatriculation",
          "required": true,
          "placeholder": "RCS Paris ..."
        },
        {
          "name": "tax_identifier",
          "label": "Identifiant fiscal / TVA",
          "required": true,
          "placeholder": "FR..."
        },
        {
          "name": "country_code",
          "label": "Pays",
          "type": "country-select",
          "required": true
        },
        {
          "name": "city",
          "label": "Ville",
          "required": true,
          "placeholder": "Paris"
        },
        {
          "name": "postal_code",
          "label": "Code postal",
          "required": true,
          "placeholder": "92130"
        },
        {
          "name": "address",
          "label": "Adresse siège",
          "required": true,
          "placeholder": "111 Quai du Président Roosevelt"
        },
        {
          "name": "contact_email",
          "label": "Email",
          "required": true,
          "placeholder": "contact@orange.com"
        },
        {
          "name": "phone",
          "label": "Téléphone",
          "required": true,
          "placeholder": "+33123456789"
        },
        {
          "name": "support_contact",
          "label": "Contact support",
          "required": true,
          "placeholder": "support@orange.com"
        },
        {
          "name": "status",
          "label": "Statut",
          "type": "select",
          "options": [
            "active",
            "suspended",
            "retired"
          ],
          "defaultValue": "active"
        },
        {
          "name": "description",
          "label": "Description",
          "placeholder": "Carte d’identité entreprise"
        }
      ]
    },
    {
      "id": "itam-organization-update",
      "label": "Modifier une organisation",
      "method": "POST",
      "path": "/v1/itam/organization/update",
      "body": [
        {
          "name": "organization_id",
          "label": "Organisation",
          "type": "organization-select",
          "required": true
        },
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "legal_name",
          "label": "Raison sociale"
        },
        {
          "name": "display_name",
          "label": "Nom d’usage"
        },
        {
          "name": "registration_number",
          "label": "N° immatriculation"
        },
        {
          "name": "tax_identifier",
          "label": "Identifiant fiscal / TVA"
        },
        {
          "name": "country_code",
          "label": "Pays",
          "type": "country-select"
        },
        {
          "name": "city",
          "label": "Ville"
        },
        {
          "name": "postal_code",
          "label": "Code postal"
        },
        {
          "name": "address",
          "label": "Adresse siège"
        },
        {
          "name": "contact_email",
          "label": "Email"
        },
        {
          "name": "phone",
          "label": "Téléphone"
        },
        {
          "name": "support_contact",
          "label": "Contact support"
        },
        {
          "name": "status",
          "label": "Statut",
          "type": "select",
          "options": [
            "",
            "active",
            "suspended",
            "retired"
          ]
        },
        {
          "name": "description",
          "label": "Description"
        }
      ]
    },
    {
      "id": "itam-organization-delete",
      "label": "Retirer une organisation",
      "method": "POST",
      "path": "/v1/itam/organization/delete",
      "body": [
        {
          "name": "organization_id",
          "label": "Organisation",
          "type": "organization-select",
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
      "id": "itam-partners",
      "label": "Lister les partenaires",
      "method": "GET",
      "path": "/v1/itam/partners",
      "query": [
        {
          "name": "organization_id",
          "label": "Organisation",
          "type": "organization-select"
        },
        {
          "name": "kind",
          "label": "Type partenaire",
          "type": "select",
          "options": [
            "",
            "manufacturer",
            "software_publisher",
            "third_party_support"
          ]
        },
        {
          "name": "include_retired",
          "label": "Inclure retirés",
          "type": "boolean"
        }
      ]
    },
    {
      "id": "itam-partner",
      "label": "Voir un partenaire",
      "method": "GET",
      "path": "/v1/itam/partner",
      "query": [
        {
          "name": "organization_id",
          "label": "Organisation",
          "type": "organization-select",
          "required": true
        },
        {
          "name": "partner_id",
          "label": "Partenaire",
          "type": "partner-select",
          "required": true
        }
      ]
    },
    {
      "id": "itam-partner-create",
      "label": "Créer un partenaire",
      "method": "POST",
      "path": "/v1/itam/partner/create",
      "body": [
        {
          "name": "organization_id",
          "label": "Organisation",
          "type": "organization-select",
          "required": true
        },
        {
          "name": "partner_id",
          "label": "Code partenaire",
          "required": true,
          "placeholder": "dell"
        },
        {
          "name": "kind",
          "label": "Type partenaire",
          "type": "select",
          "required": true,
          "options": [
            "manufacturer",
            "software_publisher",
            "third_party_support"
          ],
          "defaultValue": "manufacturer"
        },
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "legal_name",
          "label": "Raison sociale",
          "required": true,
          "placeholder": "Dell SAS"
        },
        {
          "name": "display_name",
          "label": "Nom d’usage",
          "placeholder": "Dell"
        },
        {
          "name": "registration_number",
          "label": "N° immatriculation",
          "required": true
        },
        {
          "name": "tax_identifier",
          "label": "Identifiant fiscal / TVA",
          "required": true
        },
        {
          "name": "country_code",
          "label": "Pays",
          "type": "country-select",
          "required": true
        },
        {
          "name": "city",
          "label": "Ville",
          "required": true
        },
        {
          "name": "postal_code",
          "label": "Code postal",
          "required": true
        },
        {
          "name": "address",
          "label": "Adresse siège",
          "required": true
        },
        {
          "name": "contact_email",
          "label": "Email contact",
          "required": true
        },
        {
          "name": "phone",
          "label": "Téléphone",
          "required": true,
          "placeholder": "+33123456789"
        },
        {
          "name": "support_contact",
          "label": "Contact support",
          "required": true
        },
        {
          "name": "website",
          "label": "Site web",
          "placeholder": "https://example.com"
        },
        {
          "name": "status",
          "label": "Statut",
          "type": "select",
          "options": [
            "active",
            "suspended",
            "retired"
          ],
          "defaultValue": "active"
        },
        {
          "name": "description",
          "label": "Description"
        }
      ]
    },
    {
      "id": "itam-partner-update",
      "label": "Modifier un partenaire",
      "method": "POST",
      "path": "/v1/itam/partner/update",
      "body": [
        {
          "name": "organization_id",
          "label": "Organisation",
          "type": "organization-select",
          "required": true
        },
        {
          "name": "partner_id",
          "label": "Partenaire",
          "type": "partner-select",
          "required": true
        },
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "kind",
          "label": "Type partenaire",
          "type": "select",
          "options": [
            "",
            "manufacturer",
            "software_publisher",
            "third_party_support"
          ]
        },
        {
          "name": "legal_name",
          "label": "Raison sociale"
        },
        {
          "name": "display_name",
          "label": "Nom d’usage"
        },
        {
          "name": "registration_number",
          "label": "N° immatriculation"
        },
        {
          "name": "tax_identifier",
          "label": "Identifiant fiscal / TVA"
        },
        {
          "name": "country_code",
          "label": "Pays",
          "type": "country-select"
        },
        {
          "name": "city",
          "label": "Ville"
        },
        {
          "name": "postal_code",
          "label": "Code postal"
        },
        {
          "name": "address",
          "label": "Adresse siège"
        },
        {
          "name": "contact_email",
          "label": "Email contact"
        },
        {
          "name": "phone",
          "label": "Téléphone"
        },
        {
          "name": "support_contact",
          "label": "Contact support"
        },
        {
          "name": "website",
          "label": "Site web"
        },
        {
          "name": "status",
          "label": "Statut",
          "type": "select",
          "options": [
            "",
            "active",
            "suspended",
            "retired"
          ]
        },
        {
          "name": "description",
          "label": "Description"
        }
      ]
    },
    {
      "id": "itam-partner-delete",
      "label": "Retirer un partenaire",
      "method": "POST",
      "path": "/v1/itam/partner/delete",
      "body": [
        {
          "name": "organization_id",
          "label": "Organisation",
          "type": "organization-select",
          "required": true
        },
        {
          "name": "partner_id",
          "label": "Partenaire",
          "type": "partner-select",
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
      "id": "itam-tenants",
      "label": "Lister les filiales/subdivisions",
      "method": "GET",
      "path": "/v1/itam/tenants",
      "query": [
        {
          "name": "include_retired",
          "label": "Inclure retirés",
          "type": "boolean"
        }
      ]
    },
    {
      "id": "itam-tenant",
      "label": "Voir une filiale/subdivision",
      "method": "GET",
      "path": "/v1/itam/tenant",
      "query": [
        {
          "name": "organization_id",
          "label": "Organisation",
          "type": "organization-select",
          "required": true
        },
        {
          "name": "tenant_id",
          "label": "Filiale/Subdivision",
          "type": "tenant-select",
          "required": true
        }
      ]
    },
    {
      "id": "itam-tenant-create",
      "label": "Créer une filiale/subdivision",
      "method": "POST",
      "path": "/v1/itam/tenant/create",
      "body": [
        {
          "name": "organization_id",
          "label": "Organisation",
          "type": "organization-select",
          "required": true
        },
        {
          "name": "tenant_id",
          "label": "Filiale/Subdivision",
          "required": true,
          "placeholder": "dsi"
        },
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "name",
          "label": "Nom filiale/subdivision",
          "required": true,
          "placeholder": "DSI"
        },
        {
          "name": "status",
          "label": "Statut",
          "type": "select",
          "options": [
            "active",
            "suspended",
            "retired"
          ],
          "defaultValue": "active"
        },
        {
          "name": "is_default",
          "label": "Filiale/Subdivision par défaut",
          "type": "boolean"
        },
        {
          "name": "description",
          "label": "Description",
          "placeholder": "Périmètre interne de la filiale/subdivision"
        }
      ]
    },
    {
      "id": "itam-tenant-update",
      "label": "Modifier une filiale/subdivision",
      "method": "POST",
      "path": "/v1/itam/tenant/update",
      "body": [
        {
          "name": "organization_id",
          "label": "Organisation",
          "type": "organization-select",
          "required": true
        },
        {
          "name": "tenant_id",
          "label": "Filiale/Subdivision à modifier",
          "type": "tenant-select",
          "required": true
        },
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "name",
          "label": "Nom filiale/subdivision",
          "placeholder": "DSI"
        },
        {
          "name": "status",
          "label": "Statut",
          "type": "select",
          "options": [
            "",
            "active",
            "suspended",
            "retired"
          ]
        },
        {
          "name": "is_default",
          "label": "Filiale/Subdivision par défaut",
          "type": "boolean"
        },
        {
          "name": "description",
          "label": "Description",
          "placeholder": "Périmètre interne de la filiale/subdivision"
        }
      ]
    },
    {
      "id": "itam-tenant-delete",
      "label": "Retirer une filiale/subdivision",
      "method": "POST",
      "path": "/v1/itam/tenant/delete",
      "body": [
        {
          "name": "organization_id",
          "label": "Organisation",
          "type": "organization-select",
          "required": true
        },
        {
          "name": "tenant_id",
          "label": "Filiale/Subdivision à retirer",
          "type": "tenant-select",
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
      "id": "itam-support-profile",
      "label": "Profil support actif",
      "method": "GET",
      "path": "/v1/itam/support-profile",
      "query": [
        {
          "name": "asset_tag",
          "label": "Numéro d’actif",
          "required": true,
          "placeholder": "PAR-SRV-001"
        }
      ]
    },
    {
      "id": "itam-support-coverage",
      "label": "Couverture support actif",
      "method": "GET",
      "path": "/v1/itam/support-coverage",
      "query": [
        {
          "name": "asset_tag",
          "label": "Numéro d’actif",
          "required": true,
          "placeholder": "PAR-SRV-001"
        },
        {
          "name": "as_of",
          "label": "Date de référence",
          "placeholder": "2026-07-07"
        }
      ]
    },
    {
      "id": "itam-register-manufacturer",
      "label": "Déclarer garantie constructeur",
      "method": "POST",
      "path": "/v1/itam/support-profile/manufacturer",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "asset_tag",
          "label": "Numéro d’actif",
          "required": true,
          "placeholder": "PAR-SRV-001"
        },
        {
          "name": "manufacturer_partner_id",
          "label": "Constructeur accrédité",
          "type": "partner-select",
          "partnerKind": "manufacturer",
          "required": true
        },
        {
          "name": "manufacturer",
          "label": "Constructeur",
          "type": "hidden",
          "defaultValue": "accredited"
        },
        {
          "name": "warranty_reference",
          "label": "Référence garantie",
          "required": true,
          "placeholder": "WR-123"
        },
        {
          "name": "warranty_level",
          "label": "Niveau garantie",
          "required": true,
          "placeholder": "ProSupport"
        },
        {
          "name": "warranty_start",
          "label": "Début garantie",
          "required": true,
          "placeholder": "2026-01-01"
        },
        {
          "name": "warranty_end",
          "label": "Fin garantie",
          "required": true,
          "placeholder": "2029-01-01"
        },
        {
          "name": "support_reference",
          "label": "Référence support",
          "required": true,
          "placeholder": "SUP-123"
        },
        {
          "name": "support_level",
          "label": "Niveau support",
          "required": true,
          "placeholder": "24x7"
        },
        {
          "name": "support_contact",
          "label": "Contact support",
          "required": true,
          "placeholder": "support@example.com"
        }
      ]
    },
    {
      "id": "itam-add-third-party",
      "label": "Ajouter support tiers",
      "method": "POST",
      "path": "/v1/itam/support-profile/third-party",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "asset_tag",
          "label": "Numéro d’actif",
          "required": true,
          "placeholder": "PAR-SRV-001"
        },
        {
          "name": "provider_partner_id",
          "label": "Support tiers accrédité",
          "type": "partner-select",
          "partnerKind": "third_party_support",
          "required": true
        },
        {
          "name": "provider",
          "label": "Prestataire",
          "type": "hidden",
          "defaultValue": "accredited"
        },
        {
          "name": "contract_reference",
          "label": "Référence contrat",
          "required": true,
          "placeholder": "TP-123"
        },
        {
          "name": "support_level",
          "label": "Niveau support",
          "required": true,
          "placeholder": "8x5"
        },
        {
          "name": "support_start",
          "label": "Début support",
          "required": true,
          "placeholder": "2029-01-02"
        },
        {
          "name": "support_end",
          "label": "Fin support",
          "required": true,
          "placeholder": "2030-01-01"
        },
        {
          "name": "support_contact",
          "label": "Contact support",
          "required": true,
          "placeholder": "n2@example.com"
        },
        {
          "name": "status",
          "label": "Statut",
          "type": "select",
          "options": [
            "planned",
            "active",
            "expired",
            "terminated"
          ],
          "defaultValue": "active"
        },
        {
          "name": "notes",
          "label": "Notes",
          "placeholder": "Périmètre support"
        }
      ]
    },
    {
      "id": "itam-software-license",
      "label": "Licence logicielle",
      "method": "GET",
      "path": "/v1/itam/software-license",
      "query": [
        {
          "name": "license_reference",
          "label": "Référence licence",
          "required": true,
          "placeholder": "LIC-OPENINFRA-001"
        }
      ]
    },
    {
      "id": "itam-software-compliance",
      "label": "Conformité licence",
      "method": "GET",
      "path": "/v1/itam/software-license/compliance",
      "query": [
        {
          "name": "license_reference",
          "label": "Référence licence",
          "required": true,
          "placeholder": "LIC-OPENINFRA-001"
        },
        {
          "name": "as_of",
          "label": "Date de référence",
          "placeholder": "2026-07-08"
        }
      ]
    },
    {
      "id": "itam-register-software",
      "label": "Déclarer licence logicielle",
      "method": "POST",
      "path": "/v1/itam/software-license",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "product_name",
          "label": "Produit",
          "required": true,
          "placeholder": "PostgreSQL Enterprise Support"
        },
        {
          "name": "vendor_partner_id",
          "label": "Éditeur accrédité",
          "type": "partner-select",
          "partnerKind": "software_publisher",
          "required": true
        },
        {
          "name": "vendor",
          "label": "Éditeur",
          "type": "hidden",
          "defaultValue": "accredited"
        },
        {
          "name": "license_reference",
          "label": "Référence licence",
          "required": true,
          "placeholder": "LIC-OPENINFRA-001"
        },
        {
          "name": "contract_reference",
          "label": "Référence contrat",
          "placeholder": "CTR-SW-001"
        },
        {
          "name": "metric",
          "label": "Métrique",
          "type": "select",
          "required": true,
          "options": [
            "device",
            "user",
            "core",
            "socket",
            "instance",
            "subscription"
          ],
          "defaultValue": "device"
        },
        {
          "name": "purchased_quantity",
          "label": "Quantité achetée",
          "required": true,
          "placeholder": "100"
        },
        {
          "name": "assigned_quantity",
          "label": "Quantité assignée",
          "placeholder": "0"
        },
        {
          "name": "entitlement_start",
          "label": "Début droit",
          "required": true,
          "placeholder": "2026-01-01"
        },
        {
          "name": "entitlement_end",
          "label": "Fin droit",
          "required": true,
          "placeholder": "2027-01-01"
        },
        {
          "name": "version",
          "label": "Version",
          "placeholder": "2026"
        },
        {
          "name": "status",
          "label": "Statut",
          "type": "select",
          "options": [
            "planned",
            "active",
            "expired",
            "terminated"
          ],
          "defaultValue": "active"
        },
        {
          "name": "owner",
          "label": "Propriétaire",
          "placeholder": "DSI"
        },
        {
          "name": "notes",
          "label": "Notes",
          "placeholder": "Périmètre licence"
        }
      ]
    },
    {
      "id": "itam-update-license-assignment",
      "label": "Mettre à jour affectation licence",
      "method": "POST",
      "path": "/v1/itam/software-license/assignment",
      "body": [
        {
          "name": "actor",
          "label": "Opérateur",
          "required": true,
          "placeholder": "admin@openinfra"
        },
        {
          "name": "license_reference",
          "label": "Référence licence",
          "required": true,
          "placeholder": "LIC-OPENINFRA-001"
        },
        {
          "name": "assigned_quantity",
          "label": "Quantité assignée",
          "required": true,
          "placeholder": "75"
        },
        {
          "name": "notes",
          "label": "Notes",
          "placeholder": "Ajustement inventaire"
        }
      ]
    },
    {
      "id": "finops-rule-create",
      "label": "Créer une règle d’allocation",
      "path": "/v1/finops/allocation-rules/create",
      "method": "POST",
      "body": [
        "Opérateur",
        {
          "name": "name",
          "label": "Nom de la règle",
          "required": true
        },
        {
          "name": "priority",
          "label": "Priorité",
          "type": "number",
          "defaultValue": "100"
        },
        {
          "name": "dimension",
          "label": "Dimension",
          "type": "select",
          "options": [
            "asset",
            "application",
            "business-service",
            "tenant",
            "owner",
            "tag",
            "cost-center",
            "environment",
            "dependency"
          ],
          "required": true
        },
        {
          "name": "selector_key",
          "label": "Clé de sélection",
          "required": true
        },
        {
          "name": "fixed_target",
          "label": "Cible fixe"
        },
        {
          "name": "percentage",
          "label": "Pourcentage",
          "type": "number",
          "required": true
        },
        {
          "name": "category",
          "label": "Catégorie de coût"
        },
        {
          "name": "source",
          "label": "Source de coût"
        },
        {
          "name": "active",
          "label": "Règle active",
          "type": "boolean",
          "defaultValue": "true"
        }
      ]
    },
    {
      "id": "finops-rules",
      "label": "Lister les règles d’allocation",
      "path": "/v1/finops/allocation-rules",
      "method": "GET",
      "query": [
        {
          "name": "active_only",
          "label": "Uniquement actives",
          "type": "boolean"
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
      "id": "finops-import-submit",
      "label": "Importer des coûts",
      "path": "/v1/finops/import-jobs/submit",
      "method": "POST",
      "body": [
        "Opérateur",
        {
          "name": "idempotency_key",
          "label": "Clé d’idempotence",
          "required": true
        },
        {
          "name": "source",
          "label": "Source",
          "required": true
        },
        {
          "name": "records",
          "label": "Enregistrements de coûts JSON",
          "type": "json",
          "required": true,
          "defaultValue": "[]"
        }
      ]
    },
    {
      "id": "finops-import-get",
      "label": "Consulter un import de coûts",
      "path": "/v1/finops/import-jobs/get",
      "method": "GET",
      "query": [
        {
          "name": "job_id",
          "label": "ID import",
          "required": true
        },
        {
          "name": "include_records",
          "label": "Inclure les enregistrements",
          "type": "boolean"
        }
      ]
    },
    {
      "id": "finops-imports",
      "label": "Lister les imports de coûts",
      "path": "/v1/finops/import-jobs",
      "method": "GET",
      "query": [
        {
          "name": "status",
          "label": "Statut"
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
      "id": "finops-import-run",
      "label": "Exécuter un import de coûts",
      "path": "/v1/finops/import-jobs/run",
      "method": "POST",
      "body": [
        "Opérateur",
        {
          "name": "job_id",
          "label": "ID import",
          "required": true
        }
      ]
    },
    {
      "id": "finops-import-cancel",
      "label": "Annuler un import de coûts",
      "path": "/v1/finops/import-jobs/cancel",
      "method": "POST",
      "body": [
        "Opérateur",
        {
          "name": "job_id",
          "label": "ID import",
          "required": true
        }
      ]
    },
    {
      "id": "finops-costs",
      "label": "Lister les coûts normalisés",
      "path": "/v1/finops/cost-records",
      "method": "GET",
      "query": [
        {
          "name": "period_start",
          "label": "Début de période",
          "type": "date"
        },
        {
          "name": "period_end",
          "label": "Fin de période",
          "type": "date"
        },
        {
          "name": "currency",
          "label": "Devise ISO-4217"
        },
        {
          "name": "category",
          "label": "Catégorie"
        },
        {
          "name": "source",
          "label": "Source"
        },
        {
          "name": "quality_status",
          "label": "Qualité d’allocation"
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
      "id": "finops-budget-upsert",
      "label": "Créer ou modifier un budget",
      "path": "/v1/finops/budgets/upsert",
      "method": "POST",
      "body": [
        "Opérateur",
        {
          "name": "dimension",
          "label": "Dimension",
          "required": true
        },
        {
          "name": "target",
          "label": "Cible",
          "required": true
        },
        {
          "name": "period_start",
          "label": "Début de période",
          "type": "date",
          "required": true
        },
        {
          "name": "period_end",
          "label": "Fin de période",
          "type": "date",
          "required": true
        },
        {
          "name": "currency",
          "label": "Devise ISO-4217",
          "required": true
        },
        {
          "name": "amount",
          "label": "Montant",
          "type": "number",
          "required": true
        },
        {
          "name": "warning_threshold_percent",
          "label": "Seuil d’alerte (%)",
          "type": "number",
          "required": true
        },
        {
          "name": "owner",
          "label": "Propriétaire",
          "required": true
        }
      ]
    },
    {
      "id": "finops-budgets",
      "label": "Lister les budgets",
      "path": "/v1/finops/budgets",
      "method": "GET",
      "query": [
        {
          "name": "dimension",
          "label": "Dimension"
        },
        {
          "name": "target",
          "label": "Cible"
        },
        {
          "name": "currency",
          "label": "Devise"
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
      "id": "finops-period-close",
      "label": "Clôturer une période financière",
      "path": "/v1/finops/periods/close",
      "method": "POST",
      "body": [
        "Opérateur",
        {
          "name": "period_start",
          "label": "Début de période",
          "type": "date",
          "required": true
        },
        {
          "name": "period_end",
          "label": "Fin de période",
          "type": "date",
          "required": true
        },
        {
          "name": "currency",
          "label": "Devise ISO-4217",
          "required": true
        }
      ]
    },
    {
      "id": "finops-periods",
      "label": "Lister les périodes financières",
      "path": "/v1/finops/periods",
      "method": "GET",
      "query": [
        {
          "name": "status",
          "label": "Statut"
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
      "id": "finops-report-generate",
      "label": "Générer un showback / chargeback",
      "path": "/v1/finops/reports/generate",
      "method": "POST",
      "body": [
        "Opérateur",
        {
          "name": "kind",
          "label": "Type de rapport",
          "type": "select",
          "options": [
            "showback",
            "chargeback"
          ],
          "required": true
        },
        {
          "name": "period_start",
          "label": "Début de période",
          "type": "date",
          "required": true
        },
        {
          "name": "period_end",
          "label": "Fin de période",
          "type": "date",
          "required": true
        },
        {
          "name": "group_by",
          "label": "Regroupement",
          "required": true
        },
        {
          "name": "currency",
          "label": "Devise ISO-4217",
          "required": true
        },
        {
          "name": "chargeback_markup_percent",
          "label": "Marge chargeback (%)",
          "type": "number",
          "defaultValue": "0"
        }
      ]
    },
    {
      "id": "finops-report-get",
      "label": "Consulter un rapport financier",
      "path": "/v1/finops/reports/get",
      "method": "GET",
      "query": [
        {
          "name": "report_id",
          "label": "ID rapport",
          "required": true
        }
      ]
    },
    {
      "id": "finops-reports",
      "label": "Lister les rapports financiers",
      "path": "/v1/finops/reports",
      "method": "GET",
      "query": [
        {
          "name": "kind",
          "label": "Type de rapport"
        },
        {
          "name": "currency",
          "label": "Devise"
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
      "id": "finops-report-export",
      "label": "Exporter un rapport financier",
      "path": "/v1/finops/reports/export",
      "method": "GET",
      "query": [
        {
          "name": "report_id",
          "label": "ID rapport",
          "required": true
        },
        {
          "name": "format",
          "label": "Format",
          "type": "select",
          "options": [
            "json",
            "csv"
          ],
          "defaultValue": "json"
        }
      ]
    },
    {
      "id": "finops-anomalies",
      "label": "Lister les anomalies de coûts",
      "path": "/v1/finops/anomalies",
      "method": "GET",
      "query": [
        {
          "name": "severity",
          "label": "Sévérité"
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
      "id": "finops-forecasts",
      "label": "Lister les prévisions de coûts",
      "path": "/v1/finops/forecasts",
      "method": "GET",
      "query": [
        {
          "name": "dimension",
          "label": "Dimension"
        },
        {
          "name": "target",
          "label": "Cible"
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
