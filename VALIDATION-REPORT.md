# OpenInfra 0.34.22 — rapport de qualification

## Décision

- incrément fonctionnel `TST-WEB-049` : **GO** ;
- checkpoint local reproductible : **GO** ;
- promotion final-candidate/production : **NO-GO** tant que les qualifications externes listées ci-dessous ne sont pas exécutées.

## Objet de l'incrément

OpenInfra 0.34.22 automatise le contrat `TST-WEB-049` relatif au dashboard Bootstrap `openinfra-web`. La preuve démarre un backend de contrôle et le serveur Web réel, injecte trois secrets sentinelles uniquement côté serveur, puis télécharge toutes les surfaces accessibles au navigateur.

Le scénario vérifie :

- Bootstrap 5 servi localement depuis `/assets/bootstrap.min.css` ;
- absence de dépendance CDN dans l'index packagé ;
- exactement un header principal `role="banner"` ;
- présence de la sidebar et du dashboard ;
- présence des neuf domaines canoniques OpenInfra ;
- absence du bearer backend, du DSN et du mot de passe de base dans l'index, les assets statiques et les endpoints publics `/config.json`, `/status` et `/bootstrap.json` ;
- exposition limitée aux états de confiance publics `server-side` et `configured` ;
- absence de mutation fonctionnelle, de migration et de modification du thème approuvé.

## Traçabilité

- test : `tests/integration/test_contract_web_bootstrap_dashboard.py` ;
- sélecteur : `tests/integration/test_contract_web_bootstrap_dashboard.py::test_tst_web_049_dashboard_is_local_unique_domain_complete_and_secret_free` ;
- registre : `docs/release/contract-proof-registry-v4.12.csv` ;
- politique : `docs/release/contract-completeness-promotion-policy.json` ;
- CI : `.github/workflows/contract-completeness.yml`.

## Résultats de qualification

| Contrôle | Résultat |
|---|---:|
| Fichiers de tests Python | 299/299 |
| Tests Python | 1 712/1 712 |
| Échecs | 0 |
| Instructions | 50 621 |
| Instructions couvertes | 49 625 |
| Instructions non couvertes | 996 |
| Couverture exacte | 98,03243713083504 % |
| Seuil obligatoire | >= 98 % — PASS |
| Tests frontend autonomes | 100/100 |
| Migrations PostgreSQL | 60/60 |
| Migrations Oracle | 60/60 |
| Catalogue autonome | 123/123 membres |
| Quality gate global | code 0 |
| GATE-14 | PASS |

## Métriques GATE-14

- 667 tests contractuels ;
- 32 preuves automatisées ;
- 587 preuves partielles ;
- 48 preuves externes ;
- 45 sélecteurs pytest résolus ;
- 78 fichiers d'évidence ;
- zéro preuve manquante ;
- zéro exigence N1 non classifiée.

## Packaging et reproductibilité

- wheel construit deux fois et identique bit à bit ;
- sdist construit deux fois et identique bit à bit sous `SOURCE_DATE_EPOCH` ;
- catalogue migrations construit deux fois et identique bit à bit ;
- vérification exhaustive du contenu du wheel et du sdist ;
- parité SHA-256 des 60 migrations PostgreSQL et 60 migrations Oracle avec les sources ;
- smoke du wheel installé hors de l'arbre source : **PASS** avec le runtime local disponible ;
- préflight du contexte Docker : **PASS**, 29 ressources requises, zéro absente et zéro non couverte.

## Contrôles complémentaires passés

- compilation Python ;
- security gate interne ;
- OpenAPI principal et CDC ;
- validation CDC 4.12 ;
- validation roadmap 2.5 ;
- validation Oracle et parité des catalogues ;
- contrat frontend statique ;
- WCAG 2.2 AA statique ;
- documentation GA ;
- build depuis le sdist extrait ;
- vérification de l'archive autonome des migrations.

## Qualifications externes restantes

Les contrôles suivants ne peuvent pas être déclarés exécutés dans l'environnement courant :

- Ruff, mypy, Bandit, Twine et pip-audit, outils non installés ;
- ESLint/Vite/npm audit, dépendances Node ou registre externe indisponibles ;
- installation strictement vierge avec résolution en ligne de toutes les dépendances Python ;
- Docker Compose réel et scans des images ;
- PostgreSQL live et Oracle 19c Enterprise ;
- fournisseurs DDI réels ;
- unités systemd ;
- fédération SAML, LDAP, OAuth, Auth Proxy et Okta en environnement intégré ;
- qualification de charge et de reprise sur infrastructure de production représentative.

Aucune promotion production ne doit contourner ces preuves externes.
