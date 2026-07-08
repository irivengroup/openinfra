### v0.29.52 — progression opérable des imports massifs reprenables

- Ajout du modèle domaine `BulkImportProgress` dérivé des checkpoints et rapports bulk persistés.
- Ajout du service applicatif `GenericImportService.get_bulk_progress`.
- Ajout de la commande CLI `openinfra import bulk-progress`.
- Ajout de l’endpoint API `GET /api/v1/imports/bulk-progress`.
- Publication du contrat dans le discovery document et dans `docs/api/openapi.yaml`.
- Ajout du module web **Imports / Exports** et de l’opération **Progression import massif**.
- Ajout d’un smoke CI JSON qui exécute un bulk import, récupère son `job_id` et vérifie la progression.
- Ajout des tests service, CLI, API, OpenAPI, discovery, frontend et validateur.
- Alignement CDC `REQ-00795` / `TST-WEB-096` et roadmap `TST-P13-BULK-IMPORT-PROGRESS`.

### v0.29.50 — administration éditions et quotas API/UI

- Exposition des politiques d’édition, des feature gates et des quotas runtime dans API, OpenAPI et portail web.
