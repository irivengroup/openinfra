# Pratiques enterprise retenues

## Architecture et urbanisation

OpenInfra doit conserver une architecture API-first, modulaire, testable, observable, sécurisée et compatible déploiement progressif par édition.

Pratiques retenues :

- modular monolith first pour cohérence domaine ;
- extraction possible vers composants distribués uniquement lorsque justifiée ;
- séparation backend, frontend, agents, workers et connecteurs ;
- contrats API versionnés ;
- outbox pattern pour synchronisations fiables ;
- migrations versionnées ;
- compatibilité ascendante ;
- feature gates déclaratifs ;
- absence de contournement direct de la base.

## Sécurité

Pratiques retenues :

- Zero Trust interne ;
- RBAC/ABAC ;
- SSO OIDC/SAML ;
- MFA via IdP ;
- mTLS agents ;
- secrets externalisés ;
- chiffrement en transit ;
- audit immuable ;
- contrôles OWASP ASVS pour web/API ;
- scan secrets, SCA, SAST, container scanning ;
- séparation des comptes techniques.

## Données

Pratiques retenues :

- Source of Truth gouvernée ;
- qualité de données mesurée ;
- règles de certification ;
- traçabilité par attribut critique ;
- partitionnement natif PostgreSQL ;
- hot/warm/cold ;
- séparation OLTP/analytique ;
- réplicas de lecture ;
- pagination obligatoire ;
- requêtes bornées ;
- audits et historiques partitionnés.

## Exploitation

Pratiques retenues :

- packaging par édition ;
- noms systemd invariants ;
- installateurs idempotents ;
- sauvegarde PITR ;
- runbooks PRA/PCA ;
- observabilité OpenTelemetry/Prometheus/Grafana/Loki ;
- tests de restauration ;
- tests failover ;
- journaux sans secrets.

## Qualité

Pratiques retenues :

- CI/CD multi-éditions ;
- tests unitaires, intégration, sécurité, performance, compatibilité, migration et packaging ;
- matrice de traçabilité exigences → cas d'usage → tests ;
- gates Go/No-Go ;
- non-régression CLI/API/UI ;
- validation documentaire automatisée.

