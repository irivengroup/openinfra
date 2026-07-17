# Rapport de validation — OpenInfra Python POO v0.34.0

## Objet

La version **0.34.0** livre l’intégration d’identité avancée et le support multi-SGBD demandé, sans rendre Docker nécessaire en production :

- authentification SAML 2.0 ;
- LDAP/IPA avancé ;
- Team Sync LDAP, OAuth, Auth Proxy signé et Okta ;
- Oracle Database optionnel, PostgreSQL restant le backend par défaut ;
- déploiement Linux natif complet sous systemd ;
- correction des permissions du jeton bootstrap runtime ;
- configuration de confiance et secrets exclusivement côté serveur.

## Architecture et sécurité

- L’authentification fédérée reste distincte de l’autorité RBAC OpenInfra.
- Les certificats SAML, mappings, endpoints fournisseurs et jetons ne sont jamais acceptés depuis les requêtes clientes.
- Les réponses SAML sont validées cryptographiquement via `python3-saml`.
- LDAP prend en charge LDAPS, StartTLS, CA, pagination, limites, timeouts, referrals contrôlés et groupes imbriqués bornés.
- Team Sync est idempotent et ne retire que les appartenances gérées par la source concernée.
- Les paginations OAuth et Okta sont confinées à l’origine HTTPS configurée.
- Les snapshots Auth Proxy sont des fichiers normaux, non symboliques, signés HMAC.
- Le jeton bootstrap est stocké hors `.env`, dans un répertoire `0700` et un fichier `0400`, tous deux attribués au compte runtime effectif.
- Le parseur de mappings SAML sépare le DN LDAP et les rôles au dernier `=`, ce qui accepte les groupes de type `cn=...,ou=...`.
- Les profils Okta non structurés sont rejetés proprement sans exception non contrôlée.

## Persistance et migrations

- PostgreSQL reste sélectionné lorsque `OPENINFRA_DATABASE_BACKEND` est absent.
- Oracle n’est activé que par configuration explicite.
- Chaîne PostgreSQL : **57 migrations**.
- Dernière migration : `0057_federated_identity_team_sync.sql`.
- La migration `0057` est transactionnelle et partitionne par hash de `tenant_id` les états d’identité fédérée et Team Sync.
- Oracle dispose d’un pool `python-oracledb`, d’un Unit of Work, d’un contrôle optimiste, d’un readiness check et de migrations dédiées.

## Déploiement serveur standard

Les assets suivants sont packagés et validés :

- `openinfra-runtime-secrets.service` ;
- `openinfra-migrate.service` ;
- `openinfra.service` ;
- `openinfra-web.service` ;
- `openinfra-team-sync.service` ;
- `openinfra-team-sync.timer` ;
- `openinfra-agent.service` pour les proxy collectors Enterprise.

Le runtime natif lit `/opt/openinfra/config/openinfra.conf`, les secrets `file://` et le backend sélectionné. Docker reste uniquement un environnement local facultatif.

## Validations exécutées

| Contrôle | Résultat |
|---|---:|
| Tests unitaires, architecture et performance | **714/714 PASS** |
| Tests d’intégration — 168 fichiers | **722/722 PASS** |
| Total Python | **1 436/1 436 PASS** |
| Tests de renforcement identité/Oracle/systemd/gates | **25/25 PASS** |
| Couverture globale | **46 348 lignes, 1 141 non couvertes, 98 % PASS** |
| `coverage report --fail-under=98` | **PASS** |
| Ruff format | **442 fichiers PASS** |
| Ruff lint | **PASS** |
| mypy strict | **127 modules PASS** |
| Bandit | **0 résultat, 0 erreur PASS** |
| Security Gate | **PASS** |
| Tests frontend | **79/79 PASS** |
| ESLint / contrat statique | **PASS** |
| WCAG 2.2 AA | **PASS** |
| Build Vite et budget initial | **PASS** |
| Audit npm | **0 vulnérabilité** |
| OpenAPI produit et CDC | **PASS** |
| Documentation GA | **PASS** |
| CDC | **845 exigences, 529 entités PASS** |
| Roadmap | **23 phases, 137 epics, 12 gates, 117 tests PASS** |
| Build wheel et sdist | **PASS** |
| `twine check` | **PASS** |
| Vérification du contenu wheel/sdist | **PASS** |
| Smoke assets systemd natifs | **PASS** |
| Installation du wheel hors dépôt | **PASS** |
| Smoke du wheel installé | **PASS** |

Le smoke du wheel installé confirme notamment :

- version `0.34.0` ;
- 57 migrations PostgreSQL ;
- dernière migration `0057_federated_identity_team_sync.sql` ;
- deux routes d’identité avancée ;
- runtime Oracle et identité avancée packagé ;
- cinq commandes console publiques ;
- 20 assets runtime ;
- GATE-10 présent.

## Non-régression visuelle

Le thème n’a pas été modifié. Les deux copies CSS conservent le SHA-256 :

```text
fb7feabe378613ac41efb18db94b0d95a8faa916b6f782c9fd0ea2b0d8e9fcf4
```

## Limites de qualification externe

Les validations suivantes nécessitent une infrastructure externe et ne sont pas revendiquées localement :

- connexion à une instance Oracle réelle ;
- échange avec un fournisseur SAML réel ;
- synchronisation contre un annuaire LDAP/IPA, un OAuth provider ou un tenant Okta réel ;
- démarrage des unités sur un hôte systemd réel ;
- démarrage Docker réel.

`pip-audit` a été lancé mais n’a pas pu joindre `pypi.org` en raison d’un échec DNS. Aucun résultat d’audit Python en ligne n’est donc revendiqué. Bandit, Security Gate et l’audit npm sont exécutés et verts.

Le lanceur agrégé `scripts/quality_gate.py` a dépassé la fenêtre locale de cinq minutes après plusieurs sous-gates verts. Les validations directes listées ci-dessus constituent les résultats effectivement terminés et contrôlés.
