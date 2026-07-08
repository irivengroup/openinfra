# OpenInfra v0.29.51

## v0.29.51 — ITAM licences logicielles, contrats et conformité

OpenInfra v0.29.51 ajoute un incrément ITAM aligné sur P12 / EPIC-1205 : gestion des licences logicielles et des contrats associés, avec suivi des quantités achetées/assignées, période d’entitlement, métrique de licence, statut et rapport de conformité.

**Version courante : 0.29.51 — ITAM logiciel exploitable via domaine, service applicatif, repository JSON/PostgreSQL, API HTTP, CLI, OpenAPI et portail web.**

### Points clés

- Déclaration ou mise à jour d’une licence logicielle ITAM.
- Référence de contrat séparée du droit logiciel.
- Métriques supportées : `device`, `user`, `core`, `socket`, `instance`, `subscription`.
- Quantités achetées et assignées contrôlées.
- Rapport de conformité : `compliant`, `over_assigned`, `expired`, `planned`.
- Audit des créations, mises à jour et changements d’affectation.
- Migration PostgreSQL partitionnée par tenant pour les grands volumes.
- Portail web enrichi dans le composant ITAM.

### API ITAM ajoutées

- `POST /api/v1/itam/software-license`
- `GET /api/v1/itam/software-license`
- `POST /api/v1/itam/software-license/assignment`
- `GET /api/v1/itam/software-license/compliance`

### CLI ITAM ajoutée

```bash
openinfra itam register-software-license \
  --tenant default \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --product-name "OpenInfra Enterprise Connector" \
  --vendor "Iriven Labs" \
  --license-reference LIC-001 \
  --metric device \
  --purchased-quantity 100 \
  --assigned-quantity 70 \
  --entitlement-start 2026-01-01 \
  --entitlement-end 2027-01-01

openinfra itam update-license-assignment \
  --tenant default \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --license-reference LIC-001 \
  --assigned-quantity 110

openinfra itam software-license-compliance \
  --tenant default \
  --admin-token "$OPENINFRA_ADMIN_TOKEN" \
  --license-reference LIC-001 \
  --as-of 2026-07-08
```

### Validations recommandées

```bash
python -m compileall -q src tests scripts docker
PYTHONPATH=src:. python scripts/validate_frontend.py
node --check src/openinfra/interfaces/rendering/static/assets/openinfra-web.js
PYTHONPATH=src:. pytest --collect-only --no-cov
PYTHONPATH=src:. pytest tests/integration/test_itam_software_license_services.py --no-cov
PYTHONPATH=src:. pytest tests/integration/test_itam_support_services.py tests/integration/test_itam_support_http_api.py --no-cov
PYTHONPATH=src:. pytest tests/integration/test_http_api.py tests/integration/test_openinfra_web.py tests/integration/test_installer_alignment.py --no-cov
PYTHONPATH=src:. coverage run -m pytest
PYTHONPATH=src:. coverage report --fail-under=98
```
