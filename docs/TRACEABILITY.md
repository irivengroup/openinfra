## v0.29.77 — Traçabilité correctifs CI Ruff/Bandit

- `REQ-00818` couvre la suppression du risque signalé Bandit B608 sur la requête PostgreSQL DCIM de liste des racks.
- `TST-WEB-117` couvre Ruff format, Ruff check, Bandit et le test de régression source sur `PostgreSQLDcimRepository.list_racks_in_room`.
- La livraison conserve les exigences v0.29.76 : `REQ-00817`, `TST-WEB-116` et `TST-P14-DCIM-SITE-DEPENDENCIES-RACKS-COUNTRIES`.
