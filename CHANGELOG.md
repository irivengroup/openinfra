### v0.29.51 — ITAM licences logicielles, contrats et conformité

- Ajout du modèle domaine `SoftwareLicenseEntitlement` et du rapport `SoftwareLicenseComplianceReport`.
- Ajout des commandes applicatives de déclaration, mise à jour d’affectation, lecture et conformité des licences logicielles.
- Ajout du stockage JSON `software_license_entitlements`.
- Ajout de la migration PostgreSQL `0028_itam_software_license_entitlements.sql`, partitionnée par tenant avec contraintes et index.
- Ajout des endpoints API `/api/v1/itam/software-license`, `/api/v1/itam/software-license/assignment` et `/api/v1/itam/software-license/compliance`.
- Ajout des commandes CLI `itam register-software-license`, `itam update-license-assignment`, `itam software-license`, `itam software-license-compliance`.
- Ajout des opérations ITAM correspondantes dans le portail web React et runtime statique.
- Mise à jour OpenAPI, README, architecture, UI, CDC, roadmap et traçabilité.
- Ajout des tests service/API/CLI/frontend/régression ITAM logiciel.

### v0.29.50 — administration éditions et quotas API/UI

- Exposition des politiques d’édition, des feature gates et des quotas runtime dans API, OpenAPI et portail web.
