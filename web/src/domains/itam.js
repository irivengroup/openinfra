const moduleDefinition = {
  "id": "itam",
  "label": "IT Asset Management",
  "shortLabel": "ITAM",
  "icon": "asset",
  "operations": [
    {
      "id": "itam-organizations",
      "label": "Lister les organisations",
      "path": "/v1/itam/organizations",
      "method": "GET",
      "fields": [
        "Inclure retirées"
      ]
    },
    {
      "id": "itam-organization",
      "label": "Voir une organisation",
      "path": "/v1/itam/organization",
      "method": "GET",
      "fields": [
        "Organisation"
      ]
    },
    {
      "id": "itam-organization-create",
      "label": "Créer une organisation",
      "path": "/v1/itam/organization/create",
      "method": "POST",
      "fields": [
        "Code organisation",
        "Opérateur",
        "Raison sociale",
        "N° immatriculation",
        "Identifiant fiscal / TVA",
        "Pays",
        "Ville",
        "Adresse siège",
        "Email contact",
        "Contact support"
      ]
    },
    {
      "id": "itam-organization-update",
      "label": "Modifier une organisation",
      "path": "/v1/itam/organization/update",
      "method": "POST",
      "fields": [
        "Organisation",
        "Opérateur",
        "Raison sociale",
        "Nom d’usage",
        "N° immatriculation",
        "Identifiant fiscal / TVA",
        "Pays",
        "Ville",
        "Adresse siège",
        "Email contact",
        "Contact support",
        "Statut",
        "Description"
      ]
    },
    {
      "id": "itam-organization-delete",
      "label": "Retirer une organisation",
      "path": "/v1/itam/organization/delete",
      "method": "POST",
      "fields": [
        "Organisation",
        "Opérateur"
      ]
    },
    {
      "id": "itam-partners",
      "label": "Lister les fournisseurs et supports",
      "path": "/v1/itam/partners",
      "method": "GET",
      "fields": [
        "Organisation",
        "Type partenaire",
        "Inclure retirés"
      ]
    },
    {
      "id": "itam-partner",
      "label": "Voir un partenaire",
      "path": "/v1/itam/partner",
      "method": "GET",
      "fields": [
        "Organisation",
        "Partenaire"
      ]
    },
    {
      "id": "itam-partner-create",
      "label": "Créer un partenaire",
      "path": "/v1/itam/partner/create",
      "method": "POST",
      "fields": [
        "Organisation",
        "Code partenaire",
        "Type partenaire",
        "Opérateur",
        "Raison sociale",
        "Nom d’usage",
        "N° immatriculation",
        "Identifiant fiscal / TVA",
        "Pays",
        "Ville",
        "Adresse siège",
        "Email contact",
        "Téléphone",
        "Contact support",
        "Site web",
        "Statut",
        "Description"
      ]
    },
    {
      "id": "itam-partner-update",
      "label": "Modifier un partenaire",
      "path": "/v1/itam/partner/update",
      "method": "POST",
      "fields": [
        "Organisation",
        "Partenaire",
        "Opérateur",
        "Type partenaire",
        "Raison sociale",
        "Nom d’usage",
        "N° immatriculation",
        "Identifiant fiscal / TVA",
        "Pays",
        "Ville",
        "Adresse siège",
        "Email contact",
        "Téléphone",
        "Contact support",
        "Site web",
        "Statut",
        "Description"
      ]
    },
    {
      "id": "itam-partner-delete",
      "label": "Retirer un partenaire",
      "path": "/v1/itam/partner/delete",
      "method": "POST",
      "fields": [
        "Organisation",
        "Partenaire",
        "Opérateur"
      ]
    },
    {
      "id": "itam-tenants",
      "label": "Lister les tenants",
      "path": "/v1/itam/tenants",
      "method": "GET",
      "fields": [
        "Inclure retirés"
      ]
    },
    {
      "id": "itam-tenant-create",
      "label": "Créer un tenant",
      "path": "/v1/itam/tenant/create",
      "method": "POST",
      "fields": [
        "Organisation",
        "Code tenant",
        "Opérateur",
        "Nom tenant",
        "Statut",
        "Tenant par défaut",
        "Description"
      ]
    },
    {
      "id": "itam-tenant-update",
      "label": "Modifier un tenant",
      "path": "/v1/itam/tenant/update",
      "method": "POST",
      "fields": [
        "Organisation",
        "Tenant à modifier",
        "Opérateur",
        "Nom tenant",
        "Statut",
        "Tenant par défaut",
        "Description"
      ]
    },
    {
      "id": "itam-tenant-delete",
      "label": "Retirer un tenant",
      "path": "/v1/itam/tenant/delete",
      "method": "POST",
      "fields": [
        "Organisation",
        "Tenant à retirer",
        "Opérateur"
      ]
    },
    {
      "id": "itam-support-profile",
      "label": "Profil support actif",
      "path": "/v1/itam/support-profile",
      "method": "GET",
      "fields": [
        "Numéro d’actif"
      ]
    },
    {
      "id": "itam-support-coverage",
      "label": "Couverture support actif",
      "path": "/v1/itam/support-coverage",
      "method": "GET",
      "fields": [
        "Numéro d’actif",
        "Date de référence"
      ]
    },
    {
      "id": "itam-register-manufacturer",
      "label": "Déclarer garantie constructeur",
      "path": "/v1/itam/support-profile/manufacturer",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Numéro d’actif",
        "Constructeur accrédité",
        "Référence garantie",
        "Niveau garantie",
        "Début garantie",
        "Fin garantie",
        "Référence support",
        "Niveau support",
        "Contact support"
      ]
    },
    {
      "id": "itam-add-third-party",
      "label": "Ajouter support tiers",
      "path": "/v1/itam/support-profile/third-party",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Numéro d’actif",
        "Support tiers accrédité",
        "Référence contrat",
        "Niveau support",
        "Début support",
        "Fin support",
        "Contact support",
        "Statut",
        "Notes"
      ]
    },
    {
      "id": "itam-software-license",
      "label": "Licence logicielle",
      "path": "/v1/itam/software-license",
      "method": "GET",
      "fields": [
        "Référence licence"
      ]
    },
    {
      "id": "itam-software-compliance",
      "label": "Conformité licence",
      "path": "/v1/itam/software-license/compliance",
      "method": "GET",
      "fields": [
        "Référence licence",
        "Date de référence"
      ]
    },
    {
      "id": "itam-register-software",
      "label": "Déclarer licence logicielle",
      "path": "/v1/itam/software-license",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Produit",
        "Éditeur accrédité",
        "Référence licence",
        "Référence contrat",
        "Métrique",
        "Quantité achetée",
        "Quantité assignée",
        "Début droit",
        "Fin droit",
        "Version",
        "Statut",
        "Propriétaire",
        "Notes"
      ]
    },
    {
      "id": "itam-update-license-assignment",
      "label": "Mettre à jour affectation licence",
      "path": "/v1/itam/software-license/assignment",
      "method": "POST",
      "fields": [
        "Opérateur",
        "Référence licence",
        "Quantité assignée",
        "Notes"
      ]
    },
    {
      "id": "finops-rule-create",
      "label": "Créer une règle d’allocation",
      "path": "/v1/finops/allocation-rules/create",
      "method": "POST",
      "fields": [
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
      "fields": [
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
      "fields": [
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
      "fields": [
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
      "fields": [
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
      "fields": [
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
      "fields": [
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
      "fields": [
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
      "fields": [
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
      "fields": [
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
      "fields": [
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
      "fields": [
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
      "fields": [
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
      "fields": [
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
      "fields": [
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
      "fields": [
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
      "fields": [
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
      "fields": [
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
