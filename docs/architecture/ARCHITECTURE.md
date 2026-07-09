## v0.29.77 — Correctif qualité et sécurité PostgreSQL DCIM

L’incrément v0.29.77 ne modifie pas l’architecture fonctionnelle v0.29.76. Il durcit l’implémentation infrastructure PostgreSQL DCIM en supprimant la construction de requête par fragment SQL interpolé dans la liste des racks. Le repository utilise désormais des requêtes statiques paramétrées, ce qui conserve la séparation hexagonale domaine/application/infrastructure et rend le contrat SQL plus facilement auditable par Bandit.

Le pipeline qualité est réaligné sur Ruff format, Ruff lint et Bandit sans exemption `nosec` supplémentaire. Les exceptions N802 nécessaires aux handlers HTTP `do_GET`, `do_POST`, etc. sont portées par la configuration Ruff, car ces noms sont imposés par `BaseHTTPRequestHandler`.
