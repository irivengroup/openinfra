## v0.29.78 — Profils protocoles Discovery sécurisés

L'incrément v0.29.78 étend P14 / EPIC-1403 sans modifier la séparation Clean Architecture existante. Le domaine porte les règles SNMP/SSH/WinRM, l'application orchestre l'authentification RBAC et l'audit, les repositories JSON/PostgreSQL persistent les profils, et les interfaces CLI/API/Web exposent uniquement des représentations publiques masquant les références sensibles.

La persistance PostgreSQL est additive via `0034_discovery_protocol_profiles.sql`, avec partitionnement par tenant, contraintes de sécurité et index actifs adaptés aux recherches par protocole et scope.
