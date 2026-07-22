# Rapport de certification locale — OpenInfra Python POO v0.34.9

**Date de qualification :** 22 juillet 2026
**Candidat :** `openinfra-0.34.9-validation-candidate`
**Référentiels actifs :** CDC `4.12.0`, roadmap `2.5.0`, phase `P25`, release `REL-15`, gate `GATE-14`

## Décision

L'incrément fonctionnel OpenInfra **0.34.9** et sa campagne Python complète sont **GO**.
La déclaration d'un bundle `final-candidate` reste **NO-GO** tant que les contrôles locaux obligatoires rendus indisponibles par le registre d'outillage ne sont pas rejoués sur le SHA source final : Ruff, mypy, Bandit, Twine, ESLint JSX, build Vite et audits npm/Python.

Cette décision est fail-closed : aucune indisponibilité d'outil ou de registre n'est transformée en résultat favorable.

## Périmètre fonctionnel 0.34.9

Cette version conserve toutes les capacités certifiées jusqu'à 0.34.8 et matérialise la synchronisation transactionnelle IPAM vers DNS/DHCP exigée par `TST-FUNC-0008` :

- journal de saga durable et idempotent ;
- verrouillage transactionnel PostgreSQL et persistance JSON ;
- exécution DNS BIND/nsupdate et PowerDNS ;
- exécution DHCP Kea ;
- capture de l'état fournisseur avant mutation ;
- compensation exacte en ordre inverse ;
- distinction entre échec déterministe et résultat fournisseur incertain ;
- statut `compensation_failed` et réconciliation obligatoire en cas d'incertitude ;
- secrets externalisés, HTTPS obligatoire pour les API, délais bornés et `shell=False` ;
- permission RBAC dédiée `ipam.ddi.sync` ;
- CLI `openinfra ipam ddi-sync` ;
- API `POST /api/v1/ipam/ddi-sync` ;
- OpenAPI principal et CDC, portail React et actifs statiques embarqués ;
- migration `0060_ipam_ddi_execution_journal.sql` avec parité PostgreSQL/Oracle 60/60 ;
- runbook `docs/runbooks/IPAM_DDI_SYNCHRONIZATION.md`.

Le registre GATE-14 classe désormais `TST-FUNC-0008` comme preuve automatisée :

- 667 tests contractuels ;
- 21 preuves automatisées ;
- 598 preuves partielles ;
- 48 qualifications externes ;
- 34 sélecteurs pytest résolus ;
- 59 fichiers de preuve ;
- zéro preuve manquante ;
- zéro exigence N1 non classifiée.

## Correctifs de finalisation

La reprise depuis le checkpoint a détecté deux dépendances implicites au système de fichiers, désormais éliminées :

- `LicenseMaterialStore` réapplique explicitement le mode exact `0700` après création du répertoire sensible ;
- la fixture GATE-11 fixe explicitement le groupe primaire attendu lorsque le volume parent impose un héritage `setgid`.

Les contrôles de production restent stricts : répertoire `0700`, jeton `0400`, fichiers réguliers sans lien symbolique et propriétaire UID/GID attendu. Aucun endpoint, contrat CLI, migration, permission RBAC, comportement de licence ni thème frontend n’est modifié.

## Résultats acquis

| Contrôle | Résultat |
|---|---:|
| Fichiers de tests Python isolés | **284/284 PASS** |
| Suite Python complète | **1 644/1 644 PASS** |
| Échecs | **0** |
| Durée de la campagne reproductible | **235,58 s** |
| Instructions | **49 858** |
| Instructions couvertes | **48 873** |
| Instructions non couvertes | **985** |
| Couverture exacte | **98,024389265514 % PASS** |
| Seuil exact obligatoire | **98,000000000000 %** |
| Gate anti-arrondi | **PASS** — 97,99 % est explicitement rejeté |
| `compileall` | **PASS** |
| Security gate dépôt/CI | **PASS** |
| Quality gate global | **code 0 / PASS** |
| Catalogue PostgreSQL | **60 migrations PASS** |
| Catalogue Oracle | **60 migrations PASS** |
| Génération/parité Oracle | **PASS** |
| OpenAPI principal et CDC | **PASS** |
| Frontend Node sans dépendances externes | **81/81 PASS** |
| Contrat statique des actifs frontend | **PASS** |
| Accessibilité WCAG 2.2 AA statique | **PASS** |
| Build wheel PEP 517 | **PASS** |
| Build sdist PEP 517 | **PASS** |
| Vérification du contenu wheel/sdist | **PASS** |
| Installation du wheel hors dépôt, sans dépendance à l’arbre source | **PASS** |
| Smoke de contenu du wheel avec runtime local qualifié | **PASS** |
| Smoke strict du wheel avec résolution complète des dépendances | **NON REJOUÉ** — registre indisponible |
| Version installée | **0.34.9** |
| Dernière migration installée | **0060_ipam_ddi_execution_journal.sql** |

## Contrôle exact de couverture

Le précédent contrôle `coverage report --fail-under=98` pouvait accepter un taux inférieur à 98 % lorsque l'affichage était arrondi sans décimale. La 0.34.9 ajoute :

- `precision = 8` dans la configuration Coverage.py ;
- `scripts/validate_coverage.py`, qui recalcule le taux à partir des nombres entiers `covered_lines / num_statements` avec `Decimal` ;
- son intégration au quality gate et aux workflows GATE-13/GATE-14 ;
- une non-régression prouvant que 97,99 % échoue et que 98,00 % passe.

Les 284 bases de couverture ne sont fusionnées qu'après réussite de tous les fichiers. Aucun résultat issu d'une campagne interrompue ou échouée n'est incorporé.

## Packaging qualifié

Le wheel installé hors de l'arbre source confirme notamment :

- version distribution et module `0.34.9` ;
- 60 migrations PostgreSQL et 60 migrations Oracle ;
- dernière migration `0060_ipam_ddi_execution_journal.sql` ;
- route `/api/v1/ipam/ddi-sync` ;
- route de recommandation DCIM conservée ;
- actifs runtime et documentation GA ;
- politiques et runbooks GATE-11 à GATE-14 ;
- scripts console publics jusqu'à `openinfra-gate14` ;
- aucune dépendance à l'arbre source.

Les distributions définitives ne seront reconstruites qu'après fermeture des contrôles d'outillage puis gel Git.

## Contrôles localement indisponibles

| Contrôle | Statut | Cause observée |
|---|---|---|
| Ruff format/lint | **NON REJOUÉ SUR LE SHA FINAL** | registre Python interne HTTP 503, aucun binaire local |
| mypy strict | **NON REJOUÉ SUR LE SHA FINAL** | registre Python interne HTTP 503, aucun module local |
| Bandit | **NON REJOUÉ SUR LE SHA FINAL** | registre Python interne HTTP 503, aucun module local |
| Twine check | **NON REJOUÉ** | registre Python interne HTTP 503, aucun module local |
| ESLint JSX | **NON REJOUÉ** | `node_modules` absent, registre npm HTTP 503 |
| Build Vite | **NON REJOUÉ** | Vite absent, registre npm HTTP 503 |
| npm audit | **NON REJOUÉ** | endpoint d'audit du registre npm HTTP 503 |
| pip-audit | **NON REJOUÉ** | module absent et registre Python HTTP 503 |
| Smoke strict du wheel | **NON REJOUÉ** | la résolution de `defusedxml` et des autres dépendances runtime ne peut pas utiliser le registre Python indisponible |

Les tentatives d'installation et leurs erreurs sont conservées hors de l'arbre source dans les preuves de qualification.

## Qualifications externes restant obligatoires

- PostgreSQL réel, concurrence et reprise après interruption ;
- Oracle 19c Enterprise réel ;
- BIND/nsupdate, PowerDNS et Kea réels avec compensation ;
- Docker Compose complet ;
- services systemd ;
- SAML, LDAP/FreeIPA et Team Sync ;
- scans de dépendances avec registres et bases de vulnérabilités accessibles ;
- rapports GATE-11 à GATE-14 associés au véritable commit de publication.

## Commandes de validation de référence

```bash
python -m ruff format --check src tests scripts docker installers
python -m ruff check src tests scripts docker installers
python -m mypy src/openinfra
python -m compileall -q src/openinfra tests scripts docker installers
python -m bandit -q -r src/openinfra
python scripts/security_gate.py --project-root .
python -m pytest -n 4 --dist loadfile --cov-fail-under=98
python -m coverage json -o coverage.json
python scripts/validate_coverage.py --coverage-json coverage.json --minimum 98
python scripts/quality_gate.py
```

```bash
cd web
npm ci --ignore-scripts --no-audit --no-fund
npm test
npm run lint
npm run a11y
npm run a11y:jsx
npm run build
npm audit --audit-level=high --omit=optional
```

```bash
rm -rf build dist
python -m build
python -m twine check dist/*
python scripts/verify_artifact.py dist/*
```

## Décision courante

**GO fonctionnel et tests pour OpenInfra 0.34.9.**
**NO-GO pour déclarer le bundle final-candidate tant que les contrôles d'outillage localement indisponibles ne sont pas rejoués avec succès.**
