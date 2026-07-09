## v0.29.79 — Profils protocoles Discovery SNMP/SSH/WinRM sécurisés

- Ajout du domaine `DiscoveryProtocolCredentialProfile`.
- Ajout CRUD service, CLI et API pour profils SNMP/SSH/WinRM.
- Masquage public des références sensibles en `vault://***` et conservation de `secret_materialized=false`.
- Refus de WinRM non chiffré sur le port 5985.
- Liaison des plans discovery locaux à un profil actif avec héritage des limites de débit et de concurrence.
- Ajout de la migration PostgreSQL additive `0034_discovery_protocol_profiles.sql`.
- Ajout des tests domaine, service, CLI, API, migration et web.
