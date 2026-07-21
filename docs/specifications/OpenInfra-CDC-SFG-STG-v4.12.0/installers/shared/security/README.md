# Sécurité d'installation et des flux runtime

Les secrets sont générés automatiquement, stockés dans le mécanisme sécurisé validé pour l'environnement et masqués dans les journaux. Les certificats internes sont générés ou intégrés à la PKI d'entreprise selon le profil d'installation.

## Règles obligatoires

- Aucun mot de passe, token, clé privée ou secret LDAP/IPA n'est accepté en clair dans `install.ini`, `.env`, `openinfra.conf`, les journaux ou les rapports.
- Les secrets et certificats sont déclarés par référence `env:`, `file://`, `vault://`, `sops://` ou `kms://`.
- Pro/Enterprise imposent TLS 1.3 et mTLS sur les flux frontend-backend, agent-backend et backend-backend.
- Lite reste local et loopback-only.
- Le backend n'authentifie pas directement les opérateurs humains ; il valide des jetons applicatifs et applique RBAC/audit.
- Le frontend porte l'authentification opérateur, y compris LDAP/IPA lorsque l'édition le permet.
- L'agent utilise un mécanisme technique d'enrôlement et un certificat client, sans accès direct à PostgreSQL.

## Chemins sécurisés

- Configuration runtime : `/opt/openinfra/config/openinfra.conf`.
- Chemin compatible : `/etc/openinfra/openinfra.conf`, via symlink `/etc/openinfra -> /opt/openinfra/config`.
- Verrou : `/opt/openinfra/config/.openinfra-installed.lock`.
- Certificats : `/opt/openinfra/config/tls/` et `/opt/openinfra/config/trust/` ou coffre externe référencé.
