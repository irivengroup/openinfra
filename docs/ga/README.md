# Documentation GA OpenInfra

Version cible : `0.32.4`  
Périmètre : `P18 / EPIC-1804`

Cette documentation constitue le point d’entrée opérationnel de la version GA candidate. Elle complète le CDC et la roadmap sans les remplacer. Les contrats d’API font foi dans `docs/api/openapi.yaml` et les règles d’installation natives dans `installers/`.

## Parcours par rôle

| Rôle | Document principal | Objectif |
|---|---|---|
| Administrateur plateforme | [Guide administrateur](ADMINISTRATION.md) | Identités, rôles, quotas, audit et base de données |
| Opérateur métier | [Guide utilisateur](USER_GUIDE.md) | Navigation, saisie, recherche et traitements longs |
| Intégrateur | [Guide API](API_GUIDE.md) | Authentification, pagination, erreurs et exemples HTTP |
| Ingénieur plateforme | [Installation](INSTALLATION.md) | Compose local, installation native et contrôles post-installation |
| SRE | [Exploitation](OPERATIONS.md) | Supervision, sauvegardes, maintenance et incidents |
| Responsable PRA/PCA | [PRA et PCA](DISASTER_RECOVERY.md) | RPO/RTO, PITR, bascule et exercices |
| Release manager | [Mise à niveau](UPGRADE.md) | Précontrôles, migration, validation et retour arrière |
| Support N2/N3 | [Diagnostic](TROUBLESHOOTING.md) | Collecte de preuves et résolution structurée |

## Matrice des éditions

| Capacité | Lite | Pro | Enterprise |
|---|---:|---:|---:|
| Déploiement monolithique | oui | non | non |
| Backend et web séparés | non | oui | oui |
| Authentification LDAP/IPA | non | oui | oui |
| Réplication PostgreSQL | non requise | supportée | requise pour la cible HA |
| Proxy collectors régionaux | non | non | oui |
| Multisite distribué | non | centralisé | distribué |
| Stockage objet asynchrone S3 | non requis | optionnel | recommandé |

Les feature gates et quotas restent contrôlés par le runtime. Une fonctionnalité masquée par l’édition ne doit pas être contournée par appel direct à l’API.

## Sources de vérité documentaires

1. `docs/ga/` : procédures GA exécutables.
2. `docs/api/openapi.yaml` : contrat HTTP public.
3. `docs/runbooks/` : procédures techniques détaillées par composant.
4. `docs/architecture/` : décisions et invariants techniques.
5. `docs/specifications/` : CDC, roadmap et matrices contractuelles.
6. `VALIDATION-REPORT.md` : état réel des validations de la livraison.

## Contrôles de cohérence

La documentation GA est validée par :

```bash
PYTHONPATH=src:. python scripts/validate_ga_documentation.py --project-root . --enforce
```

Le contrôle vérifie notamment :

- la version de chaque guide ;
- la présence des sections obligatoires ;
- la résolution des liens Markdown relatifs ;
- l’équilibre des blocs de code ;
- l’existence des commandes CLI documentées ;
- l’existence des opérations HTTP citées dans OpenAPI ;
- l’absence de marqueur de contenu inachevé ;
- la présence du validateur dans la CI.
