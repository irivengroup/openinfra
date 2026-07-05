# Authentification LDAP/IPA et RBAC groupes

## Architecture

Les éditions Pro et Entreprise doivent intégrer un adaptateur d'identité externe capable de se connecter à LDAP/LDAPS et IPA/FreeIPA. L'adaptateur appartient à la couche infrastructure et expose au domaine une identité normalisée.

```mermaid id="6xwzqu"
flowchart LR
  U[Utilisateur] --> WEB[Frontend React + Bootstrap 5]
  WEB --> API[API OpenInfra]
  API --> AUTH[Service AuthN/AuthZ]
  AUTH --> LDAP[LDAP/LDAPS]
  AUTH --> IPA[IPA/FreeIPA]
  AUTH --> RBAC[RBAC OpenInfra]
  RBAC --> AUDIT[Audit]
```

## Règles techniques

- Le frontend ne gère jamais directement LDAP/IPA.
- Le backend est l'unique composant autorisé à valider l'identité externe.
- Les mots de passe ou secrets de bind ne sont jamais loggés.
- Les certificats TLS LDAP/IPA doivent être validés.
- Les groupes externes sont mappés vers des rôles applicatifs.
- Les sessions et tokens portent les permissions effectives calculées.
- Un changement de mapping doit invalider les sessions concernées selon la politique configurée.

## Configuration minimale Pro/Entreprise

```yaml id="6mdlob"
auth:
  providers:
    ldap_ipa:
      enabled: true
      type: ldap_or_ipa
      url: ldaps://ipa.example.net:636
      base_dn: dc=example,dc=net
      user_filter: "(uid={username})"
      group_filter: "(member={user_dn})"
      tls_required: true
      nested_groups: true
      cache_ttl_seconds: 300
```

## RBAC

Le RBAC doit rester interne à OpenInfra. LDAP/IPA fournit l'identité et l'appartenance groupe ; OpenInfra décide des droits applicatifs.

## Break-glass

Un compte local break-glass peut exister uniquement pour Pro/Entreprise si :

- il est désactivable ;
- il est audité ;
- il est protégé par MFA si disponible ;
- son usage déclenche une alerte ;
- sa rotation est imposée.
