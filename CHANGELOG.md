### v0.29.60 — guides opérables de migration données

- Ajout du domaine `MigrationGuide` et `MigrationGuideStep`.
- Ajout service `GenericImportService.get_migration_guide`.
- Ajout CLI `openinfra import migration-guide`.
- Ajout API `GET /api/v1/imports/migration-guide`.
- Publication discovery, OpenAPI et portail web `Imports / Exports > Guide migration données`.
- Ajout runbook `IMPORTS_MIGRATION_GUIDES.md`.
- Alignement CDC `REQ-00803` et roadmap `TST-P13-DATA-MIGRATION-GUIDES`.

### v0.29.59 — rollback conflict-aware des imports massifs

- Ajout du domaine de rollback d’import massif avec plan dry-run, actions `restore-previous-version`, `retire-created`, `skip` et `conflict`.
- Ajout du service applicatif `GenericImportService.bulk_import_rollback`, protégé par `rsot.write`, avec détection de modifications concurrentes.
- Ajout CLI/API/OpenAPI/discovery et portail web Imports / Exports pour planifier ou appliquer un rollback d’import massif.
- Les objets créés par import sont mis en retrait (`status=retired`) sans suppression physique ; les objets modifiés sont restaurés par nouvelle révision RSOT depuis le snapshot précédent.
- Ajout de tests service, CLI, API HTTP, OpenAPI, discovery et frontend pour verrouiller le dry-run par défaut, l’application, les conflits et l’absence de suppression destructive.

### v0.29.58 — préparation intégration future OpenService CMDB

- Ajout du fournisseur ITSM externe `openservice`, réservé aux éditions Pro et Enterprise, sans ticketing natif OpenInfra.
- Ajout CLI/API/OpenAPI/discovery pour valider un profil OpenService et générer un plan de synchronisation CMDB depuis RSOT.
- Verrouillage explicite : OpenService possède sa propre interface web ; aucune opération OpenService n’est ajoutée au portail `openinfra-web`.
- Préparation neutre compatible avec le futur CDC OpenService, sans figer le périmètre fonctionnel OpenService dans OpenInfra.
- Non-régression ServiceNow, Jira Assets, GLPI Inventory, Freshservice Assets, RSOT et thème Bootstrap conservée.

### v0.29.57 — connecteurs externes GLPI Inventory et Freshservice Assets

- Ajout des fournisseurs `glpi` et `freshservice` dans le domaine `external_itsm`, avec alias contrôlés.
- Ajout CLI/API/UI/OpenAPI/discovery pour valider les profils GLPI/Freshservice et générer des plans de synchronisation d’assets depuis RSOT.
- Validation sécurité conservée : URL HTTPS obligatoire, aucun credential embarqué, secrets uniquement par référence, aucun ticketing natif.
- Non-régression ServiceNow, Jira Assets, RSOT et thème Bootstrap conservée.

### v0.29.56 — connecteur externe Jira Service Management Assets

- Ajout du fournisseur `jira_service_management` dans le domaine `external_itsm`, avec alias `jira`, `jsm`, `jira-assets` et `jira-service-management`.
- Ajout CLI/API/UI/OpenAPI/discovery pour valider un connecteur Jira Assets et générer un plan de synchronisation d’assets depuis RSOT.
- Validation sécurité conservée : URL HTTPS obligatoire, aucun credential embarqué, secrets uniquement par référence, aucun ticketing natif.
- Non-régression ServiceNow, RSOT et thème Bootstrap conservée.

### v0.29.56 — connecteur externe ServiceNow et corrections thème Bootstrap

- Ajout du domaine `external_itsm` pour représenter les connecteurs ITSM externes sans ticketing natif.
- Ajout du service applicatif `ExternalItsmIntegrationService`.
- Ajout CLI/API/UI/OpenAPI/discovery pour les politiques ITSM externes et les flux ServiceNow.
- Validation ServiceNow : instance HTTPS obligatoire, secrets uniquement par référence, tables CI autorisées.
- Plan de synchronisation CI ServiceNow déterministe depuis RSOT avec mapping minimal obligatoire.
- Correction UI : les boutons de soumission restent `btn btn-primary` et Bootstrap est surchargé en turquoise `#24d8ab`.
- Correction UI : le bloc runtime utilise uniquement une couleur de texte `#003D8F`, sans fond ni bordure dédiés.

### v0.29.56 — RSOT canonique, alias ITRM dépréciés et correction Ruff/UI

- Renommage public de `ITRM (IT Ressource Management)` en `RSOT (Ressource Source of Truth)`.
- Publication canonique de `openinfra rsot`, `/api/v1/rsot/*`, `rsot:*`, `core_rsot`, composant web **RSOT** et groupe de recherche globale `rsot`.
- Conservation transitoire des alias `itrm`, `sot` et `ri`, documentés comme dépréciés pour retrait progressif.
- Bloc statut runtime web rendu en bleu léger/discret pour le distinguer des composants de menu.
- Boutons de soumission des formulaires web rendus en bleu turquoise dédié, sans dépendre de `btn-primary`.
- Correction du gate CI `ruff format --check src tests scripts docker` ; les fichiers concernés sont formatés et `ruff check` passe également.

### v0.29.53 — exports massifs streaming par chunks signés

- Ajout `openinfra export artifact-chunk` pour lire un artefact exporté signé par offset/taille bornée.
- Ajout `GET /api/v1/exports/artifact-chunk` retournant `content_base64`, `chunk_sha256`, `next_offset`, `final_chunk` et métadonnées d’artefact après vérification SHA-256 + HMAC-SHA256 complète.
- Ajout de l’opération portail `Imports / Exports > Chunk export signé`.
- OpenAPI, discovery, CDC et roadmap alignés sur P13 / EPIC-1302.
- Non-régression : le téléchargement complet `/api/v1/exports/artifact` et `openinfra export artifact` restent inchangés.

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
